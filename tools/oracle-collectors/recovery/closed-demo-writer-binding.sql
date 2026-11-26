-- Install only in a verified copy of the application and delivery queue.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL search_path = pg_catalog;

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind='isolated-public-market-pilot-v1')
       OR NOT EXISTS (SELECT FROM polygon_live.installation
                      WHERE singleton AND database_name=current_database())
    THEN
        RAISE EXCEPTION 'Expected the closed app and delivery queue in one database';
    END IF;
END
$gate$;

GRANT SELECT ON demo_delivery.start_receipts, demo_delivery.subscriptions TO polygon_owner;
GRANT SELECT, INSERT ON demo_delivery.session_writers TO polygon_owner;
GRANT UPDATE (writer_oid) ON demo_delivery.session_writers TO polygon_owner;

-- The authoritative assignment is venue-owned. The start observer supplies no
-- role name, wallet, balance or policy and cannot manufacture an assignment.
CREATE OR REPLACE FUNCTION demo_delivery.app_financial_writer(target uuid, venue_code text)
RETURNS oid LANGUAGE plpgsql SET search_path=pg_catalog AS $binding$
DECLARE
    worker oid;
BEGIN
    IF venue_code='polymarket' AND to_regclass('polygon_buy.bindings') IS NOT NULL THEN
        SELECT a.writer_oid INTO worker
        FROM demo_delivery.start_receipts r
        JOIN polygon.paper_sessions s ON (s.id,s.trader_revision_id)=(r.session_id,r.trader_revision_id)
        JOIN polygon_live_activity.assignments a
          ON (a.session_id,a.user_id,a.revision_id,a.owner_address)=(s.id,s.user_id,s.trader_revision_id,r.wallet)
             AND (a.source_id,a.venue_id,a.trader_id)=(s.source_id,s.venue_id,s.trader_id)
        JOIN polygon_live_activity.release_record release
          ON (release.run_id,release.database_name)=(a.run_id,current_database())
        JOIN polygon_live_activity.stream stream ON stream.session_id=a.session_id AND stream.status='observing'
        JOIN polygon_buy.bindings b ON (b.session_id,b.run_id)=(a.session_id,a.run_id)
        JOIN pg_roles role ON (role.oid,role.rolname)=(a.writer_oid,a.writer_role)
        WHERE r.session_id=target AND r.venue=venue_code
          AND role.rolname::text ~ '^polygon_live_writer_[a-f0-9]{32}$';
    ELSIF venue_code='limitless' AND to_regclass('limitless_buy.bindings') IS NOT NULL THEN
        SELECT b.writer_oid INTO worker
        FROM demo_delivery.start_receipts r
        JOIN polygon.paper_sessions s ON (s.id,s.trader_revision_id)=(r.session_id,r.trader_revision_id)
        JOIN limitless_buy.bindings b
          ON (b.session_id,b.owner_id,b.settings_id,b.wallet)=(s.id,s.user_id,s.current_settings_revision_id,r.wallet)
        JOIN pg_roles role ON (role.oid,role.rolname)=(b.writer_oid,b.writer_role)
        WHERE r.session_id=target AND r.venue=venue_code
          AND role.rolname::text ~ '^limitless_buy_writer_[a-f0-9]{32}$';
    END IF;

    IF NOT EXISTS (
        SELECT FROM pg_roles role WHERE role.oid=worker AND role.rolcanlogin
          AND NOT (role.rolsuper OR role.rolcreaterole OR role.rolcreatedb OR role.rolreplication OR role.rolbypassrls)
          AND NOT EXISTS (SELECT FROM pg_auth_members m WHERE m.member=role.oid)
    ) THEN RETURN NULL; END IF;
    RETURN worker;
END
$binding$;

CREATE OR REPLACE FUNCTION demo_delivery.bind_confirmed_writers()
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $observe$
DECLARE
    bound_count integer;
BEGIN
    IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'Queue writer registration requires READ COMMITTED';
    END IF;

    WITH ready AS MATERIALIZED (
        SELECT r.session_id, demo_delivery.app_financial_writer(r.session_id,r.venue) AS writer_oid
        FROM demo_delivery.start_receipts r
        JOIN polygon.paper_sessions s ON s.id=r.session_id
        JOIN polygon.user_session_slots slot
          ON (slot.id,slot.user_id,slot.current_session_id)=(s.slot_id,s.user_id,s.id)
        WHERE s.lifecycle='active' AND s.evaluation_deadline_at>clock_timestamp()
        FOR SHARE OF slot,s SKIP LOCKED
    )
    INSERT INTO demo_delivery.session_writers(session_id,writer_oid)
        SELECT r.session_id,r.writer_oid FROM ready r
        LEFT JOIN demo_delivery.session_writers w USING (session_id)
        WHERE r.writer_oid IS NOT NULL AND w.writer_oid IS DISTINCT FROM r.writer_oid
        ORDER BY r.session_id LIMIT 64
        ON CONFLICT (session_id) DO UPDATE SET writer_oid=excluded.writer_oid
        WHERE demo_delivery.session_writers.writer_oid IS DISTINCT FROM excluded.writer_oid;
    GET DIAGNOSTICS bound_count = ROW_COUNT;
    IF bound_count > 0 THEN PERFORM pg_notify('demo_delivery_ready',''); END IF;
    RETURN bound_count;
END
$observe$;

ALTER FUNCTION demo_delivery.app_financial_writer(uuid,text) OWNER TO polygon_owner;
ALTER FUNCTION demo_delivery.bind_confirmed_writers() OWNER TO polygon_owner;
CREATE OR REPLACE FUNCTION demo_delivery.consume_ready_demo_sessions()
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $poll$
DECLARE
    starts jsonb;
BEGIN
    starts:=demo_delivery.consume_confirmed_starts();
    RETURN starts || jsonb_build_object('writers',demo_delivery.bind_confirmed_writers());
END
$poll$;
ALTER FUNCTION demo_delivery.consume_ready_demo_sessions() OWNER TO polygon_owner;

CREATE OR REPLACE FUNCTION demo_delivery.acknowledge_bound(
    p_signal bigint, p_session uuid, p_token uuid, p_venue text, p_execution text
)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $ack$
BEGIN
    IF EXISTS (SELECT FROM demo_delivery.start_receipts WHERE session_id=p_session) THEN
        PERFORM FROM polygon.paper_sessions s
        JOIN polygon.user_session_slots slot
          ON (slot.id,slot.user_id,slot.current_session_id)=(s.slot_id,s.user_id,s.id)
        WHERE s.id=p_session AND s.lifecycle='active' AND s.evaluation_deadline_at>clock_timestamp()
        FOR SHARE OF slot,s;
        IF NOT FOUND OR demo_delivery.app_financial_writer(p_session,p_venue)
              IS DISTINCT FROM session_user::regrole::oid
        THEN RETURN false; END IF;
    END IF;
    IF NOT EXISTS (
        SELECT FROM demo_delivery.session_writers w
        JOIN demo_delivery.subscriptions subscription USING (session_id)
        JOIN demo_delivery.signals signal
          ON (signal.venue, signal.trader_key) = (subscription.venue, subscription.trader_key)
        WHERE w.session_id = p_session AND w.writer_oid = session_user::regrole::oid
          AND signal.id = p_signal AND signal.venue = p_venue AND signal.execution_key = p_execution
    ) THEN RETURN false; END IF;
    RETURN demo_delivery.acknowledge(p_signal,p_session,p_token);
END
$ack$;

REVOKE ALL ON FUNCTION demo_delivery.app_financial_writer(uuid,text),
    demo_delivery.bind_confirmed_writers(), demo_delivery.consume_ready_demo_sessions()
    FROM PUBLIC,polygon_executor;
COMMIT;
