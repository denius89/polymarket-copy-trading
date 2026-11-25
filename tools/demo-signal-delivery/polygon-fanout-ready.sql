-- Closed pilot: wait briefly for peer leases before asking for a shared book.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR (SELECT system_identifier::text FROM pg_control_system()) = '7704424041942994981'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind='isolated-public-market-pilot-v1')
    THEN RAISE EXCEPTION 'Expected the isolated Polygon delivery queue'; END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.polygon_quote_peers_ready(p_session uuid,p_signal bigint,p_lease uuid)
RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog AS $ready$
    SELECT EXISTS (
        SELECT FROM demo_delivery.jobs own
        JOIN demo_delivery.signals signal ON signal.id=own.signal_id
        JOIN demo_delivery.closed_polygon_source enrollment ON enrollment.session_id=own.session_id
        WHERE (own.session_id,own.signal_id,own.lease_token)=(p_session,p_signal,p_lease)
          AND own.finished_at IS NULL AND own.lease_until>statement_timestamp()
          AND signal.expires_at>statement_timestamp()
          AND demo_delivery.closed_polygon_scope(p_session) IS NOT NULL
          AND NOT EXISTS (
            SELECT FROM demo_delivery.jobs peer
            JOIN demo_delivery.closed_polygon_source e
                ON e.session_id=peer.session_id AND (e.run_id,e.wallet)=(enrollment.run_id,enrollment.wallet)
            JOIN polygon_live_activity.assignments a ON
                (a.session_id,a.run_id,a.writer_oid,a.owner_address)=(e.session_id,e.run_id,e.writer_oid,e.wallet)
            JOIN polygon_live_activity.stream st ON st.session_id=peer.session_id AND st.status='observing'
            JOIN polygon.paper_sessions ps ON ps.id=peer.session_id AND ps.lifecycle='active'
            JOIN polygon.user_session_slots sl ON (sl.user_id,sl.current_session_id)=(ps.user_id,ps.id)
            WHERE peer.signal_id=p_signal AND peer.session_id<>p_session AND peer.finished_at IS NULL
              AND e.cutoff_at>statement_timestamp() AND a.database_name=current_database()
              AND (peer.lease_token IS NULL OR peer.lease_until<=statement_timestamp())
          )
    )
$ready$;
REVOKE ALL ON FUNCTION demo_delivery.polygon_quote_peers_ready(uuid,bigint,uuid) FROM PUBLIC,polygon_executor;

DO $grant$
DECLARE writer name;
BEGIN
    FOR writer IN
        SELECT DISTINCT a.writer_role FROM demo_delivery.closed_polygon_source e
        JOIN polygon_live_activity.assignments a
        ON (a.session_id,a.run_id,a.writer_oid,a.owner_address)=(e.session_id,e.run_id,e.writer_oid,e.wallet)
        WHERE a.database_name=current_database() AND polygon_live_activity.role_valid(a.writer_oid)
          AND has_function_privilege(a.writer_oid,'demo_delivery.claim_polygon_quote(uuid,jsonb)','EXECUTE')
    LOOP
        EXECUTE format('GRANT EXECUTE ON FUNCTION demo_delivery.polygon_quote_peers_ready(uuid,bigint,uuid) TO %I',writer);
    END LOOP;
END
$grant$;

ALTER TABLE demo_delivery.polygon_waiting_outcomes DROP CONSTRAINT polygon_waiting_outcomes_reason_check;
ALTER TABLE demo_delivery.polygon_waiting_outcomes ADD CHECK
    (reason IN ('signal_expired','book_unavailable','book_stale','insufficient_liquidity'));

DO $refusals$
DECLARE
    body text:=pg_get_functiondef('demo_delivery.complete_polygon_refusal(uuid,bigint,uuid,text)'::regprocedure);
    allowed constant text:=$m$p_reason NOT IN ('signal_expired','book_unavailable')$m$;
    expiry constant text:=$m$p_reason = 'book_unavailable'$m$;
BEGIN
    IF cardinality(string_to_array(body,allowed))<>2 OR cardinality(string_to_array(body,expiry))<>3
    THEN RAISE EXCEPTION 'Unexpected Polygon refusal definition'; END IF;
    EXECUTE replace(replace(body,allowed,
        $m$p_reason NOT IN ('signal_expired','book_unavailable','book_stale','insufficient_liquidity')$m$),
        expiry,$m$p_reason IN ('book_unavailable','book_stale','insufficient_liquidity')$m$);
END
$refusals$;
COMMIT;
