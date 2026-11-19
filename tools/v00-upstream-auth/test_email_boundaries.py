import base64
import json
import unittest

from dependency import Unavailable, b64url
from email_database import EmailIngressTransaction, EmailTransaction, EmailWitnessTransaction
from email_hold_proxy import EmailState
from email_protocol import decode
from test_bridge import uid
from test_email_bridge import NOW, reply


class BoundaryTests(unittest.TestCase):
    def test_roles_only_expose_their_closed_wrappers(self):
        for cls, forbidden in ((EmailTransaction, ["capture", "context_create", "send_observed", "seed_directory"]),
                               (EmailIngressTransaction, ["complete", "seal_send", "send_observed"]),
                               (EmailWitnessTransaction, ["capture", "seal_send", "complete", "context_read"])):
            instance = object.__new__(cls)
            for method in forbidden:
                with self.subTest(role=cls.__name__, method=method), self.assertRaises(Unavailable):
                    instance.call(method, {})

    def test_all_private_values_are_bound_not_interpolated_into_statement(self):
        instance = object.__new__(EmailTransaction)
        sent = []
        instance.send = sent.append
        instance.line = lambda: '{"http":503,"reason":"SERVICE_UNAVAILABLE"}'
        fields = {"code": "012345", "untrusted": "'); SELECT forbidden(); --"}
        instance.call("seal_verify", fields)
        statement, binding, execute = sent[0].splitlines()
        self.assertEqual(statement, "SELECT v00_email.seal_verify(convert_from(decode($1,'base64'),'UTF8')::jsonb)::text")
        self.assertEqual(execute, "\\g")
        self.assertNotIn("012345", statement)
        encoded = binding.removeprefix("\\bind '").removesuffix("'")
        self.assertEqual(json.loads(base64.b64decode(encoded)), fields)

    def test_saved_result_cannot_change_action_status_or_timestamp(self):
        ref = {"context_id": uid(), "operation_id": uid(), "action": "C01"}
        accepted = {"kind": "email_dispatch_accepted", "acceptedAt": NOW, "challengeId": uid(),
                    "resendNotBeforeAt": "2026-11-04T12:01:00.000Z"}
        saved = reply(accepted, 202, True)
        self.assertEqual(decode("seal_send", saved, ref), "replay")
        for change in ({"historical_http_status": 200}, {"http": 202},
                       {"resolved_at": "2026-11-04T11:59:59.999Z"}, {"extra": True}):
            with self.subTest(change=change), self.assertRaises(Unavailable):
                decode("seal_send", saved | change, ref)
        with self.assertRaises(Unavailable):
            decode("read_operation", {"http": 200, "status": "resolved", "resolved_at": NOW,
                "result": {"kind": "verification_rejected", "reasonCode": "AUTH_VERIFICATION_FAILED"}}, ref)

    def test_email_hold_accepts_only_one_exact_existing_user_request(self):
        email, token = "synthetic@example.invalid", b64url(b"o" * 32)
        state = EmailState(email, token, 7)
        dispatch = "shadow-v00-upstream/" + uid()
        raw = json.dumps({"email": email, "create_user": False}, separators=(",", ":")).encode()
        self.assertFalse(state.accept(raw.replace(b"false", b"true"), dispatch))
        self.assertTrue(state.accept(raw, dispatch))
        self.assertFalse(state.accept(raw, dispatch))
        self.assertIsNone(state._expected)
        snapshot = state.snapshot()
        self.assertEqual(snapshot["accepted_requests"], 1)
        self.assertEqual(snapshot["forwarded_requests"], 0)
        self.assertNotIn(email, json.dumps(snapshot))
        self.assertNotIn(token, json.dumps(snapshot))


if __name__ == "__main__":
    unittest.main()
