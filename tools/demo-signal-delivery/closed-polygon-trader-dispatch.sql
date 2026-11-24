-- The closed pilot's trader stage has a cursor independent of any live session state.
-- Apply after fixture enrollment. No permanent role or shared environment is accepted.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR (SELECT system_identifier::text FROM pg_control_system()) = '7704424041942994981'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind = 'isolated-public-market-pilot-v1')
    THEN RAISE EXCEPTION 'Expected the isolated Polygon delivery queue'; END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.closed_trader_checkpoint(p_session uuid)
RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog AS $scope$
    SELECT jsonb_build_object('wallet', source.wallet, 'runId', source.run_id,
                              'height', c.height::text)
    FROM demo_delivery.closed_polygon_source source
    JOIN polygon_live_activity.assignments a ON (a.session_id,a.run_id,a.writer_oid,a.owner_address) =
                                                 (source.session_id,source.run_id,source.writer_oid,source.wallet)
    JOIN demo_delivery.source_cursors c ON c.venue = 'polymarket' AND c.trader_key = source.wallet
    WHERE source.session_id = p_session AND source.cutoff_at > clock_timestamp()
      AND a.database_name = current_database() AND a.writer_oid = session_user::regrole::oid
      AND polygon_live_activity.role_valid(a.writer_oid)
      AND has_function_privilege(session_user,
          'demo_delivery.publish_closed_polygon_range(uuid,jsonb)', 'EXECUTE')
$scope$;

CREATE FUNCTION demo_delivery.dispatch_closed_trader_range(p_session uuid, p_blocks jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $dispatch$
DECLARE
    scope jsonb := demo_delivery.closed_trader_checkpoint(p_session);
    b jsonb;
    result jsonb;
    events bigint := 0;
BEGIN
    IF scope IS NULL THEN RAISE EXCEPTION 'Polygon trader assignment unavailable' USING ERRCODE = '42501'; END IF;
    IF jsonb_typeof(p_blocks) IS DISTINCT FROM 'array' OR jsonb_array_length(p_blocks) NOT BETWEEN 1 AND 16
       OR octet_length(p_blocks::text) > 4194304
    THEN RAISE EXCEPTION 'Invalid Polygon dispatch range'; END IF;

    FOR b IN SELECT value FROM jsonb_array_elements(p_blocks) LOOP
        IF EXISTS (SELECT FROM jsonb_array_elements(b->'events') e
            WHERE e#>>'{payload,kind}' IS DISTINCT FROM 'polygon-finalized-buy'
               OR e#>>'{payload,log,owner}' IS DISTINCT FROM scope->>'wallet'
               OR e#>'{payload,header}' IS DISTINCT FROM b->'header'
               OR e#>>'{payload,log,blockHash}' IS DISTINCT FROM b#>>'{header,hash}'
               OR e#>>'{payload,log,blockNumber}' IS DISTINCT FROM b#>>'{header,number}'
               OR e#>>'{payload,log,side}' IS DISTINCT FROM 'BUY'
               OR e#>>'{payload,log,logIndex}' IS DISTINCT FROM e->>'logIndex'
               OR e->>'executionKey' IS DISTINCT FROM
                  '137:' || (e#>>'{payload,log,transactionHash}') || ':' || (e->>'logIndex'))
        THEN RAISE EXCEPTION 'Polygon event outside the assigned dispatch range'; END IF;
        result := demo_delivery.commit_source_block('polymarket', scope->>'wallet',
            (b#>>'{header,number}')::bigint, b#>>'{header,hash}', b#>>'{header,parentHash}', b->'events');
        events := events + (result->>'enqueued')::bigint;
    END LOOP;
    RETURN jsonb_build_object('height',result->'height','enqueued',events);
END
$dispatch$;

REVOKE ALL ON FUNCTION demo_delivery.closed_trader_checkpoint(uuid),
    demo_delivery.dispatch_closed_trader_range(uuid,jsonb) FROM PUBLIC,polygon_executor;

DO $grant$
DECLARE writer name;
BEGIN
    SELECT DISTINCT a.writer_role INTO STRICT writer
    FROM demo_delivery.closed_polygon_source source JOIN polygon_live_activity.assignments a
       ON (source.session_id,source.run_id,source.writer_oid,source.wallet) =
          (a.session_id,a.run_id,a.writer_oid,a.owner_address)
    WHERE a.database_name = current_database() AND polygon_live_activity.role_valid(a.writer_oid)
      AND has_function_privilege(a.writer_oid, 'demo_delivery.publish_closed_polygon_range(uuid,jsonb)', 'EXECUTE');
    EXECUTE format('GRANT EXECUTE ON FUNCTION demo_delivery.closed_trader_checkpoint(uuid),
        demo_delivery.dispatch_closed_trader_range(uuid,jsonb) TO %I',writer);
END
$grant$;
COMMIT;
