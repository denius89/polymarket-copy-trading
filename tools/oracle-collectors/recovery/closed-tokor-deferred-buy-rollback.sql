BEGIN;
SET LOCAL lock_timeout='5s';
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
DO $pin$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon.live_activity_ingest(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '0804246d326c0b3ecdd52ad6b4075b4405f90b750640237ae1d3f9b60651ebf5' THEN RAISE EXCEPTION 'Unexpected polygon.live_activity_ingest(jsonb)'; END IF; END $pin$;
LOCK TABLE polygon_live_activity.checked_buy_flush IN ACCESS EXCLUSIVE MODE;
DO $pending$ BEGIN IF EXISTS(SELECT FROM polygon_live_activity.checked_buy_flush) THEN RAISE EXCEPTION 'Unexpected pending checks'; END IF; END $pending$;
CREATE OR REPLACE FUNCTION polygon.live_activity_ingest(p jsonb)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$ SELECT CASE WHEN polygon.exact_keys(p,ARRAY['session_id','flush_buy_operation_id','source_execution_id']) IS TRUE THEN
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
DROP TRIGGER activity_assignment_complete ON polygon_live_activity.checked_buy_flush;
DROP TRIGGER activity_conflicts_complete ON polygon_live_activity.checked_buy_flush;
DROP TRIGGER activity_decisions_complete ON polygon_live_activity.checked_buy_flush;
DROP TRIGGER activity_observations_complete ON polygon_live_activity.checked_buy_flush;
DROP TRIGGER activity_operations_complete ON polygon_live_activity.checked_buy_flush;
DROP TRIGGER activity_stream_complete ON polygon_live_activity.checked_buy_flush;
DROP TRIGGER complete_bound_extension ON polygon_live_activity.checked_buy_flush;
DROP TRIGGER complete_bound_skip ON polygon_live_activity.checked_buy_flush;
DROP TRIGGER complete_call ON polygon_live_activity.checked_buy_flush;
DROP FUNCTION polygon_live_activity.finish_queued_buy();
DROP FUNCTION polygon_live_activity.queue_completed_buy(uuid,uuid,text);
ALTER TABLE polygon_live_activity.checked_buy_flush DROP COLUMN deferred_buy;
COMMIT;
