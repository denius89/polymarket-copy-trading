"""Read-only scope guards. No resource creation, deletion, SQL or network calls."""
import json
from pathlib import Path
import re
import stat

from private_config import ConfigRefusal, no_symlinks, owned_root, OPERATOR_BASE

SERVICES = ('db', 'auth', 'mail', 'otp-template', 'gateway', 'api')
BINDS = {
    'db': {'/var/lib/postgresql/data': ('base', True)},
    'auth': {}, 'mail': {},
    'otp-template': {'/templates': ('templates', False)},
    'gateway': {'/app': ('gateway', False), '/runtime': ('private/gateway', False)},
    'api': {'/api': ('api', False), '/private': ('private/api', False)},
}
TMPFS = {'db': {'/tmp', '/var/run/postgresql'}, 'auth': {'/tmp'}, 'mail': {'/tmp'},
         'otp-template': {'/tmp', '/var/lib/postgresql/data'},
         'gateway': {'/tmp', '/var/lib/postgresql/data'}, 'api': {'/tmp'}}
PRIVATE_OWNERS = {
    'auth.env': 0, 'gateway.env': 0, 'roles-private.sql': 0, 'clone-key-profile.json': 0,
    'gateway/app.json': 65534, 'gateway/keys.json': 65534,
    'gateway/ingress-key.json': 65534, 'gateway/pg_service.conf': 65534,
    'gateway/.pgpass': 65534, 'api/api-config.json': 1000,
    'api/credential-key.json': 1000, 'api/ingress-key.json': 1000, 'api/cursor-key.json': 1000,
}
BOUND_OWNERS = {'gateway/tls.crt': 65534, 'gateway/tls.key': 65534, 'gateway/gateway-api.json': 65534}


def unique_json(raw):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ConfigRefusal('duplicate manifest field')
            result[k] = v
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise ConfigRefusal('invalid manifest JSON') from None


def marker(root, run_id, release_sha, *, base=OPERATOR_BASE):
    root = owned_root(root, run_id, base)
    if not re.fullmatch('[0-9a-f]{64}', release_sha):
        raise ConfigRefusal('invalid release hash')
    expected = {'format': 'polygon-browser-e2e-owned-v1', 'runId': run_id,
        'root': str(root), 'project': 'shadow-browser-e2e-' + run_id,
        'network': 'shadow-browser-e2e-' + run_id + '_lab', 'sourceReleaseSha256': release_sha}
    p = root / 'OWNED.json'
    no_symlinks(p)
    meta = p.stat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_uid != root.stat().st_uid or stat.S_IMODE(meta.st_mode) != 0o600:
        raise ConfigRefusal('invalid marker ownership or mode')
    if unique_json(p.read_bytes()) != expected:
        raise ConfigRefusal('owned marker mismatch')
    return expected


def private_tree(root, *, bound=False):
    """Actual UID/mode/shape proof; invoke only on Oracle, never infer from mocks."""
    root = Path(root)
    expected = PRIVATE_OWNERS | (BOUND_OWNERS if bound else {})
    private = root / 'private'
    no_symlinks(private)
    for rel, uid in [('', 0), ('gateway', 65534), ('api', 1000)]:
        directory = private / rel
        no_symlinks(directory)
        meta = directory.stat()
        if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != uid or stat.S_IMODE(meta.st_mode) != 0o700:
            raise ConfigRefusal('private directory permissions mismatch')
    found = set()
    for p in private.rglob('*'):
        no_symlinks(p)
        meta = p.lstat()
        if stat.S_ISDIR(meta.st_mode):
            if p not in (private / 'gateway', private / 'api'):
                raise ConfigRefusal('unexpected private directory')
            continue
        rel = str(p.relative_to(private))
        if (rel not in expected or not stat.S_ISREG(meta.st_mode)
                or meta.st_uid != expected[rel] or stat.S_IMODE(meta.st_mode) != 0o600):
            raise ConfigRefusal('private file permissions or allowlist mismatch')
        found.add(rel)
    if found != set(expected):
        raise ConfigRefusal('private file set incomplete')


def container_identity(inspect, service, owned):
    """Return immutable Docker ID only after proving exact labels/mounts/network."""
    if service not in SERVICES:
        raise ConfigRefusal('unknown disposable service')
    try:
        labels = inspect['Config']['Labels']
        if (labels.get('com.docker.compose.project') != owned['project']
                or labels.get('com.docker.compose.service') != service
                or labels.get('shadow.scope') != 'browser-e2e'
                or labels.get('shadow.run-id') != owned['runId']
                or inspect['Name'] != '/' + owned['project'] + '-' + service + '-1'):
            raise ConfigRefusal('container ownership mismatch')
        host = inspect['HostConfig']
        if (host['Privileged'] is not False or host['PortBindings'] not in ({}, None)
                or host['NetworkMode'] != owned['network']
                or set(inspect['NetworkSettings']['Networks']) != {owned['network']}
                or host['CapAdd'] not in ([], None)
                or host['CapDrop'] != ['ALL']
                or host['SecurityOpt'] != ['no-new-privileges:true']):
            raise ConfigRefusal('container isolation mismatch')
        found = {}
        for m in inspect['Mounts']:
            if m['Type'] == 'tmpfs':
                if m['Destination'] not in TMPFS[service]:
                    raise ConfigRefusal('unexpected temporary mount')
                continue
            destination = m['Destination']
            if m['Type'] != 'bind' or destination in found or destination not in BINDS[service]:
                raise ConfigRefusal('unexpected bind or volume')
            rel, writable = BINDS[service][destination]
            if m['Source'] != str(Path(owned['root']) / rel) or m['RW'] is not writable:
                raise ConfigRefusal('container mount scope mismatch')
            found[destination] = rel
        if set(found) != set(BINDS[service]):
            raise ConfigRefusal('required mount missing')
        if set(host['Tmpfs']) != TMPFS[service]:
            raise ConfigRefusal('temporary mount set mismatch')
        identifier = inspect['Id']
        if not re.fullmatch('[0-9a-f]{64}', identifier):
            raise ConfigRefusal('invalid Docker container id')
        return identifier
    except (KeyError, TypeError, AttributeError):
        raise ConfigRefusal('incomplete container inspection') from None


def network_identity(inspect, owned, *, empty=False, allowed_endpoint_ids=()):
    try:
        labels = inspect['Labels']
        if (inspect['Name'] != owned['network'] or inspect['Internal'] is not True
                or inspect['Driver'] != 'bridge' or inspect['EnableIPv6'] is not False
                or labels.get('shadow.scope') != 'browser-e2e'
                or labels.get('shadow.run-id') != owned['runId']
                or labels.get('com.docker.compose.project') != owned['project']
                or labels.get('com.docker.compose.network') != 'lab'):
            raise ConfigRefusal('network ownership or isolation mismatch')
        endpoints = set(inspect['Containers'])
        if empty and endpoints:
            raise ConfigRefusal('owned network still has endpoints')
        if not endpoints.issubset(set(allowed_endpoint_ids)):
            raise ConfigRefusal('unowned network endpoint')
        identifier = inspect['Id']
        if not re.fullmatch('[0-9a-f]{64}', identifier):
            raise ConfigRefusal('invalid Docker network id')
        return identifier
    except (KeyError, TypeError, AttributeError):
        raise ConfigRefusal('incomplete network inspection') from None


def runtime_options(inspect, service, *, image_id, image_user):
    """Separate from cleanup eligibility: prove runtime image, UID and read-only mode."""
    if service not in SERVICES or not re.fullmatch('sha256:[0-9a-f]{64}', image_id):
        raise ConfigRefusal('invalid runtime expectation')
    fixed_user = {'db': 'postgres', 'gateway': '65534:65534', 'api': '1000:1000',
                  'otp-template': '65534:65534'}.get(service, image_user)
    try:
        if (inspect['Image'] != image_id or inspect['Config']['User'] != fixed_user
                or inspect['HostConfig']['ReadonlyRootfs'] is not (service != 'db')
                or inspect['HostConfig']['RestartPolicy']['Name'] not in ('', 'no')):
            raise ConfigRefusal('runtime image/user/filesystem mismatch')
    except (KeyError, TypeError):
        raise ConfigRefusal('incomplete runtime inspection') from None
