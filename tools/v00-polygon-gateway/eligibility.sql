\set ON_ERROR_STOP on
-- SOURCE ONLY: not executed. Narrow disposable existing-user C01/C02/Q01 profile.
-- Inputs: owner1_actor_id / owner2_actor_id, UUIDs from the operator's synthetic
-- manifest. No email, OTP, key, cookie, token or digest is an input or output.
-- Use a fresh psql connection (-X -qAt), no outer transaction, after separate
-- package approval. Insufficient privileges/schema mismatch/errors mean STOP.
-- This file creates nothing, calls no project RPC and never opens any gate.
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL search_path = pg_catalog;
SET LOCAL row_security = off;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';

WITH
observed AS MATERIALIZED (SELECT statement_timestamp() AS t),
requested(slot, actor_id) AS (
  VALUES (1, :'owner1_actor_id'::uuid), (2, :'owner2_actor_id'::uuid)
),
directory_shape AS (
  SELECT (SELECT count(*) FROM v00_email.directory) AS directory_count,
    (SELECT count(DISTINCT actor_id) FROM requested) = 2
      AND (SELECT count(*) FROM v00_email.directory) = 2
      AND NOT EXISTS (SELECT 1 FROM requested r WHERE NOT EXISTS
        (SELECT 1 FROM v00_email.directory d WHERE d.actor_id = r.actor_id))
      AS exact_expected_pair
),
gate AS (
  SELECT count(*) = 1 AND coalesce(bool_and(singleton AND is_open AND clock_trusted), false)
    AS gate_open_and_clock_trusted FROM v00_upstream.gate
),
-- Sensitive provider fields are reduced to booleans here; never project row JSON.
base AS MATERIALIZED (
  SELECT r.slot, r.actor_id, d.address_digest, s.provider_user_id, s.current_factor,
    d.actor_id IS NOT NULL AS directory_present,
    coalesce(d.enabled AND d.address_key_id = 'email-address-1', false) AS directory_enabled,
    a.id IS NOT NULL AS actor_present,
    coalesce(NOT a.blocked AND a.fixed_time IS NULL, false) AS actor_real_clock_unblocked,
    s.actor_id IS NOT NULL AS subject_present,
    u.id IS NOT NULL AS provider_present,
    u.email_confirmed_at IS NOT NULL AS provider_confirmed,
    u.id IS NOT NULL AND (u.banned_until IS NULL OR u.banned_until <= o.t) AS provider_not_banned,
    coalesce(u.email <> '' AND u.email = lower(u.email COLLATE "C")
      AND octet_length(u.email) = length(u.email), false) AS provider_email_source_compatible,
    coalesce(s.paused_until > o.t, false) AS subject_totp_pause_active,
    coalesce(u.recovery_token, '') <> '' AS recovery_present,
    coalesce(u.recovery_token ~ '^(pkce_)?[0-9a-f]{56}$', false) AS recovery_shape_valid,
    u.recovery_sent_at,
    coalesce(u.confirmation_token, '') <> '' AS confirmation_present,
    coalesce(u.confirmation_token ~ '^(pkce_)?[0-9a-f]{56}$', false) AS confirmation_shape_valid,
    u.confirmation_sent_at
  FROM requested r CROSS JOIN observed o
  LEFT JOIN v00_email.directory d ON d.actor_id = r.actor_id
  LEFT JOIN v00_session.actors a ON a.id = d.actor_id
  LEFT JOIN v00_upstream.subjects s ON s.actor_id = d.actor_id
  LEFT JOIN auth.users u ON u.id = s.provider_user_id
),
mfa AS (
  SELECT b.slot,
    (SELECT count(*) FROM v00_upstream.factors f WHERE f.actor_id = b.actor_id AND f.active)
      AS active_local_factors,
    (SELECT count(*) FROM auth.mfa_factors f WHERE f.user_id = b.provider_user_id
      AND f.factor_type::text = 'totp' AND f.status::text = 'verified') AS verified_totp_factors,
    (SELECT count(*) FROM auth.mfa_factors f WHERE f.user_id = b.provider_user_id
      AND f.status::text = 'unverified') AS unverified_provider_factors,
    (SELECT count(*) FROM auth.mfa_factors f WHERE f.user_id = b.provider_user_id
      AND (f.factor_type::text IS DISTINCT FROM 'totp'
        OR f.status::text IS NULL OR f.status::text NOT IN ('verified','unverified')))
      AS other_provider_factors,
    EXISTS (SELECT 1 FROM v00_upstream.factors f JOIN auth.mfa_factors pf
      ON pf.id = f.provider_factor_id WHERE f.id = b.current_factor
        AND f.actor_id = b.actor_id AND f.active AND pf.user_id = b.provider_user_id
        AND pf.factor_type::text = 'totp' AND pf.status::text = 'verified')
      AS current_factor_binding_valid
  FROM base b
),
email_history AS (
  SELECT b.slot,
    (SELECT count(*) FROM v00_email.send_dispatches d
      JOIN v00_email.admissions a ON a.id = d.admission_id
      WHERE d.address_digest = b.address_digest AND NOT EXISTS
        (SELECT 1 FROM v00_email.results r WHERE r.context_id = a.context_id
          AND r.operation_id = a.operation_id)) AS unresolved_send_dispatches,
    (SELECT count(*) FROM v00_email.verify_dispatches d
      JOIN v00_email.admissions a ON a.id = d.admission_id
      JOIN v00_email.contexts c ON c.id = a.context_id
      WHERE c.address_digest = b.address_digest AND NOT EXISTS
        (SELECT 1 FROM v00_email.results r WHERE r.context_id = a.context_id
          AND r.operation_id = a.operation_id)) AS unresolved_verify_dispatches,
    (SELECT count(*) FROM v00_email.admissions a JOIN v00_email.contexts c ON c.id = a.context_id
      WHERE c.address_digest = b.address_digest AND a.deadline_at > o.t AND NOT EXISTS
        (SELECT 1 FROM v00_email.results r WHERE r.context_id = a.context_id
          AND r.operation_id = a.operation_id)) AS live_unresolved_admissions,
    (SELECT count(*) FROM v00_email.admissions a JOIN v00_email.contexts c ON c.id = a.context_id
      WHERE c.address_digest = b.address_digest AND a.deadline_at <= o.t AND NOT EXISTS
        (SELECT 1 FROM v00_email.results r WHERE r.context_id = a.context_id
          AND r.operation_id = a.operation_id)
        AND NOT EXISTS (SELECT 1 FROM v00_email.send_dispatches d WHERE d.admission_id = a.id)
        AND NOT EXISTS (SELECT 1 FROM v00_email.verify_dispatches d WHERE d.admission_id = a.id))
      AS expired_unsealed_admissions,
    (SELECT count(*) FROM v00_email.results r JOIN v00_email.contexts c ON c.id = r.context_id
      WHERE c.address_digest = b.address_digest) AS completed_email_results,
    (SELECT count(*) FROM v00_upstream.email_seals es
      JOIN v00_upstream.admissions a ON a.id = es.admission_id
      WHERE es.user_id = b.provider_user_id AND NOT EXISTS
        (SELECT 1 FROM v00_upstream.results r WHERE r.context_id = a.context_id
          AND r.operation_id = a.operation_id)) AS unresolved_legacy_provider_seals,
    (SELECT count(*) FROM v00_upstream.admissions a
      JOIN v00_upstream.contexts c ON c.id = a.context_id
      WHERE c.actor_id = b.actor_id AND a.deadline_at > o.t AND NOT EXISTS
        (SELECT 1 FROM v00_upstream.results r WHERE r.context_id = a.context_id
          AND r.operation_id = a.operation_id)) AS live_unresolved_legacy_admissions
  FROM base b CROSS JOIN observed o
),
send_limits AS (
  SELECT b.slot, count(so.dispatch_id) AS accepted_sends_total,
    count(so.dispatch_id) FILTER (WHERE so.accepted_at > o.t - interval '15 minutes') AS sends_in_15m,
    count(so.dispatch_id) FILTER (WHERE so.accepted_at > o.t - interval '1 hour') AS sends_in_1h,
    coalesce(max(so.accepted_at) + interval '60 seconds' > o.t, false) AS cooldown_active,
    coalesce(bool_or(so.accepted_at > o.t OR so.observed_at > o.t OR sd.sealed_at > o.t), false)
      AS future_send_evidence
  FROM base b CROSS JOIN observed o
  LEFT JOIN v00_email.send_dispatches sd ON sd.address_digest = b.address_digest
  LEFT JOIN v00_email.send_observations so ON so.dispatch_id = sd.id
  GROUP BY b.slot, o.t
),
generation_families AS (
  SELECT b.slot, f.family, g.id IS NOT NULL AS generation_present, g.state,
    f.token_present,
    coalesce(f.sent_at > o.t OR g.issued_at > o.t, false) AS future_generation_evidence,
    -- Normal unused recovery generations may be replaced only by a fresh witnessed
    -- C01. A consumed/absent generation is not a reason to delete history or reset.
    CASE WHEN cg.generation_id IS NULL THEN NOT f.token_present
      WHEN g.id IS NULL OR g.user_id IS DISTINCT FROM b.provider_user_id OR g.family <> f.family THEN false
      WHEN g.state = 'consumed' THEN NOT f.token_present AND g.issued_at IS NOT DISTINCT FROM f.sent_at
      WHEN g.state = 'issued' THEN f.token_present AND f.shape_valid
        AND g.issued_at IS NOT DISTINCT FROM f.sent_at
      ELSE false END AS state_consistent,
    coalesce(f.token_present AND f.sent_at + interval '10 minutes' >= o.t, false) AS live_token
  FROM base b CROSS JOIN observed o
  CROSS JOIN LATERAL (VALUES
    ('recovery', b.recovery_present, b.recovery_shape_valid, b.recovery_sent_at),
    ('confirmation', b.confirmation_present, b.confirmation_shape_valid, b.confirmation_sent_at)
  ) f(family, token_present, shape_valid, sent_at)
  LEFT JOIN v00_upstream.current_generations cg
    ON cg.user_id = b.provider_user_id AND cg.family = f.family
  LEFT JOIN v00_upstream.generations g ON g.id = cg.generation_id
),
generation_summary AS (
  SELECT slot, count(*) FILTER (WHERE generation_present) AS current_generations,
    count(*) FILTER (WHERE state = 'issued') AS issued_current_generations,
    count(*) FILTER (WHERE state = 'consumed') AS consumed_current_generations,
    count(*) FILTER (WHERE state = 'ambiguous') AS ambiguous_current_generations,
    bool_and(state_consistent) AS current_generation_state_consistent,
    bool_or(future_generation_evidence) AS future_generation_evidence,
    bool_or(family = 'confirmation' AND live_token) AS live_confirmation_token,
    bool_or(family = 'recovery' AND live_token) AS live_recovery_token
  FROM generation_families GROUP BY slot
),
actor_review AS (
  SELECT b.slot, b.actor_id,
    array_remove(ARRAY[
      CASE WHEN NOT b.directory_present THEN 'DIRECTORY_ACTOR_MISSING' END,
      CASE WHEN NOT b.directory_enabled THEN 'DIRECTORY_DISABLED_OR_KEY_ID_MISMATCH' END,
      CASE WHEN NOT b.actor_present OR NOT b.actor_real_clock_unblocked THEN 'ACTOR_BLOCKED_MISSING_OR_FIXED_CLOCK' END,
      CASE WHEN NOT b.subject_present OR NOT b.provider_present THEN 'PROVIDER_BINDING_MISSING' END,
      CASE WHEN NOT b.provider_confirmed THEN 'PROVIDER_EMAIL_NOT_CONFIRMED' END,
      CASE WHEN NOT b.provider_not_banned THEN 'PROVIDER_BAN_OR_MISSING' END,
      CASE WHEN NOT b.provider_email_source_compatible THEN 'PROVIDER_EMAIL_SOURCE_INCOMPATIBLE' END,
      CASE WHEN b.current_factor IS NOT NULL OR m.active_local_factors > 0 OR m.verified_totp_factors > 0
        THEN 'MFA_REQUIRES_SEPARATE_FLOW_OR_BINDING_REVIEW' END,
      CASE WHEN m.unverified_provider_factors > 0 OR m.other_provider_factors > 0
        THEN 'PROVIDER_MFA_STATE_REQUIRES_REVIEW' END,
      CASE WHEN h.unresolved_send_dispatches > 0 THEN 'UNRESOLVED_ADDRESS_SEND' END,
      CASE WHEN h.unresolved_verify_dispatches > 0 THEN 'UNRESOLVED_ADDRESS_VERIFY' END,
      CASE WHEN h.live_unresolved_admissions > 0 OR h.live_unresolved_legacy_admissions > 0
        THEN 'IN_FLIGHT_ADMISSION' END,
      CASE WHEN h.unresolved_legacy_provider_seals > 0 THEN 'UNRESOLVED_LEGACY_PROVIDER_SEAL' END,
      CASE WHEN q.sends_in_15m >= 5 OR q.sends_in_1h >= 10 OR q.cooldown_active THEN 'ADDRESS_SEND_LIMIT_ACTIVE' END,
      CASE WHEN q.future_send_evidence OR g.future_generation_evidence THEN 'FUTURE_PROVIDER_OR_SEND_EVIDENCE' END,
      CASE WHEN NOT g.current_generation_state_consistent THEN 'CURRENT_GENERATION_INCONSISTENT_OR_AMBIGUOUS' END,
      CASE WHEN g.live_confirmation_token THEN 'LIVE_CONFIRMATION_FAMILY_REQUIRES_REVIEW' END
    ]::text[], NULL) AS reasons,
    jsonb_build_object(
      'directory_enabled', b.directory_enabled, 'actor_real_clock_unblocked', b.actor_real_clock_unblocked,
      'provider_confirmed', b.provider_confirmed, 'provider_not_banned', b.provider_not_banned,
      'provider_email_source_compatible', b.provider_email_source_compatible,
      'local_current_factor_present', b.current_factor IS NOT NULL,
      'current_factor_binding_valid', m.current_factor_binding_valid,
      'subject_totp_pause_active', b.subject_totp_pause_active,
      'active_local_factors', m.active_local_factors, 'verified_totp_factors', m.verified_totp_factors,
      'unverified_provider_factors', m.unverified_provider_factors, 'other_provider_factors', m.other_provider_factors
    ) AS identity_checks,
    (to_jsonb(h) - 'slot') || (to_jsonb(q) - 'slot') || (to_jsonb(g) - 'slot') AS state_counts
  FROM base b JOIN mfa m USING(slot) JOIN email_history h USING(slot)
    JOIN send_limits q USING(slot) JOIN generation_summary g USING(slot)
),
report AS (
  SELECT ds.directory_count, ds.exact_expected_pair, gt.gate_open_and_clock_trusted,
    ds.exact_expected_pair AND gt.gate_open_and_clock_trusted
      AND coalesce(bool_and(cardinality(ar.reasons) = 0), false) AS ready_for_fresh_flow_db_snapshot,
    array_remove(ARRAY[
      CASE WHEN NOT ds.exact_expected_pair THEN 'DIRECTORY_NOT_EXACT_EXPECTED_SYNTHETIC_PAIR' END,
      CASE WHEN NOT gt.gate_open_and_clock_trusted THEN 'UPSTREAM_GATE_CLOSED_OR_CLOCK_UNTRUSTED' END
    ]::text[], NULL) AS global_reasons,
    jsonb_agg(jsonb_build_object('slot', ar.slot,
      'actor_id', CASE WHEN ds.exact_expected_pair THEN ar.actor_id END,
      'ready', ds.exact_expected_pair AND gt.gate_open_and_clock_trusted AND cardinality(ar.reasons) = 0,
      'reasons', ar.reasons, 'identity_checks', ar.identity_checks, 'state_counts', ar.state_counts
    ) ORDER BY ar.slot) AS actors
  FROM directory_shape ds CROSS JOIN gate gt CROSS JOIN actor_review ar
  GROUP BY ds.directory_count, ds.exact_expected_pair, gt.gate_open_and_clock_trusted
)
SELECT jsonb_build_object(
  'profile', 'polygon-fresh-email-eligibility-v1',
  'directory_count', directory_count, 'exact_expected_pair', exact_expected_pair,
  'gate_open_and_clock_trusted', gate_open_and_clock_trusted,
  'ready_for_fresh_flow_db_snapshot', ready_for_fresh_flow_db_snapshot,
  'global_reasons', global_reasons, 'actors', actors,
  'runtime_proof_checked', false, 'provider_credentials_invalidation_checked', false,
  'network_and_key_isolation_checked', false, 'activation_authorized_by_report', false
) AS eligibility FROM report;

ROLLBACK;
