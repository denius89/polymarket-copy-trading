import unittest

from bridge import Denied
from dependency import Unavailable
from email_bridge import EmailBridge
from email_crypto import encrypt_email
from provider import UnknownOutcome
from test_bridge import Cipher, Factory, Keys, Tx, uid
from test_ingress_app import ProofKeys


NOW = "2026-11-04T12:00:00.000Z"
EXPIRY = "2026-11-04T12:30:00.000Z"


def reply(result, http, replay=False):
    return {"http": 200 if replay else http, "replay": replay, "result": result,
            "resolved_at": NOW, "historical_http_status": http}


class Provider:
    def __init__(self, before=None, response=(200, None), fail=False):
        self.before, self.response, self.fail, self.calls = before, response, fail, []

    def send_existing_email(self, email, dispatch):
        if self.before:
            self.before()
        self.calls.append((email, dispatch))
        if self.fail:
            raise UnknownOutcome("simulated")
        return self.response[0], {} if self.response[1] is None else self.response[1]

    def verify_email(self, *args):
        self.calls.append(args)
        return 403, {"error_code": "otp_expired"}


class EmailBridgeTests(unittest.TestCase):
    def setUp(self):
        self.keys, self.cipher = ProofKeys(), Cipher()
        self.ref = {"context_id": uid(), "proof_digest": "b" * 64, "operation_id": uid(),
                    "action": "C01", "fingerprint": "c" * 64, "comparison_hmac": "d" * 64,
                    "comparison_key_id": "comparison-1"}
        binding = encrypt_email(self.keys, self.cipher, self.ref["context_id"], "synthetic@example.invalid", EXPIRY)
        self.seal = {"http": 200, "dispatch_allowed": True, "dispatch_id": uid(),
                     "email_material": binding | {"context_id": self.ref["context_id"]}, "locale": "en"}
        self.accepted = {"kind": "email_dispatch_accepted", "acceptedAt": NOW,
                         "challengeId": uid(), "resendNotBeforeAt": "2026-11-04T12:01:00.000Z"}

    def bridge(self, provider, transactions, witness=(), ingress=()):
        return EmailBridge(Factory(*transactions), provider, self.keys, self.cipher,
                           Factory(*witness), Factory(*ingress))

    def test_seal_commit_precedes_provider_and_witness_commit_precedes_finalize(self):
        sealed = Tx([("seal_send", self.seal)])
        observed = Tx([("send_observed", {"http": 200, "recorded": True})])
        def final(_):
            self.assertTrue(observed.committed)
            return reply(self.accepted, 202)
        finalized = Tx([("finalize_send", final)])
        provider = Provider(before=lambda: self.assertTrue(sealed.committed))
        result = self.bridge(provider, [sealed, finalized], [observed]).send(self.ref, uid(), "proof")
        self.assertEqual(result.http, 202)
        self.assertEqual(len(provider.calls), 1)
        self.assertTrue(finalized.committed)
        self.assertEqual(observed.calls[0][1], {"dispatch_id": self.seal["dispatch_id"]})

    def test_lost_seal_commit_never_calls_provider(self):
        provider = Provider()
        sealed = Tx([("seal_send", self.seal)], commit_failure=True)
        with self.assertRaises(Unavailable):
            self.bridge(provider, [sealed]).send(self.ref, uid(), "proof")
        self.assertEqual(provider.calls, [])

    def test_unknown_or_unexpected_provider_reply_never_creates_witness_or_retries(self):
        for provider in (Provider(fail=True), Provider(response=(503, {})),
                         Provider(response=(200, {"unexpected": True}))):
            with self.subTest(provider=provider):
                sealed = Tx([("seal_send", self.seal)])
                final = Tx([("finalize_send", {"http": 503, "reason": "SERVICE_UNAVAILABLE"})])
                with self.assertRaises(Denied) as error:
                    self.bridge(provider, [sealed, final]).send(self.ref, uid(), "proof")
                self.assertEqual(error.exception.http, 503)
                self.assertEqual(len(provider.calls), 1)
                self.assertFalse(final.committed)

    def test_nonpermit_and_replay_never_dispatch(self):
        provider = Provider()
        final = Tx([("finalize_send", {"http": 503, "reason": "SERVICE_UNAVAILABLE"})])
        with self.assertRaises(Denied):
            self.bridge(provider, [Tx([("seal_send", self.seal | {"dispatch_allowed": False})]), final]).send(self.ref, uid(), "proof")
        saved = Tx([("seal_send", reply(self.accepted, 202, True))])
        result = self.bridge(provider, [saved]).send(self.ref, uid(), "proof", deadline=0)
        self.assertEqual(result.http, 202)
        self.assertEqual(provider.calls, [])

    def test_expired_original_budget_never_dispatches(self):
        provider = Provider()
        with self.assertRaises(Unavailable):
            self.bridge(provider, [Tx([("seal_send", self.seal)])]).send(self.ref, uid(), "proof", deadline=0)
        self.assertEqual(provider.calls, [])

    def test_negative_is_committed_without_provider_and_commit_loss_is_unknown(self):
        rejection = {"kind": "verification_rejected", "reasonCode": "AUTH_VERIFICATION_FAILED"}
        ref = self.ref | {"action": "C02"}
        for lost in (False, True):
            provider = Provider()
            negative = Tx([("seal_verify", reply(rejection, 401))], commit_failure=lost)
            bridge = self.bridge(provider, [negative])
            if lost:
                with self.assertRaises(Unavailable):
                    bridge.verify_entry(ref, uid(), uid(), "proof", "012345")
            else:
                self.assertEqual(bridge.verify_entry(ref, uid(), uid(), "proof", "012345").http, 401)
                self.assertTrue(negative.committed)
            self.assertEqual(provider.calls, [])

    def test_generic_provider_403_does_not_create_negative_result(self):
        seal = {k: v for k, v in self.seal.items() if k != "locale"}
        plan = Tx([("plan_email", {"http": 503, "reason": "SERVICE_UNAVAILABLE"})])
        provider = Provider()
        with self.assertRaises(Denied) as denied:
            self.bridge(provider, [Tx([("seal_verify", seal)]), plan]).verify_entry(
                self.ref | {"action": "C02"}, uid(), uid(), "proof", "012345")
        self.assertEqual(denied.exception.http, 503)
        self.assertEqual(len(provider.calls), 1)
        self.assertFalse(plan.committed)


if __name__ == "__main__":
    unittest.main()
