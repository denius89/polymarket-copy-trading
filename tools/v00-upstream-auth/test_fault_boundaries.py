"""Local fault-boundary tests only: subprocess doubles, no PostgreSQL/provider."""
import base64
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from commit_gap import relay
from provider_observer import Observer


PSQL_DOUBLE = r'''
import json,os,sys
method=None
for line in sys.stdin:
 if line.startswith('SELECT v00_upstream.'):
  method=line.split('v00_upstream.')[1].split('(')[0]
 elif line.strip() == r'\g':
  value={'http':200,'dispatch_allowed':os.environ.get('DOUBLE_REPLAY')!='1'} if method=='seal_email' else {'http':200,'result':{'kind':'login_completed'}}
  print(json.dumps(value),flush=True)
 elif line.startswith('COMMIT'):
  print(os.environ.get('DOUBLE_COMMIT_TAG','COMMIT'),flush=True)
 elif line.startswith('BEGIN'): print('BEGIN',flush=True)
'''


class CommitGapTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.ctx, self.op = str(uuid.uuid4()), str(uuid.uuid4())
        self.marker = str(Path(self.root.name) / "fault.json")
        self.env = {"V00_COMMIT_GAP_ENABLED": "1", "V00_REAL_PSQL_COMMAND_JSON": json.dumps(
            [sys.executable, "-u", "-c", PSQL_DOUBLE])}

    def wire(self, methods, context=None):
        fields = {"context_id": context or self.ctx, "operation_id": self.op, "action": "C02",
                  "code": "654321", "executor_proof": "private-test-proof"}
        encoded = base64.b64encode(json.dumps(fields).encode()).decode()
        result = "BEGIN;\n"
        for method in methods:
            result += f"SELECT v00_upstream.{method}(convert_from(decode($1,'base64'),'UTF8')::jsonb)::text\n\\bind '{encoded}'\n\\g\n"
        return (result + "COMMIT;\n").encode()

    def run_wire(self, methods, method="seal_email", context=None, env=None):
        output = io.BytesIO()
        with patch.dict(os.environ, self.env | (env or {})):
            code = relay(method, self.ctx, self.marker, [], io.BytesIO(self.wire(methods, context)), output)
        return code, output.getvalue()

    def test_real_seal_commit_is_suppressed_after_bound_call(self):
        code, output = self.run_wire(["seal_email"])
        self.assertEqual(code, 97)
        self.assertTrue(output.startswith(b"BEGIN\n"))
        self.assertNotIn(b"COMMIT", output)
        marker = Path(self.marker)
        value = json.loads(marker.read_text())
        self.assertTrue(value["real_commit_tag_seen"])
        self.assertEqual(value["source"]["operation_id"], self.op)
        self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
        for secret in ("654321", "private-test-proof", "dispatch_allowed"):
            self.assertNotIn(secret, marker.read_text())

    def test_completion_scoped_after_plan_in_same_transaction(self):
        code, output = self.run_wire(["plan_email", "complete"], "complete")
        self.assertEqual(code, 97)
        self.assertEqual(len(output.splitlines()), 3)
        self.assertEqual(json.loads(Path(self.marker).read_text())["method"], "complete")

    def test_other_context_not_affected(self):
        code, output = self.run_wire(["seal_email"], context=str(uuid.uuid4()))
        self.assertEqual(code, 0)
        self.assertTrue(output.endswith(b"COMMIT\n"))
        self.assertFalse(Path(self.marker).exists())

    def test_other_method_not_affected(self):
        code, output = self.run_wire(["read_operation"])
        self.assertEqual(code, 0)
        self.assertTrue(output.endswith(b"COMMIT\n"))
        self.assertFalse(Path(self.marker).exists())

    def test_one_shot_marker_does_not_suppress_second_commit(self):
        self.assertEqual(self.run_wire(["seal_email"])[0], 97)
        first = Path(self.marker).read_bytes()
        code, output = self.run_wire(["seal_email"])
        self.assertEqual(code, 0)
        self.assertTrue(output.endswith(b"COMMIT\n"))
        self.assertEqual(Path(self.marker).read_bytes(), first)

    def test_rollback_tag_never_claimed_committed(self):
        code, output = self.run_wire(["seal_email"], env={"DOUBLE_COMMIT_TAG": "ROLLBACK"})
        self.assertEqual(code, 0)
        self.assertTrue(output.endswith(b"ROLLBACK\n"))
        self.assertFalse(Path(self.marker).exists())

    def test_final_seal_replay_does_not_arm_fault(self):
        code, output = self.run_wire(["seal_email"], env={"DOUBLE_REPLAY": "1"})
        self.assertEqual(code, 0)
        self.assertTrue(output.endswith(b"COMMIT\n"))
        self.assertFalse(Path(self.marker).exists())

    def test_disabled_fault_cannot_launch_child(self):
        with patch.dict(os.environ, self.env | {"V00_COMMIT_GAP_ENABLED": "0"}), self.assertRaises(ValueError):
            relay("seal_email", self.ctx, self.marker, [], io.BytesIO(), io.BytesIO())


class Connection:
    def __init__(self, status=200, failure=False):
        self.status, self.failure, self.calls, self.closed = status, failure, [], False

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.failure:
            raise OSError("synthetic transport failure")

    def getresponse(self):
        return self

    def read(self, _):
        return b'{"access_token":"private-provider-reply"}'

    def close(self):
        self.closed = True


class ObserverTests(unittest.TestCase):
    def setup_observer(self, mode="count", status=200, failure=False):
        self.conn = Connection(status, failure)
        self.state = Observer("observer@example.invalid", "654321", "a" * 43, mode,
                              "http://auth:9999", lambda: self.conn)
        self.raw = b'{"email":"observer@example.invalid","token":"654321","type":"email"}'
        self.agent = "shadow-v00-upstream/" + str(uuid.uuid4())

    def test_no_forward_without_original_accept(self):
        self.setup_observer()
        with self.assertRaises(ValueError):
            self.state.forward_once(self.raw, self.agent)
        self.assertEqual(self.conn.calls, [])

    def test_one_original_forward_no_secret_in_snapshot(self):
        self.setup_observer()
        self.assertTrue(self.state.accept(self.raw, self.agent))
        self.assertEqual(self.state.forward_once(self.raw, self.agent)[0], 200)
        self.assertEqual(self.conn.calls[0][1]["body"], self.raw)
        self.assertEqual(self.conn.calls[0][1]["headers"]["User-Agent"], self.agent)
        self.assertTrue(self.conn.closed)
        snapshot = self.state.snapshot()
        self.assertEqual((snapshot["forward_attempts"], snapshot["provider_responses"]), (1, 1))
        for secret in ("observer@example.invalid", "654321", "private-provider-reply", "a" * 43):
            self.assertNotIn(secret, json.dumps(snapshot))
        with self.assertRaises(ValueError):
            self.state.forward_once(self.raw, self.agent)
        self.assertEqual(len(self.conn.calls), 1)

    def test_failed_send_never_retries(self):
        self.setup_observer(failure=True)
        self.state.accept(self.raw, self.agent)
        with self.assertRaises(OSError):
            self.state.forward_once(self.raw, self.agent)
        with self.assertRaises(ValueError):
            self.state.forward_once(self.raw, self.agent)
        self.assertEqual((len(self.conn.calls), self.state.snapshot()["forward_errors"]), (1, 1))

    def test_redirect_never_followed(self):
        self.setup_observer(status=302)
        self.state.accept(self.raw, self.agent)
        with self.assertRaises(ValueError):
            self.state.forward_once(self.raw, self.agent)
        self.assertEqual(len(self.conn.calls), 1)
        self.assertEqual(self.state.snapshot()["provider_responses"], 0)

    def test_late_mode_declares_fixed_delay_and_no_effect_yet(self):
        self.setup_observer(mode="late")
        self.assertEqual(self.state.snapshot()["delay_seconds"], 12)
        self.assertEqual(self.state.snapshot()["forward_attempts"], 0)
        self.assertEqual(self.conn.calls, [])


if __name__ == "__main__":
    unittest.main()
