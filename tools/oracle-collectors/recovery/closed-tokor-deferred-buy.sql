BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='25s';

DO $pin$
DECLARE names text[]:=ARRAY['activity_assignment_complete','activity_conflicts_complete','activity_decisions_complete',
 'activity_observations_complete','activity_operations_complete','activity_stream_complete',
 'complete_bound_extension','complete_bound_skip','complete_call'];
BEGIN
    IF (SELECT array_agg(DISTINCT t.tgname::text ORDER BY t.tgname::text)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='polygon_live_activity' AND t.tgname=ANY(names)) IS DISTINCT FROM names
        OR (SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='polygon_live_activity' AND t.tgname=ANY(names)
              AND t.tgdeferrable AND t.tginitdeferred AND t.tgenabled='O' AND NOT t.tgisinternal
              AND t.tgfoid=(CASE WHEN t.tgname='complete_call' THEN 'polygon_live_activity.assert_calls()'
                WHEN t.tgname LIKE 'complete_bound_%' THEN 'polygon_live_activity.assert_bound_valid()'
                ELSE 'polygon_live_activity.assert_valid()' END)::regprocedure)<>15
        OR EXISTS(SELECT FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='polygon_live_activity' AND t.tgname=ANY(names)
              AND (NOT t.tgdeferrable OR NOT t.tginitdeferred OR t.tgenabled<>'O' OR t.tgisinternal
              OR t.tgfoid<>(CASE WHEN t.tgname='complete_call' THEN 'polygon_live_activity.assert_calls()'
                WHEN t.tgname LIKE 'complete_bound_%' THEN 'polygon_live_activity.assert_bound_valid()'
                ELSE 'polygon_live_activity.assert_valid()' END)::regprocedure))
    THEN RAISE EXCEPTION 'Unexpected activity constraint bindings'; END IF;
    -- SET CONSTRAINTS resolves all constraints bearing these names in this schema.
    -- Pin the full relation list as well as each underlying read-only trigger.
    IF (SELECT array_agg(pc.conname::text||'/'||rel.relname::text ORDER BY pc.conname::text COLLATE "C",rel.relname::text COLLATE "C")
        FROM pg_constraint pc JOIN pg_class rel ON rel.oid=pc.conrelid
        WHERE pc.connamespace='polygon_live_activity'::regnamespace AND pc.conname=ANY(names))
       IS DISTINCT FROM ARRAY[
           'activity_assignment_complete/assignments','activity_conflicts_complete/conflicts',
           'activity_decisions_complete/decisions','activity_observations_complete/observations',
           'activity_operations_complete/operations','activity_stream_complete/stream',
           'complete_bound_extension/conflicts','complete_bound_extension/decisions',
           'complete_bound_extension/observations','complete_bound_extension/operations',
           'complete_bound_extension/stream','complete_bound_skip/bound_requests',
           'complete_bound_skip/evaluations','complete_call/calls','complete_call/operations']
       OR EXISTS(
          SELECT FROM pg_constraint pc LEFT JOIN pg_trigger trg ON trg.tgconstraint=pc.oid
          WHERE pc.connamespace='polygon_live_activity'::regnamespace AND pc.conname=ANY(names)
            AND (pc.contype<>'t' OR trg.oid IS NULL OR trg.tgrelid<>pc.conrelid
                 OR trg.tgname<>pc.conname OR trg.tgnargs<>0 OR trg.tgqual IS NOT NULL))
    THEN RAISE EXCEPTION 'Unexpected constraints sharing checked activity names'; END IF;
END
$pin$;

DO $scope$
BEGIN
 IF current_database()<>'shadow_v00' OR NOT EXISTS (
  SELECT FROM polygon_live_activity.assignments
  WHERE session_id='1c6d9f24-0f84-4a13-82f2-e712ff6919cf'
  AND owner_address='0xa19cbababc312f9df185e49d7004c249ed1ade6b'
  AND polygon_live_activity.role_valid(writer_oid))
 THEN RAISE EXCEPTION 'Unexpected closed Tokor scope'; END IF;
END $scope$;
SET LOCAL ROLE polygon_owner;
DO $pin$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon.live_activity_ingest(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'eea97e7b671a807e515ab2ac8f65d9abd1a38277365180080ec4a4b9134996cd' THEN RAISE EXCEPTION 'Unexpected polygon.live_activity_ingest(jsonb)'; END IF; END $pin$;
DO $pin$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.flush_completed_buy(uuid,uuid,text)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '37f017748119f20d372642ff8c4f2dfbe5258962fae3ba3687fd1e9b3545f996' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.flush_completed_buy(uuid,uuid,text)'; END IF; END $pin$;
DO $pin$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.in_checked_buy_flush(uuid)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '05b4dda331b8e705379de29aaa84272f3d9167086045c7bac51c2104ff7185c4' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.in_checked_buy_flush(uuid)'; END IF; END $pin$;
DO $pin$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.bound_state_valid(uuid)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'b8ab21c4676cef6c1d0d04bdf38a144eb856537c032407b2d2744de9000e3e3a' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.bound_state_valid(uuid)'; END IF; END $pin$;
DO $pin$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.assert_valid()'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '8370803f80ffbdb194f0be1badd7f5bf06a1a47fb1a85bcf40fef133a8ee3f13' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.assert_valid()'; END IF; END $pin$;
DO $pin$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.assert_calls()'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'a2e98778519501e99b7703840958b3d67a1903cdfddfe88c00d7de58081fde9a' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.assert_calls()'; END IF; END $pin$;
DO $pin$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.assert_bound_valid()'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'f94b7cc2704ab665fabff0cd1b9b5124e4fb9a53ad28c0c24d01db149429604c' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.assert_bound_valid()'; END IF; END $pin$;
DO $checked$ BEGIN
 IF EXISTS (SELECT FROM polygon_live_activity.checked_buy_flush)
 OR EXISTS (SELECT FROM pg_trigger WHERE tgrelid='polygon_live_activity.checked_buy_flush'::regclass AND NOT tgisinternal)
 THEN RAISE EXCEPTION 'Unexpected pending checks before install'; END IF;
END $checked$;
-- One mandatory finalizer per drained constraint name. Early SET CONSTRAINTS
-- on any subset validates this session before the pending marker can suppress it.
ALTER TABLE polygon_live_activity.checked_buy_flush ADD COLUMN deferred_buy boolean NOT NULL DEFAULT false;

CREATE FUNCTION polygon_live_activity.finish_queued_buy() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE sid uuid := NEW.session_id;
BEGIN
    IF NEW.transaction_id IS DISTINCT FROM pg_current_xact_id_if_assigned()
    THEN RAISE EXCEPTION 'unexpected deferred validation transaction' USING ERRCODE='23514'; END IF;
    IF NOT EXISTS (SELECT FROM polygon_live_activity.checked_buy_flush f
                   WHERE (f.transaction_id,f.session_id)=(NEW.transaction_id,sid) AND f.deferred_buy)
    THEN RETURN NULL; END IF;
    -- The pinned bound validator first requires the full canonical state.
    IF polygon_live_activity.bound_state_valid(sid) IS DISTINCT FROM true THEN
        IF polygon_live_activity.state_valid(sid) IS DISTINCT FROM true
        THEN RAISE EXCEPTION 'incomplete or inconsistent activity bundle' USING ERRCODE='23514'; END IF;
        RAISE EXCEPTION 'incomplete bound skip bundle' USING ERRCODE='23514';
    END IF;
    IF polygon_live_activity.calls_valid(sid) IS DISTINCT FROM true
    THEN RAISE EXCEPTION 'missing immutable scoped request' USING ERRCODE='23514'; END IF;
    DELETE FROM polygon_live_activity.checked_buy_flush
    WHERE transaction_id=NEW.transaction_id AND session_id=sid AND deferred_buy;
    IF NOT FOUND THEN RAISE EXCEPTION 'pending buy check missing' USING ERRCODE='23514'; END IF;
    RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION polygon_live_activity.finish_queued_buy() FROM PUBLIC,polygon_executor;
CREATE CONSTRAINT TRIGGER activity_assignment_complete AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE CONSTRAINT TRIGGER activity_conflicts_complete AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE CONSTRAINT TRIGGER activity_decisions_complete AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE CONSTRAINT TRIGGER activity_observations_complete AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE CONSTRAINT TRIGGER activity_operations_complete AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE CONSTRAINT TRIGGER activity_stream_complete AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE CONSTRAINT TRIGGER complete_bound_extension AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE CONSTRAINT TRIGGER complete_bound_skip AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE CONSTRAINT TRIGGER complete_call AFTER INSERT ON polygon_live_activity.checked_buy_flush
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.deferred_buy)
    EXECUTE FUNCTION polygon_live_activity.finish_queued_buy();
CREATE FUNCTION polygon_live_activity.queue_completed_buy(sid uuid, op uuid, buy_source_execution text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog'
AS $function$
DECLARE tx xid8 := pg_current_xact_id_if_assigned();
BEGIN
    IF sid IS DISTINCT FROM '1c6d9f24-0f84-4a13-82f2-e712ff6919cf'::uuid
       OR current_setting('transaction_isolation') <> 'serializable'
       OR tx IS NULL OR NOT EXISTS (
        SELECT FROM polygon_live_activity.stream s
        JOIN polygon_live_activity.assignments a USING (session_id)
        JOIN pg_roles r ON (r.oid,r.rolname)=(a.writer_oid,a.writer_role)
        JOIN polygon_live_activity.operations o ON (o.session_id,o.id)=(s.session_id,s.last_range_operation_id)
        JOIN polygon_live_activity.observations ob ON (ob.session_id,ob.operation_id)=(o.session_id,o.id)
        JOIN polygon_buy.verified_quotes q ON q.session_id=ob.session_id AND q.execution_id=buy_source_execution
                  AND q.quote->>'observationId'=ob.id::text
        JOIN live_buy_core.executions e ON e.session_id=s.session_id AND e.command_id::text=q.quote->>'settleCommandId'
        JOIN live_buy_core.intents i ON (i.session_id,i.id,i.observation_id)=(e.session_id,e.intent_id,ob.id)
        JOIN live_buy_core.receipts receipt ON (receipt.session_id,receipt.command_id)=(e.session_id,e.command_id)
        WHERE s.session_id=sid AND s.status='observing' AND s.last_operation_id=op AND o.id=op
          AND o.kind='ingest' AND o.result->>'kind'='ingest' AND receipt.kind='settle'
          AND r.rolname=session_user AND a.owner_address='0xa19cbababc312f9df185e49d7004c249ed1ade6b'
          AND polygon_live_activity.role_valid(r.oid)
          AND o.xmin=tx::xid AND e.xmin=tx::xid AND receipt.xmin=tx::xid
    ) THEN RETURN jsonb_build_object('queued',false); END IF;

    INSERT INTO polygon_live_activity.checked_buy_flush(transaction_id,session_id,deferred_buy)
    VALUES(tx,sid,true) ON CONFLICT(transaction_id) DO NOTHING;
    RETURN jsonb_build_object('queued',true);
END
$function$
;
REVOKE ALL ON FUNCTION polygon_live_activity.queue_completed_buy(uuid,uuid,text) FROM PUBLIC,polygon_executor;
DO $acl$
BEGIN
 IF EXISTS (
    SELECT FROM pg_proc p,LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
    WHERE p.oid IN('polygon_live_activity.queue_completed_buy(uuid,uuid,text)'::regprocedure,'polygon_live_activity.finish_queued_buy()'::regprocedure)
      AND a.privilege_type='EXECUTE' AND a.grantee<>p.proowner
 ) OR EXISTS (
    SELECT FROM pg_class c,LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a
    WHERE c.oid='polygon_live_activity.checked_buy_flush'::regclass AND a.grantee<>c.relowner
 ) THEN RAISE EXCEPTION 'Unexpected deferred buy access'; END IF;
END $acl$;
CREATE OR REPLACE FUNCTION polygon.live_activity_ingest(p jsonb)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$ SELECT CASE WHEN polygon.exact_keys(p,ARRAY['session_id','queue_buy_operation_id','source_execution_id']) IS TRUE THEN
   CASE WHEN polygon_live_activity.uuid_value(p->'session_id') IS TRUE AND polygon_live_activity.uuid_value(p->'queue_buy_operation_id') IS TRUE
                  AND jsonb_typeof(p->'source_execution_id')='string' AND p->>'source_execution_id' ~ '^[0-9a-f]{64}$'
        THEN polygon_live_activity.queue_completed_buy((p->>'session_id')::uuid,(p->>'queue_buy_operation_id')::uuid,p->>'source_execution_id')
        ELSE jsonb_build_object('queued',false) END
 WHEN polygon.exact_keys(p,ARRAY['session_id','flush_buy_operation_id','source_execution_id']) IS TRUE THEN
   CASE WHEN polygon_live_activity.uuid_value(p->'session_id') IS TRUE AND polygon_live_activity.uuid_value(p->'flush_buy_operation_id') IS TRUE
                  AND jsonb_typeof(p->'source_execution_id')='string' AND p->>'source_execution_id' ~ '^[0-9a-f]{64}$'
        THEN polygon_live_activity.flush_completed_buy((p->>'session_id')::uuid,(p->>'flush_buy_operation_id')::uuid,p->>'source_execution_id')
        ELSE jsonb_build_object('flushed',false) END
 WHEN polygon.exact_keys(p,ARRAY['session_id','expected_scope','envelope']) IS TRUE THEN
  CASE WHEN polygon_live_activity.uuid_value(p->'session_id') IS TRUE THEN
    polygon.personal_quote_scoped_ingest_v1((p->>'session_id')::uuid,p->'expected_scope',p->'envelope')
  ELSE jsonb_build_object('denied',true) END
 ELSE polygon_live_activity.dispatch(p,'ingest') END $function$
;
DO $scope$
BEGIN
 IF current_database()<>'shadow_v00' OR NOT EXISTS (
  SELECT FROM polygon_live_activity.assignments
  WHERE session_id='1c6d9f24-0f84-4a13-82f2-e712ff6919cf'
  AND owner_address='0xa19cbababc312f9df185e49d7004c249ed1ade6b'
  AND polygon_live_activity.role_valid(writer_oid))
 THEN RAISE EXCEPTION 'Unexpected closed Tokor scope'; END IF;
END $scope$;
COMMIT;
