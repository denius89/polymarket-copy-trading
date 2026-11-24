BEGIN;
SET LOCAL lock_timeout='4s';
SET LOCAL statement_timeout='20s';
SET LOCAL ROLE polygon_owner;
DO $rollback$ BEGIN
    IF current_database()<>'shadow_v00' OR NOT EXISTS (
      SELECT FROM polygon_live_activity.assignments WHERE session_id='1c6d9f24-0f84-4a13-82f2-e712ff6919cf'
        AND owner_address='0xa19cbababc312f9df185e49d7004c249ed1ade6b'
    ) THEN RAISE EXCEPTION 'closed Tokor scope mismatch'; END IF;
    IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.bound_ingest_guarded(jsonb,jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '5328e1fa565c916c132829b1566f03f0502a2a8d205412031d5eee36a62096dc'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.inner_bound_guarded(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '9d914583b32dd4522cfefae45e481b295fd8d9e83c9f74ad66ab337079cd7db2'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.dispatch_guarded(jsonb,text)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '1459692d1c1f6b1b424f6772ace01fb660cf0671320665aec805a82699b8601b'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon.personal_quote_scoped_ingest_v1(uuid,jsonb,jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '16f5aca5ba826f2f6d8056d8097ae67eaf7cbc9e9fa30a73a64cf8c88a575122' THEN RAISE EXCEPTION 'closed helper changed'; END IF;
END $rollback$;
DO $wrapper$
DECLARE body text:=pg_get_functiondef('polygon.live_activity_ingest(jsonb)'::regprocedure);
BEGIN
    IF encode(sha256(convert_to(body,'UTF8')),'hex') <> '3beeb107ac1774606a6b3081f1afdb2939b65e7e6e396e5a2e85a5a6c65ca16c' THEN
        RAISE EXCEPTION 'closed Tokor wrapper definition mismatch';
    END IF;
    EXECUTE replace(body,$old$SELECT CASE WHEN polygon.exact_keys(p,ARRAY['session_id','expected_scope','envelope']) IS TRUE THEN
  CASE WHEN polygon_live_activity.uuid_value(p->'session_id') IS TRUE THEN
    polygon.personal_quote_scoped_ingest_v1((p->>'session_id')::uuid,p->'expected_scope',p->'envelope')
  ELSE jsonb_build_object('denied',true) END
 ELSE polygon_live_activity.dispatch(p,'ingest') END$old$,$new$SELECT polygon_live_activity.dispatch(p,'ingest')$new$);
    IF encode(sha256(convert_to(pg_get_functiondef('polygon.live_activity_ingest(jsonb)'::regprocedure),'UTF8')),'hex') <> '778da895b45d57433167a126112939d0c06d657d8593f9dfd6f16608c42da5a9' THEN
        RAISE EXCEPTION 'closed Tokor wrapper installation mismatch';
    END IF;
END
$wrapper$;
DROP FUNCTION polygon.personal_quote_scoped_ingest_v1(uuid,jsonb,jsonb);
DROP FUNCTION polygon_live_activity.dispatch_guarded(jsonb,text);
DROP FUNCTION polygon_live_activity.inner_bound_guarded(jsonb);
DROP FUNCTION polygon_live_activity.bound_ingest_guarded(jsonb,jsonb);
COMMIT;
