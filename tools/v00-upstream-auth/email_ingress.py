"""Early capture before DB waiting/cipher work; one immutable original budget."""
import hashlib
import os
import uuid

from bridge import Denied
from dependency import b64url
from email_clock import current_clock
from email_protocol import decode
from protocol import exact, require, timestamp, uid


class EmailIngress:
    def __init__(self, transaction):
        self.transaction = transaction

    def capture(self, ref):
        clock = current_clock()
        proof = b64url(os.urandom(32))
        fields = ref | {"executor_id": str(uuid.uuid4()),
                        "executor_proof_digest": hashlib.sha256(proof.encode("ascii")).hexdigest(),
                        "request_started_at": clock.started_at}
        with self.transaction() as tx:
            value = tx.call("capture", fields)
            if "reason" in value:
                decode("capture", value)
                raise Denied(value["http"], value["reason"])
            exact(value, "http admission_id created context_expires_at")
            require(type(value["created"]) is bool and type(value["http"]) is int and
                    value["http"] == (201 if value["created"] else 200))
            uid(value["admission_id"]); timestamp(value["context_expires_at"])
            tx.commit()
        return value["admission_id"], proof, value["context_expires_at"], value["created"]
