"""Synthetic inputs only; filesystem tests do not start a service or database."""
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from urllib.parse import urlsplit

import private_config as p


def inputs():
    env = {k: 'fixture' for k in p.AUTH_FIELDS}
    env.update(API_EXTERNAL_URL='http://auth:9999', DB_NAMESPACE='auth',
        GOTRUE_DB_DATABASE_URL='postgresql://v00_auth:synthetic-old-password@db:5432/shadow_v00',
        GOTRUE_DB_DRIVER='postgres', GOTRUE_API_HOST='0.0.0.0', GOTRUE_API_PORT='9999',
        GOTRUE_SMTP_HOST='mail', GOTRUE_SMTP_PORT='1025',
        GOTRUE_MAILER_AUTOCONFIRM='false', GOTRUE_MAILER_OTP_LENGTH='6',
        GOTRUE_EXTERNAL_EMAIL_ENABLED='true', GOTRUE_SITE_URL='https://localhost:18443',
        GOTRUE_SMTP_ADMIN_EMAIL='test@example.invalid',
        GOTRUE_MAILER_TEMPLATES_CONFIRMATION='http://otp-template:8080/otp.html',
        GOTRUE_MAILER_TEMPLATES_MAGIC_LINK='http://otp-template:8080/otp.html')
    keys = {k: {'id': p.KEY_IDS[k], 'hex': f'{i + 1:02x}' * 32} for i, k in enumerate(sorted(p.KEY_FIELDS))}
    return env, keys


class PrivateConfigurationTests(unittest.TestCase):
    def test_node_receives_only_credential_subset_and_no_auth_password(self):
        env, keys = inputs();plan = p.build_plan(env, keys, run_id='0123abcd')
        subset = json.loads(plan.files['api/credential-key.json'][1])
        self.assertEqual(subset, {'credential': json.loads(plan.files['gateway/keys.json'][1])['credential']})
        self.assertNotEqual(subset['credential']['hex'], keys['credential']['hex'])
        node_files = b''.join(payload for name, (_, payload) in plan.files.items() if name.startswith('api/'))
        self.assertNotIn(b'synthetic-old-password', node_files)
        self.assertNotIn(b'email_cipher', node_files)
        self.assertNotIn(b'v00_auth:', node_files)
        self.assertNotIn('synthetic-old-password', repr(plan))

    def test_source_inputs_are_unchanged_and_generated_credentials_are_fresh(self):
        env, keys = inputs();before = json.dumps([env, keys], sort_keys=True)
        a = p.build_plan(env, keys, run_id='0123abcd');b = p.build_plan(env, keys, run_id='0123abcd')
        self.assertEqual(json.dumps([env, keys], sort_keys=True), before)
        self.assertNotEqual(a.files['auth.env'][1], b.files['auth.env'][1])
        self.assertNotEqual(a.files['api/cursor-key.json'][1], b.files['api/cursor-key.json'][1])
        self.assertNotIn(b'synthetic-old-password', a.files['auth.env'][1])

    def test_original_ingress_and_cursor_purposes_are_separate(self):
        plan = p.build_plan(*inputs(), run_id='0123abcd')
        gateway = json.loads(plan.files['gateway/ingress-key.json'][1])
        node = json.loads(plan.files['api/ingress-key.json'][1])
        cursor = json.loads(plan.files['api/cursor-key.json'][1])
        self.assertEqual(gateway, node)
        self.assertNotEqual(node['hex'], cursor['keys'][0]['hex'])
        self.assertNotEqual(node['hex'], inputs()[1]['credential']['hex'])

    def test_no_hidden_activation_or_fixture_login(self):
        plan = p.build_plan(*inputs(), run_id='0123abcd');api = json.loads(plan.files['api/api-config.json'][1])
        self.assertIs(api['startEnabled'], False)
        self.assertEqual(api['ingress']['mode'], 'gateway-monotonic-v1')
        self.assertEqual(api['origin'], 'https://localhost:18444')
        self.assertEqual(json.loads(plan.files['gateway/app.json'][1]), {'fixtures': {}})
        sql = plan.files['roles-private.sql'][1]
        for word in [b'GRANT ', b'UPDATE ', b'INSERT ', b'polygon.profile', b'\\i ', b'\\ir ', b'\\include ']:
            self.assertNotIn(word, sql)
        self.assertNotIn('gateway/gateway-api.json', plan.files)
        self.assertNotIn('gateway/tls.key', plan.files)

    def test_unknown_environment_or_external_targets_fail_closed(self):
        env, keys = inputs()
        for field, value in [('GOTRUE_EXTERNAL_GOOGLE_ENABLED', 'true'),
                             ('GOTRUE_SMTP_HOST', 'smtp.external.example'),
                             ('GOTRUE_DB_DATABASE_URL', 'postgresql://v00_auth:x@external.example:5432/shadow_v00'),
                             ('GOTRUE_MAILER_TEMPLATES_MAGIC_LINK', 'http://external.example:8080/otp.html')]:
            mutated = env | {field: value}
            with self.assertRaises(p.ConfigRefusal):p.build_plan(mutated, keys, run_id='0123abcd')

    def test_query_options_cannot_redirect_or_switch_roles(self):
        env, keys = inputs()
        for query in ['host=external.example', 'options=-crole=postgres', 'search_path=auth&search_path=public']:
            with self.assertRaises(p.ConfigRefusal):
                p.build_plan(env | {'GOTRUE_DB_DATABASE_URL': env['GOTRUE_DB_DATABASE_URL'] + '?' + query}, keys, run_id='0123abcd')

    def test_missing_or_wrong_credential_key_refuses(self):
        env, keys = inputs()
        for changed in [{}, keys | {'credential': {'id': 'other-id', 'hex': 'ab' * 32}}]:
            with self.assertRaises(p.ConfigRefusal):p.build_plan(env, changed, run_id='0123abcd')

    def test_environment_injection_characters_refuse(self):
        for value in ['x\nTOKEN=y', '${SECRET}', "x'y", ' x', 'x\\y']:
            with self.assertRaises(p.ConfigRefusal):p.safe_env({'FIELD': value})

    def test_upstream_binding_requires_own_private_network(self):
        self.assertEqual(p.gateway_binding('172.30.10.5', '172.30.10.0/24')['upstreamHost'], '172.30.10.5')
        for ip, network in [('172.30.11.5', '172.30.10.0/24'), ('127.0.0.1', '127.0.0.0/8'),
                            ('172.30.10.0', '172.30.10.0/24'), ('8.8.8.8', '8.8.8.0/24')]:
            with self.assertRaises(p.ConfigRefusal):p.gateway_binding(ip, network)

    def test_file_write_is_exclusive_private_and_does_not_claim_linux_ownership(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            base = Path(directory).resolve();root = base / '.browser-e2e.0123abcd';root.mkdir(mode=0o700)
            owners = {}
            def record_owner(path, uid, gid):owners[str(Path(path).relative_to(root))] = (uid, gid)
            plan = p.build_plan(*inputs(), run_id='0123abcd')
            report = p.write_plan(root, '0123abcd', plan, source_auth_env=inputs()[0], source_keys=inputs()[1], base=base, chown=record_owner)
            self.assertFalse(report['paperStartEnabled']);self.assertFalse(report['tlsPrepared'])
            for name, (uid, payload) in plan.files.items():
                target = root / 'private' / name
                self.assertEqual(target.read_bytes(), payload)
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
                self.assertEqual(owners['private/' + name], (uid, uid))
            with self.assertRaises(p.ConfigRefusal):p.write_plan(root, '0123abcd', plan, source_auth_env=inputs()[0], source_keys=inputs()[1], base=base, chown=record_owner)

    def test_symlinked_mount_root_or_child_cannot_escape(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            base = Path(directory).resolve();outside = base / 'outside';outside.mkdir(mode=0o700)
            root = base / '.browser-e2e.0123abcd';root.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(p.ConfigRefusal):p.owned_root(root, '0123abcd', base)
            root.unlink();root.mkdir(mode=0o700);(root / 'private').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(p.ConfigRefusal):p.write_plan(root, '0123abcd', p.build_plan(*inputs(), run_id='0123abcd'), source_auth_env=inputs()[0], source_keys=inputs()[1], base=base, chown=lambda *args: None)
            self.assertEqual(list(outside.iterdir()), [])

    def test_group_readable_root_and_wrong_run_id_refuse(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            base = Path(directory).resolve();root = base / '.browser-e2e.0123abcd';root.mkdir(mode=0o755)
            with self.assertRaises(p.ConfigRefusal):p.owned_root(root, '0123abcd', base)
            root.chmod(0o700)
            with self.assertRaises(p.ConfigRefusal):p.owned_root(root, 'bad', base)


class CloneKeyIsolationTests(unittest.TestCase):
    def test_three_clone_keys_are_fresh_and_historical_directory_purposes_retained(self):
        env, source = inputs();plan = p.build_plan(env, source, run_id='0123abcd')
        clone = json.loads(plan.files['gateway/keys.json'][1])
        self.assertEqual(set(clone), set(p.KEY_IDS))
        for purpose in ('context', 'credential', 'cipher'):
            self.assertNotIn(clone[purpose]['hex'], {v['hex'] for v in source.values()})
            self.assertEqual(clone[purpose]['id'], p.KEY_IDS[purpose])
        for purpose in ('email_address', 'email_cipher', 'comparison'):
            self.assertEqual(clone[purpose], source[purpose])
        profile = json.loads(plan.files['clone-key-profile.json'][1])
        self.assertEqual(profile['installationId'], '0123abcd')
        self.assertFalse(profile['oldKeyFallback']);self.assertFalse(profile['historicalRowsReencrypted'])
        self.assertFalse(profile['productionRotation'])
        self.assertEqual(len({v['hex'] for v in clone.values()}), 6)

    def test_every_hardcoded_key_id_and_duplicate_material_fail_before_outputs(self):
        env, source = inputs()
        for purpose in p.KEY_IDS:
            changed = {k: dict(v) for k, v in source.items()};changed[purpose]['id'] = 'other-id'
            with self.assertRaises(p.ConfigRefusal):p.build_plan(env, changed, run_id='0123abcd')
        changed = {k: dict(v) | {'hex': 'ab' * 32} for k, v in source.items()}
        with self.assertRaises(p.ConfigRefusal):p.build_plan(env, changed, run_id='0123abcd')

    def test_mutated_plan_is_rejected_before_any_private_directory_is_created(self):
        plan = p.build_plan(*inputs(), run_id='0123abcd')
        with self.assertRaises(TypeError):plan.files['extra'] = (0, b'x')
        for changed in [dict(plan.files) | {'../../escape': (0, b'x')},
                        dict(plan.files) | {'api/api-config.json': (0, b'{}')},
                        dict(plan.files) | {'api/api-config.json': (1000, '{}')}]:
            with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
                base = Path(directory).resolve();root = base / '.browser-e2e.0123abcd';root.mkdir(mode=0o700)
                with self.assertRaises(p.ConfigRefusal):
                    p.write_plan(root, '0123abcd', p.PrivatePlan(changed), source_auth_env=inputs()[0], source_keys=inputs()[1], base=base, chown=lambda *args: None)
                self.assertFalse((root / 'private').exists())

    def test_partial_write_has_no_completion_marker_and_cannot_restart(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            base = Path(directory).resolve();root = base / '.browser-e2e.0123abcd';root.mkdir(mode=0o700)
            plan = p.build_plan(*inputs(), run_id='0123abcd')
            count = [0]
            def fail(path, uid, gid):
                count[0] += 1
                if count[0] == 4:raise OSError('synthetic ownership failure')
            with self.assertRaises(OSError):p.write_plan(root, '0123abcd', plan, source_auth_env=inputs()[0], source_keys=inputs()[1], base=base, chown=fail)
            self.assertFalse((root / 'PRIVATE-PREPARED.json').exists())
            with self.assertRaises(FileExistsError):
                p.write_plan(root, '0123abcd', plan, source_auth_env=inputs()[0], source_keys=inputs()[1], base=base, chown=lambda *args: None)


class SemanticAndCompletionRegressionTests(unittest.TestCase):
    def assert_refuses_before_write(self, changed):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            base = Path(directory).resolve();root = base / '.browser-e2e.0123abcd';root.mkdir(mode=0o700)
            with self.assertRaises(p.ConfigRefusal):
                p.write_plan(root, '0123abcd', p.PrivatePlan(changed), source_auth_env=inputs()[0],
                             source_keys=inputs()[1], base=base, chown=lambda *args: None)
            self.assertFalse((root / 'private').exists())
            self.assertFalse((root / 'PRIVATE-PREPARED.json').exists())

    def test_early_start_enabled_cannot_be_hidden_by_a_false_completion_marker(self):
        plan = p.build_plan(*inputs(), run_id='0123abcd');changed = dict(plan.files)
        api = json.loads(changed['api/api-config.json'][1]);api['startEnabled'] = True
        changed['api/api-config.json'] = (1000, json.dumps(api).encode())
        self.assert_refuses_before_write(changed)

    def test_cross_service_key_mismatch_and_fixture_or_destination_tampering_refuse(self):
        plan = p.build_plan(*inputs(), run_id='0123abcd')
        for name, uid, payload in [
            ('api/credential-key.json', 1000, json.dumps({'credential': inputs()[1]['credential']}).encode()),
            ('api/ingress-key.json', 1000, b'{"format":"polygon-ingress-hmac-v1","hex":"' + b'f' * 64 + b'"}'),
            ('gateway/app.json', 65534, b'{"fixtures":{"fake-login":true}}'),
            ('gateway/pg_service.conf', 65534, plan.files['gateway/pg_service.conf'][1].replace(b'host=db', b'host=source-db')),
            ('roles-private.sql', 0, plan.files['roles-private.sql'][1] + b'GRANT polygon_executor TO postgres;\n')]:
            self.assert_refuses_before_write(dict(plan.files) | {name: (uid, payload)})

    def test_old_cipher_or_unknown_installation_flags_cannot_be_smuggled_in(self):
        plan = p.build_plan(*inputs(), run_id='0123abcd')
        clone = json.loads(plan.files['gateway/keys.json'][1]);clone['cipher'] = inputs()[1]['cipher']
        self.assert_refuses_before_write(dict(plan.files) | {'gateway/keys.json': (65534, json.dumps(clone).encode())})
        profile = json.loads(plan.files['clone-key-profile.json'][1])
        for value in (True, 0, 'false'):
            changed_profile = profile | {'oldKeyFallback': value}
            self.assert_refuses_before_write(dict(plan.files) | {'clone-key-profile.json': (0, json.dumps(changed_profile).encode())})

    def test_final_marker_chown_failure_never_publishes_valid_completion(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            base = Path(directory).resolve();root = base / '.browser-e2e.0123abcd';root.mkdir(mode=0o700)
            def fail(path, uid, gid):
                if Path(path).name.startswith('.PRIVATE-PREPARED.'):
                    raise OSError('synthetic final ownership failure')
            with self.assertRaises(OSError):
                p.write_plan(root, '0123abcd', p.build_plan(*inputs(), run_id='0123abcd'),
                             source_auth_env=inputs()[0], source_keys=inputs()[1], base=base, chown=fail)
            self.assertFalse((root / 'PRIVATE-PREPARED.json').exists())

    def test_preexisting_completion_marker_refuses_before_writing_private_files(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            base = Path(directory).resolve();root = base / '.browser-e2e.0123abcd';root.mkdir(mode=0o700)
            marker = root / 'PRIVATE-PREPARED.json';marker.write_text('{}')
            with self.assertRaises(p.ConfigRefusal):
                p.write_plan(root, '0123abcd', p.build_plan(*inputs(), run_id='0123abcd'),
                             source_auth_env=inputs()[0], source_keys=inputs()[1], base=base, chown=lambda *args: None)
            self.assertFalse((root / 'private').exists());self.assertEqual(marker.read_text(), '{}')


class SQLLiteralRegressionTests(unittest.TestCase):
    def test_valid_random_password_containing_008_is_not_an_activation_command(self):
        from unittest.mock import patch
        count = [0]
        def synthetic_hex(size):
            if size == 16:return 'ab' * 16
            count[0] += 1
            assert size == 32
            return f'{count[0]:04x}' + '008' + 'c' * 57
        env, keys = inputs()
        with patch('private_config.secrets.token_hex', side_effect=synthetic_hex):
            plan = p.build_plan(env, keys, run_id='0123abcd')
        self.assertIn(b'008', plan.files['roles-private.sql'][1])
        # Exact allowed SQL/password correspondence is checked independently of
        # accidental characters inside valid literals; GRANT tampering is tested above.
        p.validate_semantics(plan, '0123abcd', env, keys)


if __name__ == '__main__':
    unittest.main()
