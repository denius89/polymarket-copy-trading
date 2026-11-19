"""Opt-in disposable browser operator. Default command is plan; never touches permanent gates."""
import argparse
import base64
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import tarfile
import time

from private_config import (ConfigRefusal, OPERATOR_BASE, build_plan, no_symlinks,
                            source_auth, source_keyset, write_plan, gateway_binding)
from operator_guards import (container_identity, network_identity, marker, private_tree,
                             runtime_options, unique_json, SERVICES, BINDS)
from eligibility_report import require_ready, SQL_SHA256

SOURCE = {'db': 'shadow-polygon-db-1', 'auth': 'shadow-polygon-auth-1', 'gateway': 'shadow-polygon-app-1'}
SOURCE_IDS = {'db': 'sha256:839fbb5a4942a7758dd93e18b42ea5649807491a0545b5eeeb8f0b8bb11857a5',
    'auth': 'sha256:1736a63078f5922b198c4cbe50f80ab9a2d3b54fe8b7b6cfb2e9dc5dbbc12c6b',
    'gateway': 'sha256:5981ac5b703b70c1bd0d940514007b47f7d7c81daa1e2ff666a8305bab69fc73'}
SOURCE_RELEASE = '2db10029126f83c2c6b3ba1f851f8caa416a2335a391eb7383c65439bf739dca'
PAPER_MANIFEST = 'e7a856711a1b8edf6275084c9b608d592f737efe464217584285cb30d7b1bc7d'
PAPER_ORDER = ['001-storage.sql', '002-guards-numbers.sql', '003-drafts-reviews.sql',
    '004-start.sql', '005-integrity.sql', '006-reads.sql', '007-operator-seed.sql']
STATE_FILE = 'OPERATOR-STATE.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, *, data=None, timeout=90):
    # Never print child argv/stdout/stderr: env/config/SQL may contain private values.
    try:
        result = subprocess.run(argv, input=data, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise ConfigRefusal('operator child unavailable; no automatic retry') from None
    if result.returncode:
        raise ConfigRefusal('operator child failed; no automatic retry')
    return result.stdout


def inspect_container(name):
    data = unique_json(run(['docker', 'inspect', name]))
    if type(data) is not list or len(data) != 1:
        raise ConfigRefusal('single container inspection required')
    return data[0]


def source_container(service):
    item = inspect_container(SOURCE[service])
    if (item['Config']['Labels'].get('com.docker.compose.project') != 'shadow-polygon'
            or item['Image'] != SOURCE_IDS[service]):
        raise ConfigRefusal('permanent source identity changed')
    return item


def private_source(path, uid=None):
    path = Path(path);no_symlinks(path);s = path.stat()
    if (not stat.S_ISREG(s.st_mode) or stat.S_IMODE(s.st_mode) != 0o600
            or (uid is not None and s.st_uid != uid)):
        raise ConfigRefusal('source private file permissions changed')
    return unique_json(path.read_bytes())


def exclusive(path, data, uid=0):
    path = Path(path);no_symlinks(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600);os.fchown(fd, uid, uid)
        with os.fdopen(fd, 'wb', closefd=False) as f:
            f.write(data);f.flush();os.fsync(fd)
    finally:
        os.close(fd)


def record(path, value):
    # Atomic journal replacement is restricted to this owned operator state file.
    path = Path(path);no_symlinks(path)
    temporary = path.with_name('.state-' + secrets.token_hex(8))
    exclusive(temporary, (json.dumps(value, separators=(',', ':')) + '\n').encode())
    os.replace(temporary, path)


def verify_package(package, expected_sha):
    package = Path(package);no_symlinks(package)
    if not package.is_dir() or package.resolve() != package:
        raise ConfigRefusal('canonical package directory required')
    manifest_path = package / 'PACKAGE.json'
    if digest(manifest_path) != expected_sha:
        raise ConfigRefusal('package manifest pin mismatch')
    manifest = unique_json(manifest_path.read_bytes())
    if (set(manifest) != {'format', 'sourceReleaseSha256', 'files'}
            or manifest['format'] != 'polygon-browser-package-v1'
            or manifest['sourceReleaseSha256'] != SOURCE_RELEASE or type(manifest['files']) is not dict):
        raise ConfigRefusal('unexpected package manifest')
    required = {'source-release.tar.gz', 'compose.disposable.template.json', 'eligibility.sql',
                'paper/SHA256SUMS', 'paper/008-operator-activate.sql', 'clone_codec_probe.py'} | {'paper/' + p for p in PAPER_ORDER}
    if not required.issubset(manifest['files']):
        raise ConfigRefusal('package incomplete')
    for name, sha in manifest['files'].items():
        rel = Path(name)
        if rel.is_absolute() or '..' in rel.parts or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ConfigRefusal('unsafe package member')
        file = package / rel;no_symlinks(file)
        if not file.is_file() or digest(file) != sha:
            raise ConfigRefusal('package source hash mismatch')
    if digest(package / 'source-release.tar.gz') != SOURCE_RELEASE or digest(package / 'eligibility.sql') != SQL_SHA256:
        raise ConfigRefusal('source release or eligibility pin mismatch')
    if digest(package / 'paper/SHA256SUMS') != PAPER_MANIFEST:
        raise ConfigRefusal('paper candidate pin mismatch')
    for line in (package / 'paper/SHA256SUMS').read_text().splitlines():
        sha, name = line.split(None, 1)
        rel = Path(name.strip())
        if rel.is_absolute() or '..' in rel.parts or digest(package / 'paper' / rel) != sha:
            raise ConfigRefusal('paper group leaf mismatch')
    actual = set()
    for file in package.rglob('*'):
        no_symlinks(file)
        if file.is_file():actual.add(str(file.relative_to(package)))
    if actual != set(manifest['files']) | {'PACKAGE.json'}:
        raise ConfigRefusal('package contains unpinned files')
    # A manifest must cover the actual executing control code as well.
    if package / 'browser_operator.py' != Path(__file__).resolve():
        raise ConfigRefusal('operator must execute from the pinned package')
    for name in ('browser_operator.py', 'private_config.py', 'operator_guards.py', 'eligibility_report.py'):
        if name not in manifest['files']:
            raise ConfigRefusal('control code missing from manifest')
    return package


def extract_release(archive, root):
    seen = set()
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            path = Path(member.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or path.parts[0] not in ('gateway', 'api', 'RELEASE-SHA256.json')
                    or (path.parts[0] == 'RELEASE-SHA256.json' and (len(path.parts) != 1 or not member.isfile()))
                    or not (member.isfile() or member.isdir()) or str(path) in seen):
                raise ConfigRefusal('unsafe release archive entry')
            seen.add(str(path))
        source.extractall(root)
    manifest = unique_json((root / 'RELEASE-SHA256.json').read_bytes())
    expected = manifest['files']
    found = {str(p.relative_to(root)) for n in ('gateway', 'api') for p in (root / n).rglob('*') if p.is_file()}
    if found != set(expected):
        raise ConfigRefusal('release file set differs from manifest')
    for rel, sha in expected.items():
        path = root / rel;no_symlinks(path)
        if digest(path) != sha:
            raise ConfigRefusal('release leaf hash mismatch')
    for name in ('gateway', 'api'):
        for path in [root / name, *(root / name).rglob('*')]:
            no_symlinks(path);path.chmod(0o755 if path.is_dir() else 0o644)


def login_probe_result(raw, role, expect_connected):
    value = unique_json(raw.strip())
    if expect_connected:
        if value != {'status': 'connected', 'currentUser': role}:
            raise ConfigRefusal('runtime LOGIN identity mismatch')
    elif (type(value) is not dict or set(value) != {'status', 'code', 'severity'}
            or value['status'] != 'refused' or value['code'] not in ('28000', '28P01')
            or value['severity'] != 'FATAL'):
        raise ConfigRefusal('negative LOGIN did not prove authentication refusal')
    return True


class Operator:
    def __init__(self, package, root, owned):
        self.package, self.root, self.owned = Path(package), Path(root), owned
        self.template = unique_json((self.package / 'compose.disposable.template.json').read_bytes())
        self.state = {'format': 'polygon-browser-state-v1', 'runId': owned['runId'],
            'phase': 'created', 'resourcesMayExist': False, 'sourceBackupOwned': False, 'activation': False}

    def save(self, phase):
        self.state['phase'] = phase;record(self.root / STATE_FILE, self.state)

    def compose(self, *args):
        return run(['docker', 'compose', '--env-file', str(self.root / 'compose.env'),
                    '-f', str(self.root / 'compose.json'), *args], timeout=120)

    def container(self, service):
        value = inspect_container(self.owned['project'] + '-' + service + '-1')
        identifier = container_identity(value, service, self.owned)
        ref = self.template['services'][service]['image']
        image = unique_json(run(['docker', 'image', 'inspect', ref]))[0]
        runtime_options(value, service, image_id=image['Id'], image_user=image['Config']['User'])
        return identifier, value

    def bind_sources(self):
        seen=[]
        for service in SERVICES:
            for rel,_ in BINDS[service].values():
                path=self.root/rel;no_symlinks(path)
                if not path.is_dir() or path.resolve()!=path:
                    raise ConfigRefusal('noncanonical or missing bind source')
                meta=path.stat()
                for other,device,inode in seen:
                    if (path==other or path.is_relative_to(other) or other.is_relative_to(path)
                            or (meta.st_dev,meta.st_ino)==(device,inode)):
                        raise ConfigRefusal('bind sources overlap or alias')
                seen.append((path,meta.st_dev,meta.st_ino))

    def psql(self, sql, *, args=(), source=False):
        if source:
            source_container('db');identifier = SOURCE['db']
        else:
            identifier, _ = self.container('db')
        return run(['docker', 'exec', '-i', '-u', 'postgres', identifier,
            'psql', '-XqAt', '-U', 'postgres', '-d', 'shadow_v00', '-v', 'ON_ERROR_STOP=1', *args], data=sql)

    def safety_snapshot(self, source=False):
        safety = unique_json(self.psql(b"BEGIN READ ONLY; SELECT jsonb_build_object('no_paper',NOT EXISTS(SELECT FROM pg_namespace WHERE nspname='polygon'),'synthetic_only',(SELECT count(*)=2 AND bool_and(email LIKE '%.invalid') FROM auth.users),'roles_ok',(SELECT count(*)=4 AND bool_and(rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls) FROM pg_roles WHERE rolname IN ('polygon_runtime','polygon_ingress','polygon_witness','v00_auth'))); ROLLBACK;", source=source).strip())
        if safety != {'no_paper': True, 'synthetic_only': True, 'roles_ok': True}:
            raise ConfigRefusal('source/copy scope or role safety changed')

    def resolve_actors(self, accounts, source=False):
        encoded = [base64.b64encode(a['email'].encode()).decode() for a in accounts]
        lookup = ("BEGIN READ ONLY; SET LOCAL row_security=off; SELECT jsonb_agg(actor_id ORDER BY slot) FROM (" +
            " UNION ALL ".join(f"SELECT {i+1} AS slot,s.actor_id FROM auth.users u JOIN v00_upstream.subjects s ON s.provider_user_id=u.id WHERE u.email=convert_from(decode('{value}','base64'),'UTF8')" for i,value in enumerate(encoded)) + ") q; ROLLBACK;").encode()
        identifiers = unique_json(self.psql(lookup, source=source).strip())
        if (type(identifiers) is not list or len(identifiers) != 2 or identifiers[0] == identifiers[1]
                or any(type(v) is not str or not re.fullmatch('[0-9a-f-]{36}', v) for v in identifiers)):
            raise ConfigRefusal('trusted alias-to-actor mapping incomplete')
        return identifiers

    def source_inputs(self):
        auth = source_container('auth');source_container('gateway')
        env = dict(x.split('=', 1) for x in auth['Config']['Env'] if '=' in x)
        source_auth(env)
        self.safety_snapshot(source=True)
        keys = private_source('/opt/shadow-polygon/private/runtime/keys.json', 65534);source_keyset(keys)
        accounts = []
        for alias in ('owner1', 'owner2'):
            entry = private_source('/opt/shadow-polygon/private/entry/' + alias + '-client.json')
            if (set(entry) != {'email', 'origin'} or entry['origin'] != 'https://localhost:18443'
                    or type(entry['email']) is not str or not entry['email'].endswith('.invalid')
                    or not entry['email'].isascii() or entry['email'] != entry['email'].lower()):
                raise ConfigRefusal('trusted synthetic account manifest changed')
            accounts.append({'alias': alias, 'email': entry['email']})
        if accounts[0]['email'] == accounts[1]['email']:
            raise ConfigRefusal('synthetic addresses must differ')
        identifiers = self.resolve_actors(accounts, source=True)
        for account, actor in zip(accounts, identifiers):account['actorId'] = actor
        return env, keys, accounts

    def eligibility(self, accounts, source=False):
        args = ['-v', 'owner1_actor_id=' + accounts[0]['actorId'], '-v', 'owner2_actor_id=' + accounts[1]['actorId']]
        raw = self.psql((self.package / 'eligibility.sql').read_bytes(), args=args, source=source)
        return require_ready(raw, 0, [a['actorId'] for a in accounts])

    def backup(self):
        source_container('db')
        inside = '/tmp/polygon-browser-base-' + self.owned['runId']
        nonce = self.state['sourceBackupNonce'] = secrets.token_hex(32)
        self.state['sourceBackupAttempted'] = True;self.save('before-source-backup-claim')
        # Source-side directory is claimed only if created exclusively with a marker.
        script = 'set -eu; test ! -e "$1"; mkdir -m 700 "$1"; printf "%s" "$2" > "$1/.scope"'
        run(['docker', 'exec', '-u', 'postgres', SOURCE['db'], 'bash', '-c', script, '--', inside, nonce.encode().decode()])
        self.state['sourceBackupOwned'] = True;self.save('backup-owned')
        # pg_basebackup requires an empty destination; scope marker lives beside it.
        run(['docker', 'exec', '-u', 'postgres', SOURCE['db'], 'pg_basebackup', '-U', 'postgres',
             '-D', inside + '/data', '-X', 'stream', '--checkpoint=fast'], timeout=180)
        run(['docker', 'exec', '-u', 'postgres', SOURCE['db'], 'pg_verifybackup', inside + '/data'], timeout=120)
        (self.root / 'base').mkdir(mode=0o700)
        run(['docker', 'cp', SOURCE['db'] + ':' + inside + '/data/.', str(self.root / 'base')], timeout=120)
        for path in [self.root / 'base', *(self.root / 'base').rglob('*')]:
            no_symlinks(path);os.chown(path, 999, 999)
        self.save('physical-copy-verified')

    def tls(self):
        private = self.root / 'private/gateway'
        key, cert = private / 'tls.key', private / 'tls.crt'
        if key.exists() or cert.exists():raise ConfigRefusal('TLS output must be absent')
        run(['openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
            '-sha256', '-days', '1', '-nodes', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
            '-keyout', str(key), '-out', str(cert)])
        for path in (key, cert):
            no_symlinks(path);path.chmod(0o600);os.chown(path, 65534, 65534)
        pub = run(['openssl', 'x509', '-in', str(cert), '-pubkey', '-noout'])
        der = run(['openssl', 'pkey', '-pubin', '-outform', 'DER'], data=pub)
        self.state['tlsSpki'] = base64.b64encode(hashlib.sha256(der).digest()).decode()

    def network(self):
        data = unique_json(run(['docker', 'network', 'inspect', self.owned['network']]))[0]
        allowed = []
        for service in SERVICES:
            identifier, _ = self.container(service);allowed.append(identifier)
        network_identity(data, self.owned, allowed_endpoint_ids=allowed)
        configs = data['IPAM']['Config']
        if len(configs) != 1:raise ConfigRefusal('single owned IPv4 subnet required')
        cidr = str(ipaddress.ip_network(configs[0]['Subnet'], strict=True))
        return cidr

    def hba(self, cidr):
        network = ipaddress.ip_network(cidr)
        if network.version != 4 or not network.is_private or network.is_loopback:
            raise ConfigRefusal('unexpected owned subnet')
        root = self.root / 'base';no_symlinks(root / 'pg_hba.conf')
        content = ('local all postgres peer\nlocal all all reject\n'
            f'host shadow_v00 v00_auth,polygon_runtime,polygon_ingress,polygon_witness,polygon_paper_runtime {cidr} scram-sha-256\n'
            'host all all 0.0.0.0/0 reject\nhost all all ::/0 reject\n').encode()
        temporary = root / '.hba-owned-new';exclusive(temporary, content, 999)
        os.replace(temporary, root / 'pg_hba.conf')

    def prepare(self):
        env, keys, accounts = self.source_inputs()
        self.eligibility(accounts, source=True)
        extract_release(self.package / 'source-release.tar.gz', self.root)
        # Only public mail templates are copied, no source private directory tree.
        templates = self.root / 'templates';templates.mkdir(mode=0o755)
        for item in Path('/opt/shadow-polygon/templates').iterdir():
            no_symlinks(item)
            if not item.is_file() or item.suffix != '.html':raise ConfigRefusal('unexpected test template')
            shutil.copyfile(item, templates / item.name);(templates / item.name).chmod(0o644)
        plan = build_plan(env, keys, run_id=self.owned['runId'])
        write_plan(self.root, self.owned['runId'], plan, source_auth_env=env, source_keys=keys)
        exclusive(self.root / 'ACCOUNTS.json', (json.dumps(accounts) + '\n').encode())
        self.tls();self.backup()
        shutil.copyfile(self.package / 'compose.disposable.template.json', self.root / 'compose.json')
        exclusive(self.root / 'compose.env', ('SHADOW_E2E_ID=' + self.owned['runId'] + '\nSHADOW_E2E_ROOT=' + str(self.root) + '\n').encode())
        self.bind_sources();private_tree(self.root,tls_ready=True)
        self.compose('config', '--quiet')
        self.state['resourcesMayExist'] = True;self.save('creating-owned-services')
        self.compose('create', '--no-build', '--pull', 'never')
        cidr = self.network();self.hba(cidr)
        self.compose('start', 'db', 'mail', 'otp-template')
        db, _ = self.container('db')
        deadline = time.monotonic() + 45
        while True:
            try:
                run(['docker', 'exec', '-u', 'postgres', db, 'pg_isready', '-U', 'postgres'], timeout=5)
                break
            except ConfigRefusal:
                if time.monotonic() >= deadline:raise ConfigRefusal('copy database readiness failed')
                time.sleep(.5)
        self.safety_snapshot()
        if self.resolve_actors(accounts) != [a['actorId'] for a in accounts]:
            raise ConfigRefusal('copied account bindings changed since source capture')
        self.eligibility(accounts)
        self.psql((self.root / 'private/roles-private.sql').read_bytes())
        self.eligibility(accounts)
        for name in PAPER_ORDER:
            args = ['-v', 'polygon_tzdb_version=2026e'] if name.startswith('007') else []
            self.psql((self.package / 'paper' / name).read_bytes(), args=args)
        self.login_probes()
        # Prove every actual prepared payload still equals the validated immutable plan.
        for name, (_, payload) in plan.files.items():
            no_symlinks(self.root / 'private' / name)
            if (self.root / 'private' / name).read_bytes() != payload:
                raise ConfigRefusal('private preparation changed before activation')
        # Explicit clone-only activation, reachable only from acknowledged prepare command.
        self.psql((self.package / 'paper/008-operator-activate.sql').read_bytes(),
                  args=['-v', 'polygon_runtime_role=polygon_paper_runtime', '-v', 'polygon_tzdb_version=2026e'])
        checked = unique_json(self.psql(b"SELECT jsonb_build_object('profile',(SELECT count(*)=1 AND bool_and(enabled AND timezone_database_version='2026e') FROM polygon.profile),'controls',(SELECT count(*)=1 AND bool_and(enabled) FROM polygon.paper_controls),'membership',(SELECT count(*)=1 AND bool_and(roleid='polygon_executor'::regrole AND NOT admin_option) FROM pg_auth_members WHERE member='polygon_paper_runtime'::regrole),'sessions',(SELECT count(*) FROM polygon.paper_sessions));").strip())
        if checked != {'profile':True,'controls':True,'membership':True,'sessions':0}:
            raise ConfigRefusal('clone activation facts mismatch')
        api_cfg = self.root / 'private/api/api-config.json'
        config = private_source(api_cfg, 1000)
        if config['startEnabled'] is not False:raise ConfigRefusal('initial API gate changed')
        config['startEnabled'] = True
        temp = api_cfg.with_name('.activation-new');exclusive(temp, (json.dumps(config)+'\n').encode(),1000)
        os.replace(temp, api_cfg)
        exclusive(self.root / 'ACTIVATION.json', (json.dumps({'format':'polygon-clone-activation-v1',
            'runId':self.owned['runId'],'scope':'disposable-only','paper008Committed':True,
            'apiStartEnabled':True,'permanentActivation':False})+'\n').encode())
        self.state['activation'] = True;self.save('clone-only-paper-activated')
        self.bind_sources();private_tree(self.root,tls_ready=True)
        self.compose('start', 'auth', 'api')
        api, api_inspect = self.container('api')
        api_ip = api_inspect['NetworkSettings']['Networks'][self.owned['network']]['IPAddress']
        binding = gateway_binding(api_ip, cidr)
        exclusive(self.root / 'private/gateway/gateway-api.json', (json.dumps(binding)+'\n').encode(),65534)
        private_tree(self.root, bound=True)
        self.bind_sources()
        self.compose('start', 'gateway')
        gateway, info = self.container('gateway')
        self.state['gatewayIp'] = info['NetworkSettings']['Networks'][self.owned['network']]['IPAddress']
        self.network();self.wait_http(gateway,'http://auth:9999/health')
        self.wait_http(gateway,'https://localhost:8443/_polygon/health',gateway_tls=True)
        probe = (self.package / 'clone_codec_probe.py').read_bytes()
        native = unique_json(run(['docker','exec','-i',gateway,'python3','-'],data=probe).strip())
        if native.get('nativeCipher') != 'old_positive_and_fresh_negative_passed':
            raise ConfigRefusal('native synthetic codec prerequisite failed')
        self.save('services-started-not-browser-proven')
        return {'runId': self.owned['runId'], 'gatewayIp': self.state['gatewayIp'],
                'tlsSpki': self.state['tlsSpki'], 'origin': 'https://localhost:18444',
                'browserPass': False, 'permanentActivation': False}

    def wait_http(self, identifier, url, gateway_tls=False):
        # Read-only liveness prerequisite only. It never claims Auth/browser readiness.
        code = ("import urllib.request,ssl; c=ssl._create_unverified_context(); "
                "r=urllib.request.Request("+repr(url)+",headers={'Host':'localhost:18444'}); "
                "x=urllib.request.urlopen(r,timeout=2,context=c); "
                "assert x.status in (200,204)").encode()
        deadline=time.monotonic()+45
        while True:
            try:
                run(['docker','exec','-i',identifier,'python3','-'],data=code,timeout=4);return
            except ConfigRefusal:
                if time.monotonic()>=deadline:raise ConfigRefusal('private service liveness failed')
                time.sleep(.5)

    def login_probes(self):
        # Start only the already-pinned API with startEnabled=false; no gateway/Auth
        # exists yet. Typed pg error fields distinguish auth denial from infra errors.
        self.bind_sources();private_tree(self.root,tls_ready=True)
        self.compose('start','api')
        api,_=self.container('api')
        _, info=self.container('db')
        ip=info['NetworkSettings']['Networks'][self.owned['network']]['IPAddress']
        auth=dict(line.split('=',1) for line in (self.root/'private/auth.env').read_text().splitlines())
        from urllib.parse import urlsplit
        passwords={'v00_auth':urlsplit(auth['GOTRUE_DB_DATABASE_URL']).password,
            'polygon_paper_runtime':urlsplit(private_source(self.root/'private/api/api-config.json',1000)['databaseUrl']).password}
        for line in (self.root/'private/gateway/.pgpass').read_text().splitlines():
            fields=line.split(':');passwords[fields[3]]=fields[4]
        code = b"""import {createRequire} from 'node:module';
const require=createRequire('/api/apps/api/package.json'),{Client}=require('pg');
const client=new Client({host:process.env.PGHOST,port:5432,database:'shadow_v00',user:process.env.PGUSER,password:process.env.PGPASSWORD,connectionTimeoutMillis:3000,ssl:false});
try {await client.connect();const result=await client.query('SELECT current_user');console.log(JSON.stringify({status:'connected',currentUser:result.rows[0].current_user}));}
catch(error){if(['28000','28P01'].includes(error.code)&&error.severity==='FATAL')console.log(JSON.stringify({status:'refused',code:error.code,severity:error.severity}));else process.exitCode=2;}
finally{await client.end().catch(()=>{process.exitCode=2;});}
"""
        path=self.root/'.login-probe.env'
        def one(role,password,positive):
            exclusive(path,('PGHOST='+ip+'\nPGUSER='+role+'\nPGPASSWORD='+password+'\n').encode())
            try:
                raw=run(['docker','exec','-i','--env-file',str(path),api,'node','--input-type=module','-'],data=code,timeout=10)
                login_probe_result(raw,role,positive)
            finally:
                if path.exists():path.unlink()
        try:
            for role,password in passwords.items():one(role,password,True)
            for role in ('postgres','polygon_owner','v00_session_owner','v00_email_owner','polygon_paper_runtime'):
                one(role,'deliberately-wrong-synthetic-password',False)
        finally:
            # A later start must reload startEnabled=true only after explicit008.
            self.compose('stop','--timeout','10','api')
        self.save('five-positive-five-negative-logins')

    def cleanup(self):
        marker(self.root,self.owned['runId'],SOURCE_RELEASE)
        # Remove by immutable ID after complete scope validation, never by a name glob.
        for service in reversed(SERVICES):
            names = run(['docker','container','ls','-aq','--filter','name=^/'+self.owned['project']+'-'+service+'-1$']).strip()
            if names:
                if len(names.split()) != 1:raise ConfigRefusal('ambiguous cleanup container selector')
                value = inspect_container(names.decode());identifier = container_identity(value,service,self.owned)
                run(['docker','rm','-f',identifier])
        nets = run(['docker','network','ls','-q','--filter','name=^'+self.owned['network']+'$']).strip()
        if nets:
            if len(nets.split()) != 1:raise ConfigRefusal('ambiguous cleanup network selector')
            value=unique_json(run(['docker','network','inspect',nets.decode()]))[0]
            identifier=network_identity(value,self.owned,empty=True);run(['docker','network','rm',identifier])
        if self.state.get('sourceBackupAttempted'):
            source_container('db');inside='/tmp/polygon-browser-base-'+self.owned['runId']
            nonce=self.state['sourceBackupNonce'].encode()
            observed=run(['docker','exec',SOURCE['db'],'bash','-ceu',
                'if [ -d "$1" ]; then cat "$1/.scope"; else printf ABSENT; fi','--',inside])
            if observed != b'ABSENT':
                if observed != nonce:raise ConfigRefusal('source temporary backup ownership mismatch')
                run(['docker','exec',SOURCE['db'],'rm','-rf','--',inside])
        # Prove no remaining Docker mount references the owned root before removal.
        ids=run(['docker','ps','-aq']).split()
        if ids:
            all_containers=unique_json(run(['docker','inspect',*[x.decode() for x in ids]]))
            for value in all_containers:
                for m in value['Mounts']:
                    source=m.get('Source','')
                    if source==str(self.root) or source.startswith(str(self.root)+'/'):
                        raise ConfigRefusal('owned root still referenced by Docker')
        marker(self.root,self.owned['runId'],SOURCE_RELEASE)
        shutil.rmtree(self.root)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',nargs='?',default='plan',choices=['plan','prepare','cleanup'])
    parser.add_argument('--package',required=True);parser.add_argument('--package-sha',required=True)
    parser.add_argument('--run-id');parser.add_argument('--ack-disposable-real-auth',action='store_true')
    parser.add_argument('--ack-clone-only-008',action='store_true');args=parser.parse_args()
    package=verify_package(Path(args.package),args.package_sha)
    if args.action=='plan':
        print(json.dumps({'scope':'disposable real Auth/browser; no permanent activation',
                          'sourceRelease':SOURCE_RELEASE,'executionAuthorizedByPlan':False}));return
    if os.geteuid()!=0:raise ConfigRefusal('root operator required')
    if args.action=='prepare':
        if not args.ack_disposable_real_auth or not args.ack_clone_only_008:
            raise ConfigRefusal('explicit reviewed execution scope required')
        run_id=secrets.token_hex(4);root=OPERATOR_BASE/('.browser-e2e.'+run_id);no_symlinks(root);root.mkdir(mode=0o700)
        owned={'format':'polygon-browser-e2e-owned-v1','runId':run_id,'root':str(root),
               'project':'shadow-browser-e2e-'+run_id,'network':'shadow-browser-e2e-'+run_id+'_lab',
               'sourceReleaseSha256':SOURCE_RELEASE}
        exclusive(root/'OWNED.json',(json.dumps(owned)+'\n').encode());op=Operator(package,root,owned);op.save('created')
        print(json.dumps({'event':'owned-run-created','runId':run_id,'root':str(root)}),flush=True)
        try:print(json.dumps(op.prepare(),sort_keys=True))
        except Exception:
            op.state['lastCompletedPhase']=op.state['phase'];op.save('failed-no-automatic-retry')
            # Retain exact owned root for inspected cleanup. Never infer that a timed-out
            # create/COMMIT did not happen, and never remove data under uncertain mounts.
            raise ConfigRefusal('preparation failed; inspect and cleanup this owned run') from None
    else:
        if not args.run_id:raise ConfigRefusal('run id required')
        root=OPERATOR_BASE/('.browser-e2e.'+args.run_id);owned=marker(root,args.run_id,SOURCE_RELEASE)
        op=Operator(package,root,owned);op.state=private_source(root/STATE_FILE,0);op.cleanup()
        print(json.dumps({'runId':args.run_id,'cleanupCompleted':True}))


if __name__=='__main__':
    try:main()
    except ConfigRefusal:
        raise SystemExit('Operator refused; no retry or broader cleanup performed')
