import json
import unittest
import uuid

from provider import Provider, UnknownOutcome, ConfirmedNotSent


class Response:
    status = 200
    data = b'{"access_token":"private-test-only"}'

    def read(self, limit):
        return self.data[:limit]


class Connection:
    sock = None

    def __init__(self):
        self.calls = []
        self.response = Response()
        self.closed = False
        self.fail = False

    def request(self, method, path, body=None, headers=None):
        self.calls.append((method, path, body, headers))
        if self.fail:
            raise OSError("simulated private transport failure")

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.provider = Provider("http://auth:9999", lambda: self.connection)
        self.dispatch = str(uuid.uuid4())

    def test_exact_email_otp_path(self):
        status, _ = self.provider.verify_email("synthetic@example.invalid", "012345", self.dispatch)
        self.assertEqual(status, 200)
        method, path, body, headers = self.connection.calls[0]
        self.assertEqual((method, path), ("POST", "/verify"))
        self.assertEqual(json.loads(body), {"email": "synthetic@example.invalid", "token": "012345", "type": "email"})
        self.assertEqual(headers["User-Agent"], "shadow-v00-upstream/" + self.dispatch)
        self.assertTrue(self.connection.closed)

    def test_wrong_code_shape_never_dispatched(self):
        for code in (123456, "12345", "１２３４５６", " 123456"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.provider.verify_email("synthetic@example.invalid", code, self.dispatch)
        self.assertEqual(self.connection.calls, [])

    def test_unknown_does_not_retry(self):
        self.connection.fail = True
        with self.assertRaises(UnknownOutcome):
            self.provider.send_email("synthetic@example.invalid", self.dispatch)
        self.assertEqual(len(self.connection.calls), 1)

    def test_before_send_is_separate_from_unknown(self):
        with self.assertRaises(ConfirmedNotSent):
            self.provider.send_email("synthetic@example.invalid", self.dispatch, "before_send")
        self.assertEqual(self.connection.calls, [])

    def test_response_losses_never_return_success(self):
        for fault in ("after_send", "after_headers", "after_body"):
            with self.subTest(fault=fault), self.assertRaises(UnknownOutcome):
                self.provider.verify_email("synthetic@example.invalid", "012345", self.dispatch, fault)
        self.assertEqual(len(self.connection.calls), 3)

    def test_redirect_never_followed(self):
        self.connection.response.status = 302
        with self.assertRaises(UnknownOutcome):
            self.provider.send_email("synthetic@example.invalid", self.dispatch)
        self.assertEqual(len(self.connection.calls), 1)

    def test_oversize_response_unknown(self):
        self.connection.response.data = b"x" * 65537
        with self.assertRaises(UnknownOutcome):
            self.provider.send_email("synthetic@example.invalid", self.dispatch)

    def test_provider_targets_are_canonical(self):
        with self.assertRaises(ValueError):
            self.provider.challenge("../other", "private-token", self.dispatch)
        self.assertEqual(self.connection.calls, [])

    def test_no_secret_in_exception(self):
        self.connection.response.data = b"private-test-only-not-json"
        with self.assertRaises(UnknownOutcome) as failure:
            self.provider.send_email("synthetic@example.invalid", self.dispatch)
        self.assertNotIn("private-test-only", str(failure.exception))


if __name__ == "__main__":
    unittest.main()
