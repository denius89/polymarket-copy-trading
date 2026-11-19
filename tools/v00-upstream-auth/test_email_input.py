import json
import unittest

from email_input import canonical_email, send_intent
from test_bridge import Keys, uid


class EmailInputTests(unittest.TestCase):
    def test_product_normalization_preserves_dots_and_suffix(self):
        self.assertEqual(canonical_email("  A.B+Tag@Example.INVALID  "), "a.b+tag@example.invalid")
        self.assertEqual(canonical_email("x@xn--bcher-kva.invalid"), "x@xn--bcher-kva.invalid")
        self.assertEqual(canonical_email("a!#$%&'*+-/=?^_`{|}~@a.invalid"), "a!#$%&'*+-/=?^_`{|}~@a.invalid")

    def test_rejects_repairable_and_ambiguous_inputs_without_echo(self):
        invalid = [None, 1, "", " x@example.invalid\t", "\nx@example.invalid", "x@localhost",
                   "x@a.invalid.", "x@-a.invalid", "x@a-.invalid", "x@a..invalid", "x@@a.invalid",
                   "x..y@a.invalid", ".x@a.invalid", "x.@a.invalid", '"x"@a.invalid',
                   "X <x@a.invalid>", "x(comment)@a.invalid", "x@[127.0.0.1]", "é@a.invalid",
                   "x@bücher.invalid", "x\u00a0@a.invalid", "x@" + "a" * 64 + ".invalid",
                   "x" * 65 + "@a.invalid", "x@a.invalid" + " " * 513]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError) as error:
                canonical_email(value)
            self.assertEqual(str(error.exception), "invalid email")

    def test_accepted_length_boundaries(self):
        address = "x" * 64 + "@" + "a" * 63 + "." + "b" * 63 + "." + "c" * 61
        self.assertEqual(len(address), 254)
        self.assertEqual(canonical_email(address), address)
        with self.assertRaises(ValueError):
            canonical_email(address + "c")
        self.assertEqual(canonical_email(" " * (512 - len(address)) + address), address)

    def test_raw_intent_differs_even_for_equal_canonical_addresses(self):
        body = {"requestSchemaVersion": "v1", "commandType": "C01", "authContextId": uid(),
                "authOperationId": uid(), "email": " A@Example.INVALID ", "locale": "en"}
        baseline = send_intent(Keys(), body, "b" * 64)
        changed = send_intent(Keys(), body | {"email": "a@example.invalid"}, "b" * 64)
        self.assertEqual(canonical_email(body["email"]), canonical_email("a@example.invalid"))
        self.assertEqual(baseline["fingerprint"], changed["fingerprint"])
        self.assertNotEqual(baseline["comparison_hmac"], changed["comparison_hmac"])
        self.assertNotIn("email", json.dumps(baseline))
        for field, value in (("locale", "ru"), ("authOperationId", uid()), ("authContextId", uid())):
            self.assertNotEqual(baseline["comparison_hmac"],
                                send_intent(Keys(), body | {field: value}, "b" * 64)["comparison_hmac"])

    def test_resend_binds_current_expected_challenge(self):
        body = {"requestSchemaVersion": "v1", "commandType": "C03", "authContextId": uid(),
                "authOperationId": uid(), "expectedChallengeId": uid(), "locale": "en"}
        a = send_intent(Keys(), body, "b" * 64)
        b = send_intent(Keys(), body | {"expectedChallengeId": uid()}, "b" * 64)
        self.assertNotEqual(a["fingerprint"], b["fingerprint"])


if __name__ == "__main__":
    unittest.main()
