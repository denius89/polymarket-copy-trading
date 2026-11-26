-- Install after closed-demo-runtime-profile.sql on the closed app database.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (
           SELECT FROM demo_delivery.pilot_marker WHERE kind = 'isolated-public-market-pilot-v1'
       )
       OR demo_delivery.activation_release() IS NULL
       OR to_regprocedure('demo_delivery.activation_runtime_profile(uuid,uuid)') IS NULL
    THEN RAISE EXCEPTION 'Expected the closed demo runtime database'; END IF;
END
$gate$;

-- The venue provisioner consumes a canonical C06 identity, not caller-supplied
-- assignment data. The same request ID survives a provisioner restart.
CREATE FUNCTION demo_delivery.pending_demo_assignments(p_venue text)
RETURNS TABLE (
    request_id uuid, session_id uuid, owner_id uuid, trader_revision_id uuid,
    settings_revision_id uuid, wallet text, run_id uuid, session_expires_at timestamptz
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $pending$
    SELECT r.outbox_id, s.id, s.user_id, s.trader_revision_id,
           settings.id, r.wallet, demo_delivery.activation_release(), s.evaluation_deadline_at
    FROM demo_delivery.activation_requests j
    JOIN demo_delivery.start_receipts r ON (r.outbox_id,r.session_id) = (j.request_id,j.session_id)
    JOIN demo_delivery.subscriptions subscription
      ON (subscription.session_id,subscription.venue,subscription.trader_key) = (r.session_id,r.venue,r.wallet)
    JOIN polygon.paper_sessions s ON (s.id,s.trader_revision_id) = (r.session_id,r.trader_revision_id)
    JOIN polygon.user_session_slots slot
      ON (slot.id,slot.user_id,slot.current_session_id) = (s.slot_id,s.user_id,s.id)
    JOIN polygon.settings_revisions settings ON (settings.id,settings.session_id) = (s.current_settings_revision_id,s.id)
    WHERE j.activated_at IS NULL AND r.venue = p_venue AND r.venue IN ('polymarket','limitless')
      AND s.lifecycle = 'active' AND s.evaluation_deadline_at > statement_timestamp() + interval '15 seconds'
      AND settings.sizing_mode = 'fixed' AND settings.fixed_n > 0 AND settings.fixed_d > 0
      AND demo_delivery.app_financial_writer(r.session_id,r.venue) IS NULL
    ORDER BY j.attempt_after,j.request_id
    LIMIT 16
$pending$;

-- Broker mode requires a prepared assignment and leaves jobs without one to
-- the provisioner. Existing in-process adapters can still prepare on claim.
CREATE FUNCTION demo_delivery.claim_activation(p_broker_venues text[])
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $claim$
DECLARE
    claimed jsonb;
BEGIN
    IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'Activation claims require READ COMMITTED';
    END IF;
    IF p_broker_venues IS NULL
       OR NOT (p_broker_venues <@ ARRAY['polymarket','limitless']::text[])
       OR cardinality(p_broker_venues) > 2
    THEN RAISE EXCEPTION 'Invalid activation broker venues'; END IF;

    WITH candidate AS (
        SELECT j.request_id
        FROM demo_delivery.activation_requests j
        JOIN demo_delivery.start_receipts r ON (r.outbox_id,r.session_id) = (j.request_id,j.session_id)
        WHERE j.activated_at IS NULL AND j.attempt_after <= statement_timestamp()
          AND (j.lease_until IS NULL OR j.lease_until <= statement_timestamp())
          AND demo_delivery.app_subscription_current(j.session_id)
          AND (
              NOT (r.venue = ANY(p_broker_venues))
              OR EXISTS (
                  SELECT FROM demo_delivery.session_writers w
                  JOIN demo_delivery.subscriptions subscription ON subscription.session_id = w.session_id
                  WHERE (subscription.session_id,subscription.venue,subscription.trader_key)
                      = (r.session_id,r.venue,r.wallet)
                    AND w.writer_oid = demo_delivery.app_financial_writer(r.session_id,r.venue)
              )
          )
        ORDER BY j.attempt_after,j.request_id
        LIMIT 1 FOR UPDATE OF j SKIP LOCKED
    ), leased AS (
        UPDATE demo_delivery.activation_requests j
           SET token = gen_random_uuid(), lease_until = clock_timestamp() + interval '90 seconds',
               attempt = j.attempt + 1
          FROM candidate c WHERE j.request_id = c.request_id
        RETURNING j.request_id,j.session_id,j.token,j.attempt
    )
    SELECT jsonb_build_object('requestId',j.request_id,'sessionId',j.session_id,
           'token',j.token,'attempt',j.attempt,'venue',r.venue,
           'wallet',r.wallet,'traderRevisionId',r.trader_revision_id)
      INTO claimed
      FROM leased j JOIN demo_delivery.start_receipts r ON (r.outbox_id,r.session_id) = (j.request_id,j.session_id);
    RETURN claimed;
END
$claim$;

ALTER FUNCTION demo_delivery.pending_demo_assignments(text) OWNER TO polygon_owner;
ALTER FUNCTION demo_delivery.claim_activation(text[]) OWNER TO polygon_owner;
REVOKE ALL ON FUNCTION demo_delivery.pending_demo_assignments(text), demo_delivery.claim_activation(text[])
    FROM PUBLIC,polygon_executor;
COMMIT;
