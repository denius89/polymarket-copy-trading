BEGIN;
SET LOCAL lock_timeout='4s';
SET LOCAL statement_timeout='20s';
SET LOCAL ROLE polygon_owner;

-- Scope lookup holds the session and stream row locks throughout this serializable
-- call. Prior to their first write, dispatch and its two helpers read the same
-- envelope and state. Original public entry points retain their own guards.
DO $install$
DECLARE
    body text;
BEGIN
    IF current_database()<>'shadow_v00' OR NOT EXISTS (
      SELECT FROM polygon_live_activity.assignments WHERE session_id='1c6d9f24-0f84-4a13-82f2-e712ff6919cf'
        AND owner_address='0xa19cbababc312f9df185e49d7004c249ed1ade6b'
    ) THEN RAISE EXCEPTION 'closed Tokor scope mismatch'; END IF;
    IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.bound_ingest(jsonb,jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '0a4dc01b39c1bd73067049636c51a49432f477e41e803112258a569c481d1505'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.inner_bound(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '4f310765c90b7ec44beb7e8cdf3fee9618e18bd4e91e2d386079622a8988c64b'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.dispatch(jsonb,text)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'f7bf732a26679509f51258ca319be7c28b48b078ba50be86fa93516f9b9f5e77'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.writer_guard(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'd31beb5a6d5742d8e46fd003765363f68bd39dc28205801373f7f15977312376'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon.personal_quote_scope_v1(uuid)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM 'fbaffab1141e94f891203aaec8f6d240eeb19cae41a9e96ec17d8a57077eb6cf'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon_buy.writer(uuid)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '4568e0f14c7b66552cfb02152c3a5142d156fd8259df0122bbb98ed91daaad88' THEN RAISE EXCEPTION 'closed Tokor source mismatch'; END IF;
    body:=pg_get_functiondef('polygon_live_activity.bound_ingest(jsonb,jsonb)'::regprocedure);
    body:=replace(body, $old$FUNCTION polygon_live_activity.bound_ingest($old$, $new$FUNCTION polygon_live_activity.bound_ingest_guarded($new$);
    body:=replace(body, $old$a:=polygon_live_activity.writer_guard(p); IF a->>'http'<>'200' THEN RETURN a; END IF;$old$, $new$-- Closed Tokor scoped entry already holds the checked locks.$new$);
    EXECUTE replace(body, 'CREATE OR REPLACE FUNCTION', 'CREATE FUNCTION');
    body:=pg_get_functiondef('polygon_live_activity.inner_bound(jsonb)'::regprocedure);
    body:=replace(body, $old$FUNCTION polygon_live_activity.inner_bound($old$, $new$FUNCTION polygon_live_activity.inner_bound_guarded($new$);
    body:=replace(body, $old$b:=p->'ingest';a:=polygon_live_activity.writer_guard(b);IF a->>'http'<>'200' THEN RETURN a;END IF;
 IF polygon_live_activity.bound_state_valid((b->>'sessionId')::uuid) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;$old$, $new$b:=p->'ingest';$new$);
    body:=replace(body, $old$a:=polygon_live_activity.bound_ingest($old$, $new$a:=polygon_live_activity.bound_ingest_guarded($new$);
    EXECUTE replace(body, 'CREATE OR REPLACE FUNCTION', 'CREATE FUNCTION');
    body:=pg_get_functiondef('polygon_live_activity.dispatch(jsonb,text)'::regprocedure);
    body:=replace(body, $old$FUNCTION polygon_live_activity.dispatch($old$, $new$FUNCTION polygon_live_activity.dispatch_guarded($new$);
    body:=replace(body, $old$a:=polygon_live_activity.writer_guard(b);IF a->>'http'<>'200' THEN RETURN a; END IF;$old$, $new$IF k IS DISTINCT FROM 'ingest' THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;$new$);
    body:=replace(body, $old$a:=polygon_live_activity.inner_bound($old$, $new$a:=polygon_live_activity.inner_bound_guarded($new$);
    EXECUTE replace(body, 'CREATE OR REPLACE FUNCTION', 'CREATE FUNCTION');
END
$install$;

CREATE FUNCTION polygon.personal_quote_scoped_ingest_v1(sid uuid, expected_scope jsonb, envelope jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $scoped$
DECLARE
    reply jsonb;
    scope jsonb;
BEGIN
    IF sid IS DISTINCT FROM '1c6d9f24-0f84-4a13-82f2-e712ff6919cf'::uuid THEN
        RETURN jsonb_build_object('denied',true);
    END IF;
    reply:=polygon.personal_quote_scope_v1(sid);
    IF reply->>'http' IS DISTINCT FROM '200' OR jsonb_typeof(reply->'result') IS DISTINCT FROM 'object' THEN
        RETURN jsonb_build_object('denied',true);
    END IF;
    scope:=reply->'result';
    IF scope->>'sessionId' IS DISTINCT FROM sid::text OR scope->>'wallet' IS DISTINCT FROM '0xa19cbababc312f9df185e49d7004c249ed1ade6b'
       OR scope->>'runId' IS NULL OR envelope->>'session_id' IS DISTINCT FROM sid::text
       OR envelope#>>'{request,ingest,sessionId}' IS DISTINCT FROM sid::text
       OR envelope#>>'{request,ingest,runId}' IS DISTINCT FROM scope->>'runId' THEN
        RETURN jsonb_build_object('denied',true);
    END IF;
    IF scope IS DISTINCT FROM expected_scope THEN
        RETURN jsonb_build_object('scope',scope);
    END IF;
    RETURN jsonb_build_object('scope',scope,'ingest',polygon_live_activity.dispatch_guarded(envelope,'ingest'));
END
$scoped$;
REVOKE ALL ON FUNCTION polygon_live_activity.bound_ingest_guarded(jsonb,jsonb), polygon_live_activity.inner_bound_guarded(jsonb), polygon_live_activity.dispatch_guarded(jsonb,text), polygon.personal_quote_scoped_ingest_v1(uuid,jsonb,jsonb) FROM PUBLIC, polygon_executor;

DO $wrapper$
DECLARE body text:=pg_get_functiondef('polygon.live_activity_ingest(jsonb)'::regprocedure);
BEGIN
    IF encode(sha256(convert_to(body,'UTF8')),'hex') <> '778da895b45d57433167a126112939d0c06d657d8593f9dfd6f16608c42da5a9' THEN
        RAISE EXCEPTION 'closed Tokor wrapper definition mismatch';
    END IF;
    EXECUTE replace(body,$old$SELECT polygon_live_activity.dispatch(p,'ingest')$old$,$new$SELECT CASE WHEN polygon.exact_keys(p,ARRAY['session_id','expected_scope','envelope']) IS TRUE THEN
  CASE WHEN polygon_live_activity.uuid_value(p->'session_id') IS TRUE THEN
    polygon.personal_quote_scoped_ingest_v1((p->>'session_id')::uuid,p->'expected_scope',p->'envelope')
  ELSE jsonb_build_object('denied',true) END
 ELSE polygon_live_activity.dispatch(p,'ingest') END$new$);
    IF encode(sha256(convert_to(pg_get_functiondef('polygon.live_activity_ingest(jsonb)'::regprocedure),'UTF8')),'hex') <> '3beeb107ac1774606a6b3081f1afdb2939b65e7e6e396e5a2e85a5a6c65ca16c' THEN
        RAISE EXCEPTION 'closed Tokor wrapper installation mismatch';
    END IF;
END
$wrapper$;

DO $exposure$
DECLARE
    enrolled name;
    writer_oid oid;
BEGIN
    SELECT r.rolname,r.oid INTO STRICT enrolled, writer_oid
    FROM polygon_live_activity.assignments a JOIN pg_roles r ON (a.writer_role,a.writer_oid)=(r.rolname,r.oid)
    WHERE a.session_id='1c6d9f24-0f84-4a13-82f2-e712ff6919cf';
    IF polygon_live_activity.role_valid(writer_oid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'closed Tokor writer scope changed'; END IF;
    IF EXISTS (
        SELECT FROM pg_proc p, LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
        WHERE p.oid IN ('polygon_live_activity.bound_ingest_guarded(jsonb,jsonb)'::regprocedure,'polygon_live_activity.inner_bound_guarded(jsonb)'::regprocedure,'polygon_live_activity.dispatch_guarded(jsonb,text)'::regprocedure,'polygon.personal_quote_scoped_ingest_v1(uuid,jsonb,jsonb)'::regprocedure) AND a.privilege_type='EXECUTE' AND a.grantee<>p.proowner
    ) THEN RAISE EXCEPTION 'unexpected closed Tokor grants'; END IF;
    IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.bound_ingest_guarded(jsonb,jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '5328e1fa565c916c132829b1566f03f0502a2a8d205412031d5eee36a62096dc'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.inner_bound_guarded(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '9d914583b32dd4522cfefae45e481b295fd8d9e83c9f74ad66ab337079cd7db2'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.dispatch_guarded(jsonb,text)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '1459692d1c1f6b1b424f6772ace01fb660cf0671320665aec805a82699b8601b'
       OR encode(sha256(convert_to(pg_get_functiondef('polygon.personal_quote_scoped_ingest_v1(uuid,jsonb,jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '16f5aca5ba826f2f6d8056d8097ae67eaf7cbc9e9fa30a73a64cf8c88a575122' THEN RAISE EXCEPTION 'private helper mismatch'; END IF;
END
$exposure$;
COMMIT;
