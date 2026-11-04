import json
from pathlib import Path
import tempfile
import unittest

from prepare import generate
from test_bridge import uid


class FixtureTests(unittest.TestCase):
    def test_shared_actor_distinct_contexts_and_private_files(self):
        provider, factor = uid(), uid()
        mapping = {"fixtures": [{"name": name, "email": "fixture@example.invalid",
            "provider_user_id": provider, "provider_factor_id": factor} for name in ("a", "b")]}
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "private"
            report = generate(out, mapping, "https://session-upstream.invalid:8443")
            self.assertEqual(report, {"subjects": 1, "contexts": 2, "clock": "wall"})
            seed = json.loads((out / "seed.json").read_text())
            server = json.loads((out / "server.json").read_text())
            client = json.loads((out / "client.json").read_text())
            self.assertEqual(seed["contexts"][0]["actor_id"], seed["contexts"][1]["actor_id"])
            self.assertNotEqual(server["fixtures"]["a"]["proof"], server["fixtures"]["b"]["proof"])
            self.assertNotIn("proof", client["fixtures"]["a"])
            self.assertNotIn("email", client["fixtures"]["a"])
            self.assertTrue(all(p.stat().st_mode & 0o077 == 0 for p in out.iterdir()))
            with self.assertRaises(FileExistsError):
                generate(out, mapping, client["origin"])

    def test_conflicting_factor_mapping_rejected_before_files(self):
        provider = uid()
        mapping = {"fixtures": [{"name": name, "email": "fixture@example.invalid",
            "provider_user_id": provider, "provider_factor_id": factor} for name, factor in (("a", None), ("b", uid()))]}
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "private"
            with self.assertRaises(ValueError):
                generate(out, mapping, "https://session-upstream.invalid:8443")
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
