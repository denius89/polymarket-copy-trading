"""Offline generator checks; no DB, provider, service startup, or network."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from prepare_client import prepare


class TargetedManifest(unittest.TestCase):
    def fixture(self):
        actor = str(uuid.uuid4())
        config = {"principals": {"public-unit-token": actor}, "contexts": {}, "cases": {},
                  "fingerprint_key_hex": "33" * 32, "email_operations": {}}
        for label in ("wall_clock", "collision", "collision_reuse", "partial_overlap", "new_factor_version",
                      "expired_challenge", "missing_current_challenge", "wrong_codes", "concurrent_a",
                      "concurrent_b", "lost_client_reply"):
            ctx = str(uuid.uuid4())
            config["cases"][label] = {"contextId": ctx, "challengeId": str(uuid.uuid4()), "principal_id": actor}
            config["contexts"][ctx] = {"principal_id": actor, "factor_version": str(uuid.uuid4()),
                                        "secret_base32": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"}
        return config

    def run_prepare(self, config, root):
        seed = root / "seed.json"
        seed.write_text(json.dumps(config))
        env = {"V00_SEED_CONFIG": str(seed), "V00_CONTROLLER_ORIGIN": "http://controller:8080",
               "V00_FORBIDDEN_TCP_JSON": '[{"label":"Auth","host":"127.0.0.2","port":9999},{"label":"DB","host":"127.0.0.3","port":5432}]',
               "V00_CONTROLLER_OUTPUT": str(root / "controller.json"), "V00_CLIENT_OUTPUT": str(root / "client.json"),
               "V00_ONLY_LOST_TOTP": "1"}
        with patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(io.StringIO()):
            prepare()

    def test_targeted_manifest_contains_only_lost_totp(self):
        config = self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_prepare(config, root)
            client = json.loads((root / "client.json").read_text())
            server = json.loads((root / "controller.json").read_text())
            self.assertEqual(client["cases"], [])
            self.assertEqual(client["races"], [])
            self.assertEqual(len(client["lost_client_reply"]), 1)
            entry = client["lost_client_reply"][0]
            self.assertEqual(entry["payload"]["contextId"], config["cases"]["lost_client_reply"]["contextId"])
            self.assertEqual(entry["api_token"], "public-unit-token")
            self.assertEqual(entry["result_route"], "/v00/totp/result")
            self.assertEqual(server["contexts"], config["contexts"])
            self.assertNotIn("secret_base32", json.dumps(client))
            self.assertNotIn("fingerprint_key_hex", json.dumps(client))
            self.assertEqual((root / "client.json").stat().st_mode & 0o777, 0o600)

    def test_missing_fresh_target_cannot_fall_back_to_full_run(self):
        config = self.fixture()
        del config["cases"]["lost_client_reply"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError): self.run_prepare(config, root)
            self.assertFalse((root / "client.json").exists())


if __name__ == "__main__":
    unittest.main()
