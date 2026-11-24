-- Apply only to the combined, isolated demo queue database.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind = 'isolated-public-market-pilot-v1')
       OR NOT EXISTS (SELECT FROM polygon_live.installation
                      WHERE singleton AND database_name = current_database())
    THEN
        RAISE EXCEPTION 'Expected the isolated app and delivery queue in one database';
    END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.acknowledge_polygon_result(
    p_signal bigint, p_session uuid, p_token uuid
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $ack$
DECLARE
    execution_key text;
    is_skip boolean;
    deadline timestamptz;
BEGIN
    IF current_setting('transaction_isolation') <> 'serializable'
       OR NOT EXISTS (SELECT FROM demo_delivery.session_writers
                      WHERE session_id = p_session AND writer_oid = session_user::regrole::oid)
    THEN RETURN false; END IF;

    SELECT s.execution_key, d.status = 'skipped' AND i.id IS NULL, s.expires_at
    INTO execution_key, is_skip, deadline
    FROM demo_delivery.signals s
    JOIN polygon_live_activity.assignments a
      ON a.session_id = p_session AND a.owner_address = s.trader_key
    JOIN polygon_live_activity.observations o ON o.session_id = a.session_id
      AND s.payload->'log' = o.raw_log AND s.payload->'header' = o.header
    JOIN polygon_live_activity.decisions d
      ON (d.session_id, d.observation_id) = (o.session_id, o.id)
    LEFT JOIN live_buy_core.intents i
      ON (i.session_id, i.observation_id) = (o.session_id, o.id)
    LEFT JOIN live_buy_core.executions x
      ON (x.session_id, x.intent_id) = (i.session_id, i.id)
    LEFT JOIN live_buy_core.receipts r
      ON (r.session_id, r.command_id, r.intent_id) = (x.session_id, x.command_id, x.intent_id)
      AND r.kind = 'settle'
    WHERE s.id = p_signal AND s.venue = 'polymarket'
      AND s.payload->>'kind' = 'polygon-finalized-buy'
      AND o.classification = 'accepted' AND o.raw_log->>'side' = 'BUY'
      AND s.execution_key = '137:' || o.transaction_hash || ':' || o.log_index::text
      AND ((d.status = 'skipped' AND i.id IS NULL) OR r.command_id IS NOT NULL);

    IF NOT FOUND THEN RETURN false; END IF;
    IF deadline <= clock_timestamp() THEN
        IF NOT is_skip OR (polygon_buy.writer(p_session)->>'http') IS DISTINCT FROM '200'
        THEN RETURN false; END IF;
        UPDATE demo_delivery.jobs j
        SET finished_at = clock_timestamp(), finish_reason = 'acknowledged', lease_token = NULL, lease_until = NULL
        WHERE (j.signal_id, j.session_id, j.lease_token) = (p_signal, p_session, p_token)
          AND j.finished_at IS NULL AND j.lease_until > clock_timestamp();
        IF NOT FOUND THEN RETURN false; END IF;
        PERFORM pg_notify('demo_delivery_ready','');
        RETURN true;
    END IF;
    RETURN demo_delivery.acknowledge_bound(p_signal, p_session, p_token, 'polymarket', execution_key);
END
$ack$;

REVOKE ALL ON FUNCTION demo_delivery.acknowledge_polygon_result(bigint,uuid,uuid)
    FROM PUBLIC,polygon_executor;
COMMIT;
