import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dependency import Keys
from email_crypto import address_digest
from email_prepare import prepare
from email_probe import run
from test_bridge import uid


class OperatorTests(unittest.TestCase):
    def test_preparation_creates_private_separate_keys_and_no_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "new"
            source = {"origin": "https://entry.invalid:8443", "entries": [
                {"name": "basic", "actor_id": uid(), "email": "Synthetic@Example.INVALID"}]}
            report = prepare(source, root)
            self.assertEqual(report["contexts_created"], 0)
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            for path in root.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            keys = json.loads((root / "keys.json").read_text())
            self.assertEqual(len({v["hex"] for v in keys.values()}), 6)
            row = json.loads((root / "directory-input.json").read_text())["entries"][0]
            self.assertEqual(row["address_digest"], address_digest(Keys(root / "keys.json"), row["normalized_email"]))
            original = (root / "keys.json").read_bytes()
            with self.assertRaises(FileExistsError):
                prepare(source, root)
            self.assertEqual((root / "keys.json").read_bytes(), original)

    def test_preparation_rejects_unsafe_alias_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "new"
            with self.assertRaises(ValueError):
                prepare({"origin": "https://entry.invalid:8443", "entries": [
                    {"name": "../escape", "actor_id": uid(), "email": "synthetic@example.invalid"}]}, root)
            self.assertFalse(root.exists())

    def test_unknown_probe_preserves_original_and_only_tests_one_other_context(self):
        calls = []
        class Client:
            def __init__(self, *_):
                self.ctx = uid()
            def request(self, path, body=None):
                if path == "/api/auth/contexts":
                    return 201, {"authContext": {"stage": "ready", "accessConfirmed": False, "authContextId": self.ctx}}, {
                        "Set-Cookie": "__Host-shadow-authctx-" + self.ctx}
                if body is None:
                    return 200, {"authContext": {"accessConfirmed": True}}, {}
                calls.append((path, dict(body)))
                return 503, {"reasonCode": "SERVICE_UNAVAILABLE"}, {}
            def operation(self, ctx, op, action):
                return 202, {"status": "unresolved", "result": None, "resolvedAt": None}, {}
        with patch("email_probe.Client", Client), patch("email_probe.emit"), patch("email_probe.receive", side_effect=AssertionError("no code needed")):
            report = run({"origin": "https://entry.invalid", "email": "synthetic@example.invalid"}, "ca", "unknown")
        self.assertTrue(all(row["passed"] for row in report["checks"]))
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0], calls[1])
        self.assertNotEqual(calls[0][1]["authContextId"], calls[2][1]["authContextId"])
        self.assertEqual({p for p, _ in calls}, {"/api/auth/request"})
        self.assertNotIn("synthetic@example.invalid", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
