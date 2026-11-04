from concurrent.futures import ThreadPoolExecutor
import json
import unittest
import uuid

from hold_proxy import State


class HoldProxyTests(unittest.TestCase):
    def setUp(self):
        self.state = State("proxy-fixture@example.invalid", "012345", "a" * 43, 7)
        self.raw = json.dumps({"email": "proxy-fixture@example.invalid", "token": "012345", "type": "email"}, separators=(",", ":")).encode()
        self.agent = "shadow-v00-upstream/" + str(uuid.uuid4())

    def test_one_exact_request_accepted_then_secret_discarded(self):
        self.assertTrue(self.state.accept(self.raw, self.agent))
        self.assertIsNone(self.state._expected)
        self.assertFalse(self.state.accept(self.raw, self.agent))
        self.state.close_accepted()
        value = self.state.snapshot()
        self.assertEqual((value["seen_requests"], value["accepted_requests"], value["rejected_requests"], value["closed_requests"], value["forwarded_requests"]), (2, 1, 1, 1, 0))

    def test_concurrent_duplicates_only_one_accepted(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(lambda _: self.state.accept(self.raw, self.agent), range(20)))
        self.assertEqual(sum(values), 1)
        self.assertEqual(self.state.snapshot()["seen_requests"], 20)

    def test_mismatch_never_consumes_expected_request(self):
        self.assertFalse(self.state.accept(self.raw.replace(b"012345", b"012346"), self.agent))
        self.assertTrue(self.state.accept(self.raw, self.agent))

    def test_invalid_source_dispatch_rejected(self):
        for agent in ("curl", "shadow-v00-upstream/../bad", None):
            self.assertFalse(self.state.accept(self.raw, agent))
        self.assertEqual(self.state.snapshot()["accepted_requests"], 0)

    def test_observer_cannot_see_private_values(self):
        self.state.accept(self.raw, self.agent)
        value = json.dumps(self.state.snapshot())
        for secret in ("012345", "proxy-fixture@example.invalid", "a" * 43):
            self.assertNotIn(secret, value)
        self.assertFalse(self.state.observe_allowed("Bearer wrong"))
        self.assertTrue(self.state.observe_allowed("Bearer " + "a" * 43))

    def test_hold_bound_exceeds_adapter_timeout(self):
        for duration in (0, 5, 16):
            with self.assertRaises(ValueError):
                State("a@example.invalid", "012345", "a" * 43, duration)


if __name__ == "__main__":
    unittest.main()
