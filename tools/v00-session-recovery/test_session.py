import base64
from email.message import Message
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from controller import Controller, Rejection, cookie, selected_cookie, selected_login, strict_json
from crypto import Keys, Unavailable, aad, b64url, secret_bytes, private_json
from prepare import generate
from storage import Transaction


class FakeTransaction:
    def __init__(self, replies, fail_commit=False):
        self.replies = list(replies)
        self.fail_commit = fail_commit
        self.committed = False
        self.closed = False
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def call(self, method, fields):
        self.calls.append((method, fields))
        return self.replies.pop(0)

    def commit(self):
        if self.fail_commit:
            raise Unavailable("lost commit")
        self.committed = True


class FakeSodium:
    """Unit test only; never inject this into the server."""
    def __init__(self, plaintext=None):
        self.plaintext = plaintext
        self.on_decrypt = None

    def decrypt(self, *args):
        if self.on_decrypt:
            self.on_decrypt()
        return self.plaintext

    def encrypt(self, *args):
        return "test-cipher", "test-nonce"


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "fixtures"
        generate(self.root, "https://session-d0307.invalid:8443")
        self.config = private_json(self.root / "server.json")
        self.keys = Keys(self.root / "keys.json")
        self.f = self.config["fixtures"]["basic"]
        self.headers = Message()
        self.headers["Cookie"] = f'__Host-shadow-authctx-{self.f["context_id"]}={self.f["proof"]}'
        self.path = f'/api/auth/contexts/{self.f["context_id"]}/operations/{self.f["operation_id"]}/login-cookie'
        self.body = {"requestSchemaVersion": "v1", "commandType": "C02"}
        self.value = b64url(b"S" * 32)
        self.result = {"kind": "login_completed", "completion": {"authContextId": self.f["context_id"],
            "authOperationId": self.f["operation_id"], "loginId": self.f["login_id"], "realm": "user", "completedAt": "2026-11-04T12:00:00.000Z"}}
        self.metadata = {"environment": "v00-d03-07", "realm": "user", "login_id": self.f["login_id"],
            "secret_id": self.f["secret_id"], "source_context_id": self.f["context_id"], "source_operation_id": self.f["operation_id"],
            "owner_kind": "login", "owner_id": self.f["login_id"], "purpose": "login_cookie",
            "cipher_format": "v00-test-short-secret-xchacha20poly1305-v1", "credential_format": "v00-test-login-cookie-v1",
            "reveal_until": "2026-11-04T12:05:00.000Z"}
        self.recovery = {"http": 200, "result": self.result, "ciphertext": "test", "nonce": "test",
            "key_id": "cipher-1", "credential_key_id": "credential-1", "cookie_digest": self.keys.login(self.f["login_id"], self.value),
            "metadata": self.metadata, "login_expires_at": "2026-12-04T12:00:00.000Z"}

    def tearDown(self):
        self.tmp.cleanup()

    def controller(self, replies, fail_commit=False):
        tx = FakeTransaction(replies, fail_commit)
        sodium = FakeSodium(self.value.encode())
        c = Controller(self.config, self.keys, sodium, lambda: tx)
        return c, tx, sodium

    def recover(self, c):
        return c.handle("POST", self.path, {}, self.body, self.headers)

    def test_recovery_crypto_precedes_commit(self):
        c, tx, sodium = self.controller([self.recovery])
        sodium.on_decrypt = lambda: self.assertFalse(tx.committed)
        status, body, headers, _ = self.recover(c)
        self.assertTrue(tx.committed)
        self.assertEqual(status, 200)
        self.assertEqual(body["completion"], self.result["completion"])
        self.assertIn(self.value, headers[0][1])
        self.assertNotIn("ciphertext", body)

    def test_new_completion_is_one_transaction(self):
        c, tx, _ = self.controller([{"http": 200, "replay": False, "metadata": self.metadata},
            {"http": 200, "result": self.result, "login_expires_at": self.recovery["login_expires_at"]}])
        self.headers["Authorization"] = "Bearer " + self.f["fixture_token"]
        r = c.handle("POST", "/__v00__/fixtures/basic/complete", {},
            self.body | {"authOperationId": self.f["operation_id"]}, self.headers)
        self.assertEqual(r[0], 200)
        self.assertEqual([x[0] for x in tx.calls], ["plan_completion", "complete"])
        self.assertTrue(tx.committed)

    def test_completion_error_rolls_back_plan(self):
        c, tx, _ = self.controller([{"http": 200, "replay": False, "metadata": self.metadata},
            {"http": 401, "reason": "AUTH_EXPIRED"}])
        self.headers["Authorization"] = "Bearer " + self.f["fixture_token"]
        with self.assertRaises(Rejection):
            c.handle("POST", "/__v00__/fixtures/basic/complete", {},
                self.body | {"authOperationId": self.f["operation_id"]}, self.headers)
        self.assertFalse(tx.committed)

    def test_completion_replay_after_close_has_no_cookie(self):
        c, tx, _ = self.controller([{"http": 200, "replay": True, "result": self.result},
            {"http": 409, "reason": "AUTH_COOKIE_RECOVERY_CLOSED"}])
        self.headers["Authorization"] = "Bearer " + self.f["fixture_token"]
        r = c.handle("POST", "/__v00__/fixtures/basic/complete", {},
            self.body | {"authOperationId": self.f["operation_id"]}, self.headers)
        self.assertEqual(r[1]["completion"], self.result["completion"])
        self.assertEqual(r[2], [])
        self.assertTrue(tx.committed)

    def test_unknown_commit_never_returns_cookie(self):
        c, tx, _ = self.controller([self.recovery], True)
        with self.assertRaises(Unavailable):
            self.recover(c)
        self.assertFalse(tx.committed)
        self.assertEqual(len(tx.calls), 1)

    def test_wrong_decrypted_secret_rolls_back(self):
        c, tx, sodium = self.controller([self.recovery])
        sodium.plaintext = b64url(b"T" * 32).encode()
        with self.assertRaises(Unavailable):
            self.recover(c)
        self.assertFalse(tx.committed)

    def test_key_unavailable_rolls_back(self):
        c, tx, _ = self.controller([self.recovery])
        original = self.keys.get
        self.keys.get = lambda purpose, key: (_ for _ in ()).throw(Unavailable()) if purpose == "cipher" else original(purpose, key)
        with self.assertRaises(Unavailable):
            self.recover(c)
        self.assertFalse(tx.committed)

    def test_closed_recovery_commits_erasure_no_cookie(self):
        c, tx, _ = self.controller([{"http": 409, "reason": "AUTH_COOKIE_RECOVERY_CLOSED"}])
        with self.assertRaises(Rejection) as result:
            self.recover(c)
        self.assertEqual(result.exception.status, 409)
        self.assertTrue(tx.committed)

    def test_history_does_not_decrypt_or_issue_cookie(self):
        c, tx, sodium = self.controller([{"http": 200, "status": "resolved", "result": self.result, "resolved_at": "2026-11-04T12:00:01.000Z"}])
        sodium.on_decrypt = lambda: self.fail("history decrypted")
        r = c.handle("GET", self.path.removesuffix("/login-cookie"), self.body, {}, self.headers)
        self.assertEqual(r[0], 200)
        self.assertEqual(r[2], [])
        self.assertEqual(r[1]["result"], self.result)
        self.assertEqual(r[1]["resolvedAt"], "2026-11-04T12:00:01.000Z")

    def test_record_unavailable_does_not_commit(self):
        c, tx, _ = self.controller([{"http": 503, "reason": "RECORD_UNAVAILABLE"}])
        with self.assertRaises(Rejection):
            self.recover(c)
        self.assertFalse(tx.committed)

    def test_neighbor_proof_changes_digest(self):
        a = self.keys.proof(self.f["context_id"], self.f["proof"])
        b = self.keys.proof(str(uuid.uuid4()), self.f["proof"])
        self.assertNotEqual(a, b)

    def test_extra_recovery_target_rejected_before_db(self):
        c, tx, _ = self.controller([])
        with self.assertRaises(Rejection):
            c.handle("POST", self.path, {}, self.body | {"loginId": self.f["login_id"]}, self.headers)
        self.assertEqual(tx.calls, [])

    def test_duplicate_selected_cookie_and_header(self):
        h = Message()
        h["Cookie"] = "x=" + self.value + "; x=" + self.value
        with self.assertRaises(Rejection):
            selected_cookie(h, "x")
        h["X-Shadow-Login-Id"] = self.f["login_id"]
        h["X-Shadow-Login-Id"] = self.f["login_id"]
        with self.assertRaises(Rejection):
            selected_login(h)

    def test_unknown_other_cookie_never_selected(self):
        h = Message()
        h["Cookie"] = "another=" + self.value
        with self.assertRaises(Rejection):
            selected_cookie(h, "expected")

    def test_cookie_attributes(self):
        c = cookie("__Host-example", self.value)
        self.assertNotIn("Expires", c)
        self.assertNotIn("Domain", c)
        for part in ("Secure", "HttpOnly", "SameSite=Strict", "Path=/"):
            self.assertIn(part, c)

    def test_strict_json_rejects_duplicates_surrogates_nonfinite_depth(self):
        for raw in (b'{"a":1,"\\u0061":2}', b'{"a":"\\ud800"}', b'{"a":NaN}', b'\xef\xbb\xbf{}',
                    b'{"a":' + b'['*10 + b'0' + b']'*10 + b'}'):
            with self.subTest(raw=raw), self.assertRaises(Rejection):
                strict_json(raw)

    def test_noncanonical_base64url(self):
        with self.assertRaises(ValueError):
            secret_bytes("A"*42 + "B")

    def test_metadata_binding(self):
        original = aad(self.metadata)
        changed = aad(self.metadata | {"source_operation_id": str(uuid.uuid4())})
        self.assertNotEqual(original, changed)
        with self.assertRaises(Unavailable):
            aad(self.metadata | {"owner_id": str(uuid.uuid4())})

    def test_fixture_files_private_and_cannot_overwrite(self):
        for path in self.root.iterdir():
            self.assertEqual(path.stat().st_mode & 0o077, 0)
        with self.assertRaises(FileExistsError):
            generate(self.root, "https://session-d0307.invalid:8443")
        client = private_json(self.root / "client.json")
        self.assertNotIn("proof", client["fixtures"]["basic"])
        self.assertNotIn("keys", client)

    def test_logout_wrong_selected_target_does_not_execute(self):
        ctx, op = str(uuid.uuid4()), str(uuid.uuid4())
        h = Message(); h["Cookie"] = "__Host-shadow-logoutctx-" + ctx + "=" + self.value
        h["X-Shadow-Login-Id"] = str(uuid.uuid4())
        c, tx, _ = self.controller([{"http": 202, "target_login_id": self.f["login_id"]}])
        with self.assertRaises(Rejection) as exc:
            c.handle("POST", "/api/auth/logout", {}, {"requestSchemaVersion": "v1", "commandType": "C07",
                "logoutContextId": ctx, "authOperationId": op}, h)
        self.assertEqual(exc.exception.status, 400)
        self.assertEqual([x[0] for x in tx.calls], ["logout_result"])
        self.assertFalse(tx.committed)


class PsqlProtocolTests(unittest.TestCase):
    def script(self, response):
        # Independent subprocess emulates psql command tags; no PostgreSQL installation.
        return [sys.executable, "-u", "-c", "import sys,json\nfor l in sys.stdin:\n"
                " if l.startswith('BEGIN'): print('BEGIN',flush=True)\n"
                " elif l.startswith('SELECT'): print(json.dumps({'http':200}),flush=True)\n"
                " elif l.startswith('COMMIT'): print(" + repr(response) + ",flush=True)\n"]

    def test_confirmed_commit_tag(self):
        with Transaction(self.script("COMMIT")) as tx:
            self.assertEqual(tx.call("q01", {"value": "'; DROP TABLE x;"}), {"http": 200})
            tx.commit()
            self.assertTrue(tx.finished)

    def test_rollback_tag_is_not_success(self):
        with self.assertRaises(Unavailable), Transaction(self.script("ROLLBACK")) as tx:
            tx.commit()

    def test_unknown_method_never_sent(self):
        with Transaction(self.script("COMMIT")) as tx, self.assertRaises(Unavailable):
            tx.call("revoke", {})

    def test_pipe_loss_after_real_child_commit_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "commit.jsonl"
            command = [sys.executable, str(Path(__file__).with_name("psql_commit_loss.py")),
                       "--action", "q01", "--marker", str(marker), "--"]
            with patch.dict(os.environ, {"V00_REAL_PSQL_COMMAND_JSON": json.dumps(self.script("COMMIT"))}):
                with Transaction(command) as tx:
                    self.assertEqual(tx.call("q01", {"private": "not-in-marker"}), {"http": 200})
                    with self.assertRaises(Unavailable):
                        tx.commit()
                    self.assertFalse(tx.finished)
            data = json.loads(marker.read_text())
            self.assertEqual(data, {"fault": "commit_ack_pipe_loss", "action": "q01", "real_commit_tag_seen": True})
            self.assertNotIn("private", marker.read_text())

    def test_pipe_fault_does_not_drop_other_action_commit(self):
        command = [sys.executable, str(Path(__file__).with_name("psql_commit_loss.py")), "--action", "complete", "--"]
        with patch.dict(os.environ, {"V00_REAL_PSQL_COMMAND_JSON": json.dumps(self.script("COMMIT"))}):
            with Transaction(command) as tx:
                tx.call("q01", {})
                tx.commit()
                self.assertTrue(tx.finished)


if __name__ == "__main__":
    unittest.main()
