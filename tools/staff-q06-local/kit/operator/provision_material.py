"""Offline operator material for the accepted synthetic pilot; no network or DB calls."""
import base64
from datetime import datetime, timedelta, time, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import struct
import sys
import uuid
from zoneinfo import ZoneInfo

UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
KEY_NAMES = ('permit', 'context', 'login', 'cipher', 'logout', 'ingress-auth', 'ingress-reader', 'network')


def exact(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise ValueError('invalid shape')
    return value


def identifier(value):
    if not isinstance(value, str) or not UUID.fullmatch(value):
        raise ValueError('invalid identifier')
    return value


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z', value):
        raise ValueError('invalid time')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.isoformat(timespec='milliseconds').replace('+00:00', 'Z') != value:
        raise ValueError('noncanonical time')
    return result


def descriptor(value):
    exact(value, ('version', 'runId', 'origin', 'openedAt', 'cutoffAt'))
    if value['version'] != 'pilot-staff-deployment-v1' or value['origin'] != 'https://localhost:18443':
        raise ValueError('wrong deployment')
    identifier(value['runId'])
    opened, cutoff = timestamp(value['openedAt']), timestamp(value['cutoffAt'])
    zone = ZoneInfo('Europe/Warsaw')
    expected = datetime.combine(opened.astimezone(zone).date() + timedelta(days=1), time(23), zone)
    if cutoff != expected.astimezone(timezone.utc) or cutoff <= opened:
        raise ValueError('wrong calendar cutoff')
    # Only ASCII strings in this closed descriptor; matches sorted-key canonical JSON.
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return raw, hashlib.sha256(raw).hexdigest()


def permit_digest(run_id, deployment_digest, permit_id, raw_secret, key):
    identifier(run_id)
    identifier(permit_id)
    if not re.fullmatch('[a-f0-9]{64}', deployment_digest) or len(raw_secret) != 32 or len(key) != 32:
        raise ValueError('invalid proof input')
    data = b'shadow.pilot.permit-proof.v1\0'
    for part in (run_id.encode('ascii'), deployment_digest.encode('ascii'), permit_id.encode('ascii'), raw_secret):
        data += struct.pack('>I', len(part)) + part
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def read_input(path):
    path = Path(path).absolute()
    for directory in (path.parent, *path.parent.parents):
        if directory.is_symlink():
            raise ValueError('symlink parent')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o600 or s.st_size > 8192:
            raise ValueError('private input required')
        def pairs(items):
            result = {}
            for k, v in items:
                if k in result:
                    raise ValueError('duplicate field')
                result[k] = v
            return result
        return json.loads(f.read(), object_pairs_hook=pairs)


def materialize(config, output):
    exact(config, ('descriptor', 'targetUserIds'))
    raw_descriptor, digest = descriptor(config['descriptor'])
    targets = config['targetUserIds']
    if type(targets) is not list or len(targets) != 2 or len(set(targets)) != 2:
        raise ValueError('two distinct targets required')
    for target in targets:
        identifier(target)
    output = Path(output).absolute()
    parent = output.parent
    for directory in (parent, *parent.parents):
        if directory.is_symlink():
            raise ValueError('symlink parent')
    ps = parent.stat()
    if ps.st_uid != os.getuid() or stat.S_IMODE(ps.st_mode) & 0o077:
        raise ValueError('private owned parent required')
    output.mkdir(mode=0o700)  # Fail if any previous attempt exists; never overwrite it.
    def write(name, content):
        data = content if isinstance(content, bytes) else (json.dumps(content, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
        with os.fdopen(os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    write('INCOMPLETE', b'Not ready for use\n')
    keys = {name: secrets.token_bytes(32) for name in KEY_NAMES}
    if len(set(keys.values())) != len(KEY_NAMES):
        raise ValueError('duplicate key')
    for name, value in keys.items():
        write(name + '.key', value)
    d = config['descriptor']
    principals = []
    for ordinal in (1, 2):
        principal_id, permit_id = str(uuid.uuid4()), str(uuid.uuid4())
        secret = secrets.token_bytes(32)
        principals.append({'principal_id': principal_id, 'permit_id': permit_id,
            'permit_digest': permit_digest(d['runId'], digest, permit_id, secret, keys['permit'])})
        write(f'owner-{ordinal}.json', {'displayLabel': f'владелец {ordinal}', 'origin': d['origin'],
            'permitId': permit_id, 'secret': base64.urlsafe_b64encode(secret).decode('ascii').rstrip('='), 'cutoffAt': d['cutoffAt']})
    write('descriptor.json', raw_descriptor)
    write('runtime-binding.json', {'runId': d['runId'], 'deploymentDigest': digest, 'cipherKeyId': str(uuid.uuid4()), 'cutoffAt': d['cutoffAt']})
    write('provision.json', {'request_id': str(uuid.uuid4()), 'run_id': d['runId'], 'deployment_digest': digest,
        'origin': d['origin'], 'opened_at': d['openedAt'], 'cutoff_at': d['cutoffAt'],
        'principals': principals, 'targets': [{'user_id': target} for target in targets]})
    (output / 'INCOMPLETE').unlink()
    write('READY', b'Offline material only; database not provisioned\n')
    return digest


def main():
    try:
        if len(sys.argv) != 3:
            raise ValueError('usage')
        digest = materialize(read_input(sys.argv[1]), sys.argv[2])
        print(json.dumps({'status': 'material_created', 'deploymentDigest': digest, 'databaseTouched': False}))
    except Exception:
        print('{"status":"material_failed","databaseTouched":false}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
