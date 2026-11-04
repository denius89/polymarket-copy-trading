"""Protocol fault injection only: these tests do not claim real DB/Auth behavior."""
import base64
import copy
import unittest
from unittest.mock import patch
import uuid

from bridge import Bridge, Denied, read_ref
from dependency import Unavailable, b64url, ENV, LOGIN_FORMAT, CIPHER_FORMAT
from protocol import decode
from provider import UnknownOutcome


def uid():
    return str(uuid.uuid4())


NOW = "2026-11-04T12:00:00.000Z"
DEADLINE = "2026-11-04T12:05:00.000Z"
EXPIRY = "2026-12-04T12:00:00.000Z"


class Tx:
    def __init__(self, responses, commit_failure=False):
        self.responses, self.commit_failure = list(responses), commit_failure
        self.calls, self.committed, self.closed = [], False, False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def call(self, method, fields):
        self.calls.append((method, fields))
        expected, response = self.responses.pop(0)
        if method != expected:
            raise AssertionError((method, expected))
        return response(fields) if callable(response) else copy.deepcopy(response)

    def commit(self):
        if self.commit_failure:
            raise Unavailable("simulated lost COMMIT")
        self.committed = True


class Factory:
    def __init__(self, *transactions):
        self.pending = list(transactions)

    def __call__(self):
        return self.pending.pop(0)


class Keys:
    def get(self, *_):
        return b"k" * 32

    def login(self, *_):
        return "a" * 64


class Cipher:
    def __init__(self):
        self.fail = False
        self.plain = b64url(b"s" * 32).encode()

    def encrypt(self, plaintext, *_):
        if self.fail:
            raise Unavailable("simulated key failure")
        self.plain = plaintext
        return base64.b64encode(b"c" * 59).decode(), base64.b64encode(b"n" * 24).decode()

    def decrypt(self, *_):
        return self.plain


class Provider:
    def __init__(self):
        self.calls = 0
        self.fail = False

    def verify_email(self, *_args, **_kwargs):
        self.calls += 1
        if self.fail:
            raise UnknownOutcome("simulated response loss")
        return 200, {"access_token": "must-not-be-used"}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.ref = {"context_id": uid(), "proof_digest": "b" * 64,
                    "operation_id": uid(), "action": "C02", "fingerprint": "c" * 64,
                    "comparison_hmac": "d" * 64, "comparison_key_id": "comparison-1"}
        self.provider, self.keys, self.cipher = Provider(), Keys(), Cipher()
        self.stage = {"kind": "auth_step_required", "stage": "totp_verification",
                      "challengeId": uid(), "challengeIssuedAt": NOW, "challengeExpiresAt": DEADLINE}
        self.seal = {"http": 200, "dispatch_allowed": True, "dispatch_id": uid()}
        self.last_plan = None

    def bridge(self, *tx):
        return Bridge(Factory(*tx), self.provider, self.keys, self.cipher)

    def email(self, bridge):
        return bridge.verify_email(self.ref, uid(), uid(), b64url(b"e" * 32),
                                   "synthetic@example.invalid", "012345")

    def plan(self, fields):
        meta = {"environment": ENV, "realm": "user", "login_id": fields["login_id"],
                "secret_id": fields["secret_id"], "source_context_id": self.ref["context_id"],
                "source_operation_id": self.ref["operation_id"], "owner_kind": "login",
                "owner_id": fields["login_id"], "purpose": "login_cookie", "cipher_format": CIPHER_FORMAT,
                "credential_format": LOGIN_FORMAT, "reveal_until": DEADLINE}
        self.last_plan = {"http": 200, "replay": False, "metadata": meta,
                          "completed_at": NOW, "login_expires_at": EXPIRY}
        return copy.deepcopy(self.last_plan)

    def complete(self, _fields):
        c = {"authContextId": self.ref["context_id"], "authOperationId": self.ref["operation_id"],
             "loginId": self.last_plan["metadata"]["login_id"], "realm": "user", "completedAt": NOW}
        return {"http": 200, "result": {"kind": "login_completed", "completion": c}, "login_expires_at": EXPIRY}

    def test_seal_commit_loss_never_dispatches(self):
        tx = Tx([("seal_email", self.seal)], commit_failure=True)
        with self.assertRaises(Unavailable):
            self.email(self.bridge(tx))
        self.assertEqual(self.provider.calls, 0)

    def test_expired_handler_budget_never_dispatches(self):
        tx = Tx([("seal_email", self.seal)])
        with patch("bridge.time.monotonic", return_value=11), self.assertRaises(Unavailable):
            self.bridge(tx).verify_email(self.ref, uid(), uid(), b64url(b"e" * 32),
                "synthetic@example.invalid", "012345", deadline=10)
        self.assertTrue(tx.committed)
        self.assertEqual(self.provider.calls, 0)

    def test_intermediate_commits_without_full_cookie(self):
        seal = Tx([("seal_email", self.seal)])
        plan = Tx([("plan_email", {"http": 200, "replay": False, "result": self.stage})])
        outcome = self.email(self.bridge(seal, plan))
        self.assertTrue(seal.committed and plan.committed)
        self.assertEqual(outcome.value, self.stage)
        self.assertIsNone(outcome.cookie)
        self.assertEqual(self.provider.calls, 1)

    def test_lost_provider_response_uses_witness_without_retry(self):
        self.provider.fail = True
        seal = Tx([("seal_email", self.seal)])
        plan = Tx([("plan_email", self.plan), ("complete", self.complete)])
        outcome = self.email(self.bridge(seal, plan))
        self.assertEqual(outcome.value["kind"], "login_completed")
        self.assertIsNotNone(outcome.cookie)
        self.assertEqual(self.provider.calls, 1)

    def test_provider_success_without_witness_not_success(self):
        seal = Tx([("seal_email", self.seal)])
        plan = Tx([("plan_email", {"http": 503, "reason": "SERVICE_UNAVAILABLE"})])
        with self.assertRaises(Denied):
            self.email(self.bridge(seal, plan))
        self.assertFalse(plan.committed)

    def test_final_commit_loss_releases_no_outcome(self):
        tx = Tx([("plan_email", self.plan), ("complete", self.complete)], commit_failure=True)
        with self.assertRaises(Unavailable):
            self.bridge(tx).plan("plan_email", self.ref)
        self.assertFalse(tx.committed)

    def test_crypto_failure_rolls_back_plan(self):
        self.cipher.fail = True
        tx = Tx([("plan_email", self.plan)])
        with self.assertRaises(Unavailable):
            self.bridge(tx).plan("plan_email", self.ref)
        self.assertEqual([m for m, _ in tx.calls], ["plan_email"])
        self.assertTrue(tx.closed and not tx.committed)

    def test_wrong_completed_login_rolls_back(self):
        def wrong(fields):
            value = self.complete(fields)
            value["result"]["completion"]["loginId"] = uid()
            return value
        tx = Tx([("plan_email", self.plan), ("complete", wrong)])
        with self.assertRaises(Unavailable):
            self.bridge(tx).plan("plan_email", self.ref)
        self.assertFalse(tx.committed)

    def test_plan_wrong_source_rejected_before_crypto(self):
        def wrong(fields):
            value = self.plan(fields)
            value["metadata"]["source_operation_id"] = uid()
            return value
        tx = Tx([("plan_email", wrong)])
        with self.assertRaises(Unavailable):
            self.bridge(tx).plan("plan_email", self.ref)
        self.assertFalse(tx.committed)

    def test_totp_rejection_commits(self):
        self.ref["action"] = "AUTH_TOTP_VERIFY"
        rejected = {"kind": "verification_rejected", "reasonCode": "AUTH_VERIFICATION_FAILED"}
        tx = Tx([("plan_totp", {"http": 401, "replay": False, "result": rejected})])
        outcome = self.bridge(tx).verify_totp(self.ref, uid(), uid(), b64url(b"e" * 32), "012345")
        self.assertTrue(tx.committed)
        self.assertEqual(outcome.http, 401)
        self.assertIsNone(outcome.cookie)

    def test_totp_technical_error_not_committed_as_rejection(self):
        self.ref["action"] = "AUTH_TOTP_VERIFY"
        tx = Tx([("plan_totp", {"http": 503, "reason": "RECORD_UNAVAILABLE"})])
        with self.assertRaises(Denied):
            self.bridge(tx).verify_totp(self.ref, uid(), uid(), b64url(b"e" * 32), "012345")
        self.assertFalse(tx.committed)

    def test_seal_replay_never_resends(self):
        self.seal["dispatch_allowed"] = False
        seal = Tx([("seal_email", self.seal)])
        plan = Tx([("plan_email", {"http": 200, "replay": True, "result": self.stage})])
        self.email(self.bridge(seal, plan))
        self.assertEqual(self.provider.calls, 0)

    def test_recovery_closed_commits_erasure(self):
        tx = Tx([("recover", {"http": 409, "reason": "AUTH_COOKIE_RECOVERY_CLOSED"})])
        with self.assertRaises(Denied):
            self.bridge(tx).recover(read_ref(self.ref))
        self.assertTrue(tx.committed)

    def test_recovery_closed_commit_loss_is_unknown(self):
        tx = Tx([("recover", {"http": 409, "reason": "AUTH_COOKIE_RECOVERY_CLOSED"})], commit_failure=True)
        with self.assertRaises(Unavailable):
            self.bridge(tx).recover(read_ref(self.ref))

    def test_read_never_recovers_or_dispatches(self):
        value = {"http": 200, "status": "resolved", "result": self.stage, "resolved_at": NOW}
        tx = Tx([("read_operation", value)])
        outcome = self.bridge(tx).read(read_ref(self.ref))
        self.assertIsNone(outcome.cookie)
        self.assertEqual(self.provider.calls, 0)

    def test_malformed_private_variants_fail_closed(self):
        variants = [
            {"http": True, "status": "unresolved", "result": None, "resolved_at": None},
            {"http": 202, "status": "unresolved", "result": {}, "resolved_at": None},
            {"http": 200, "status": "resolved", "result": self.stage, "resolved_at": None},
            {"http": 503, "reason": "raw provider text"},
            {"http": 202, "status": "unresolved", "result": None, "resolved_at": None, "secret": "x"},
        ]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(Unavailable):
                decode("read_operation", value, self.ref)

    def test_wrong_q01_login_rejected(self):
        login = uid()
        tx = Tx([("q01", {"http": 200, "authenticated": True, "login_id": uid(), "actor_id": uid()})])
        with self.assertRaises(Unavailable):
            self.bridge(tx).q01(login, "a" * 64)
        self.assertFalse(tx.committed)


if __name__ == "__main__":
    unittest.main()
