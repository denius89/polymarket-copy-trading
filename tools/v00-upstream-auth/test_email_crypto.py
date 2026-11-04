import unittest

from dependency import Unavailable
from email_crypto import address_digest, decrypt_email, email_aad, encrypt_email
from test_bridge import Cipher, Keys, uid


class EmailCryptoTests(unittest.TestCase):
    def test_bound_material_and_private_key_roles(self):
        ctx, keys, cipher = uid(), Keys(), Cipher()
        expiry = "2026-11-04T12:30:00.000Z"
        binding = encrypt_email(keys, cipher, ctx, "a@example.invalid", expiry)
        material = binding | {"context_id": ctx}
        self.assertEqual(decrypt_email(keys, cipher, ctx, material), "a@example.invalid")
        for changed in ({"context_id": uid()}, {"address_digest": "f" * 64},
                        {"key_id": "cipher-1"}, {"address_key_id": "comparison-1"},
                        {"cipher_format": "unknown"}, {"nonce": "!!!"}):
            with self.subTest(changed=changed), self.assertRaises(Unavailable):
                decrypt_email(keys, cipher, ctx, material | changed)

    def test_aad_scope_and_deadline_are_distinct(self):
        ctx, secret = uid(), uid()
        baseline = email_aad(ctx, secret, "2026-11-04T12:30:00.000Z")
        self.assertTrue(baseline.startswith(b"shadow.v00.email.aad.v1\0"))
        self.assertNotEqual(baseline, email_aad(uid(), secret, "2026-11-04T12:30:00.000Z"))
        self.assertNotEqual(baseline, email_aad(ctx, uid(), "2026-11-04T12:30:00.000Z"))
        self.assertNotEqual(baseline, email_aad(ctx, secret, "2026-11-04T12:30:00.001Z"))

    def test_address_digest_shared_across_contexts_not_an_identity(self):
        keys = Keys()
        self.assertEqual(address_digest(keys, "a@example.invalid"), address_digest(keys, "a@example.invalid"))
        self.assertNotEqual(address_digest(keys, "a@example.invalid"), address_digest(keys, "a+tag@example.invalid"))
        with self.assertRaises(Unavailable):
            address_digest(keys, " A@example.invalid ")


if __name__ == "__main__":
    unittest.main()
