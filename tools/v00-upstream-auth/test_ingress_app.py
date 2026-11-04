from email.message import Message
import json
import unittest

from app import App
from bridge import Denied
from controller import Rejection
from dependency import b64url, Unavailable
from ingress import Ingress, intent
from test_bridge import Factory, Tx, Keys, Cipher, uid


class ProofKeys(Keys):
    def proof(self, *_):
        return "b" * 64


class InputTests(unittest.TestCase):
    def setUp(self):
        self.ctx, self.op, self.challenge = uid(), uid(), uid()
        self.body = {"requestSchemaVersion": "v1", "commandType": "C02", "authContextId": self.ctx,
                     "authOperationId": self.op, "challengeId": self.challenge, "code": "012345"}
        self.keys = ProofKeys()

    def test_code_changes_comparison_not_nonsecret_digest(self):
        a = intent(self.keys, self.body, "a" * 64)
        b = intent(self.keys, self.body | {"code": "012346"}, "a" * 64)
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertNotEqual(a["comparison_hmac"], b["comparison_hmac"])
        self.assertNotIn("012345", json.dumps(a))

    def test_action_challenge_and_scope_bound(self):
        baseline = intent(self.keys, self.body, "a" * 64)
        for field, value in (("commandType", "AUTH_TOTP_VERIFY"), ("challengeId", uid()),
                             ("authContextId", uid()), ("authOperationId", uid())):
            with self.subTest(field=field):
                changed = intent(self.keys, self.body | {field: value}, "a" * 64)
                self.assertNotEqual(baseline["fingerprint"], changed["fingerprint"])

    def test_capture_has_no_raw_secret_or_caller_time(self):
        tx = Tx([("capture", {"http": 201, "admission_id": uid(), "created": True})])
        ref = intent(self.keys, self.body, "a" * 64)
        _, proof = Ingress(Factory(tx)).capture(ref)
        fields = tx.calls[0][1]
        self.assertEqual(set(fields), set(ref) | {"executor_id", "executor_proof_digest"})
        self.assertNotIn(proof, json.dumps(fields))
        self.assertTrue(tx.committed)

    def test_capture_replay_does_not_recover_executor_proof(self):
        admission = uid()
        tx = [Tx([("capture", {"http": status, "admission_id": admission, "created": created})])
              for status, created in ((201, True), (200, False))]
        ingress = Ingress(Factory(*tx))
        first, second = (ingress.capture(intent(self.keys, self.body, "a" * 64)) for _ in range(2))
        self.assertEqual(first[0], second[0])
        self.assertNotEqual(first[1], second[1])

    def app(self):
        config = {"fixtures": {"basic": {"context_id": self.ctx, "email": "synthetic@example.invalid",
            "proof": b64url(b"p" * 32), "fixture_token": b64url(b"f" * 32)}}}
        return App(config, self.keys, Cipher(), None, None, lambda: None)

    def test_synthetic_completion_and_provider_management_not_exposed(self):
        for path in ("/__v00__/fixtures/basic/complete", "/api/auth/request", "/api/auth/resend", "/factors"):
            with self.subTest(path=path), self.assertRaises(Rejection) as denied:
                self.app().handle("POST", path, {}, {"requestSchemaVersion": "v1"}, Message())
            self.assertEqual(denied.exception.status, 404)

    def test_context_bootstrap_does_not_create_login(self):
        headers = Message()
        headers["Authorization"] = "Bearer " + b64url(b"f" * 32)
        status, body, cookies, _ = self.app().handle("POST", "/__v00__/fixtures/basic/context", {},
            {"requestSchemaVersion": "v1"}, headers)
        self.assertEqual(status, 201)
        self.assertEqual(body, {"authContextId": self.ctx})
        self.assertIn("__Host-shadow-authctx-", cookies[0][1])
        self.assertNotIn("user-login", cookies[0][1])

    def test_wrong_action_or_secret_shape_rejected_before_admission(self):
        for body in (self.body | {"commandType": "AUTH_TOTP_VERIFY"}, self.body | {"code": "１２３４５６"},
                     self.body | {"success": True}, self.body | {"factorId": uid()}):
            with self.subTest(body=body), self.assertRaises(Rejection) as denied:
                self.app().handle("POST", "/api/auth/verify", {}, body, Message())
            self.assertEqual(denied.exception.status, 400)


if __name__ == "__main__":
    unittest.main()
