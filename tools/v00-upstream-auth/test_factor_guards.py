"""Guard/HTTP-probe tests with doubles. No real DB factor transition is claimed."""
import copy
import unittest
from unittest.mock import patch

from bridge import Bridge, Denied
from dependency import b64url
import factor_probe
from test_bridge import Factory, Tx, Keys, Provider, Cipher, uid


class FactorGuardTests(unittest.TestCase):
    def setUp(self):
        self.ref = {"context_id": uid(), "operation_id": uid(), "action": "AUTH_TOTP_VERIFY",
                    "proof_digest": "b" * 64, "fingerprint": "c" * 64,
                    "comparison_hmac": "d" * 64, "comparison_key_id": "comparison-1"}

    def test_factor_guards_never_complete_or_dispatch_or_create_wrong_code_result(self):
        for http, reason in ((409, "AUTH_CONTEXT_STATE_CONFLICT"), (503, "RECORD_UNAVAILABLE"), (401, "AUTH_REVOKED")):
            with self.subTest(reason=reason):
                tx = Tx([("plan_totp", {"http": http, "reason": reason})])
                provider, cipher = Provider(), Cipher()
                cipher.fail = True  # Any accidental attempt to mint a new cookie fails.
                bridge = Bridge(Factory(tx), provider, Keys(), cipher)
                with self.assertRaises(Denied) as error:
                    bridge.verify_totp(self.ref, uid(), uid(), b64url(b"e" * 32), "012345")
                self.assertEqual((error.exception.http, error.exception.reason), (http, reason))
                self.assertFalse(tx.committed)
                self.assertTrue(tx.closed)
                self.assertEqual([m for m, _ in tx.calls], ["plan_totp"])
                self.assertEqual(provider.calls, 0)


class ClientDouble:
    def __init__(self, status=409):
        self.status, self.posts, self.operations = status, [], []
        self.challenge = uid()
        self.email_result = {"kind": "auth_step_required", "stage": "totp_verification",
                             "challengeId": self.challenge, "challengeIssuedAt": "2026-11-04T12:00:00.000Z",
                             "challengeExpiresAt": "2026-11-04T12:05:00.000Z"}

    def request(self, path, body):
        self.posts.append((path, copy.deepcopy(body)))
        if path == "/api/auth/verify":
            return 200, {}, {}
        return self.status, {"reasonCode": "AUTH_CONTEXT_STATE_CONFLICT"}, {}

    def operation(self, ctx, op, action, recover=False):
        self.operations.append((ctx, op, action, recover))
        if recover:
            return 503, {"reasonCode": "SERVICE_UNAVAILABLE"}, {}
        email = action == "C02"
        return (200 if email else 202), {
            "operationRef": {"authContextId": ctx, "authOperationId": op, "commandType": action},
            "status": "resolved" if email else "unresolved", "result": copy.deepcopy(self.email_result) if email else None,
            "resolvedAt": "2026-11-04T12:00:00.000Z" if email else None}, {}


class FactorProbeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = {"context_id": uid(), "email_challenge_id": uid()}

    def run_probe(self, client, transition=None):
        lines = [{"code": "012345"}, transition or {"transition_observed": True, "evidence_id": "synthetic-transition", "code": "654321"}]
        with patch.object(factor_probe, "bootstrap", return_value=(self.fixture, client)), \
                patch.object(factor_probe, "receive", side_effect=lines), patch.object(factor_probe, "emit") as events:
            result = factor_probe.run({}, "unused-ca", "factor_stale")
        return result, events

    def test_exactly_one_totp_attempt_after_transition_no_retry(self):
        client = ClientDouble()
        report, events = self.run_probe(client)
        self.assertTrue(all(c["passed"] for c in report["checks"]))
        self.assertEqual([path for path, _ in client.posts], ["/api/auth/verify", "/api/auth/totp/verify"])
        request = client.posts[1][1]
        self.assertEqual(request["challengeId"], client.challenge)
        self.assertEqual(request["authContextId"], self.fixture["context_id"])
        for ctx, op, action, _ in client.operations:
            if action == "AUTH_TOTP_VERIFY":
                self.assertEqual((ctx, op), (request["authContextId"], request["authOperationId"]))
        self.assertEqual([c.args[0]["event"] for c in events.call_args_list],
                         ["need_email_code", "factor_guard_ready", "stale_factor_dispatching"])
        self.assertNotIn("654321", str(report))
        self.assertNotIn("654321", str(events.call_args_list))

    def test_unobserved_transition_stops_before_totp(self):
        client = ClientDouble()
        with self.assertRaises(ValueError):
            self.run_probe(client, {"transition_observed": False, "evidence_id": "synthetic", "code": "654321"})
        self.assertEqual(len(client.posts), 1)

    def test_success_or_unavailable_is_not_mislabelled_stale_guard(self):
        for status in (200, 503):
            with self.subTest(status=status):
                client = ClientDouble(status)
                with self.assertRaisesRegex(AssertionError, "stale_version_conflict_no_cookie"):
                    self.run_probe(client)
                self.assertEqual(len(client.posts), 2)
                self.assertFalse(any(recover for _, _, _, recover in client.operations))


if __name__ == "__main__":
    unittest.main()
