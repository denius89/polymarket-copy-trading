"""Runtime library smoke checks; not independent cryptographic certification."""
import json
from crypto import Sodium, Unavailable


def run():
    sodium = Sodium()
    key, wrong_key = bytes(range(32)), bytes(range(1, 33))  # Public test vectors only.
    plaintext, ad = b"public D03-07 library probe", b"public associated data"
    cipher, nonce = sodium.encrypt(plaintext, ad, key)
    assert sodium.decrypt(cipher, nonce, ad, key) == plaintext
    for altered_ad, k in ((ad + b"!", key), (ad, wrong_key)):
        try:
            sodium.decrypt(cipher, nonce, altered_ad, k)
        except Unavailable:
            continue
        raise AssertionError("tamper accepted")
    return {"library": "libsodium", "version": sodium.version, "roundtrip": True,
            "wrong_aad_rejected": True, "wrong_key_rejected": True}


if __name__ == "__main__":
    try:
        print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps({"passed": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
