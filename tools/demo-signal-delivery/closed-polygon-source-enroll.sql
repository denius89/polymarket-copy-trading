-- Pass -v session=<existing session UUID> and -v cutoff=<approved UTC cutoff>.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';
SELECT set_config('demo_delivery.enrollment_session', :'session', true);
SELECT set_config('demo_delivery.enrollment_cutoff', :'cutoff', true);

DO $enroll$
DECLARE
    sid uuid := current_setting('demo_delivery.enrollment_session')::uuid;
    cutoff timestamptz := current_setting('demo_delivery.enrollment_cutoff')::timestamptz;
    assignment polygon_live_activity.assignments;
    stream polygon_live_activity.stream;
BEGIN
    SELECT a.* INTO STRICT assignment FROM polygon_live_activity.assignments a
    JOIN polygon.paper_sessions p ON p.id = a.session_id AND p.lifecycle = 'active'
    JOIN polygon.user_session_slots slot ON (slot.user_id,slot.current_session_id) = (p.user_id,p.id)
    WHERE a.session_id = sid AND a.database_name = current_database()
      AND polygon_live_activity.role_valid(a.writer_oid);
    SELECT * INTO STRICT stream FROM polygon_live_activity.stream st
    WHERE st.session_id = sid AND st.status = 'observing';
    IF cutoff <= clock_timestamp() OR cutoff > clock_timestamp() + interval '7 days'
    THEN RAISE EXCEPTION 'Invalid closed Polygon delivery window'; END IF;
    INSERT INTO demo_delivery.traders VALUES ('polymarket', assignment.owner_address);
    INSERT INTO demo_delivery.subscriptions VALUES (sid,'polymarket',assignment.owner_address,stream.armed_at);
    INSERT INTO demo_delivery.source_cursors VALUES ('polymarket',assignment.owner_address,
        (stream.checkpoint->>'number')::bigint,stream.checkpoint->>'hash');
    INSERT INTO demo_delivery.closed_polygon_source
    VALUES (sid,assignment.run_id,assignment.writer_oid,assignment.owner_address,cutoff);
    EXECUTE format('GRANT USAGE ON SCHEMA demo_delivery TO %I',assignment.writer_role);
    EXECUTE format('GRANT EXECUTE ON FUNCTION demo_delivery.closed_polygon_scope(uuid),
        demo_delivery.publish_closed_polygon_range(uuid,jsonb) TO %I',assignment.writer_role);
END
$enroll$;
COMMIT;
