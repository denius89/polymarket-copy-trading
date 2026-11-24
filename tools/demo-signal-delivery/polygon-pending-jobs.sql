-- Apply after polygon-result-ack.sql in the isolated app database.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind = 'isolated-public-market-pilot-v1')
    THEN RAISE EXCEPTION 'Expected the isolated Polygon delivery queue'; END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.claim_polygon_result(p_session uuid, p_lease interval)
RETURNS TABLE(signal_id bigint, session_id uuid, lease_token uuid, expires_at timestamptz,
              payload jsonb, status text, venue text, execution_key text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $claim$
BEGIN
    IF p_lease IS NULL OR p_lease <= interval '0' OR p_lease > interval '30 seconds'
    THEN RAISE EXCEPTION 'Invalid Polygon delivery lease'; END IF;
    IF NOT EXISTS (SELECT FROM demo_delivery.session_writers w
                   WHERE w.session_id = p_session AND w.writer_oid = session_user::regrole::oid)
       OR (polygon_buy.writer(p_session)->>'http') IS DISTINCT FROM '200'
    THEN RETURN; END IF;

    RETURN QUERY
    WITH next_job AS MATERIALIZED (
        SELECT j.signal_id
        FROM demo_delivery.jobs j
        WHERE j.session_id = p_session AND j.finished_at IS NULL
          AND NOT EXISTS (SELECT FROM demo_delivery.jobs earlier
                          WHERE earlier.session_id = j.session_id AND earlier.signal_id < j.signal_id
                            AND earlier.finished_at IS NULL)
        ORDER BY j.signal_id LIMIT 1
        FOR UPDATE OF j SKIP LOCKED
    ), claimed AS (
        UPDATE demo_delivery.jobs j
        SET lease_token = gen_random_uuid(), lease_until = clock_timestamp() + p_lease
        FROM next_job n JOIN demo_delivery.signals s ON s.id = n.signal_id
        WHERE (j.signal_id, j.session_id) = (n.signal_id, p_session)
          AND (j.lease_until IS NULL OR j.lease_until <= clock_timestamp())
          AND s.venue = 'polymarket' AND s.payload->>'kind' = 'polygon-finalized-buy'
          AND s.trader_key = (SELECT a.owner_address FROM polygon_live_activity.assignments a
                              WHERE a.session_id = p_session)
        RETURNING j.signal_id, j.session_id, j.lease_token, s.expires_at,
                  s.payload, s.venue, s.execution_key
    )
    SELECT c.signal_id, c.session_id, c.lease_token, c.expires_at, c.payload,
           CASE WHEN c.expires_at <= clock_timestamp() THEN 'expired' ELSE 'claimed' END,
           c.venue, c.execution_key
    FROM claimed c;
END
$claim$;

REVOKE ALL ON FUNCTION demo_delivery.claim_polygon_result(uuid,interval)
    FROM PUBLIC,polygon_executor;

-- Financial jobs are leased only through the scoped entry point after rollout.
DO $patch$
DECLARE
    definition text := pg_get_functiondef('demo_delivery.claim(integer,interval)'::regprocedure);
    predicate text := 'WHERE j.finished_at IS NULL AND (j.lease_until';
BEGIN
    IF cardinality(string_to_array(definition,predicate)) <> 2
    THEN RAISE EXCEPTION 'Unexpected generic delivery claim'; END IF;
    EXECUTE replace(definition,predicate,
        'WHERE s.payload->>''kind'' IS DISTINCT FROM ''polygon-finalized-buy'' AND j.finished_at IS NULL AND (j.lease_until');
END
$patch$;

DO $patch$
DECLARE
    definition text := pg_get_functiondef('demo_delivery.commit_source_block(text,text,bigint,text,text,jsonb)'::regprocedure);
    predicate text := 'IF enqueued_now > 0 AND (event->>''expiresAt'')';
BEGIN
    IF cardinality(string_to_array(definition,predicate)) <> 2
    THEN RAISE EXCEPTION 'Unexpected source expiry handling'; END IF;
    EXECUTE replace(definition,predicate,
        'IF enqueued_now > 0 AND event#>>''{payload,kind}'' IS DISTINCT FROM ''polygon-finalized-buy'' AND (event->>''expiresAt'')');
END
$patch$;

CREATE FUNCTION demo_delivery.require_polygon_outcome()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $guard$
BEGIN
    IF NEW.finish_reason = 'expired' AND EXISTS (
        SELECT FROM demo_delivery.signals s WHERE s.id = NEW.signal_id
          AND s.venue = 'polymarket' AND s.payload->>'kind' = 'polygon-finalized-buy'
    ) THEN RAISE EXCEPTION 'Polygon job needs an Activity outcome'; END IF;
    RETURN NEW;
END
$guard$;
REVOKE ALL ON FUNCTION demo_delivery.require_polygon_outcome() FROM PUBLIC,polygon_executor;
CREATE TRIGGER polygon_jobs_need_outcomes
    BEFORE UPDATE OF finish_reason ON demo_delivery.jobs
    FOR EACH ROW WHEN (NEW.finish_reason = 'expired')
    EXECUTE FUNCTION demo_delivery.require_polygon_outcome();
COMMIT;
