-- Bind a verified live source candidate to its already recorded queue item.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

CREATE FUNCTION demo_delivery.claim_polygon_quote(p_session uuid,p_log jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $claim$
DECLARE
    target record;
    leased record;
BEGIN
    IF current_setting('transaction_isolation') <> 'serializable'
       OR demo_delivery.closed_polygon_scope(p_session) IS NULL
    THEN RETURN NULL; END IF;
    SELECT j.signal_id, o.id AS observation_id INTO target
    FROM demo_delivery.jobs j
    JOIN demo_delivery.signals s ON s.id=j.signal_id
    JOIN polygon_live_activity.observations o ON o.session_id=j.session_id
        AND o.raw_log=s.payload->'log' AND o.header=s.payload->'header'
    JOIN polygon_live_activity.decisions d ON (d.session_id,d.observation_id)=(o.session_id,o.id)
    WHERE j.session_id=p_session AND j.finished_at IS NULL AND o.raw_log=p_log
      AND s.venue='polymarket' AND s.payload->>'kind'='polygon-finalized-buy'
      AND s.expires_at>clock_timestamp()
      AND d.checks->>'executionAdmission'='awaiting_quote'
      AND demo_delivery.polygon_waiting_valid(o.id,d.checks->'evidence',true)
      AND NOT EXISTS (SELECT FROM demo_delivery.jobs earlier
          WHERE earlier.session_id=j.session_id AND earlier.finished_at IS NULL AND earlier.signal_id<j.signal_id);
    IF NOT FOUND THEN RETURN NULL; END IF;
    SELECT * INTO leased FROM demo_delivery.claim_polygon_result(p_session,interval '15 seconds');
    IF NOT FOUND THEN RETURN NULL; END IF;
    IF leased.signal_id IS DISTINCT FROM target.signal_id OR leased.status IS DISTINCT FROM 'claimed'
    THEN RAISE EXCEPTION 'Polygon quote claim moved' USING ERRCODE='40001'; END IF;
    RETURN jsonb_build_object('signalId',leased.signal_id::text,'observationId',target.observation_id,
                              'lease',leased.lease_token,'expiresAt',leased.expires_at);
END
$claim$;

REVOKE ALL ON FUNCTION demo_delivery.claim_polygon_quote(uuid,jsonb) FROM PUBLIC,polygon_executor;

CREATE FUNCTION demo_delivery.polygon_waiting_evaluations(p_session uuid,p_logs jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $stage$
DECLARE
    scope jsonb;
    items jsonb;
BEGIN
    scope := demo_delivery.closed_polygon_scope(p_session);
    IF scope IS NULL OR current_setting('transaction_isolation') <> 'serializable'
    THEN RETURN NULL; END IF;
    IF jsonb_typeof(p_logs) IS DISTINCT FROM 'array' OR jsonb_array_length(p_logs) > 128
       OR octet_length(p_logs::text) > 1048576
    THEN RAISE EXCEPTION 'Invalid Polygon waiting evidence request'; END IF;

    SELECT coalesce(jsonb_agg(jsonb_build_object(
           'transactionHash', log->>'transactionHash', 'logIndex', log->>'logIndex',
           'evidence', jsonb_build_object('schemaVersion','polygon-queue-waiting-v1',
               'kind','awaiting_quote','signalId',s.id::text,'binding',NULL,
               'evidenceSha256',log->>'receiptSha256')) ORDER BY s.id),'[]'::jsonb)
    INTO items
    FROM jsonb_array_elements(p_logs) log
    JOIN demo_delivery.signals s ON s.venue='polymarket'
        AND s.trader_key=scope->>'wallet' AND s.payload->>'kind'='polygon-finalized-buy'
        AND s.execution_key='137:' || (log->>'transactionHash') || ':' || (log->>'logIndex')
        AND s.payload->'log'=log
    JOIN demo_delivery.jobs j ON j.signal_id=s.id AND j.session_id=p_session AND j.finished_at IS NULL;
    RETURN items;
END
$stage$;
REVOKE ALL ON FUNCTION demo_delivery.polygon_waiting_evaluations(uuid,jsonb) FROM PUBLIC,polygon_executor;

CREATE FUNCTION demo_delivery.expire_next_polygon_job(p_session uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $expire$
DECLARE
    target bigint;
    leased record;
BEGIN
    IF current_setting('transaction_isolation') <> 'serializable'
       OR demo_delivery.closed_polygon_scope(p_session) IS NULL
    THEN RETURN false; END IF;
    SELECT j.signal_id INTO target
    FROM demo_delivery.jobs j
    WHERE j.session_id=p_session AND j.finished_at IS NULL
    ORDER BY j.signal_id LIMIT 1;
    IF target IS NULL OR NOT EXISTS (
        SELECT FROM demo_delivery.signals s
        JOIN polygon_live_activity.observations o ON o.session_id=p_session AND o.raw_log=s.payload->'log'
        JOIN polygon_live_activity.decisions d ON (d.session_id,d.observation_id)=(o.session_id,o.id)
        WHERE s.id=target AND s.expires_at<=clock_timestamp()
          AND d.checks#>>'{evidence,signalId}'=target::text
    ) THEN RETURN false; END IF;
    SELECT * INTO leased FROM demo_delivery.claim_polygon_result(p_session,interval '10 seconds');
    IF NOT FOUND THEN RETURN false; END IF;
    IF leased.signal_id IS DISTINCT FROM target OR leased.status IS DISTINCT FROM 'expired'
    THEN RAISE EXCEPTION 'Polygon expiry claim moved' USING ERRCODE='40001'; END IF;
    RETURN demo_delivery.complete_polygon_expiry(p_session,target,leased.lease_token);
END
$expire$;
REVOKE ALL ON FUNCTION demo_delivery.expire_next_polygon_job(uuid) FROM PUBLIC,polygon_executor;
COMMIT;
