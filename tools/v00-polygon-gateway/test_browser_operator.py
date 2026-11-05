"""Fault/scope tests only. No Docker daemon, database, TLS key or service is used."""
import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import subprocess

import browser_operator as b
from private_config import ConfigRefusal
from test_operator_guards import OWNED, container


class OperatorBoundaryTests(unittest.TestCase):
    def test_negative_login_requires_typed_authentication_refusal(self):
        for value in [{'status':'refused','code':'ECONNREFUSED','severity':'FATAL'},
                      {'status':'refused','code':'42601','severity':'ERROR'},
                      {'status':'connected','currentUser':'polygon_paper_runtime'},
                      {'status':'refused','code':'28P01'}]:
            with self.assertRaises(ConfigRefusal):
                b.login_probe_result(json.dumps(value).encode(),'polygon_paper_runtime',False)
        self.assertTrue(b.login_probe_result(b'{"status":"refused","code":"28P01","severity":"FATAL"}', 'postgres',False))
        with patch('browser_operator.subprocess.run',return_value=subprocess.CompletedProcess(['docker'],125,b'',b'private')):
            with self.assertRaises(ConfigRefusal):b.run(['docker','exec'])

    def test_copied_safety_failure_cannot_be_accepted_as_source_proof(self):
        op=object.__new__(b.Operator)
        for field in ('no_paper','synthetic_only','roles_ok'):
            value={'no_paper':True,'synthetic_only':True,'roles_ok':True};value[field]=False
            with patch.object(op,'psql',return_value=json.dumps(value).encode()) as sql:
                with self.assertRaises(ConfigRefusal):op.safety_snapshot()
                self.assertIs(sql.call_args.kwargs['source'],False)

    def test_bind_sources_refuse_symlinks_and_overlapping_directories(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            op=object.__new__(b.Operator);op.root=Path(directory).resolve()
            (op.root/'data').mkdir();(op.root/'data'/'nested').mkdir()
            (op.root/'alias').symlink_to(op.root/'data',target_is_directory=True)
            for rel in ('alias','data/nested'):
                binds={'db':{'/one':('data',True),'/two':(rel,False)}}
                with patch('browser_operator.SERVICES',('db',)),patch('browser_operator.BINDS',binds):
                    with self.assertRaises(ConfigRefusal):op.bind_sources()

    def test_child_timeout_is_unknown_and_never_retried_or_printed(self):
        with patch('browser_operator.subprocess.run', side_effect=subprocess.TimeoutExpired(['private'], 1)) as run:
            with self.assertRaises(ConfigRefusal):b.run(['private-command'])
            self.assertEqual(run.call_count, 1)

    def test_source_container_requires_original_project_and_pinned_image(self):
        for item in [{'Config': {'Labels': {'com.docker.compose.project': 'other'}}, 'Image': b.SOURCE_IDS['db']},
                     {'Config': {'Labels': {'com.docker.compose.project': 'shadow-polygon'}}, 'Image': 'sha256:' + 'f' * 64}]:
            with patch('browser_operator.inspect_container', return_value=item):
                with self.assertRaises(ConfigRefusal):b.source_container('db')

    def test_release_symlink_or_path_escape_is_rejected_before_extracting_any_member(self):
        for name, symlink in [('gateway/../../escape', False), ('gateway/link', True), ('/api/absolute', False), ('private/keys.json', False)]:
            with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
                root = Path(directory);archive = root / 'input.tar';dest = root / 'dest';dest.mkdir()
                with tarfile.open(archive, 'w') as t:
                    info=tarfile.TarInfo(name)
                    if symlink:info.type=tarfile.SYMTYPE;info.linkname='/outside'
                    else:info.size=1
                    t.addfile(info,None if symlink else io.BytesIO(b'x'))
                with self.assertRaises(ConfigRefusal):b.extract_release(archive,dest)
                self.assertEqual(list(dest.iterdir()),[])

    def test_clone_sql_uses_the_proven_immutable_container_id(self):
        op=object.__new__(b.Operator)
        op.container=lambda service:('a' * 64,{})
        with patch('browser_operator.run',return_value=b'1') as run:
            self.assertEqual(op.psql(b'SELECT 1'),b'1')
            args=run.call_args.args[0]
            self.assertIn('a' * 64,args);self.assertNotIn(b.SOURCE['db'],args)
            self.assertEqual(run.call_args.kwargs['data'],b'SELECT 1')

    def test_wrong_container_scope_prevents_sql_execution(self):
        op=object.__new__(b.Operator)
        def reject(service):raise ConfigRefusal('wrong scope')
        op.container=reject
        with patch('browser_operator.run') as run:
            with self.assertRaises(ConfigRefusal):op.psql(b'ALTER ROLE example')
            run.assert_not_called()

    def test_cleanup_wrong_mount_refuses_before_delete_or_root_removal(self):
        op=object.__new__(b.Operator);op.root=Path(OWNED['root']);op.owned=OWNED;op.state={}
        bad=container('api');bad['Mounts'][0]['Source']='/var/lib/docker/volumes/shadow-polygon_db-data/_data'
        with patch('browser_operator.marker',return_value=OWNED),patch('browser_operator.run',return_value=b'bad-id') as run,patch('browser_operator.inspect_container',return_value=bad),patch('browser_operator.shutil.rmtree') as delete:
            with self.assertRaises(ConfigRefusal):op.cleanup()
            self.assertTrue(all('rm' not in call.args[0] for call in run.call_args_list))
            delete.assert_not_called()

    def test_cleanup_failed_inventory_is_not_absence(self):
        op=object.__new__(b.Operator);op.root=Path(OWNED['root']);op.owned=OWNED;op.state={}
        with patch('browser_operator.marker',return_value=OWNED),patch('browser_operator.run',side_effect=ConfigRefusal('inventory unavailable')),patch('browser_operator.shutil.rmtree') as delete:
            with self.assertRaises(ConfigRefusal):op.cleanup()
            delete.assert_not_called()

    def test_plan_default_has_no_resource_or_private_config_side_effects(self):
        with patch('browser_operator.sys',create=True):
            pass
        with patch('sys.argv',['browser_operator.py','--package','/p','--package-sha','a'*64]),patch('browser_operator.verify_package',return_value=Path('/p')),patch('browser_operator.run') as run,patch('browser_operator.Operator') as op,patch('builtins.print'):
            b.main();run.assert_not_called();op.assert_not_called()

    def test_prepare_without_both_explicit_scope_acknowledgements_has_no_side_effects(self):
        for flags in [[],['--ack-disposable-real-auth'],['--ack-clone-only-008']]:
            argv=['browser_operator.py','prepare','--package','/p','--package-sha','a'*64,*flags]
            with patch('sys.argv',argv),patch('browser_operator.verify_package',return_value=Path('/p')),patch('browser_operator.os.geteuid',return_value=0),patch('browser_operator.Operator') as op,patch('browser_operator.Path.mkdir') as mkdir:
                with self.assertRaises(ConfigRefusal):b.main()
                op.assert_not_called();mkdir.assert_not_called()


if __name__=='__main__':
    unittest.main()
