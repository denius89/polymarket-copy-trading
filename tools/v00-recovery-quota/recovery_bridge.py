"""One HTTP admission, one durable attempt, one bound subject transaction.

The trusted adapter has no SAVEPOINT, automatic retry or persisted executor
secret. No cookie is returned on any unknown COMMIT, even after a real commit.
"""
from datetime import timedelta
import hashlib
import os
import re
import uuid

import bootstrap
from bridge import Denied, Outcome, read_ref
from dependency import Unavailable, b64url
from email_bridge import EmailBridge
from email_clock import current_clock
from protocol import decode, exact, require, timestamp, uid


def recovery_deadline():
    # The existing clock is captured before parsing and has a 10s endpoint.
    # Derive 5s from that same start, never from a later dispatch/DB phase.
    return current_clock().deadline - 5


def private_reply(method, value, fields):
    require(type(value) is dict and type(value.get("http")) is int)
    if "reason" in value:
        decode(method, value, fields)
        raise Denied(value["http"], value["reason"])
    if method == "recovery_admit":
        exact(value, "http admission_token deadline_at")
        require(value["http"] == 201 and value["admission_token"] == fields["admission_token"])
        uid(value["admission_token"])
        require(timestamp(value["deadline_at"]) == timestamp(fields["request_started_at"]) + timedelta(seconds=5))
    elif method == "recovery_target":
        exact(value, "http target_pid target_txid")
        require(value["http"] == 200 and type(value["target_pid"]) is int and value["target_pid"] > 0
                and type(value["target_txid"]) is str and re.fullmatch(r"[1-9][0-9]*", value["target_txid"]))
    elif method == "recovery_seal":
        exact(value, "http sealed admission_token target_pid target_txid")
        require(value["http"] == 200 and value["sealed"] is True
                and type(value["target_pid"]) is int and type(value["target_txid"]) is str
                and all(value[k] == fields[k] for k in ("admission_token", "target_pid", "target_txid")))
    else:
        raise Unavailable("unsupported private recovery reply")
    return value


class RecoveryBridge(EmailBridge):
    def __init__(self, *args, quota_transaction, subject_transaction, observe=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.quota_transaction = quota_transaction
        self.subject_transaction = subject_transaction
        self.observe = observe or (lambda *_: None)

    def call(self, tx, method, ref, extra=None, ids=None):
        if method == "recover":
            # Called by the inherited completion replay ONLY, in the same DB T
            # where plan_email/plan_totp established the exact replay permit.
            value = tx.call("recover_completion_replay", ref | (extra or {}))
            variant = decode("recover", value, ref, ids)
            if variant == "error":
                raise Denied(value["http"], value["reason"])
            return variant, value
        return super().call(tx, method, ref, extra, ids)

    def recover(self, ref):
        ref = read_ref(ref)
        require(ref["action"] in {"C02", "AUTH_TOTP_VERIFY"})
        deadline, clock = recovery_deadline(), current_clock()
        self.observe("recovery_entered", ref)
        self.check_budget(deadline)
        token, executor = str(uuid.uuid4()), str(uuid.uuid4())
        proof = b64url(os.urandom(32))
        admitted = ref | {"admission_token": token, "executor_id": executor,
            "executor_proof_digest": hashlib.sha256(proof.encode("ascii")).hexdigest(),
            "request_started_at": clock.started_at}
        self.observe("before_admission", admitted)
        with self.quota_transaction(deadline) as tx:
            private_reply("recovery_admit", tx.call("recovery_admit", admitted), admitted)
            self.check_budget(deadline)
            tx.commit()
        self.observe("admission_committed", admitted)
        self.check_budget(deadline)
        credentials = ref | {"admission_token": token, "executor_id": executor, "executor_proof": proof}
        with self.subject_transaction(deadline) as subject:
            target = private_reply("recovery_target", subject.call("recovery_target", {}), {})
            seal = credentials | {k: target[k] for k in ("target_pid", "target_txid")}
            self.observe("target_open", admitted | {k: target[k] for k in ("target_pid", "target_txid")})
            self.check_budget(deadline)
            with self.quota_transaction(deadline) as tx:
                private_reply("recovery_seal", tx.call("recovery_seal", seal), seal)
                self.check_budget(deadline)
                tx.commit()
            self.observe("attempt_committed", admitted)
            self.check_budget(deadline)
            self.observe("before_subject", admitted)
            value = subject.call("recovery_once", credentials)
            variant = decode("recover", value, ref)
            if variant == "error":
                if (value["http"], value["reason"]) == (409, "AUTH_COOKIE_RECOVERY_CLOSED"):
                    # Closure can erase expired material. Preserve this commit.
                    self.check_budget(deadline)
                    subject.commit()
                    self.observe("subject_committed", admitted)
                raise Denied(value["http"], value["reason"])
            self.check_budget(deadline)
            cookie, expires = self.recover_secret(value)
            self.check_budget(deadline)
            subject.commit()
            self.observe("subject_committed", admitted)
        self.check_budget(deadline)
        self.observe("cookie_ready", admitted)
        self.check_budget(deadline)
        return Outcome(200, value["result"], cookie, expires)
