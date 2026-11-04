import base64
import json
import unittest

from database import Transaction, IngressTransaction
from dependency import Unavailable


class WireTests(unittest.TestCase):
    def make(self, cls):
        tx = cls.__new__(cls)
        tx.output = []
        tx.send = tx.output.append
        tx.line = lambda: '{"http":503,"reason":"SERVICE_UNAVAILABLE"}'
        return tx

    def test_sensitive_input_bound_not_in_server_statement(self):
        tx = self.make(Transaction)
        fields = {"code": "123456", "executor_proof": "synthetic-private-marker"}
        tx.call("plan_totp", fields)
        sql, bind, execute = tx.output[0].splitlines()
        self.assertIn("decode($1,'base64')", sql)
        self.assertNotIn("123456", sql)
        self.assertNotIn("synthetic-private-marker", sql)
        self.assertFalse(sql.endswith(";"))
        self.assertEqual(execute, "\\g")
        encoded = bind.removeprefix("\\bind '").removesuffix("'")
        self.assertEqual(json.loads(base64.b64decode(encoded)), fields)

    def test_no_synthetic_or_operator_method_in_runtime(self):
        for name in ("plan_completion", "capture", "snapshot", "reconcile_email", "complete;DROP TABLE x"):
            tx = self.make(Transaction)
            with self.subTest(name=name), self.assertRaises(Unavailable):
                tx.call(name, {})
            self.assertEqual(tx.output, [])

    def test_ingress_only_capture(self):
        tx = self.make(IngressTransaction)
        tx.call("capture", {"executor_proof_digest": "a" * 64})
        self.assertIn("v00_upstream.capture", tx.output[0])
        with self.assertRaises(Unavailable):
            tx.call("complete", {})

    def test_invalid_private_json_not_empty_success(self):
        tx = self.make(Transaction)
        tx.line = lambda: "[]"
        with self.assertRaises(Unavailable):
            tx.call("read_operation", {})


if __name__ == "__main__":
    unittest.main()
