"""Independent adversarial evidence checks. Fixtures only; no external requests."""
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request
from urllib.parse import parse_qs, urlparse

import collector as c
import run_shadow as supervisor


class CaptureEvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run = Path(self.temporary.name) / 'run'
        self.scope = {'address': '0x' + 'a' * 40}
        self.config = c.validate_config({'schemaVersion':'forward-collector-config-v1', 'leaders':[self.scope], 'websocket':False})

    def test_no_secret_or_endpoint_configuration(self):
        for key in ('secret', 'apiKey', 'baseUrl', 'headers', 'signer'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.validate_config(dict(self.config, **{key:'untrusted'}))
        for endpoint in ('create-order', 'polymarket-order', 'limitless-withdrawal'):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                c.endpoint_url(endpoint, self.scope)

    def test_window_and_account_queries_explicit(self):
        query = parse_qs(urlparse(c.endpoint_url('polymarket-activity', self.scope, start=1, end=20)).query)
        self.assertEqual(query['exclude_deposits_withdrawals'], ['false'])
        self.assertEqual(query['user'], [self.scope['address']])
        self.assertEqual(query['start'], ['1'])
        positions = parse_qs(urlparse(c.endpoint_url('polymarket-positions', self.scope)).query)
        self.assertEqual(positions['filter_amount'], ['0'])
        self.assertEqual(positions['include_archived'], ['true'])
        with self.assertRaises(ValueError):
            c.endpoint_url('polymarket-activity', self.scope, start=20, end=1)
        with self.assertRaises(ValueError):
            c.endpoint_url('limitless-book', {'slug':'../../orders'})

    def test_redirect_refused(self):
        with self.assertRaises(HTTPError):
            c.NoRedirect().redirect_request(Request('https://clob.polymarket.com/book'), None, 302, '', {}, 'https://example.org')

    def test_missing_and_conflicting_pagination_not_empty(self):
        for invalid in ({}, {'data':None}, {'data':[]},
                        {'data':[], 'pagination':{'has_more':True,'next_cursor':None}},
                        {'data':[], 'pagination':{'has_more':False,'next_cursor':'abc'}}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                c.v2_page(invalid)
        self.assertEqual(c.v2_page({'data':[], 'pagination':{'has_more':False,'next_cursor':None}}), ([],None))

    def make_run(self):
        recorder = c.Recorder(self.run, self.config, 100000)
        recorder.append('polymarket','http_response', self.scope, raw=b'{"data":null}',
                        observed_at='2026-10-18T12:00:00Z', observed_ns=123)
        recorder.append('polymarket','coverage_gap', self.scope, reason='timeout')
        recorder.close('completed')
        return self.run

    def test_verified_bytes_do_not_certify_completeness(self):
        result = c.verify_run(self.make_run())
        self.assertEqual(result['verifiedRecords'], 2)
        self.assertFalse(result['marketContinuityVerified'])
        self.assertEqual(result['economicSignalsQualified'], 0)
        with self.assertRaises(FileExistsError):
            c.Recorder(self.run, self.config, 100000)

    def test_deleted_gap_and_body_tampering_fail(self):
        self.make_run()
        events = self.run / 'events.jsonl'
        original = events.read_bytes()
        events.write_bytes(original.splitlines(keepends=True)[0])
        with self.assertRaises(ValueError):
            c.verify_run(self.run)
        row = json.loads(original.splitlines()[0])
        row['rawBase64'] = 'e30='
        events.write_text(json.dumps(row)+'\n'+original.splitlines()[1].decode()+'\n')
        with self.assertRaises(ValueError):
            c.verify_run(self.run)

    def test_archive_roundtrip_and_compressed_tamper(self):
        self.make_run()
        original = (self.run / 'events.jsonl').read_bytes()
        self.assertTrue(supervisor.archive_chunk(self.run))
        self.assertFalse((self.run / 'events.jsonl').exists())
        import gzip
        with gzip.open(self.run / 'events.jsonl.gz', 'rb') as stream:
            self.assertEqual(stream.read(), original)
        self.assertEqual(c.verify_run(self.run)['verifiedRecords'], 2)
        compressed = self.run / 'events.jsonl.gz'
        compressed.write_bytes(compressed.read_bytes() + b'tamper')
        with self.assertRaises(ValueError):
            c.verify_run(self.run)

    def test_tampered_raw_not_removed_by_archive(self):
        self.make_run()
        raw = self.run / 'events.jsonl'
        raw.write_bytes(raw.read_bytes()+b'tamper')
        with self.assertRaises(ValueError):
            supervisor.archive_chunk(self.run)
        self.assertTrue(raw.exists())
        self.assertFalse((self.run / 'events.jsonl.gz').exists())

    def test_unfinalized_run_retains_raw(self):
        self.make_run()
        manifest_path = self.run / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest.pop('eventsSha256')
        manifest_path.write_text(json.dumps(manifest))
        self.assertFalse(supervisor.archive_chunk(self.run))
        self.assertTrue((self.run / 'events.jsonl').exists())

    def test_archive_is_not_overwritten(self):
        self.make_run()
        (self.run / 'events.jsonl.gz').write_bytes(b'previous')
        with self.assertRaises(ValueError):
            supervisor.archive_chunk(self.run)
        self.assertEqual((self.run / 'events.jsonl.gz').read_bytes(), b'previous')
        self.assertTrue((self.run / 'events.jsonl').exists())

    def test_byte_limit_preserves_existing_records(self):
        recorder = c.Recorder(self.run, self.config, 1500)
        recorder.append('system','capture_start',{},raw=b'valid')
        with self.assertRaises(c.ByteLimit):
            recorder.append('system','oversize',{},raw=b'x'*4000)
        recorder.close('stopped_byte_limit')
        result = c.verify_run(self.run)
        self.assertEqual(result['verifiedRecords'], 1)
        self.assertEqual(result['captureStatus'], 'stopped_byte_limit')


if __name__ == '__main__':
    unittest.main()
