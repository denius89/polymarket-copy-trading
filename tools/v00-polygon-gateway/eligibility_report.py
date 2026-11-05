"""Closed decoder for the pinned read-only eligibility SELECT; no execution/grants."""
import re

from operator_guards import unique_json
from private_config import ConfigRefusal

PROFILE = 'polygon-fresh-email-eligibility-v1'
SQL_SHA256 = 'af62c72d92b12cd95863572009b4f981c18806eec63eb597638c48f16e14bc5f'
TOP = {'profile', 'directory_count', 'exact_expected_pair', 'gate_open_and_clock_trusted',
       'ready_for_fresh_flow_db_snapshot', 'global_reasons', 'actors', 'runtime_proof_checked',
       'provider_credentials_invalidation_checked', 'network_and_key_isolation_checked',
       'activation_authorized_by_report'}
IDENTITY_BOOL = {'directory_enabled', 'actor_real_clock_unblocked', 'provider_confirmed',
    'provider_not_banned', 'provider_email_source_compatible', 'local_current_factor_present',
    'current_factor_binding_valid', 'subject_totp_pause_active'}
IDENTITY_COUNT = {'active_local_factors', 'verified_totp_factors', 'unverified_provider_factors', 'other_provider_factors'}
STATE_BOOL = {'cooldown_active', 'future_send_evidence', 'current_generation_state_consistent',
              'future_generation_evidence', 'live_confirmation_token', 'live_recovery_token'}
STATE_COUNT = {'unresolved_send_dispatches', 'unresolved_verify_dispatches', 'live_unresolved_admissions',
    'expired_unsealed_admissions', 'completed_email_results', 'unresolved_legacy_provider_seals',
    'live_unresolved_legacy_admissions', 'accepted_sends_total', 'sends_in_15m', 'sends_in_1h',
    'current_generations', 'issued_current_generations', 'consumed_current_generations', 'ambiguous_current_generations'}
ACTOR_REASONS = {'DIRECTORY_ACTOR_MISSING', 'DIRECTORY_DISABLED_OR_KEY_ID_MISMATCH',
    'ACTOR_BLOCKED_MISSING_OR_FIXED_CLOCK', 'PROVIDER_BINDING_MISSING', 'PROVIDER_EMAIL_NOT_CONFIRMED',
    'PROVIDER_BAN_OR_MISSING', 'PROVIDER_EMAIL_SOURCE_INCOMPATIBLE',
    'MFA_REQUIRES_SEPARATE_FLOW_OR_BINDING_REVIEW', 'PROVIDER_MFA_STATE_REQUIRES_REVIEW',
    'UNRESOLVED_ADDRESS_SEND', 'UNRESOLVED_ADDRESS_VERIFY', 'IN_FLIGHT_ADMISSION',
    'UNRESOLVED_LEGACY_PROVIDER_SEAL', 'ADDRESS_SEND_LIMIT_ACTIVE', 'FUTURE_PROVIDER_OR_SEND_EVIDENCE',
    'CURRENT_GENERATION_INCONSISTENT_OR_AMBIGUOUS', 'LIVE_CONFIRMATION_FAMILY_REQUIRES_REVIEW'}
GLOBAL_REASONS = {'DIRECTORY_NOT_EXACT_EXPECTED_SYNTHETIC_PAIR', 'UPSTREAM_GATE_CLOSED_OR_CLOCK_UNTRUSTED'}
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'


def _count(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def _reasons(value, allowed):
    return (type(value) is list and all(type(v) is str and v in allowed for v in value)
            and len(set(value)) == len(value))


def _fields(value, bool_fields, count_fields):
    if (type(value) is not dict or set(value) != bool_fields | count_fields
            or any(type(value[k]) is not bool for k in bool_fields)
            or any(not _count(value[k]) for k in count_fields)):
        raise ConfigRefusal('incomplete eligibility details')


def decode_report(raw, exit_code, expected_actor_ids):
    if type(exit_code) is not int or exit_code != 0:
        raise ConfigRefusal('eligibility process did not complete successfully')
    if (type(raw) is not bytes or len(raw) > 131072 or len(raw.strip().splitlines()) != 1
            or type(expected_actor_ids) not in (tuple, list) or len(expected_actor_ids) != 2
            or any(type(v) is not str or not re.fullmatch(UUID, v) for v in expected_actor_ids)
            or expected_actor_ids[0] == expected_actor_ids[1]):
        raise ConfigRefusal('invalid eligibility transport or expected identities')
    report = unique_json(raw)
    flags = TOP - {'profile', 'directory_count', 'global_reasons', 'actors'}
    if (type(report) is not dict or set(report) != TOP or report['profile'] != PROFILE
            or not _count(report['directory_count']) or any(type(report[k]) is not bool for k in flags)
            or not _reasons(report['global_reasons'], GLOBAL_REASONS)
            or type(report['actors']) is not list or len(report['actors']) != 2):
        raise ConfigRefusal('invalid eligibility report shape')
    for k in ('runtime_proof_checked', 'provider_credentials_invalidation_checked',
              'network_and_key_isolation_checked', 'activation_authorized_by_report'):
        if report[k] is not False:
            raise ConfigRefusal('read-only snapshot cannot authorize or prove runtime')
    pair, gate = report['exact_expected_pair'], report['gate_open_and_clock_trusted']
    if pair and report['directory_count'] != 2:
        raise ConfigRefusal('directory pair and count disagree')
    globals_expected = ([] if pair else ['DIRECTORY_NOT_EXACT_EXPECTED_SYNTHETIC_PAIR']) + ([] if gate else ['UPSTREAM_GATE_CLOSED_OR_CLOCK_UNTRUSTED'])
    if report['global_reasons'] != globals_expected:
        raise ConfigRefusal('global reasons do not match snapshot flags')
    for slot, actor in enumerate(report['actors'], 1):
        if (type(actor) is not dict or set(actor) != {'slot', 'actor_id', 'ready', 'reasons', 'identity_checks', 'state_counts'}
                or type(actor['slot']) is not int or actor['slot'] != slot or type(actor['ready']) is not bool
                or not _reasons(actor['reasons'], ACTOR_REASONS)):
            raise ConfigRefusal('invalid eligibility actor shape')
        if actor['actor_id'] != (expected_actor_ids[slot - 1] if pair else None):
            raise ConfigRefusal('actor does not match the expected synthetic manifest')
        _fields(actor['identity_checks'], IDENTITY_BOOL, IDENTITY_COUNT)
        _fields(actor['state_counts'], STATE_BOOL, STATE_COUNT)
        if actor['ready'] != (pair and gate and not actor['reasons']):
            raise ConfigRefusal('actor ready flag disagrees with reasons')
        if actor['ready']:
            identity, state = actor['identity_checks'], actor['state_counts']
            if (not all(identity[k] for k in ('directory_enabled', 'actor_real_clock_unblocked',
                    'provider_confirmed', 'provider_not_banned', 'provider_email_source_compatible'))
                    or identity['local_current_factor_present'] or identity['current_factor_binding_valid']
                    or any(identity[k] != 0 for k in IDENTITY_COUNT)
                    or any(state[k] != 0 for k in ('unresolved_send_dispatches', 'unresolved_verify_dispatches',
                        'live_unresolved_admissions', 'unresolved_legacy_provider_seals', 'live_unresolved_legacy_admissions',
                        'ambiguous_current_generations'))
                    or state['sends_in_15m'] >= 5 or state['sends_in_1h'] >= 10
                    or any(state[k] for k in ('cooldown_active', 'future_send_evidence', 'future_generation_evidence', 'live_confirmation_token'))
                    or not state['current_generation_state_consistent']):
                raise ConfigRefusal('ready report contains blocking state')
    expected_ready = pair and gate and all(actor['ready'] for actor in report['actors'])
    if report['ready_for_fresh_flow_db_snapshot'] != expected_ready:
        raise ConfigRefusal('overall readiness disagrees with actor readiness')
    return report


def require_ready(raw, exit_code, expected_actor_ids):
    report = decode_report(raw, exit_code, expected_actor_ids)
    if report['ready_for_fresh_flow_db_snapshot'] is not True:
        raise ConfigRefusal('snapshot does not permit this short fresh-auth scenario')
    return report
