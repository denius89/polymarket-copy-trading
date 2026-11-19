from concurrent.futures import ThreadPoolExecutor
from email.message import Message
import json
import unittest
from unittest.mock import patch

from dependency import Unavailable, b64url
from bridge import Outcome
from controller import Rejection
from email_app import EmailApp
from email_bridge import EmailBridge
from email_clock import current_clock, request_clock
from email_ingress import EmailIngress
from test_bridge import Cipher, Factory, Tx, uid
from test_ingress_app import ProofKeys


def context(ctx, confirmed=True):
    return {"authContextId": ctx, "stage": "ready", "accessConfirmed": confirmed,
        "createdAt": "2026-11-04T12:00:00.000Z", "expiresAt": "2026-11-04T12:30:00.000Z",
        "emailCodeIssuedAt": None, "emailCodeExpiresAt": None, "currentEmailChallengeId": None,
        "currentTotpChallengeId": None, "totpChallengeIssuedAt": None, "totpChallengeExpiresAt": None,
        "loginCookieRecoveryDeadlineAt": None}


class ContextTests(unittest.TestCase):
    def test_context_cookie_only_after_confirmed_ingress_commit(self):
        keys, cipher = ProofKeys(), Cipher()
        for lost in (False, True):
            def created(fields):
                self.assertEqual(set(fields), {"context_id", "proof_digest"})
                return {"http": 201, "auth_context": context(fields["context_id"], False),
                        "observed_at": "2026-11-04T12:00:00.000Z", "paused_until": None, "pending_operation": False}
            tx = Tx([("context_create", created)], commit_failure=lost)
            bridge = EmailBridge(Factory(), None, keys, cipher, Factory(), Factory(tx))
            app = EmailApp({"fixtures": {}}, keys, cipher, bridge, None, Factory())
            if lost:
                with self.assertRaises(Unavailable):
                    app.handle("POST", "/api/auth/contexts", {}, {"requestSchemaVersion": "v1"}, Message())
            else:
                status, body, headers, _ = app.handle("POST", "/api/auth/contexts", {}, {"requestSchemaVersion": "v1"}, Message())
                self.assertEqual(status, 201)
                self.assertTrue(tx.committed)
                self.assertFalse(body["authContext"]["accessConfirmed"])
                self.assertEqual(len(headers), 1)
                self.assertIn("Secure; HttpOnly; SameSite=Strict", headers[0][1])
                self.assertNotIn("Expires", headers[0][1])
                self.assertNotIn("user-login", headers[0][1])
                self.assertNotIn("proof", json.dumps(body))

    def test_only_explicit_get_confirms_context(self):
        ctx, keys, cipher = uid(), ProofKeys(), Cipher()
        response = {"http": 200, "auth_context": context(ctx), "observed_at": "2026-11-04T12:00:01.000Z",
                    "paused_until": None, "pending_operation": False}
        read = Tx([("context_read", response)])
        inspect = Tx([("context_for_send", response)])
        bridge = EmailBridge(Factory(read, inspect), None, keys, cipher, Factory(), Factory())
        app = EmailApp({"fixtures": {}}, keys, cipher, bridge, None, Factory())
        headers = Message()
        headers["Cookie"] = "__Host-shadow-authctx-" + ctx + "=" + b64url(b"p" * 32)
        status, body, cookies, _ = app.handle("GET", "/api/auth/contexts/" + ctx,
                                             {"requestSchemaVersion": "v1"}, {}, headers)
        self.assertEqual(status, 200)
        self.assertEqual(cookies, [])
        self.assertNotIn("pending_operation", body)
        bridge.context(ctx, "b" * 64)
        self.assertEqual(read.calls[0][0], "context_read")
        self.assertEqual(inspect.calls[0][0], "context_for_send")


class CaptureTests(unittest.TestCase):
    def test_clock_is_mandatory_original_and_request_local(self):
        with self.assertRaises(Unavailable):
            current_clock()
        with request_clock():
            original = current_clock()
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(current_clock)
                with self.assertRaises(Unavailable):
                    future.result()
            self.assertIs(current_clock(), original)
        with self.assertRaises(Unavailable):
            current_clock()

    def test_capture_uses_initial_clock_and_does_not_restore_capability(self):
        admission = uid()
        refs = {"context_id": uid(), "operation_id": uid(), "action": "C01"}
        txs = [Tx([("capture", {"http": status, "created": new, "admission_id": admission,
                               "context_expires_at": "2026-11-04T12:30:00.000Z"})])
               for status, new in ((201, True), (200, False))]
        ingress = EmailIngress(Factory(*txs))
        with request_clock():
            started = current_clock().started_at
            first = ingress.capture(refs)
            second = ingress.capture(refs)
        self.assertEqual(first[0], second[0])
        self.assertNotEqual(first[1], second[1])
        for tx in txs:
            self.assertEqual(tx.calls[0][1]["request_started_at"], started)
            self.assertNotIn(first[1], json.dumps(tx.calls))
            self.assertNotIn(second[1], json.dumps(tx.calls))

    def test_c01_captures_before_encryption_without_internal_confirmation_read(self):
        events = []
        class Ingress:
            def capture(self, fields):
                events.append("capture")
                self.fields = fields
                return uid(), "proof", "2026-11-04T12:30:00.000Z", True
        class Bridge:
            def send(self, *args, **kwargs):
                events.append("seal")
                return Outcome(202, {})
        ctx, ingress, bridge = uid(), Ingress(), Bridge()
        app = EmailApp({"fixtures": {}}, ProofKeys(), Cipher(), bridge, ingress, Factory())
        headers = Message()
        headers["Cookie"] = "__Host-shadow-authctx-" + ctx + "=" + b64url(b"p" * 32)
        body = {"requestSchemaVersion": "v1", "commandType": "C01", "authContextId": ctx,
                "authOperationId": uid(), "email": "A@example.invalid", "locale": "en"}
        def encrypt(*args):
            events.append("encrypt")
            return {"private": "material"}
        with request_clock(), patch("email_app.encrypt_email", side_effect=encrypt), patch.object(app, "public", return_value=(202, {}, [], None)):
            app.handle("POST", "/api/auth/request", {}, body, headers)
        self.assertEqual(events, ["capture", "encrypt", "seal"])
        self.assertEqual(set(ingress.fields["email_binding"]), {"address_digest", "address_key_id"})
        self.assertNotIn(body["email"], json.dumps(ingress.fields))

    def test_c01_existing_capture_does_not_need_cipher_or_new_nonce(self):
        class Ingress:
            def capture(self, _):
                return uid(), "fresh-non-restored-proof", "2026-11-04T12:30:00.000Z", False
        class Bridge:
            def send(inner, ref, admission, proof, material, deadline=None):
                self.assertIsNone(material)
                return Outcome(202, {})
        ctx = uid()
        app = EmailApp({"fixtures": {}}, ProofKeys(), Cipher(), Bridge(), Ingress(), Factory())
        headers = Message()
        headers["Cookie"] = "__Host-shadow-authctx-" + ctx + "=" + b64url(b"p" * 32)
        body = {"requestSchemaVersion": "v1", "commandType": "C01", "authContextId": ctx,
                "authOperationId": uid(), "email": "synthetic@example.invalid", "locale": "en"}
        with request_clock(), patch("email_app.encrypt_email", side_effect=Unavailable("missing cipher key")), patch.object(app, "public", return_value=(202, {}, [], None)):
            self.assertEqual(app.handle("POST", "/api/auth/request", {}, body, headers)[0], 202)

    def test_fifth_negative_navigation_is_current_not_stored_result(self):
        ctx = uid()
        state = {"auth_context": context(ctx), "observed_at": "2026-11-04T12:00:01.000Z",
                 "paused_until": "2026-11-04T12:15:00.000Z", "pending_operation": False}
        self.assertEqual(EmailApp.current_navigation(state), ("retry_later", {"retryAt": state["paused_until"]}))
        state["paused_until"] = "2026-11-04T12:45:00.000Z"
        self.assertEqual(EmailApp.current_navigation(state), ("retry_later", {}))


if __name__ == "__main__":
    unittest.main()
