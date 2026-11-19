"""Verify the public JS vector with native libsodium; no runtime key/DB/network access."""
import base64
import ctypes as C
import ctypes.util
import json
import sys

value = json.loads(sys.stdin.read(4096))
assert set(value) == {"purpose", "wire"} and value["purpose"] == "public-test-vector-only"
wire = base64.urlsafe_b64decode(value["wire"] + "=" * (-len(value["wire"]) % 4))
assert base64.urlsafe_b64encode(wire).decode().rstrip("=") == value["wire"]
header = bytes([1]) + bytes([1]) * 16
nonce, key = bytes(range(24)), bytes(range(32))
assert wire[:17] == header and wire[17:41] == nonce
ad = b"shadow.q02.cursor.v1\0" + header
payload = {"requestSchemaVersion": "v1", "environmentBinding": "a" * 64,
           "readerBinding": "b" * 64, "venueId": "00000010-1111-4111-8111-111111111111",
           "venueCode": "polymarket", "limit": 2, "lastTraderId": "00000002-1111-4111-8111-111111111111",
           "catalogFingerprint": "c" * 64}
plain = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
lib = C.CDLL(ctypes.util.find_library("sodium") or "libsodium.so.23")
lib.sodium_init.restype = C.c_int
assert lib.sodium_init() >= 0
lib.sodium_version_string.restype = C.c_char_p
enc = lib.crypto_aead_xchacha20poly1305_ietf_encrypt
enc.argtypes = [C.c_void_p, C.POINTER(C.c_ulonglong), C.c_void_p, C.c_ulonglong,
                C.c_void_p, C.c_ulonglong, C.c_void_p, C.c_void_p, C.c_void_p]
enc.restype = C.c_int
dec = lib.crypto_aead_xchacha20poly1305_ietf_decrypt
dec.argtypes = [C.c_void_p, C.POINTER(C.c_ulonglong), C.c_void_p, C.c_void_p,
                C.c_ulonglong, C.c_void_p, C.c_ulonglong, C.c_void_p, C.c_void_p]
dec.restype = C.c_int
out, size = C.create_string_buffer(len(plain) + 16), C.c_ulonglong()
assert enc(out, C.byref(size), plain, len(plain), ad, len(ad), None, nonce, key) == 0
assert header + nonce + out.raw[:size.value] == wire
clear, count = C.create_string_buffer(len(plain)), C.c_ulonglong()
cipher = wire[41:]
assert dec(clear, C.byref(count), None, cipher, len(cipher), ad, len(ad), nonce, key) == 0
assert clear.raw[:count.value] == plain
tampered = cipher[:-1] + bytes([cipher[-1] ^ 1])
assert dec(clear, C.byref(count), None, tampered, len(tampered), ad, len(ad), nonce, key) == -1
print(json.dumps({"verdict": "pass", "native_sodium": lib.sodium_version_string().decode(),
                  "wire_bytes": len(wire), "plaintext_bytes": len(plain),
                  "exact_encryption_match": True, "decryption_match": True, "tampered_tag_rejected": True}))
