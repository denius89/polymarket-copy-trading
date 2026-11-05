"""Preparation-only private-config builder. No Docker, SQL execution or activation."""
from dataclasses import dataclass
import ipaddress
import json
import os
from pathlib import Path
from types import MappingProxyType
import re
import secrets
import stat
from urllib.parse import urlsplit, urlunsplit, parse_qsl

ORIGIN = 'https://localhost:18444'
OPERATOR_BASE = Path('/opt/shadow-polygon')
ROLES = ('polygon_runtime', 'polygon_ingress', 'polygon_witness', 'v00_auth')
PAPER_ROLE = 'polygon_paper_runtime'
AUTH_FIELDS = frozenset(('API_EXTERNAL_URL DB_NAMESPACE GOTRUE_API_HOST GOTRUE_API_PORT '
    'GOTRUE_DB_DATABASE_URL GOTRUE_DB_DRIVER GOTRUE_DB_MIGRATIONS_PATH '
    'GOTRUE_EXTERNAL_EMAIL_ENABLED GOTRUE_JWT_AUD GOTRUE_JWT_DEFAULT_GROUP_NAME '
    'GOTRUE_JWT_SECRET GOTRUE_MAILER_AUTOCONFIRM GOTRUE_MAILER_OTP_EXP '
    'GOTRUE_MAILER_OTP_LENGTH GOTRUE_MAILER_TEMPLATES_CONFIRMATION '
    'GOTRUE_MAILER_TEMPLATES_MAGIC_LINK GOTRUE_MFA_TOTP_ENROLL_ENABLED '
    'GOTRUE_MFA_TOTP_VERIFY_ENABLED GOTRUE_SITE_URL GOTRUE_SMTP_ADMIN_EMAIL '
    'GOTRUE_SMTP_HOST GOTRUE_SMTP_PORT').split())
KEY_IDS = {'cipher': 'cipher-1', 'comparison': 'comparison-1', 'context': 'context-1',
           'credential': 'credential-1', 'email_address': 'email-address-1', 'email_cipher': 'email-cipher-1'}
KEY_FIELDS = frozenset(KEY_IDS)


class ConfigRefusal(Exception):
    """Safe messages only: never attach input values, secrets or raw OS errors."""


def no_symlinks(path):
    path = Path(path)
    if not path.is_absolute():
        raise ConfigRefusal('absolute path required')
    for part in [*reversed(path.parents), path]:
        try:
            mode = part.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ConfigRefusal('symlink rejected')


def owned_root(root, run_id, base=OPERATOR_BASE):
    if not re.fullmatch('[0-9a-f]{8}', run_id):
        raise ConfigRefusal('invalid run id')
    root, base = Path(root), Path(base)
    if root != base / ('.browser-e2e.' + run_id):
        raise ConfigRefusal('root does not match run id')
    no_symlinks(root)
    if not root.is_dir() or root.resolve() != root:
        raise ConfigRefusal('existing canonical root required')
    meta = root.stat()
    if meta.st_uid != os.geteuid() or stat.S_IMODE(meta.st_mode) != 0o700:
        raise ConfigRefusal('owned private root required')
    return root


def safe_env(values):
    result = []
    for key, value in sorted(values.items()):
        if not re.fullmatch('[A-Z][A-Z0-9_]*', key) or type(value) is not str:
            raise ConfigRefusal('invalid environment shape')
        if value != value.strip() or any(ord(c) < 32 or ord(c) > 126 for c in value) or any(c in value for c in '$\\\''):
            raise ConfigRefusal('unsupported environment characters')
        result.append(key + '=' + value + '\n')
    return ''.join(result).encode()


def source_auth(values):
    if type(values) is not dict or set(values) - {'PATH'} != AUTH_FIELDS:
        raise ConfigRefusal('source Auth environment changed')
    if any(type(values[k]) is not str for k in AUTH_FIELDS):
        raise ConfigRefusal('invalid source Auth value type')
    db = urlsplit(values['GOTRUE_DB_DATABASE_URL'])
    if (db.scheme not in ('postgres', 'postgresql') or db.hostname != 'db'
            or db.port != 5432 or db.username != 'v00_auth' or db.path != '/shadow_v00'
            or db.fragment):
        raise ConfigRefusal('unexpected source Auth database target')
    query = parse_qsl(db.query, keep_blank_values=True, strict_parsing=True)
    if len({k for k, _ in query}) != len(query) or any(
            (k, v) not in [('search_path', 'auth'), ('options', '-csearch_path=auth'),
                           ('options', '-c search_path=auth'), ('sslmode', 'disable')]
            for k, v in query):
        raise ConfigRefusal('unexpected source Auth database options')
    if (values['GOTRUE_SMTP_HOST'] != 'mail' or values['GOTRUE_SMTP_PORT'] != '1025'
            or values['GOTRUE_MAILER_AUTOCONFIRM'] != 'false'
            or values['GOTRUE_MAILER_OTP_LENGTH'] != '6'
            or values['GOTRUE_EXTERNAL_EMAIL_ENABLED'] != 'true'
            or values['GOTRUE_API_PORT'] != '9999' or values['DB_NAMESPACE'] != 'auth'):
        raise ConfigRefusal('unexpected source test Auth profile')
    for field in ('GOTRUE_MAILER_TEMPLATES_CONFIRMATION', 'GOTRUE_MAILER_TEMPLATES_MAGIC_LINK'):
        u = urlsplit(values[field])
        if (u.scheme != 'http' or u.hostname != 'otp-template' or u.port != 8080
                or u.username or u.password or u.query or u.fragment
                or not re.fullmatch(r'/[A-Za-z0-9_-]+\.html', u.path)):
            raise ConfigRefusal('unexpected test mail template target')
    safe_env({k: values[k] for k in AUTH_FIELDS})
    return db


def source_keyset(values):
    if type(values) is not dict or set(values) != KEY_FIELDS:
        raise ConfigRefusal('source V00 keyset changed')
    for purpose, entry in values.items():
        if (type(entry) is not dict or set(entry) != {'id', 'hex'}
                or entry['id'] != KEY_IDS[purpose]
                or type(entry['hex']) is not str or not re.fullmatch('[0-9a-f]{64}', entry['hex'])):
            raise ConfigRefusal('invalid source V00 key entry')
    if len({entry['hex'] for entry in values.values()}) != len(KEY_IDS):
        raise ConfigRefusal('key purpose material must be distinct')


@dataclass(frozen=True)
class PrivatePlan:
    # Deliberately no __str__ dumping: repr hides all confidential payloads.
    files: dict
    def __post_init__(self):
        object.__setattr__(self, 'files', MappingProxyType(dict(self.files)))

    def __repr__(self):
        return '<PrivatePlan: confidential files; contents suppressed>'


def build_plan(auth_env, keys, *, run_id):
    if not re.fullmatch('[0-9a-f]{8}', run_id):
        raise ConfigRefusal('invalid installation run id')
    db = source_auth(auth_env)
    source_keyset(keys)
    used_material = {entry['hex'] for entry in keys.values()}
    def fresh():
        for _ in range(16):
            value = secrets.token_hex(32)
            if value not in used_material:
                used_material.add(value)
                return value
        raise ConfigRefusal('fresh independent material unavailable')
    clone_keys = {k: dict(v) for k, v in keys.items()}
    # Clone-only proposal: NEVER rotate the permanent profile or rewrite old rows.
    # Retaining old cipher material would still reveal copied old login cookies.
    for purpose in ('context', 'credential', 'cipher'):
        clone_keys[purpose]['hex'] = fresh()
    source_keyset(clone_keys)
    passwords = {role: fresh() for role in (*ROLES, PAPER_ROLE)}
    ingress = {'format': 'polygon-ingress-hmac-v1', 'hex': fresh()}
    cursor_id = secrets.token_hex(16)
    auth = {k: auth_env[k] for k in AUTH_FIELDS}
    auth.update(GOTRUE_DB_DATABASE_URL=urlunsplit((db.scheme, 'v00_auth:' + passwords['v00_auth'] + '@db:5432', db.path, db.query, '')),
                GOTRUE_JWT_SECRET=fresh(), GOTRUE_SITE_URL=ORIGIN,
                API_EXTERNAL_URL='http://auth:9999')
    gateway = {
        'PGPASSFILE': '/runtime/.pgpass', 'PGSERVICEFILE': '/runtime/pg_service.conf',
        'V00_POLYGON_ENABLED': '1', 'V00_POLYGON_PAPER_ENABLED': '1',
        'V00_ORIGIN': ORIGIN, 'V00_PROVIDER_ORIGIN': 'http://auth:9999',
        'V00_EMAIL_CONFIG': '/runtime/app.json', 'V00_KEY_FILE': '/runtime/keys.json',
        'V00_TLS_CERT_FILE': '/runtime/tls.crt', 'V00_TLS_KEY_FILE': '/runtime/tls.key',
        'POLYGON_API_GATEWAY_CONFIG': '/runtime/gateway-api.json',
    }
    for section, field in [('runtime', 'V00_EMAIL_PSQL_COMMAND_JSON'),
                           ('ingress', 'V00_EMAIL_INGRESS_PSQL_COMMAND_JSON'),
                           ('witness', 'V00_EMAIL_WITNESS_PSQL_COMMAND_JSON')]:
        gateway[field] = json.dumps(['psql', 'service=' + section], separators=(',', ':'))
    pg_service, pgpass = '', ''
    for section, role in zip(('runtime', 'ingress', 'witness'), ROLES):
        pg_service += f'[{section}]\nhost=db\nport=5432\ndbname=shadow_v00\nuser={role}\nconnect_timeout=3\n\n'
        pgpass += f'db:5432:shadow_v00:{role}:{passwords[role]}\n'
    api = dict(profile='polygon-paper-v1', origin=ORIGIN,
        databaseUrl=f'postgresql://{PAPER_ROLE}:{passwords[PAPER_ROLE]}@db:5432/shadow_v00',
        credentialKeyFile='/private/credential-key.json', cursorKeyFile='/private/cursor-key.json',
        calendarProfile=dict(node='24.22.2', icu='78.3', tzdb='2026e', temporalPolyfill='0.5.1'),
        startEnabled=False, bindHost='0.0.0.0', port=19090,
        ingress=dict(mode='gateway-monotonic-v1', keyFile='/private/ingress-key.json'))
    # Keep this copy's start gate false. A separate reviewed activation step is required.
    encode = lambda v: (json.dumps(v, separators=(',', ':')) + '\n').encode()
    files = {
        'clone-key-profile.json': (0, encode({'format': 'polygon-clone-key-profile-v1',
            'installationId': run_id, 'scope': 'disposable-fresh-auth-only',
            'freshPurposes': ['context', 'credential', 'cipher'],
            'retainedPurposes': ['email_address', 'email_cipher', 'comparison'],
            'oldKeyFallback': False, 'historicalRowsReencrypted': False,
            'productionRotation': False})),
        'auth.env': (0, safe_env(auth)), 'gateway.env': (0, safe_env(gateway)),
        'gateway/app.json': (65534, encode({'fixtures': {}})),
        'gateway/keys.json': (65534, encode(clone_keys)),
        'gateway/ingress-key.json': (65534, encode(ingress)),
        'gateway/pg_service.conf': (65534, pg_service.encode()),
        'gateway/.pgpass': (65534, pgpass.encode()),
        'api/api-config.json': (1000, encode(api)),
        'api/credential-key.json': (1000, encode({'credential': clone_keys['credential']})),
        'api/ingress-key.json': (1000, encode(ingress)),
        'api/cursor-key.json': (1000, encode({'format': 'q02-cursor-keyset-v1', 'enabled': True,
            'issuerKeyId': cursor_id, 'keys': [{'keyId': cursor_id, 'hex': fresh()}], 'revoked': []})),
    }
    sql = "\\set ON_ERROR_STOP on\nBEGIN;\nSET LOCAL password_encryption='scram-sha-256';\n"
    for role in ROLES:
        sql += f"ALTER ROLE {role} PASSWORD '{passwords[role]}';\n"
    sql += f"CREATE ROLE {PAPER_ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{passwords[PAPER_ROLE]}';\nCOMMIT;\n"
    files['roles-private.sql'] = (0, sql.encode())
    return PrivatePlan(files)


def _json(payload):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ConfigRefusal('duplicate private payload field')
            out[key] = value
        return out
    return json.loads(payload, object_pairs_hook=unique)


def _env(payload):
    values = {}
    for line in payload.decode('ascii').splitlines():
        key, sep, value = line.partition('=')
        if not sep or key in values:
            raise ConfigRefusal('invalid private environment')
        values[key] = value
    if safe_env(values) != payload:
        raise ConfigRefusal('noncanonical private environment')
    return values


def validate_semantics(plan, run_id, source_auth_env, source_keys):
    """Validate actual payloads before any filesystem write or readiness claim."""
    original_db = source_auth(source_auth_env)
    source_keyset(source_keys)
    get = lambda n: plan.files[n][1]
    profile = _json(get('clone-key-profile.json'))
    expected_profile = {'format': 'polygon-clone-key-profile-v1', 'installationId': run_id,
            'scope': 'disposable-fresh-auth-only', 'freshPurposes': ['context', 'credential', 'cipher'],
            'retainedPurposes': ['email_address', 'email_cipher', 'comparison'],
            'oldKeyFallback': False, 'historicalRowsReencrypted': False, 'productionRotation': False}
    if (type(profile) is not dict or set(profile) != set(expected_profile)
            or any(type(profile[k]) is not type(v) or profile[k] != v for k, v in expected_profile.items())):
        raise ConfigRefusal('unexpected clone installation profile')
    clone = _json(get('gateway/keys.json'))
    source_keyset(clone)
    old_values = {v['hex'] for v in source_keys.values()}
    for purpose in ('context', 'credential', 'cipher'):
        if clone[purpose]['hex'] in old_values:
            raise ConfigRefusal('old installation secret retained')
    for purpose in ('email_address', 'email_cipher', 'comparison'):
        if clone[purpose] != source_keys[purpose]:
            raise ConfigRefusal('unexpected historical compatibility key change')
    if _json(get('api/credential-key.json')) != {'credential': clone['credential']}:
        raise ConfigRefusal('credential subset mismatch')
    if _json(get('gateway/app.json')) != {'fixtures': {}}:
        raise ConfigRefusal('fixture configuration prohibited')
    ingress = _json(get('gateway/ingress-key.json'))
    if (type(ingress) is not dict or set(ingress) != {'format', 'hex'}
            or ingress['format'] != 'polygon-ingress-hmac-v1'
            or not re.fullmatch('[0-9a-f]{64}', ingress['hex'])
            or ingress != _json(get('api/ingress-key.json'))):
        raise ConfigRefusal('ingress purpose or cross-service mismatch')
    api = _json(get('api/api-config.json'))
    expected_api = dict(profile='polygon-paper-v1', origin=ORIGIN,
        credentialKeyFile='/private/credential-key.json', cursorKeyFile='/private/cursor-key.json',
        calendarProfile=dict(node='24.22.2', icu='78.3', tzdb='2026e', temporalPolyfill='0.5.1'),
        startEnabled=False, bindHost='0.0.0.0', port=19090,
        ingress=dict(mode='gateway-monotonic-v1', keyFile='/private/ingress-key.json'))
    if (set(api) != set(expected_api) | {'databaseUrl'} or api['startEnabled'] is not False
            or any(api[k] != v for k, v in expected_api.items())):
        raise ConfigRefusal('initial API configuration or disabled gate mismatch')
    node_db = urlsplit(api['databaseUrl'])
    if (node_db.scheme != 'postgresql' or node_db.hostname != 'db' or node_db.port != 5432
            or node_db.username != PAPER_ROLE or node_db.path != '/shadow_v00' or node_db.query or node_db.fragment):
        raise ConfigRefusal('unexpected Node database target')
    auth = _env(get('auth.env'));auth_db = source_auth(auth)
    changed = {'GOTRUE_DB_DATABASE_URL', 'GOTRUE_JWT_SECRET', 'GOTRUE_SITE_URL', 'API_EXTERNAL_URL'}
    if (any(auth[k] != source_auth_env[k] for k in AUTH_FIELDS - changed)
            or auth['API_EXTERNAL_URL'] != 'http://auth:9999' or auth['GOTRUE_SITE_URL'] != ORIGIN
            or auth_db.scheme != original_db.scheme or auth_db.query != original_db.query
            or auth_db.password == original_db.password
            or auth['GOTRUE_JWT_SECRET'] == source_auth_env['GOTRUE_JWT_SECRET']):
        raise ConfigRefusal('Auth policy or clone target changed unexpectedly')
    expected_gateway = {
        'PGPASSFILE': '/runtime/.pgpass', 'PGSERVICEFILE': '/runtime/pg_service.conf',
        'V00_POLYGON_ENABLED': '1', 'V00_POLYGON_PAPER_ENABLED': '1', 'V00_ORIGIN': ORIGIN,
        'V00_PROVIDER_ORIGIN': 'http://auth:9999', 'V00_EMAIL_CONFIG': '/runtime/app.json',
        'V00_KEY_FILE': '/runtime/keys.json', 'V00_TLS_CERT_FILE': '/runtime/tls.crt',
        'V00_TLS_KEY_FILE': '/runtime/tls.key', 'POLYGON_API_GATEWAY_CONFIG': '/runtime/gateway-api.json'}
    service_file = ''
    for section, role, field in [('runtime', 'polygon_runtime', 'V00_EMAIL_PSQL_COMMAND_JSON'),
                                ('ingress', 'polygon_ingress', 'V00_EMAIL_INGRESS_PSQL_COMMAND_JSON'),
                                ('witness', 'polygon_witness', 'V00_EMAIL_WITNESS_PSQL_COMMAND_JSON')]:
        expected_gateway[field] = json.dumps(['psql', 'service=' + section], separators=(',', ':'))
        service_file += f'[{section}]\nhost=db\nport=5432\ndbname=shadow_v00\nuser={role}\nconnect_timeout=3\n\n'
    if _env(get('gateway.env')) != expected_gateway or get('gateway/pg_service.conf') != service_file.encode():
        raise ConfigRefusal('gateway destinations or role connections mismatch')
    passwords = {'v00_auth': auth_db.password, PAPER_ROLE: node_db.password}
    lines = get('gateway/.pgpass').decode('ascii').splitlines()
    if len(lines) != 3:
        raise ConfigRefusal('invalid role password file')
    for role, line in zip(ROLES[:3], lines):
        parts = line.split(':')
        if len(parts) != 5 or parts[:4] != ['db', '5432', 'shadow_v00', role]:
            raise ConfigRefusal('role password scope mismatch')
        passwords[role] = parts[4]
    if (any(type(v) is not str or not re.fullmatch('[0-9a-f]{64}', v) for v in passwords.values())
            or len(set(passwords.values())) != 5):
        raise ConfigRefusal('invalid independent role password material')
    sql = "\\set ON_ERROR_STOP on\nBEGIN;\nSET LOCAL password_encryption='scram-sha-256';\n"
    for role in ROLES:
        sql += f"ALTER ROLE {role} PASSWORD '{passwords[role]}';\n"
    sql += f"CREATE ROLE {PAPER_ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{passwords[PAPER_ROLE]}';\nCOMMIT;\n"
    if get('roles-private.sql') != sql.encode():
        raise ConfigRefusal('role SQL differs from scoped preparation')
    cursor = _json(get('api/cursor-key.json'))
    if (set(cursor) != {'format', 'enabled', 'issuerKeyId', 'keys', 'revoked'}
            or cursor['format'] != 'q02-cursor-keyset-v1' or cursor['enabled'] is not True
            or not re.fullmatch('[0-9a-f]{32}', cursor['issuerKeyId']) or cursor['revoked'] != []
            or type(cursor['keys']) is not list or len(cursor['keys']) != 1
            or set(cursor['keys'][0]) != {'keyId', 'hex'}
            or cursor['keys'][0]['keyId'] != cursor['issuerKeyId']
            or not re.fullmatch('[0-9a-f]{64}', cursor['keys'][0]['hex'])):
        raise ConfigRefusal('initial cursor purpose mismatch')
    material = [v['hex'] for v in clone.values()] + [ingress['hex'], cursor['keys'][0]['hex'], auth['GOTRUE_JWT_SECRET']] + list(passwords.values())
    if any(type(v) is not str or not re.fullmatch('[0-9a-f]{64}', v) for v in material) or len(set(material)) != len(material):
        raise ConfigRefusal('private purpose material not independent')


def write_plan(root, run_id, plan, *, source_auth_env, source_keys, base=OPERATOR_BASE, chown=os.chown):
    # Caller must already own the exclusive root. This function never overwrites.
    root = owned_root(root, run_id, base)
    expected = {'auth.env': 0, 'gateway.env': 0, 'roles-private.sql': 0,
        'clone-key-profile.json': 0, 'gateway/app.json': 65534, 'gateway/keys.json': 65534,
        'gateway/ingress-key.json': 65534, 'gateway/pg_service.conf': 65534, 'gateway/.pgpass': 65534,
        'api/api-config.json': 1000, 'api/credential-key.json': 1000,
        'api/ingress-key.json': 1000, 'api/cursor-key.json': 1000}
    if not isinstance(plan, PrivatePlan) or set(plan.files) != set(expected):
        raise ConfigRefusal('closed private plan required')
    for name, entry in plan.files.items():
        if (type(entry) is not tuple or len(entry) != 2 or type(entry[0]) is not int
                or entry[0] != expected[name] or type(entry[1]) is not bytes or len(entry[1]) > 65536):
            raise ConfigRefusal('private plan ownership or payload mismatch')
    try:
        validate_semantics(plan, run_id, source_auth_env, source_keys)
    except (KeyError, ValueError, TypeError, UnicodeError, RecursionError):
        raise ConfigRefusal('invalid private semantic payload') from None
    ready_path = root / 'PRIVATE-PREPARED.json'
    no_symlinks(ready_path)
    if ready_path.exists():
        raise ConfigRefusal('completion marker already exists')
    private = root / 'private'
    no_symlinks(private)
    private.mkdir(mode=0o700)
    for name, uid in [('gateway', 65534), ('api', 1000)]:
        p = private / name
        p.mkdir(mode=0o700)
        chown(p, uid, uid)
    for name, (uid, payload) in plan.files.items():
        p = private / name
        if p.parent not in (private, private / 'gateway', private / 'api') or p.name in ('', '.', '..'):
            raise ConfigRefusal('private path outside allowlist')
        no_symlinks(p)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'wb', closefd=False) as f:
                f.write(payload)
            chown(p, uid, uid)
        finally:
            os.close(fd)
    complete = {'format': 'polygon-private-files-written-v1', 'runId': run_id,
        'filesWritten': len(plan.files), 'paperStartEnabled': False,
        'tlsPrepared': False, 'gatewayBound': False}
    ready_path = root / 'PRIVATE-PREPARED.json'
    pending = root / ('.PRIVATE-PREPARED.' + secrets.token_hex(8))
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        chown(pending, 0, 0)
        with os.fdopen(fd, 'wb', closefd=False) as f:
            f.write((json.dumps(complete, separators=(',', ':')) + '\n').encode())
            f.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    # Atomic, no-overwrite publication only after contents and metadata succeeded.
    try:
        os.link(pending, ready_path, follow_symlinks=False)
    finally:
        try:
            pending.unlink()
        except OSError:
            # Non-secret temporary metadata may remain. Completion was already
            # published only after all payload/ownership writes succeeded.
            pass
    # TLS and gateway-api.json are deliberately absent: no service may be started
    # as a complete browser profile until explicit source/TLS/IP binding checks.
    return {'format': 'polygon-private-preparation-v1', 'filesWritten': len(plan.files),
            'paperStartEnabled': False, 'tlsPrepared': False, 'gatewayBound': False}


def gateway_binding(api_ip, owned_network_cidr):
    ip = ipaddress.ip_address(api_ip)
    network = ipaddress.ip_network(owned_network_cidr, strict=True)
    private_ranges = [ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')]
    if (ip.version != 4 or network.version != 4 or ip not in network
            or not any(network.subnet_of(n) for n in private_ranges) or network.is_loopback or network.is_link_local
            or ip in (network.network_address, network.broadcast_address)):
        raise ConfigRefusal('upstream must belong to the owned private network')
    return {'format': 'polygon-gateway-v1', 'upstreamHost': str(ip), 'upstreamPort': 19090,
            'ingressKeyFile': '/runtime/ingress-key.json'}
