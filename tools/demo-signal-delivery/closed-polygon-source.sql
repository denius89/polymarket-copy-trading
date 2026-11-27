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

CREATE TABLE demo_delivery.closed_polygon_source (
    session_id uuid PRIMARY KEY REFERENCES demo_delivery.subscriptions,
    run_id uuid NOT NULL,
    writer_oid oid NOT NULL,
    wallet text NOT NULL,
    cutoff_at timestamptz NOT NULL
);

CREATE FUNCTION demo_delivery.closed_polygon_scope(p_session uuid)
RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog AS $scope$
    SELECT jsonb_build_object(
        'wallet', source.wallet, 'runId', source.run_id, 'checkpoint', jsonb_build_object('number', c.height::text, 'hash', c.block_hash),
        'baseline', st.baseline)
    FROM demo_delivery.closed_polygon_source source
    JOIN polygon_live_activity.assignments a ON (a.session_id,a.run_id,a.writer_oid,a.owner_address) =
                                                 (source.session_id,source.run_id,source.writer_oid,source.wallet)
    JOIN polygon_live_activity.stream st ON st.session_id = a.session_id
    JOIN polygon.paper_sessions p ON p.id = a.session_id
    JOIN polygon.user_session_slots slot ON (slot.user_id,slot.current_session_id) = (p.user_id,p.id)
    JOIN demo_delivery.source_cursors c ON c.venue = 'polymarket' AND c.trader_key = source.wallet
    WHERE source.session_id = p_session AND source.cutoff_at > clock_timestamp()
      AND p.lifecycle = 'active' AND st.status = 'observing'
      AND a.database_name = current_database() AND a.writer_oid = session_user::regrole::oid
      AND polygon_live_activity.role_valid(a.writer_oid)
$scope$;

CREATE FUNCTION demo_delivery.publish_closed_polygon_range(p_session uuid, p_blocks jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $publish$
DECLARE
    scope jsonb;
    b jsonb;
    result jsonb;
    events bigint := 0;
BEGIN
    scope := demo_delivery.closed_polygon_scope(p_session);
    IF scope IS NULL THEN RAISE EXCEPTION 'Polygon source assignment unavailable' USING ERRCODE = '42501'; END IF;
    IF jsonb_typeof(p_blocks) IS DISTINCT FROM 'array' OR jsonb_array_length(p_blocks) NOT BETWEEN 1 AND 16
       OR octet_length(p_blocks::text) > 4194304
    THEN RAISE EXCEPTION 'Invalid Polygon source range'; END IF;

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
        THEN RAISE EXCEPTION 'Polygon source event outside assigned range'; END IF;
        result := demo_delivery.commit_source_block('polymarket', scope->>'wallet',
            (b#>>'{header,number}')::bigint, b#>>'{header,hash}', b#>>'{header,parentHash}', b->'events');
        events := events + (result->>'enqueued')::bigint;
    END LOOP;
    RETURN jsonb_build_object('height',result->'height','enqueued',events);
END
$publish$;

REVOKE ALL ON FUNCTION demo_delivery.closed_polygon_scope(uuid),
    demo_delivery.publish_closed_polygon_range(uuid,jsonb) FROM PUBLIC,polygon_executor;
COMMIT;
