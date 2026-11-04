"""Executable bridge orchestration. DB guards are authoritative; no synthetic success.

This layer has no fixture routes or provider credential persistence. It releases
cookie material only after confirmed COMMIT. Transport and DB outcomes remain
separate. HTTP ingress/admission and real DB capability checks are dependencies.
"""
from dataclasses import dataclass
import hmac
import os
import time
import uuid

from dependency import Unavailable, aad, b64url, secret_bytes
from protocol import decode, require
from provider import UnknownOutcome, ConfirmedNotSent, six_digits


@dataclass(frozen=True)
class Outcome:
    http: int
    value: dict
    cookie: str | None = None
    expires: str | None = None


class Denied(Exception):
    def __init__(self, http, reason):
        self.http, self.reason = http, reason
        super().__init__(reason)


def read_ref(ref):
    return {key: ref[key] for key in ("context_id", "proof_digest", "operation_id", "action")}


class Bridge:
    def __init__(self, transaction, provider, keys, sodium):
        self.transaction, self.provider = transaction, provider
        self.keys, self.sodium = keys, sodium

    def call(self, tx, method, ref, extra=None, ids=None):
        value = tx.call(method, ref | (extra or {}))
        variant = decode(method, value, ref, ids)
        if variant == "error":
            raise Denied(value["http"], value["reason"])
        return variant, value

    def verify_email(self, ref, challenge_id, admission_id, executor_proof, email, code, fault="none", deadline=None):
        require(ref["action"] == "C02")
        six_digits(code)
        with self.transaction() as tx:
            _, seal = self.call(tx, "seal_email", ref,
                                {"challenge_id": challenge_id, "admission_id": admission_id,
                                 "executor_proof": executor_proof})
            tx.commit()
        if seal.get("dispatch_allowed", False):
            if deadline is not None and time.monotonic() >= deadline:
                raise Unavailable("dispatch budget exhausted")
            try:
                # Status/body never authorize finalization: the exact DB witness does.
                # Credentials in the response stay transient and are not used as proof.
                self.provider.verify_email(email, code, seal["dispatch_id"], fault=fault)
            except (UnknownOutcome, ConfirmedNotSent):
                pass  # No retry and no inferred rejection/rollback. Consult original witness.
        return self.plan("plan_email", ref, deadline=deadline)

    def verify_totp(self, ref, challenge_id, admission_id, executor_proof, code, deadline=None):
        require(ref["action"] == "AUTH_TOTP_VERIFY")
        six_digits(code)
        return self.plan("plan_totp", ref,
                         {"challenge_id": challenge_id, "admission_id": admission_id,
                          "executor_proof": executor_proof, "code": code}, deadline=deadline)

    def plan(self, method, ref, extra=None, deadline=None):
        ids = {"login_id": str(uuid.uuid4()), "secret_id": str(uuid.uuid4())}
        with self.transaction() as tx:
            variant, value = self.call(tx, method, ref, ids | (extra or {}), ids)
            if variant != "replay":
                self.check_budget(deadline)
            cookie = expires = None
            if variant == "plan":
                result, cookie, expires = self.finish(tx, ref, value, deadline)
                status = 200
            elif variant in {"replay", "intermediate"}:
                result = value["result"]
                kind = result["kind"]
                status = 401 if kind == "verification_rejected" else 200
                if kind == "auth_completion_not_issued":
                    status = 409
                if variant == "replay" and kind == "login_completed":
                    try:
                        _, recovered = self.call(tx, "recover", read_ref(ref))
                        require(recovered["result"] == result)
                        cookie, expires = self.recover_secret(recovered)
                    except Denied as denial:
                        if (denial.http, denial.reason) != (409, "AUTH_COOKIE_RECOVERY_CLOSED"):
                            raise
                        # Deadline closure may mutate window/erasure and must COMMIT.
            else:
                raise Unavailable("unexpected plan outcome")
            if variant != "replay":
                self.check_budget(deadline)
            tx.commit()
        return Outcome(status, result, cookie, expires)

    @staticmethod
    def check_budget(deadline):
        if deadline is not None and time.monotonic() >= deadline:
            raise Unavailable("original handler budget exhausted")

    def finish(self, tx, ref, plan, deadline=None):
        meta = plan["metadata"]
        value = b64url(os.urandom(32))
        ciphertext, nonce = self.sodium.encrypt(value.encode("ascii"), aad(meta),
                                               self.keys.get("cipher", "cipher-1"))
        material = {"cookie_digest": self.keys.login(meta["login_id"], value),
                    "ciphertext": ciphertext, "nonce": nonce, "key_id": "cipher-1",
                    "credential_key_id": "credential-1"}
        self.check_budget(deadline)
        _, completed = self.call(tx, "complete", ref, material)
        c = completed["result"]["completion"]
        require(c["loginId"] == meta["login_id"] and c["completedAt"] == plan["completed_at"]
                and completed["login_expires_at"] == plan["login_expires_at"])
        return completed["result"], value, completed["login_expires_at"]

    def recover_secret(self, value):
        plaintext = self.sodium.decrypt(value["ciphertext"], value["nonce"],
            aad(value["metadata"]), self.keys.get("cipher", value["key_id"]))
        try:
            cookie = plaintext.decode("ascii")
            secret_bytes(cookie)
            digest = self.keys.login(value["metadata"]["login_id"], cookie, value["credential_key_id"])
        except (ValueError, UnicodeError):
            raise Unavailable("invalid recovered credential") from None
        require(hmac.compare_digest(digest, value["cookie_digest"]))
        return cookie, value["login_expires_at"]

    def read(self, ref):
        with self.transaction() as tx:
            _, value = self.call(tx, "read_operation", ref)
            tx.commit()
        return Outcome(value["http"], value)

    def recover(self, ref):
        with self.transaction() as tx:
            try:
                _, value = self.call(tx, "recover", ref)
            except Denied as denial:
                if (denial.http, denial.reason) == (409, "AUTH_COOKIE_RECOVERY_CLOSED"):
                    tx.commit()
                raise
            cookie, expires = self.recover_secret(value)
            tx.commit()
        return Outcome(200, value["result"], cookie, expires)

    def q01(self, login_id, cookie_digest):
        with self.transaction() as tx:
            _, value = self.call(tx, "q01", {"login_id": login_id, "cookie_digest": cookie_digest})
            tx.commit()
        return Outcome(200, value)
