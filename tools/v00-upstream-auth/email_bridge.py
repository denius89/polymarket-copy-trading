"""Email entry orchestration; current DB guards remain authoritative."""
import os
import uuid

from bridge import Bridge, Denied, Outcome
from dependency import b64url, Unavailable
from email_crypto import decrypt_email
from email_protocol import decode
from provider import ConfirmedNotSent, UnknownOutcome, six_digits


class EmailBridge(Bridge):
    def __init__(self, transaction, provider, keys, sodium, witness_transaction, ingress_transaction):
        super().__init__(transaction, provider, keys, sodium)
        self.witness_transaction = witness_transaction
        self.ingress_transaction = ingress_transaction

    def call(self, tx, method, ref, extra=None, ids=None):
        value = tx.call(method, ref | (extra or {}))
        variant = decode(method, value, ref, ids)
        if variant == "error":
            raise Denied(value["http"], value["reason"])
        return variant, value

    def create_context(self):
        context_id, proof = str(uuid.uuid4()), b64url(os.urandom(32))
        ref = {"context_id": context_id, "proof_digest": self.keys.proof(context_id, proof)}
        with self.ingress_transaction() as tx:
            _, value = self.call(tx, "context_create", ref)
            tx.commit()
        # A lost COMMIT reply cannot emit a cookie; a new empty context is allowed
        # only via a new explicit preparation, before any C01 external effect.
        return value, proof

    def context(self, context_id, proof_digest, confirm=False):
        with self.transaction() as tx:
            _, value = self.call(tx, "context_read" if confirm else "context_for_send",
                                 {"context_id": context_id, "proof_digest": proof_digest})
            tx.commit()
        return value

    def send(self, ref, admission_id, executor_proof, email_binding=None, deadline=None):
        with self.transaction() as tx:
            variant, sealed = self.call(tx, "seal_send", ref,
                {"admission_id": admission_id, "executor_proof": executor_proof, "email_binding": email_binding})
            tx.commit()
        if variant == "replay":
            return Outcome(sealed["historical_http_status"], sealed["result"])
        if sealed["dispatch_allowed"]:
            if sealed["locale"] != "en":
                raise Unavailable("mail locale capability unavailable")
            email = decrypt_email(self.keys, self.sodium, ref["context_id"], sealed["email_material"])
            self.check_budget(deadline)
            try:
                status, response = self.provider.send_existing_email(email, sealed["dispatch_id"])
            except (UnknownOutcome, ConfirmedNotSent):
                pass
            else:
                if type(status) is int and status == 200 and type(response) is dict and not response:
                    # Distinct role, no caller success flag. DB additionally requires
                    # the exact changed provider generation for this one seal.
                    with self.witness_transaction() as tx:
                        self.call(tx, "send_observed", {"dispatch_id": sealed["dispatch_id"]})
                        tx.commit()
        with self.transaction() as tx:
            variant, value = self.call(tx, "finalize_send", ref)
            if variant != "replay":
                self.check_budget(deadline)
            tx.commit()
        return Outcome(value["historical_http_status"], value["result"])

    def verify_entry(self, ref, challenge_id, admission_id, executor_proof, code, deadline=None):
        six_digits(code)
        with self.transaction() as tx:
            variant, sealed = self.call(tx, "seal_verify", ref,
                {"admission_id": admission_id, "executor_proof": executor_proof, "code": code})
            if variant != "replay":
                self.check_budget(deadline)
            tx.commit()  # Includes proven rejection and its single counter update.
        if variant == "intermediate":
            return Outcome(sealed["historical_http_status"], sealed["result"])
        if variant != "replay" and sealed["dispatch_allowed"]:
            email = decrypt_email(self.keys, self.sodium, ref["context_id"], sealed["email_material"])
            self.check_budget(deadline)
            try:
                self.provider.verify_email(email, code, sealed["dispatch_id"])
            except (UnknownOutcome, ConfirmedNotSent):
                pass
        # Replay and completion use the same original operation. Generic provider
        # errors never create a negative result here; the independent DB proof does.
        return self.plan("plan_email", ref, deadline=deadline)

    def verify_totp(self, ref, challenge_id, admission_id, executor_proof, code, deadline=None):
        six_digits(code)
        # The immutable admission already carries challenge_id. No second caller
        # challenge field can replace that source at the plan boundary.
        return self.plan("plan_totp", ref, {"admission_id": admission_id,
            "executor_proof": executor_proof, "code": code}, deadline=deadline)
