"""Independent process-level checks; fake collector, no network or actual capture."""
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

BASE = Path(__file__).resolve().parent


class SupervisorLifecycle(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copy2(BASE / 'run_shadow.py', self.root / 'run_shadow.py')
        (self.root / 'collector.py').write_text('''import argparse, json, pathlib, time
p=argparse.ArgumentParser()
p.add_argument('command', choices=['capture'])
p.add_argument('--config');p.add_argument('--output');p.add_argument('--duration-seconds');p.add_argument('--max-bytes')
a=p.parse_args()
o=pathlib.Path(a.output);o.mkdir()
(o/'read-config.json').write_text(pathlib.Path(a.config).read_text())
(o/'started').write_text('started')
time.sleep(20)
''')
        self.config = self.root / 'source.json'
        self.config.write_text('{"marker":"before"}\n')
        self.capture = self.root / 'capture'
        self.command = [sys.executable, str(self.root / 'run_shadow.py'), '--config', str(self.config),
                        '--root', str(self.capture), '--hours', '0.001', '--chunk-seconds', '30',
                        '--max-bytes', '2097152']

    def reap(self, process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def invoke(self):
        return subprocess.run(self.command, capture_output=True, text=True, timeout=15)

    def test_existing_stop_prevents_child(self):
        self.capture.mkdir()
        (self.capture / 'STOP').touch()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.capture / 'runner-status.json').read_text())
        self.assertEqual(state['status'], 'stopped_by_request')
        self.assertEqual(state['completed_chunks'], 0)
        self.assertFalse(list(self.capture.glob('capture-*')))
        self.assertFalse(state['continuous_coverage_guaranteed'])

    def test_root_lock_rejects_duplicate(self):
        self.capture.mkdir()
        with (self.capture / 'runner.lock').open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.invoke()
        self.assertEqual(result.returncode, 2)
        self.assertIn('another runner', result.stderr)
        self.assertFalse(list(self.capture.glob('config-*')))

    def test_deadline_terminates_child_and_freezes_config(self):
        process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.reap, process)
        deadline = time.monotonic() + 5
        marker = None
        while time.monotonic() < deadline:
            starts = list(self.capture.glob('capture-*/started')) if self.capture.exists() else []
            if starts:
                marker = starts[0]
                break
            time.sleep(.02)
        self.assertIsNotNone(marker, 'fake child never started')
        self.config.write_text('{"marker":"after"}\n')
        _, errors = process.communicate(timeout=12)
        self.assertEqual(process.returncode, 0, errors)
        state = json.loads((self.capture / 'runner-status.json').read_text())
        self.assertEqual(state['status'], 'deadline_reached')
        self.assertEqual(state['failed_chunks'], 1)
        self.assertEqual(state['completed_chunks'], 0)
        self.assertEqual(json.loads((marker.parent / 'read-config.json').read_text()), {'marker':'before'})
        self.assertIsNone(state['child_pid'])

    def test_successful_chunk_is_archived(self):
        (self.root / 'collector.py').write_text("""import argparse, hashlib, json, pathlib
p=argparse.ArgumentParser()
p.add_argument('command',choices=['capture']);p.add_argument('--config');p.add_argument('--output');p.add_argument('--duration-seconds');p.add_argument('--max-bytes')
a=p.parse_args();o=pathlib.Path(a.output);o.mkdir()
raw=b'{"fixture":"finalized"}\\n'
(o/'events.jsonl').write_bytes(raw)
(o/'manifest.json').write_text(json.dumps({'eventsSha256':hashlib.sha256(raw).hexdigest()}))
""")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.capture / 'runner-status.json').read_text())
        self.assertEqual(state['completed_chunks'], 1)
        chunk = Path(state['current_chunk'])
        self.assertFalse((chunk / 'events.jsonl').exists())
        self.assertTrue((chunk / 'events.jsonl.gz').exists())
        self.assertTrue((chunk / 'archive.json').exists())
        self.assertEqual(state['status'], 'deadline_reached')

    def test_stop_during_child_does_not_mark_complete(self):
        process = subprocess.Popen(self.command[:-6] + ['--hours', '.01', '--chunk-seconds', '30', '--max-bytes', '2097152'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.reap, process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.capture.exists() and list(self.capture.glob('capture-*/started')):
                break
            time.sleep(.02)
        (self.capture / 'STOP').touch()
        _, errors = process.communicate(timeout=8)
        self.assertEqual(process.returncode, 0, errors)
        state = json.loads((self.capture / 'runner-status.json').read_text())
        self.assertEqual(state['status'], 'stopped_by_request')
        self.assertEqual(state['completed_chunks'], 0)
        self.assertFalse(state['real_money'])


if __name__ == '__main__':
    unittest.main()
