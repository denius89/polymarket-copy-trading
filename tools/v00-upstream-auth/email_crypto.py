"""Explicit V00 test address codec; not a claim of complete D02 codec support."""
import base64
import hmac
import uuid

from dependency import ENV, Unavailable, mac
from email_input import canonical_email
from email_api import private_uid
from protocol import exact, require, timestamp, uid

FORMAT = "v00-test-email-xchacha20poly1305-v1"
FIELDS = "address_digest address_key_id secret_id ciphertext nonce key_id cipher_format reveal_until"


def address_digest(keys, canonical):
    require(canonical_email(canonical) == canonical)
    return mac(keys.get("email_address", "email-address-1"), "shadow.v00.email-address.v1",
               [ENV, "email_send", "ascii-email-v1", canonical])


def email_aad(context_id, secret_id, reveal_until):
    private_uid(context_id); private_uid(secret_id); timestamp(reveal_until)
    fields = [ENV, "user", secret_id, "context", context_id, "email_delivery", FORMAT, reveal_until]
    def frame(value):
        wire = value.encode("utf-8")
        return len(wire).to_bytes(4, "big") + wire
    return b"shadow.v00.email.aad.v1\0" + b"".join(frame(field) for field in fields)


def encrypt_email(keys, sodium, context_id, canonical, expires_at):
    require(canonical_email(canonical) == canonical)
    secret_id = str(uuid.uuid4())
    encrypted, nonce = sodium.encrypt(canonical.encode("ascii"),
        email_aad(context_id, secret_id, expires_at), keys.get("email_cipher", "email-cipher-1"))
    return {"address_digest": address_digest(keys, canonical), "address_key_id": "email-address-1",
            "secret_id": secret_id, "ciphertext": encrypted, "nonce": nonce,
            "key_id": "email-cipher-1", "cipher_format": FORMAT, "reveal_until": expires_at}


def decrypt_email(keys, sodium, context_id, material):
    exact(material, FIELDS + " context_id")
    require(material["context_id"] == context_id and material["cipher_format"] == FORMAT
            and material["address_key_id"] == "email-address-1" and material["key_id"] == "email-cipher-1")
    try:
        require(type(material["ciphertext"]) is str and type(material["nonce"]) is str)
        encrypted = base64.b64decode(material["ciphertext"], validate=True)
        nonce = base64.b64decode(material["nonce"], validate=True)
        require(17 <= len(encrypted) <= 270 and len(nonce) == 24
                and base64.b64encode(encrypted).decode() == material["ciphertext"]
                and base64.b64encode(nonce).decode() == material["nonce"])
        value = sodium.decrypt(material["ciphertext"], material["nonce"],
            email_aad(context_id, material["secret_id"], material["reveal_until"]),
            keys.get("email_cipher", material["key_id"])).decode("ascii")
        require(canonical_email(value) == value)
        require(type(material["address_digest"]) is str
                and hmac.compare_digest(address_digest(keys, value), material["address_digest"]))
    except (ValueError, TypeError, UnicodeError):
        raise Unavailable("address material unavailable") from None
    return value
