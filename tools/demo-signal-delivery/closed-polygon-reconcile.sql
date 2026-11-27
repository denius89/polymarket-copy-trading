-- Reconcile queue deliveries with immutable outcomes made by the personal writer.
-- Call in the same transaction as the outcome, or later to recover a lost handoff.
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

CREATE FUNCTION demo_delivery.reconcile_closed_polygon_results(
    p_session uuid, p_first bigint, p_last bigint
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $reconcile$
DECLARE
    scope jsonb;
    completed integer;
BEGIN
    scope := demo_delivery.closed_polygon_scope(p_session);
    IF scope IS NULL THEN RAISE EXCEPTION 'Polygon result assignment unavailable' USING ERRCODE = '42501'; END IF;
    IF NOT ((p_first IS NULL AND p_last IS NULL)
         OR (p_first IS NOT NULL AND p_last IS NOT NULL AND p_first >= 1
             AND p_last >= p_first AND p_last - p_first < 256))
    THEN RAISE EXCEPTION 'Invalid Polygon outcome range'; END IF;

    WITH matching AS MATERIALIZED (
        SELECT j.signal_id
        FROM demo_delivery.jobs j
        JOIN demo_delivery.signals s ON s.id = j.signal_id
        JOIN polygon_live_activity.observations o ON o.session_id = j.session_id
            AND o.transaction_hash = s.payload#>>'{log,transactionHash}'
            AND o.log_index = (s.payload#>>'{log,logIndex}')::numeric
            AND o.classification = 'accepted' AND o.raw_log = s.payload->'log'
            AND o.header = s.payload->'header'
        JOIN polygon_live_activity.decisions d ON (d.session_id,d.observation_id) = (o.session_id,o.id)
        LEFT JOIN live_buy_core.intents i ON (i.session_id,i.observation_id) = (o.session_id,o.id)
        LEFT JOIN live_buy_core.executions x ON (x.session_id,x.intent_id) = (i.session_id,i.id)
        LEFT JOIN live_buy_core.receipts r ON (r.session_id,r.intent_id,r.command_id) =
                                               (x.session_id,x.intent_id,x.command_id) AND r.kind = 'settle'
        WHERE j.session_id = p_session AND j.finished_at IS NULL
          AND (j.lease_until IS NULL OR j.lease_until <= clock_timestamp())
          AND s.venue = 'polymarket' AND s.trader_key = scope->>'wallet'
          AND s.payload->>'kind' = 'polygon-finalized-buy' AND o.raw_log->>'side' = 'BUY'
          AND s.execution_key = '137:' || o.transaction_hash || ':' || o.log_index::text
          AND (p_first IS NULL OR (o.raw_log->>'blockNumber')::bigint BETWEEN p_first AND p_last)
          AND ((d.status = 'skipped' AND i.id IS NULL) OR r.command_id IS NOT NULL)
        ORDER BY j.signal_id LIMIT 128
        FOR UPDATE OF j SKIP LOCKED
    )
    UPDATE demo_delivery.jobs j SET
        finished_at = clock_timestamp(), finish_reason = 'acknowledged', lease_token = NULL, lease_until = NULL
    FROM matching m
    WHERE j.session_id = p_session AND j.signal_id = m.signal_id;
    GET DIAGNOSTICS completed = ROW_COUNT;
    IF completed > 0 THEN PERFORM pg_notify('demo_delivery_ready',''); END IF;
    RETURN completed;
END
$reconcile$;

REVOKE ALL ON FUNCTION demo_delivery.reconcile_closed_polygon_results(uuid,bigint,bigint)
    FROM PUBLIC,polygon_executor;
COMMIT;
