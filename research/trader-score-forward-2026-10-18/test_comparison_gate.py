"""Synthetic structural-gate tests; no market outcomes or financial validation."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo
from compare_models import assess, check_session, digest, validate_target

HERE = Path(__file__).resolve().parent


class Gates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = json.loads((HERE / 'comparison-config.json').read_text())
        evidence = self.base / 'test-only-evidence.txt'
        evidence.write_text('synthetic structural evidence, not a completed audit')
        self.sha = digest(evidence)
        self.now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        self.standard = 'a' * 64
        self.row = {
            'session_id': 'test-session', 'canonical_identity': 'test-address',
            'venue_binding_id': 'synthetic-binding', 'standard_sha256': self.standard,
            'started_at': '2026-10-18T00:00:00+02:00',
            'cutoff_at': '2026-11-17T00:00:00+01:00',
            'observed_until': '2026-11-17T00:00:00+01:00',
            'outcome_kind': 'forward_shadow_conditional', 'ledger_status': 'independently_crosschecked',
            'unknown_components': [], 'path_sha256': self.sha, 'terminal_net_wealth': '200',
            'evidence': [{'path': evidence.name, 'sha256': self.sha}],
            'requirement_evidence': {key: [self.sha] for key in self.config['point_outcome_requirements']}}

    def check(self, row=None):
        return check_session(row or self.row, self.config, self.base, self.standard, self.now)

    def test_cash_structurally_computable_not_audit_certification(self):
        self.assertEqual(self.check()['conditional_X'], '1')
        report = assess(self.config, [self.row], self.base, self.standard, self.now)
        self.assertFalse(report['comparison_executed'])
        self.assertIsNone(report['winner'])
        self.assertEqual(report['status'], 'not_eligible')

    def test_empty_is_collecting_not_zero_return(self):
        report = assess(self.config, [], self.base, self.standard, self.now)
        self.assertEqual(report['status'], 'collecting')
        self.assertEqual(report['sessions'], [])
        self.assertIsNone(report['winner'])

    def test_future_cutoff_refused(self):
        self.now = datetime(2026, 10, 18, tzinfo=timezone.utc)
        self.assertIsNone(self.check()['conditional_X'])

    def test_utc_720_hours_does_not_replace_calendar_dst(self):
        self.row['cutoff_at'] = '2026-11-16T22:00:00Z'
        self.assertIn('horizon_mismatch', self.check()['reasons'])

    def test_unknown_wealth_not_cash(self):
        self.row['terminal_net_wealth'] = None
        self.assertIsNone(self.check()['conditional_X'])

    def test_nan_and_binary_float_rejected(self):
        for value in ['NaN', 'Infinity', 200.0, '-1']:
            with self.subTest(value=value):
                self.row['terminal_net_wealth'] = value
                self.assertIsNone(self.check()['conditional_X'])

    def test_missing_fee_evidence_blocks(self):
        self.row['requirement_evidence'].pop('applicable_fee_and_price_bindings')
        self.assertIsNone(self.check()['conditional_X'])

    def test_evidence_hash_tampering_blocks(self):
        (self.base / self.row['evidence'][0]['path']).write_text('changed')
        self.assertIn('invalid_evidence_bundle', self.check()['reasons'])

    def test_path_escape_blocks(self):
        self.row['evidence'][0]['path'] = '../outside'
        self.assertIn('invalid_evidence_bundle', self.check()['reasons'])

    def test_duplicate_session_not_two_observations(self):
        report = assess(self.config, [self.row, copy.deepcopy(self.row)], self.base, self.standard, self.now)
        self.assertEqual(report['sessions_structurally_eligible'], 0)
        self.assertTrue(all(x['conditional_X'] is None for x in report['sessions']))

    def test_engine_fixture_outcome_cannot_be_forward(self):
        self.row['outcome_kind'] = 'synthetic_accounting'
        self.assertIsNone(self.check()['conditional_X'])

    def test_missing_inventory_not_assumed_no_sales(self):
        self.row['unknown_components'] = ['leader_inventory']
        self.assertIsNone(self.check()['conditional_X'])

    def test_standard_hash_mismatch_blocks(self):
        self.row['standard_sha256'] = 'b' * 64
        self.assertIsNone(self.check()['conditional_X'])

    def test_malformed_requirement_evidence_is_diagnostic(self):
        self.row['requirement_evidence'] = []
        self.assertIn('invalid_evidence_bundle', self.check()['reasons'])

    def test_non_string_session_id_is_diagnostic(self):
        self.row['session_id'] = ['bad']
        report = assess(self.config, [self.row], self.base, self.standard, self.now)
        self.assertEqual(report['sessions_structurally_eligible'], 0)

    def test_target_timezone_cannot_silently_change(self):
        standard = json.loads((HERE.parent / 'trader-score-reference-2026-10-18/copier-standard.json').read_text())
        validate_target(self.config, standard)
        self.config['target']['timezone'] = 'UTC'
        with self.assertRaises(ValueError):
            validate_target(self.config, standard)


if __name__ == '__main__':
    unittest.main()
