import json
import unittest

from dependency import Unavailable
from controller import Rejection
from email_api import context_view, dispatch_result, send_request
from provider import Provider
from test_bridge import uid
from test_provider import Connection


class EmailApiTests(unittest.TestCase):
    def test_closed_send_forms_fail_before_any_effect(self):
        a = {"requestSchemaVersion": "v1", "commandType": "C01", "authContextId": uid(),
             "authOperationId": uid(), "email": " X@Example.INVALID ", "locale": "en"}
        self.assertEqual(send_request(a, "C01"), "x@example.invalid")
        invalid = [a | {"email": 5}, a | {"locale": []}, a | {"commandType": "C03"},
                   a | {"providerId": uid()}, a | {"authOperationId": str(a["authOperationId"]).upper()},
                   {k: v for k, v in a.items() if k != "locale"}]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(Rejection) as denied:
                send_request(body, "C01")
            self.assertEqual(denied.exception.status, 400)
        resend = {k: v for k, v in a.items() if k != "email"} | {"commandType": "C03", "expectedChallengeId": uid()}
        self.assertIsNone(send_request(resend, "C03"))
        with self.assertRaises(Rejection):
            send_request(resend | {"email": a["email"]}, "C03")

    def test_context_projection_rejects_partial_or_misleading_groups(self):
        ctx = uid()
        v = {"authContextId": ctx, "stage": "ready", "accessConfirmed": False,
             "createdAt": "2026-11-04T12:00:00.000Z", "expiresAt": "2026-11-04T12:30:00.000Z",
             "emailCodeIssuedAt": None, "emailCodeExpiresAt": None, "currentEmailChallengeId": None,
             "currentTotpChallengeId": None, "totpChallengeIssuedAt": None, "totpChallengeExpiresAt": None,
             "loginCookieRecoveryDeadlineAt": None}
        context_view(v, ctx, True)
        context_view(v | {"accessConfirmed": True}, ctx)
        for changed in ({"email": "private@example.invalid"}, {"accessConfirmed": 0},
                        {"stage": "email_verification"}, {"currentEmailChallengeId": uid()},
                        {"expiresAt": "2026-11-04T12:31:00.000Z"}, {"authContextId": uid()}):
            with self.subTest(changed=changed), self.assertRaises(Unavailable):
                context_view(v | changed, ctx, True)

    def test_accepted_dispatch_is_resolved_historical_shape(self):
        v = {"kind": "email_dispatch_accepted", "acceptedAt": "2026-11-04T12:00:00.000Z",
             "challengeId": uid(), "resendNotBeforeAt": "2026-11-04T12:01:00.000Z"}
        dispatch_result(v, "C01")
        for changed in ({"delivered": True}, {"resendNotBeforeAt": "2026-11-04T12:00:59.999Z"},
                        {"challengeId": None}):
            with self.subTest(changed=changed), self.assertRaises(Unavailable):
                dispatch_result(v | changed, "C03")

    def test_existing_user_send_and_resend_use_one_passwordless_request(self):
        connection = Connection()
        connection.response.data = b"{}"
        provider = Provider("http://auth:9999", lambda: connection)
        status, body = provider.send_existing_email("synthetic@example.invalid", uid())
        self.assertEqual((status, body), (200, {}))
        self.assertEqual(len(connection.calls), 1)
        method, path, body, _ = connection.calls[0]
        self.assertEqual((method, path), ("POST", "/otp"))
        self.assertEqual(json.loads(body), {"email": "synthetic@example.invalid", "create_user": False})


if __name__ == "__main__":
    unittest.main()
