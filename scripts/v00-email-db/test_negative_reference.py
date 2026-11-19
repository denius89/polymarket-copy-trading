import hashlib
import unittest

from negative_reference import classify
from seed_directory import address_digest

EMAIL = 'fixture@example.test'
CODE = '012345'
TOKEN = hashlib.sha224((EMAIL + CODE).encode()).hexdigest()


class NegativeSourceVectors(unittest.TestCase):
    def classify(self, code=CODE, **overrides):
        value = dict(email=EMAIL, code=code, now=1500, challenge_expiry=1600,
                     recovery_token=TOKEN, recovery_issued=1000)
        return classify(**(value | overrides))

    def test_both_supported_recovery_formats(self):
        self.assertEqual(self.classify(), 'positive_candidate')
        self.assertEqual(self.classify(recovery_token='pkce_' + TOKEN), 'positive_candidate')
        self.assertEqual(self.classify('012346'), 'live_mismatch')

    def test_foreign_family_match_is_not_wrong_or_success(self):
        other = hashlib.sha224((EMAIL + '654321').encode()).hexdigest()
        self.assertEqual(self.classify('654321', confirmation_token=other, confirmation_issued=1000), 'unsupported_other_family')
        self.assertEqual(self.classify('654321', confirmation_token='pkce_' + other, confirmation_issued=900), 'unsupported_other_family')
        self.assertEqual(self.classify('654321', confirmation_token=other, confirmation_issued=899), 'live_mismatch')
        self.assertEqual(self.classify(confirmation_token=TOKEN, confirmation_issued=1000), 'unsupported_other_family')

    def test_expiry_boundary_never_increments_wrong_counter(self):
        self.assertEqual(self.classify('012346', now=1599.999), 'live_mismatch')
        self.assertEqual(self.classify('012346', now=1600), 'expired_current')
        self.assertEqual(self.classify(now=1601), 'expired_current')

    def test_missing_unsupported_future_source_is_unavailable(self):
        for override in [dict(recovery_token=''), dict(recovery_token='unsupported'), dict(recovery_issued=None),
                         dict(recovery_issued=1501), dict(confirmation_token='unsupported'),
                         dict(confirmation_token=TOKEN, confirmation_issued=None),
                         dict(confirmation_token=TOKEN, confirmation_issued=1501)]:
            with self.subTest(override=tuple(override)):
                self.assertEqual(self.classify(**override), 'unavailable')

    def test_strict_six_ascii_digits(self):
        for code in [12345, None, '12345', '1234567', ' 12345', '１２３４５６', '١٢٣٤٥٦']:
            self.assertEqual(self.classify(code), 'malformed')

    def test_address_digest_preserves_canonical_distinctions(self):
        key = bytes(range(32))
        first = address_digest(key, 'a+b@example.test')
        self.assertEqual(first, address_digest(key, 'a+b@example.test'))
        self.assertNotEqual(first, address_digest(key, 'ab@example.test'))
        self.assertNotEqual(first, address_digest(bytes(32), 'a+b@example.test'))


if __name__ == '__main__':
    unittest.main()
