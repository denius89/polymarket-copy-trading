-- Closed single-host pilot. Drain only the existing financial validators after
-- settlement and queue acknowledgement. Keep every other constraint active.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $pin$
DECLARE rule record; actual bigint;
BEGIN
    IF current_database()<>'shadow_v00'
       OR (SELECT system_identifier::text FROM pg_control_system())='7704424041942994981'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker WHERE kind='isolated-public-market-pilot-v1')
    THEN RAISE EXCEPTION 'Expected the isolated Polygon delivery queue'; END IF;
    FOR rule IN SELECT * FROM (VALUES
        ('live_buy_core','complete_graph','live_buy_core.enforce()',13),
        ('live_buy_core','complete_composed','polygon_buy.enforce()',13),
        ('polygon_buy','complete_composed','polygon_buy.enforce()',3)
    ) targets(schema_name,constraint_name,validator,n) LOOP
        SELECT count(*) INTO actual FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
          JOIN pg_namespace ns ON ns.oid=c.relnamespace
          WHERE (ns.nspname,t.tgname)=(rule.schema_name,rule.constraint_name)
             AND t.tgdeferrable AND t.tginitdeferred AND t.tgenabled='O' AND NOT t.tgisinternal
             AND t.tgfoid=to_regprocedure(rule.validator);
        IF actual<>rule.n OR (SELECT count(*) FROM pg_constraint c JOIN pg_namespace ns ON ns.oid=c.connamespace
          WHERE (ns.nspname,c.conname)=(rule.schema_name,rule.constraint_name))<>rule.n
        THEN RAISE EXCEPTION 'Unexpected financial constraint bindings'; END IF;
    END LOOP;
    IF position('live_buy_core.valid(sid)' IN pg_get_functiondef('polygon_buy.session_valid(uuid)'::regprocedure))=0
    THEN RAISE EXCEPTION 'Composed validator does not include the core graph'; END IF;
END
$pin$;

SET LOCAL ROLE polygon_owner;
CREATE TABLE polygon_buy.checked_purchase_flush (
    transaction_id xid8 PRIMARY KEY,
    session_id uuid NOT NULL
);
REVOKE ALL ON polygon_buy.checked_purchase_flush FROM PUBLIC,polygon_executor;

CREATE FUNCTION polygon_buy.in_checked_purchase_flush(sid uuid) RETURNS boolean
LANGUAGE sql STABLE SET search_path=pg_catalog AS $marker$
    SELECT EXISTS(SELECT FROM polygon_buy.checked_purchase_flush m
      WHERE m.transaction_id=pg_current_xact_id_if_assigned() AND m.session_id=sid)
$marker$;
REVOKE ALL ON FUNCTION polygon_buy.in_checked_purchase_flush(uuid) FROM PUBLIC,polygon_executor;

DO $wrappers$
DECLARE rule record; body text; guard text;
BEGIN
    FOR rule IN SELECT * FROM (VALUES
        ('live_buy_core.enforce()', 'live_buy_core.valid(COALESCE(NEW.session_id,OLD.session_id)) IS DISTINCT FROM true'),
        ('polygon_buy.enforce()', 'polygon_buy.session_valid(sid) IS DISTINCT FROM true OR polygon_buy.command_valid(sid) IS DISTINCT FROM true')
    ) targets(validator,check_expression) LOOP
        body:=pg_get_functiondef(to_regprocedure(rule.validator));
        guard:='BEGIN'||chr(10)||' IF '||rule.check_expression;
        IF cardinality(string_to_array(body,guard))<>2
        THEN RAISE EXCEPTION 'Unexpected financial validation body'; END IF;
        EXECUTE replace(body,guard,$guard$BEGIN
 IF (TG_OP<>'UPDATE' OR OLD.session_id IS NOT DISTINCT FROM NEW.session_id)
    AND polygon_buy.in_checked_purchase_flush(COALESCE(NEW.session_id,OLD.session_id))
 THEN RETURN NULL; END IF;
 IF $guard$||rule.check_expression);
    END LOOP;
END
$wrappers$;

CREATE FUNCTION polygon_buy.flush_verified_purchase(sid uuid) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog AS $flush$
DECLARE tx xid8;
BEGIN
    IF polygon_buy.session_valid(sid) IS DISTINCT FROM true OR polygon_buy.command_valid(sid) IS DISTINCT FROM true
    THEN RAISE EXCEPTION 'incomplete composed financial state' USING ERRCODE='23514'; END IF;

    tx:=pg_current_xact_id();
    INSERT INTO polygon_buy.checked_purchase_flush VALUES(tx,sid);
    SET CONSTRAINTS
        live_buy_core.complete_graph,live_buy_core.complete_composed,polygon_buy.complete_composed
        IMMEDIATE;
    DELETE FROM polygon_buy.checked_purchase_flush WHERE transaction_id=tx;
    SET CONSTRAINTS
        live_buy_core.complete_graph,live_buy_core.complete_composed,polygon_buy.complete_composed
        DEFERRED;
END
$flush$;
REVOKE ALL ON FUNCTION polygon_buy.flush_verified_purchase(uuid) FROM PUBLIC,polygon_executor;
RESET ROLE;

CREATE FUNCTION demo_delivery.flush_recorded_polygon_purchase(p_session uuid,p_signal bigint,p_command uuid,p_execution text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $check$
BEGIN
    IF current_setting('transaction_isolation')<>'serializable'
       OR demo_delivery.closed_polygon_scope(p_session) IS NULL
       OR (polygon_buy.writer(p_session)->>'http') IS DISTINCT FROM '200'
       OR NOT EXISTS(
        SELECT FROM demo_delivery.jobs j
        JOIN demo_delivery.signals s ON s.id=j.signal_id
        JOIN polygon_buy.verified_quotes q ON q.session_id=j.session_id AND q.execution_id=p_execution
        JOIN polygon_live_activity.observations o ON (o.session_id,o.raw_log,o.header)=(j.session_id,s.payload->'log',s.payload->'header')
        JOIN live_buy_core.intents i ON (i.session_id,i.observation_id)=(o.session_id,o.id)
        JOIN live_buy_core.executions e ON (e.session_id,e.intent_id)=(i.session_id,i.id)
        JOIN live_buy_core.receipts r ON (r.session_id,r.command_id,r.intent_id)=(e.session_id,e.command_id,e.intent_id)
        WHERE (j.session_id,j.signal_id,e.command_id)=(p_session,p_signal,p_command)
          AND j.finish_reason='acknowledged' AND j.finished_at IS NOT NULL
          AND q.quote->>'observationId'=o.id::text AND q.quote->>'settleCommandId'=p_command::text
          AND r.kind='settle'
       )
    THEN RETURN false; END IF;
    PERFORM polygon_buy.flush_verified_purchase(p_session);
    RETURN true;
END
$check$;
REVOKE ALL ON FUNCTION demo_delivery.flush_recorded_polygon_purchase(uuid,bigint,uuid,text) FROM PUBLIC,polygon_executor;

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
        EXECUTE format('GRANT EXECUTE ON FUNCTION demo_delivery.flush_recorded_polygon_purchase(uuid,bigint,uuid,text) TO %I',writer);
    END LOOP;
END
$grant$;
COMMIT;
