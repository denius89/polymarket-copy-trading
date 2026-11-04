"""Independent RFC6238 oracle for the isolated V00 SQL verifier.

No provider, database, environment, file or network reads. This module is a test
oracle, not the trusted runtime source of matched steps. Caller-supplied steps
are never accepted by the SQL bridge.
"""
import base64
import hashlib
import hmac
import re
import struct


def decode_seed(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z2-7]+', value):
        raise ValueError('unsupported factor encoding')
    try:
        decoded = base64.b32decode(value + '=' * ((-len(value)) % 8))
    except (ValueError, base64.binascii.Error):
        raise ValueError('unsupported factor encoding') from None
    if not decoded or base64.b32encode(decoded).decode().rstrip('=') != value:
        raise ValueError('noncanonical factor encoding')
    return decoded


def hotp(seed, step):
    if type(step) is not int or not 0 <= step <= 2**63 - 1:
        raise ValueError('invalid step')
    digest = hmac.new(seed, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 15
    binary = int.from_bytes(digest[offset:offset + 4], 'big') & 0x7fffffff
    return f'{binary % 1000000:06d}'


def matching_steps(encoded_seed, code, unix_seconds):
    if not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code):
        raise ValueError('invalid code shape')
    if type(unix_seconds) is not int or not 0 <= unix_seconds <= 2**63 - 1:
        raise ValueError('untrusted time')
    seed = decode_seed(encoded_seed)
    current = unix_seconds // 30
    return [step for step in range(max(0, current - 1), current + 2)
            if hmac.compare_digest(hotp(seed, step), code)]
