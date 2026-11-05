import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

import operator_guards as g
from private_config import ConfigRefusal

OWNED = {'format': 'polygon-browser-e2e-owned-v1', 'runId': '0123abcd',
         'root': '/opt/shadow-polygon/.browser-e2e.0123abcd',
         'project': 'shadow-browser-e2e-0123abcd', 'network': 'shadow-browser-e2e-0123abcd_lab',
         'sourceReleaseSha256': 'a' * 64}


def container(service='api'):
    return {'Id': 'b' * 64, 'Name': '/' + OWNED['project'] + '-' + service + '-1',
        'Image': 'sha256:' + 'c' * 64,
        'Config': {'User': {'api': '1000:1000', 'db': 'postgres'}.get(service, ''),
            'Labels': {'com.docker.compose.project': OWNED['project'],
                'com.docker.compose.service': service, 'shadow.scope': 'browser-e2e',
                'shadow.run-id': OWNED['runId']}},
        'HostConfig': {'Privileged': False, 'PortBindings': {}, 'NetworkMode': OWNED['network'],
            'CapAdd': None, 'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges:true'],
            'Tmpfs': {p: '' for p in g.TMPFS[service]}, 'ReadonlyRootfs': service != 'db',
            'RestartPolicy': {'Name': 'no'}},
        'NetworkSettings': {'Networks': {OWNED['network']: {}}},
        'Mounts': [{'Type': 'bind', 'Source': str(Path(OWNED['root']) / rel),
                    'Destination': target, 'RW': rw} for target, (rel, rw) in g.BINDS[service].items()]}


def network():
    return {'Id': 'd' * 64, 'Name': OWNED['network'], 'Internal': True, 'Driver': 'bridge',
            'EnableIPv6': False, 'Labels': {'com.docker.compose.project': OWNED['project'],
                'com.docker.compose.network': 'lab', 'shadow.scope': 'browser-e2e',
                'shadow.run-id': OWNED['runId']}, 'Containers': {}}


class ResourceGuardsTests(unittest.TestCase):
    def test_cleanup_returns_immutable_id_only_for_each_exact_owned_service(self):
        for service in g.SERVICES:
            value = container(service)
            self.assertEqual(g.container_identity(value, service, OWNED), 'b' * 64)

    def test_permanent_project_or_another_run_is_never_cleanup_eligible(self):
        for key, value in [('com.docker.compose.project', 'shadow-polygon'),
                           ('shadow.run-id', 'deadbeef'), ('shadow.scope', 'other')]:
            item = container();item['Config']['Labels'][key] = value
            with self.assertRaises(ConfigRefusal):g.container_identity(item, 'api', OWNED)
        item = container();item['Name'] = '/shadow-polygon-app-1'
        with self.assertRaises(ConfigRefusal):g.container_identity(item, 'api', OWNED)

    def test_correct_labels_do_not_override_source_data_or_socket_mount_mismatch(self):
        for source in ['/var/lib/docker/volumes/shadow-polygon_db-data/_data', '/var/run/docker.sock',
                       '/opt/shadow-polygon/private/runtime', OWNED['root'] + '/private/../source']:
            item = container();item['Mounts'][0]['Source'] = source
            with self.assertRaises(ConfigRefusal):g.container_identity(item, 'api', OWNED)

    def test_extra_volume_rw_secret_mount_and_missing_mount_refuse(self):
        item = container();item['Mounts'].append({'Type': 'volume', 'Destination': '/escape'})
        rw = container();rw['Mounts'][1]['RW'] = True
        missing = container();missing['Mounts'].pop()
        for value in [item, rw, missing]:
            with self.assertRaises(ConfigRefusal):g.container_identity(value, 'api', OWNED)

    def test_public_ports_shared_network_privileged_and_capability_changes_refuse(self):
        cases = []
        for key, value in [('PortBindings', {'19090/tcp': [{'HostPort': '19090'}]}),
                           ('Privileged', True), ('NetworkMode', 'host'), ('CapAdd', ['SYS_ADMIN']),
                           ('CapDrop', []), ('SecurityOpt', [])]:
            item = container();item['HostConfig'][key] = value;cases.append(item)
        item = container();item['NetworkSettings']['Networks']['shadow-polygon_lab'] = {};cases.append(item)
        for item in cases:
            with self.assertRaises(ConfigRefusal):g.container_identity(item, 'api', OWNED)

    def test_incomplete_inspection_never_returns_a_deletion_target(self):
        for item in [{}, {'Config': {}}, container() | {'Id': 'name-instead-of-id'}]:
            with self.assertRaises(ConfigRefusal):g.container_identity(item, 'api', OWNED)

    def test_network_requires_owner_internal_and_no_unknown_endpoints(self):
        self.assertEqual(g.network_identity(network(), OWNED, empty=True), 'd' * 64)
        for key, value in [('Name', 'shadow-polygon_lab'), ('Internal', False), ('EnableIPv6', True)]:
            item = network();item[key] = value
            with self.assertRaises(ConfigRefusal):g.network_identity(item, OWNED)
        item = network();item['Containers'] = {'e' * 64: {}}
        with self.assertRaises(ConfigRefusal):g.network_identity(item, OWNED)
        self.assertEqual(g.network_identity(item, OWNED, allowed_endpoint_ids=['e' * 64]), 'd' * 64)
        with self.assertRaises(ConfigRefusal):g.network_identity(item, OWNED, empty=True, allowed_endpoint_ids=['e' * 64])

    def test_runtime_image_uid_readonly_and_restart_are_a_separate_gate(self):
        item = container()
        g.runtime_options(item, 'api', image_id='sha256:' + 'c' * 64, image_user='node')
        for field, value in [('Image', 'sha256:' + 'f' * 64)]:
            changed = copy.deepcopy(item);changed[field] = value
            with self.assertRaises(ConfigRefusal):g.runtime_options(changed, 'api', image_id='sha256:' + 'c' * 64, image_user='node')
        changed = copy.deepcopy(item);changed['Config']['User'] = 'root'
        with self.assertRaises(ConfigRefusal):g.runtime_options(changed, 'api', image_id='sha256:' + 'c' * 64, image_user='node')

    def test_marker_binds_root_run_release_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            base = Path(directory).resolve();root = base / '.browser-e2e.0123abcd';root.mkdir(mode=0o700)
            owned = OWNED | {'root': str(root)}
            marker = root / 'OWNED.json';marker.write_text(json.dumps(owned));marker.chmod(0o600)
            self.assertEqual(g.marker(root, '0123abcd', 'a' * 64, base=base), owned)
            marker.write_text(json.dumps(owned | {'sourceReleaseSha256': 'f' * 64}))
            with self.assertRaises(ConfigRefusal):g.marker(root, '0123abcd', 'a' * 64, base=base)
        with self.assertRaises(ConfigRefusal):g.unique_json('{"runId":"a","runId":"b"}')


class MissingSecurityFieldsRegressionTests(unittest.TestCase):
    def test_unknown_host_security_fields_are_not_safe_defaults(self):
        for field in ('Privileged', 'PortBindings', 'CapAdd', 'CapDrop', 'SecurityOpt', 'Tmpfs'):
            item = container();del item['HostConfig'][field]
            with self.assertRaises(ConfigRefusal):g.container_identity(item, 'api', OWNED)
        for value in (None, 0, 'false'):
            item = container();item['HostConfig']['Privileged'] = value
            with self.assertRaises(ConfigRefusal):g.container_identity(item, 'api', OWNED)

    def test_missing_or_nonboolean_ipv6_flag_refuses(self):
        item = network();del item['EnableIPv6']
        with self.assertRaises(ConfigRefusal):g.network_identity(item, OWNED)
        for value in (None, 0, 'false'):
            item = network();item['EnableIPv6'] = value
            with self.assertRaises(ConfigRefusal):g.network_identity(item, OWNED)


if __name__ == '__main__':
    unittest.main()
