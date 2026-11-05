import copy
import json
import unittest

import eligibility_report as e
from private_config import ConfigRefusal

ACTORS = ('11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222')


def ready_report():
    actors = []
    for slot, identifier in enumerate(ACTORS, 1):
        identity = {k: False for k in e.IDENTITY_BOOL} | {k: 0 for k in e.IDENTITY_COUNT}
        for k in ('directory_enabled', 'actor_real_clock_unblocked', 'provider_confirmed', 'provider_not_banned', 'provider_email_source_compatible'):
            identity[k] = True
        state = {k: False for k in e.STATE_BOOL} | {k: 0 for k in e.STATE_COUNT}
        state['current_generation_state_consistent'] = True
        actors.append(dict(slot=slot, actor_id=identifier, ready=True, reasons=[], identity_checks=identity, state_counts=state))
    return dict(profile=e.PROFILE, directory_count=2, exact_expected_pair=True,
        gate_open_and_clock_trusted=True, ready_for_fresh_flow_db_snapshot=True,
        global_reasons=[], actors=actors, runtime_proof_checked=False,
        provider_credentials_invalidation_checked=False, network_and_key_isolation_checked=False,
        activation_authorized_by_report=False)


def wire(report):
    return json.dumps(report).encode() + b'\n'


class EligibilityDecoderTests(unittest.TestCase):
    def test_one_complete_snapshot_accepts_but_never_claims_runtime_or_activation(self):
        report = e.require_ready(wire(ready_report()), 0, ACTORS)
        self.assertTrue(report['ready_for_fresh_flow_db_snapshot'])
        self.assertFalse(report['activation_authorized_by_report'])
        self.assertFalse(report['runtime_proof_checked'])

    def test_old_completed_history_and_expired_unsealed_do_not_force_a_reset(self):
        report = ready_report()
        for actor in report['actors']:
            actor['state_counts'].update(completed_email_results=50, expired_unsealed_admissions=20, accepted_sends_total=40)
            actor['identity_checks']['subject_totp_pause_active'] = True
        e.require_ready(wire(report), 0, ACTORS)

    def test_unsuccessful_exit_empty_multiple_records_or_duplicate_fields_refuse(self):
        valid = wire(ready_report())
        for raw, status in [(valid, 1), (b'', 0), (valid + valid, 0), (b'{}\n{}', 0),
                            (valid.replace(b'"directory_count": 2', b'"directory_count": 2, "directory_count": 2'), 0)]:
            with self.assertRaises(ConfigRefusal):e.require_ready(raw, status, ACTORS)

    def test_missing_extra_fields_and_null_boolean_never_become_empty_success(self):
        cases = []
        missing = ready_report();del missing['gate_open_and_clock_trusted'];cases.append(missing)
        cases.append(ready_report() | {'email': 'must-not-be-accepted@example.invalid'})
        cases.append(ready_report() | {'exact_expected_pair': None})
        numeric = ready_report();numeric['actors'][0]['ready'] = 1;cases.append(numeric)
        counter = ready_report();counter['actors'][0]['state_counts']['sends_in_1h'] = False;cases.append(counter)
        for report in cases:
            with self.assertRaises(ConfigRefusal):e.require_ready(wire(report), 0, ACTORS)

    def test_wrong_manifest_identity_or_duplicate_slots_refuse(self):
        report = ready_report();report['actors'][0]['actor_id'] = ACTORS[1]
        with self.assertRaises(ConfigRefusal):e.require_ready(wire(report), 0, ACTORS)
        report = ready_report();report['actors'][1]['slot'] = 1
        with self.assertRaises(ConfigRefusal):e.require_ready(wire(report), 0, ACTORS)
        with self.assertRaises(ConfigRefusal):e.require_ready(wire(ready_report()), 0, (ACTORS[0], ACTORS[0]))

    def test_read_only_report_cannot_authorize_or_claim_provider_invalidation(self):
        for name in ('runtime_proof_checked', 'provider_credentials_invalidation_checked',
                     'network_and_key_isolation_checked', 'activation_authorized_by_report'):
            report = ready_report();report[name] = True
            with self.assertRaises(ConfigRefusal):e.require_ready(wire(report), 0, ACTORS)

    def test_mfa_or_unknown_dispatch_blocks_even_when_overall_ready_is_forged(self):
        for field in e.IDENTITY_COUNT:
            report = ready_report();report['actors'][0]['identity_checks'][field] = 1
            with self.assertRaises(ConfigRefusal):e.require_ready(wire(report), 0, ACTORS)
        for field in ('unresolved_send_dispatches', 'unresolved_verify_dispatches', 'unresolved_legacy_provider_seals'):
            report = ready_report();report['actors'][0]['state_counts'][field] = 1
            with self.assertRaises(ConfigRefusal):e.require_ready(wire(report), 0, ACTORS)

    def test_well_formed_refusal_is_preserved_and_never_cleans_or_disables_mfa(self):
        report = ready_report();report['ready_for_fresh_flow_db_snapshot'] = False
        actor = report['actors'][0];actor['ready'] = False
        actor['reasons'] = ['MFA_REQUIRES_SEPARATE_FLOW_OR_BINDING_REVIEW']
        actor['identity_checks']['verified_totp_factors'] = 1
        before = copy.deepcopy(report)
        self.assertEqual(e.decode_report(wire(report), 0, ACTORS), before)
        with self.assertRaises(ConfigRefusal):e.require_ready(wire(report), 0, ACTORS)
        self.assertEqual(report, before)

    def test_directory_mismatch_hides_ids_and_remains_a_refusal(self):
        report = ready_report();report.update(directory_count=3, exact_expected_pair=False,
            ready_for_fresh_flow_db_snapshot=False, global_reasons=['DIRECTORY_NOT_EXACT_EXPECTED_SYNTHETIC_PAIR'])
        for actor in report['actors']:actor.update(actor_id=None, ready=False)
        self.assertFalse(e.decode_report(wire(report), 0, ACTORS)['ready_for_fresh_flow_db_snapshot'])
        with self.assertRaises(ConfigRefusal):e.require_ready(wire(report), 0, ACTORS)


if __name__ == '__main__':
    unittest.main()
