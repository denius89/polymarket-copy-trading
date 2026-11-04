"""Public RFC vectors and deterministic collision, no deployed credentials."""
import unittest
from totp import InvalidRequest, fingerprint, hotp, matching_steps, strict_object, verify_request


class TotpVectors(unittest.TestCase):
    secret = b"12345678901234567890"  # Public RFC 4226 vector, NEVER a live factor.

    def test_rfc4226(self):
        expected = ["755224", "287082", "359152", "969429", "338314",
                    "254676", "287922", "162583", "399871", "520489"]
        self.assertEqual([hotp(self.secret, i) for i in range(10)], expected)

    def test_rfc6238_sha1_six_digits(self):
        for timestamp, expected in [(59, "287082"), (1111111109, "081804"),
                                    (1111111111, "050471"), (1234567890, "005924"),
                                    (2000000000, "279037"), (20000000000, "353130")]:
            self.assertEqual(hotp(self.secret, timestamp // 30), expected)

    def test_collision_all_matches_and_boundary(self):
        # Independently pin both HOTP outputs, including the nonmatching middle.
        self.assertEqual(hotp(self.secret, 153567), "468457")
        self.assertNotEqual(hotp(self.secret, 153568), "468457")
        self.assertEqual(hotp(self.secret, 153569), "468457")
        self.assertEqual(matching_steps(self.secret, "468457", 153568 * 30), [153567, 153569])
        self.assertEqual(matching_steps(self.secret, "468457", 153568 * 30 - 1), [153567])
        self.assertEqual(matching_steps(self.secret, "468457", 153569 * 30), [153569])
        self.assertEqual(matching_steps(self.secret, "468457", 153571 * 30), [])

    def test_strict_input_and_no_caller_clock(self):
        for raw in [b'{"code":"000000","code":"111111"}', b'{"x":NaN}', b'[]', b'\xff']:
            with self.assertRaises(InvalidRequest): strict_object(raw)
        request = {"operationId": "00000000-0000-4000-8000-000000000001",
                   "contextId": "00000000-0000-4000-8000-000000000002",
                   "challengeId": "00000000-0000-4000-8000-000000000003", "code": "000000"}
        verify_request(request)
        for change in [{"code": 123456}, {"code": "１２３４５６"}, {"now": 123}, {"matchedSteps": []}]:
            with self.assertRaises(InvalidRequest): verify_request(request | change)

    def test_fingerprint_scope_and_payload(self):
        key = b"public-test-key-only"
        self.assertEqual(fingerprint(key, "u1", {"a": 1, "b": 2}), fingerprint(key, "u1", {"b": 2, "a": 1}))
        self.assertNotEqual(fingerprint(key, "u1", {"a": 1}), fingerprint(key, "u2", {"a": 1}))
        self.assertNotEqual(fingerprint(key, "u1", {"a": 1}), fingerprint(key, "u1", {"a": 2}))


if __name__ == "__main__":
    unittest.main()
