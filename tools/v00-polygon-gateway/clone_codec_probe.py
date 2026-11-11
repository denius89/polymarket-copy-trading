"""Synthetic-only source-codec probe. No DB, real key file, cookie or provider access."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

EXPECTED_SHA256 = 'e8f62a46bd1a491c596c8154249eefb9b30ac26f55859a12294260835edf1a1f'


def probe(codec_path, *, require_native=True):
    path = Path(codec_path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError('unexpected source codec')
    spec = importlib.util.spec_from_file_location('polygon_probe_codec', path)
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    ids = {'cipher': 'cipher-1', 'context': 'context-1', 'credential': 'credential-1',
           'comparison': 'comparison-1', 'email_address': 'email-address-1', 'email_cipher': 'email-cipher-1'}
    old = {k: {'id': ids[k], 'hex': f'{i + 1:02x}' * 32} for i, k in enumerate(sorted(ids))}
    fresh = {k: dict(v) for k, v in old.items()}
    for i, purpose in enumerate(('context', 'credential', 'cipher')):
        fresh[purpose]['hex'] = f'{i + 16:02x}' * 32

    class MemoryKeys(codec.Keys):
        # Inherit actual proof/login framing. This override never reads a key file.
        def __init__(self, values):
            self.values = values
        def get(self, purpose, key_id):
            if self.values[purpose]['id'] != key_id:
                raise codec.Unavailable('synthetic purpose mismatch')
            return bytes.fromhex(self.values[purpose]['hex'])

    a, b = MemoryKeys(old), MemoryKeys(fresh)
    context_id = '11111111-1111-4111-8111-111111111111'
    login_id = '22222222-2222-4222-8222-222222222222'
    proof = codec.b64url(bytes(range(32)))
    assert a.proof(context_id, proof) != b.proof(context_id, proof)
    assert a.login(login_id, proof) != b.login(login_id, proof)
    result = {'format': 'polygon-clone-codec-probe-v1', 'actualSourceSha256': EXPECTED_SHA256,
        'contextOldProofDiffers': True, 'loginOldProofDiffers': True,
        'scope': 'actual source codecs, synthetic material only; no DB/Auth/browser proof'}
    try:
        sodium = codec.Sodium()
    except codec.Unavailable:
        if require_native:
            raise RuntimeError('native libsodium prerequisite unavailable') from None
        return result | {'nativeCipher': 'not_run_prerequisite_unavailable'}
    meta = dict(environment=codec.ENV, realm='user', login_id=login_id,
        secret_id='33333333-3333-4333-8333-333333333333', source_context_id=context_id,
        source_operation_id='44444444-4444-4444-8444-444444444444', owner_kind='login',
        owner_id=login_id, purpose='login_cookie', cipher_format=codec.CIPHER_FORMAT,
        credential_format=codec.LOGIN_FORMAT, reveal_until='2026-11-05T12:00:00.000Z')
    ad = codec.aad(meta)
    ciphertext, nonce = sodium.encrypt(proof.encode(), ad, a.get('cipher', 'cipher-1'))
    assert sodium.decrypt(ciphertext, nonce, ad, a.get('cipher', 'cipher-1')) == proof.encode()
    try:
        sodium.decrypt(ciphertext, nonce, ad, b.get('cipher', 'cipher-1'))
    except codec.Unavailable:
        pass
    else:
        raise AssertionError('old ciphertext accepted under a fresh cipher key')
    return result | {'nativeCipher': 'old_positive_and_fresh_negative_passed', 'sodiumVersion': sodium.version}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--codec', default='/app/tools/v00-session-recovery/crypto.py')
    parser.add_argument('--allow-missing-native', action='store_true')
    args = parser.parse_args()
    print(json.dumps(probe(args.codec, require_native=not args.allow_missing_native), sort_keys=True))
