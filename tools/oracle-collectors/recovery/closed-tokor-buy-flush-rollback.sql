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
DO $pin_func$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon.live_activity_ingest(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'eea97e7b671a807e515ab2ac8f65d9abd1a38277365180080ec4a4b9134996cd' THEN RAISE EXCEPTION 'Unexpected polygon.live_activity_ingest(jsonb)'; END IF; END $pin_func$;
CREATE OR REPLACE FUNCTION polygon.live_activity_ingest(p jsonb)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$ SELECT CASE WHEN polygon.exact_keys(p,ARRAY['session_id','expected_scope','envelope']) IS TRUE THEN
  CASE WHEN polygon_live_activity.uuid_value(p->'session_id') IS TRUE THEN
    polygon.personal_quote_scoped_ingest_v1((p->>'session_id')::uuid,p->'expected_scope',p->'envelope')
  ELSE jsonb_build_object('denied',true) END
 ELSE polygon_live_activity.dispatch(p,'ingest') END $function$
;
DO $pin_func$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.assert_valid()'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '8370803f80ffbdb194f0be1badd7f5bf06a1a47fb1a85bcf40fef133a8ee3f13' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.assert_valid()'; END IF; END $pin_func$;
CREATE OR REPLACE FUNCTION polygon_live_activity.assert_valid()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$
BEGIN
 IF polygon_live_activity.state_valid(COALESCE(NEW.session_id,OLD.session_id)) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete or inconsistent activity bundle' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $function$
;
DO $pin_func$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.assert_bound_valid()'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'f94b7cc2704ab665fabff0cd1b9b5124e4fb9a53ad28c0c24d01db149429604c' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.assert_bound_valid()'; END IF; END $pin_func$;
CREATE OR REPLACE FUNCTION polygon_live_activity.assert_bound_valid()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$
BEGIN
 IF polygon_live_activity.bound_state_valid(COALESCE(NEW.session_id,OLD.session_id)) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete bound skip bundle' USING ERRCODE='23514';END IF;
 RETURN NULL;
END $function$
;
DO $pin_func$ BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.assert_calls()'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'a2e98778519501e99b7703840958b3d67a1903cdfddfe88c00d7de58081fde9a' THEN RAISE EXCEPTION 'Unexpected polygon_live_activity.assert_calls()'; END IF; END $pin_func$;
CREATE OR REPLACE FUNCTION polygon_live_activity.assert_calls()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$
BEGIN
 IF polygon_live_activity.calls_valid(COALESCE(NEW.session_id,OLD.session_id)) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'missing immutable scoped request' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $function$
;
DROP FUNCTION polygon_live_activity.flush_completed_buy(uuid,uuid,text);
DROP FUNCTION polygon_live_activity.in_checked_buy_flush(uuid);
DROP TABLE polygon_live_activity.checked_buy_flush;
COMMIT;
