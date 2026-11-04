"""Public RFC vectors and known collision; never actual factor material."""
import base64
import unittest

from totp_reference import decode_seed, hotp, matching_steps

# RFC4226/6238 published example, not a credential.
SEED = b'12345678901234567890'
B32 = base64.b32encode(SEED).decode().rstrip('=')


class TotpVectors(unittest.TestCase):
    def test_rfc4226_counters(self):
        expected = ['755224', '287082', '359152', '969429', '338314',
                    '254676', '287922', '162583', '399871', '520489']
        self.assertEqual([hotp(SEED, i) for i in range(10)], expected)

    def test_rfc6238_sha1_vectors_six_digit_projection(self):
        vectors = [(59, '287082'), (1111111109, '081804'),
                   (1111111111, '050471'), (1234567890, '005924'),
                   (2000000000, '279037'), (20000000000, '353130')]
        for seconds, expected in vectors:
            self.assertEqual(hotp(SEED, seconds // 30), expected)
            self.assertIn(seconds // 30, matching_steps(B32, expected, seconds))

    def test_all_matching_collision_not_first_match(self):
        self.assertEqual(matching_steps(B32, '468457', 153568 * 30), [153567, 153569])

    def test_window_edges_and_epoch(self):
        self.assertEqual(matching_steps(B32, '755224', 0), [0])
        self.assertEqual(matching_steps(B32, '755224', 59), [0])
        self.assertEqual(matching_steps(B32, '755224', 60), [])
        self.assertEqual(matching_steps(B32, '359152', 29), [])
        self.assertEqual(matching_steps(B32, '359152', 30), [2])

    def test_reject_noncanonical_or_unsupported_material(self):
        for value in ['', 'my', 'MY=', 'MZ', 'AAAA1', 'v1:encrypted', None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode_seed(value)
        self.assertEqual(decode_seed('MY'), b'f')

    def test_strict_code_and_time_types(self):
        for code in [123456, '12345', '1234567', '１２３４５６', '12345\n', None]:
            with self.assertRaises(ValueError):
                matching_steps(B32, code, 0)
        for value in [-1, 1.5, True, '30', None, 2**63]:
            with self.assertRaises(ValueError):
                matching_steps(B32, '123456', value)


if __name__ == '__main__':
    unittest.main()
