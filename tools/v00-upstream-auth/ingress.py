"""Private capture before the handler's executable work; no durable raw proof."""
import hashlib
import json
import os
import uuid

from dependency import ENV, b64url, mac
from protocol import decode, exact, require, uid
from bridge import Denied


def intent(keys, body, proof_digest):
    # This closed body contains ASCII UUIDs/enums only after API validation.
    # Lexical sorted compact JSON is therefore the JCS representation here.
    public = {k: v for k, v in body.items() if k != "code"}
    wire = json.dumps(public, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ctx, op, action = body["authContextId"], body["authOperationId"], body["commandType"]
    comparison = mac(keys.get("comparison", "comparison-1"), "shadow.auth.sensitive-compare.v1",
                     [ENV, "context", ctx, action, op, "otp_code", body["code"]])
    return {"context_id": ctx, "operation_id": op, "action": action,
            "proof_digest": proof_digest, "fingerprint": hashlib.sha256(wire).hexdigest(),
            "comparison_hmac": comparison, "comparison_key_id": "comparison-1"}


class Ingress:
    def __init__(self, transaction):
        self.transaction = transaction

    def capture(self, ref):
        proof = b64url(os.urandom(32))
        fields = ref | {"executor_id": str(uuid.uuid4()),
                        "executor_proof_digest": hashlib.sha256(proof.encode("ascii")).hexdigest()}
        with self.transaction() as tx:
            value = tx.call("capture", fields)
            if "reason" in value:
                decode("capture", value)
                raise Denied(value["http"], value["reason"])
            exact(value, "http admission_id created")
            require(type(value["created"]) is bool and type(value["http"]) is int and
                    value["http"] == (201 if value["created"] else 200))
            uid(value["admission_id"])
            tx.commit()
        # A repeated capture never recovers the old proof. DB only allows replay
        # or the already sealed finalizer, not a fresh network/verification permit.
        return value["admission_id"], proof
