import unittest
from unittest.mock import patch

from controller import Controller, Unavailable


OP = "00000000-0000-4000-8000-000000000001"
CTX = "00000000-0000-4000-8000-000000000002"
CHALLENGE = "00000000-0000-4000-8000-000000000003"
FACTOR = "00000000-0000-4000-8000-000000000004"
REQUEST = {"operationId": OP, "contextId": CTX, "challengeId": CHALLENGE, "code": "468457"}


class StubDatabase:
    def __init__(self):
        self.calls = []
        self.original = None
        self.mode = "fixed_fixture"
        self.dispatch_allowed = True

    def call(self, action, fields):
        self.calls.append((action, fields))
        if action == "lookup": return self.original
        if action == "clock": return {"unix_seconds": 153568 * 30, "clock_mode": self.mode}
        if action == "verify": return {"http": 200, "status": "resolved", "kind": "totp_consumed"}
        if action == "seal":
            allowed, self.dispatch_allowed = self.dispatch_allowed, False
            return {"http": 200, "dispatch_allowed": allowed}
        if action == "outcome": return {"status": "uncertain"}
        raise AssertionError(action)


class ControllerBoundary(unittest.TestCase):
    def setUp(self):
        self.db = StubDatabase()
        self.config = {"fingerprint_key_hex": "11" * 32, "principals": {"public-unit-token": "u1"},
            "contexts": {CTX: {"principal_id": "u1", "factor_version": FACTOR,
                               "secret_base32": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"}},
            "email_operations": {OP: {"principal_id": "u1", "user_id": FACTOR,
                "token_digest": "22" * 32, "verify_path": "/verify?type=signup&token=public-unit-fixture"}},
            "provider_origin": "http://private-provider:9999"}
        self.controller = Controller(self.config, self.db)

    def test_whole_set_is_computed_by_controller(self):
        status, result = self.controller.verify("u1", REQUEST)
        self.assertEqual(status, 200)
        payload = self.db.calls[-1][1]
        self.assertEqual(payload["matched_steps"], [153567, 153569])
        self.assertEqual(payload["factor_version"], FACTOR)
        self.assertNotIn("code", payload)
        self.assertNotIn("login", result)

    def test_cross_principal_blocked_before_database(self):
        self.assertEqual(self.controller.verify("u2", REQUEST)[0], 404)
        self.assertEqual(self.db.calls, [])

    def test_replay_precedes_clock_and_compute(self):
        self.db.original = {"http": 401, "kind": "verification_rejected", "status": "resolved"}
        with patch.object(self.controller, "clock_trusted", side_effect=AssertionError("must not recheck")):
            self.assertEqual(self.controller.verify("u1", REQUEST), (401, self.db.original))
        self.assertEqual([c[0] for c in self.db.calls], ["lookup"])

    def test_unknown_clock_never_mutates_or_counts_failure(self):
        self.db.mode = "wall"
        with patch.object(self.controller, "clock_trusted", return_value=False):
            self.assertEqual(self.controller.verify("u1", REQUEST)[0], 503)
        self.assertEqual([c[0] for c in self.db.calls], ["lookup", "clock"])

    def test_read_missing_is_unknown_not_retry_or_failure(self):
        status, result = self.controller.verify("u1", REQUEST, lookup_only=True)
        self.assertEqual((status, result["status"]), (202, "unresolved"))
        self.assertEqual([c[0] for c in self.db.calls], ["lookup"])

    def test_email_replay_and_unknown_do_not_redispatch(self):
        with patch.object(self.controller, "dispatch") as dispatch:
            for _ in range(3):
                status, result = self.controller.email("u1", {"operationId": OP})
                self.assertEqual(status, 202)
                self.assertFalse(result["full_login_issued"])
            self.assertEqual(dispatch.call_count, 1)

    def test_effect_then_lost_local_result_can_only_read(self):
        self.config["email_operations"][OP]["fault"] = "after_effect_before_result"
        with patch.object(self.controller, "dispatch") as dispatch:
            with self.assertRaises(Unavailable): self.controller.email("u1", {"operationId": OP})
            self.controller.email("u1", {"operationId": OP}, lookup_only=True)
            self.controller.email("u1", {"operationId": OP})
            self.assertEqual(dispatch.call_count, 1)

    def test_lost_seal_response_never_sends(self):
        with patch.object(self.db, "call", side_effect=Unavailable("lost DB reply")):
            with patch.object(self.controller, "dispatch") as dispatch:
                with self.assertRaises(Unavailable): self.controller.email("u1", {"operationId": OP})
                dispatch.assert_not_called()

    def test_conflicting_seal_cannot_disclose_old_outcome(self):
        with patch.object(self.db, "call", return_value={"http": 409, "dispatch_allowed": False}) as call:
            with patch.object(self.controller, "dispatch") as dispatch:
                self.assertEqual(self.controller.email("u1", {"operationId": OP})[0], 409)
                dispatch.assert_not_called()
                self.assertEqual(call.call_count, 1)

    def test_before_headers_closes_socket_without_read(self):
        self.config["email_operations"][OP]["fault"] = "before_headers"
        with patch("controller.http.client.HTTPConnection") as connection:
            self.controller.dispatch(self.config["email_operations"][OP])
            connection.return_value.request.assert_called_once()
            connection.return_value.sock.shutdown.assert_called_once()
            connection.return_value.getresponse.assert_not_called()
            connection.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
