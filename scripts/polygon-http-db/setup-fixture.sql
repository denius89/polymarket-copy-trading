\set ON_ERROR_STOP on
-- Trusted operator only: fresh offline HTTP-integration clone, never permanent.
-- Required private psql variables: fixture_input (JSON), runtime_role (role name).
-- No raw cookie or cryptographic key is supplied to SQL or emitted here.
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL search_path=pg_catalog,pg_temp;
CREATE TEMP TABLE http_fixture_input(body jsonb NOT NULL, runtime_role text NOT NULL) ON COMMIT DROP;
INSERT INTO http_fixture_input VALUES(:'fixture_input'::jsonb,:'runtime_role');
CREATE TEMP TABLE http_fixture_descriptor(ordinal integer PRIMARY KEY,user_id uuid,login_id uuid,venue_id uuid,trader_id uuid);
DO $$
DECLARE b jsonb; item jsonb; runtime_name text; runtime_oid oid; role_row pg_roles;
 u record; n integer:=0; ctx uuid; lid uuid; op uuid; sid uuid; p jsonb; r jsonb;
 venue uuid; trader uuid; profile polygon.profile; expected oid[];
BEGIN
 IF current_setting('polygon.disposable_test',true) IS DISTINCT FROM 'offline-http-clone' THEN
  RAISE EXCEPTION 'explicit offline HTTP clone marker required'; END IF;
 SELECT body,runtime_role INTO b,runtime_name FROM http_fixture_input;
 IF NOT polygon.exact_keys(b,ARRAY['format','users']) OR b->>'format' IS DISTINCT FROM 'polygon-http-fixture-v1'
 OR jsonb_typeof(b->'users') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'invalid fixture envelope'; END IF;
 IF jsonb_array_length(b->'users')<>2 THEN RAISE EXCEPTION 'two fixture users required'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(b->'users') LOOP
  IF NOT polygon.exact_keys(item,ARRAY['loginId','cookieDigest']) OR NOT polygon.uuid_text(item->>'loginId')
   OR jsonb_typeof(item->'loginId') IS DISTINCT FROM 'string'
   OR jsonb_typeof(item->'cookieDigest') IS DISTINCT FROM 'string'
   OR (item->>'cookieDigest' ~ '^[0-9a-f]{64}$') IS DISTINCT FROM true
  THEN RAISE EXCEPTION 'invalid fixture subject'; END IF;
 END LOOP;
 IF b#>>'{users,0,loginId}'=b#>>'{users,1,loginId}' OR b#>>'{users,0,cookieDigest}'=b#>>'{users,1,cookieDigest}'
 THEN RAISE EXCEPTION 'fixture credentials must be distinct'; END IF;
 SELECT * INTO role_row FROM pg_roles WHERE rolname=runtime_name;
 runtime_oid:=role_row.oid;
 IF runtime_oid IS NULL OR NOT role_row.rolcanlogin OR NOT role_row.rolinherit OR role_row.rolsuper
 OR role_row.rolcreatedb OR role_row.rolcreaterole OR role_row.rolreplication OR role_row.rolbypassrls
 THEN RAISE EXCEPTION 'dedicated unprivileged runtime LOGIN required'; END IF;
 IF (SELECT count(*) FROM pg_auth_members WHERE member=runtime_oid)<>1
 OR NOT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=runtime_oid AND roleid='polygon_executor'::regrole AND NOT admin_option)
 OR pg_has_role(runtime_oid,'polygon_owner','MEMBER')
 OR pg_has_role(runtime_oid,'v00_session_owner','MEMBER')
 THEN RAISE EXCEPTION 'runtime membership must be only polygon_executor'; END IF;
 expected:=ARRAY['polygon.current_identity(jsonb)'::regprocedure,'polygon.catalog_read(jsonb)'::regprocedure,
 'polygon.c04_save(jsonb)'::regprocedure,'polygon.c05_validate(jsonb)'::regprocedure,
 'polygon.c06_prepare(jsonb)'::regprocedure,'polygon.c06_finish(jsonb)'::regprocedure,
 'polygon.q03_draft(jsonb)'::regprocedure,'polygon.q04_session(jsonb)'::regprocedure,
 'polygon.q05_command(jsonb)'::regprocedure]::oid[];
 IF NOT has_schema_privilege(runtime_oid,'polygon','USAGE') OR has_schema_privilege(runtime_oid,'polygon','CREATE')
 OR EXISTS(SELECT 1 FROM pg_proc f WHERE f.pronamespace='polygon'::regnamespace
 AND (has_function_privilege(runtime_oid,f.oid,'EXECUTE') IS DISTINCT FROM (f.oid=ANY(expected))
 OR has_function_privilege(runtime_oid,f.oid,'EXECUTE WITH GRANT OPTION')))
 OR has_function_privilege(runtime_oid,'v00_session.polygon_identity(jsonb)','EXECUTE')
 OR EXISTS(SELECT 1 FROM pg_class c WHERE c.relnamespace='polygon'::regnamespace AND c.relkind IN ('r','p')
 AND has_table_privilege(runtime_oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))
 THEN RAISE EXCEPTION 'runtime effective privileges exceed RPC-only boundary'; END IF;
 SELECT * INTO profile FROM polygon.profile WHERE singleton FOR UPDATE;
 IF profile.singleton IS NULL OR profile.enabled OR EXISTS(SELECT 1 FROM polygon.paper_controls WHERE enabled)
 OR (SELECT count(*) FROM polygon.users)<>2 OR (SELECT count(*) FROM polygon.venues)<>2
 OR (SELECT count(*) FROM polygon.catalog_sources)<>2 OR (SELECT count(*) FROM polygon.traders)<>4
 OR EXISTS(SELECT 1 FROM polygon.command_keys) OR EXISTS(SELECT 1 FROM polygon.drafts)
 OR EXISTS(SELECT 1 FROM polygon.setup_reviews) OR EXISTS(SELECT 1 FROM polygon.paper_sessions)
 OR EXISTS(SELECT 1 FROM polygon.user_session_slots)
 THEN RAISE EXCEPTION 'fresh disabled paper seed required'; END IF;
 FOR u IN SELECT * FROM polygon.users ORDER BY id LOOP
  item:=b->'users'->n; n:=n+1;
  ctx:=gen_random_uuid(); lid:=(item->>'loginId')::uuid; op:=gen_random_uuid(); sid:=gen_random_uuid();
  INSERT INTO v00_session.contexts(id,actor_id,proof_digest,expires_at,login_expires_at,idle_expires_at)
  VALUES(ctx,u.auth_actor_id,repeat('a',64),clock_timestamp()+interval '1 hour',clock_timestamp()+interval '1 hour',clock_timestamp()+interval '1 hour');
  p:=jsonb_build_object('context_id',ctx,'proof_digest',repeat('a',64),'operation_id',op,'fingerprint',repeat('b',64));
  r:=v00_session.plan_completion(p||jsonb_build_object('login_id',lid,'secret_id',sid));
  IF r->>'http' IS DISTINCT FROM '200' THEN RAISE EXCEPTION 'synthetic completion plan failed'; END IF;
  -- Opaque synthetic secret envelope, NOT a real provider/cookie-recovery proof.
  r:=v00_session.complete(p||jsonb_build_object('cookie_digest',item->>'cookieDigest',
   'ciphertext',encode(decode(repeat('11',16),'hex'),'base64'),'nonce',encode(decode(repeat('22',24),'hex'),'base64'),
   'key_id','http-fixture-only','credential_key_id','credential-1'));
  IF r->>'http' IS DISTINCT FROM '200' THEN RAISE EXCEPTION 'synthetic completion failed'; END IF;
  SELECT v.id,t.id INTO venue,trader FROM polygon.venues v JOIN polygon.traders t ON t.venue_id=v.id
   WHERE v.code=CASE n WHEN 1 THEN 'polymarket' ELSE 'limitless' END ORDER BY t.id LIMIT 1;
  IF venue IS NULL OR trader IS NULL THEN RAISE EXCEPTION 'fixture catalog incomplete'; END IF;
  INSERT INTO http_fixture_descriptor VALUES(n,u.id,lid,venue,trader);
 END LOOP;
 UPDATE polygon.paper_controls SET enabled=true,version=version+1;
 UPDATE polygon.profile SET enabled=true;
END $$;
SET CONSTRAINTS ALL IMMEDIATE;
COMMIT;
SELECT jsonb_build_object('format','polygon-http-descriptor-v1','users',jsonb_agg(jsonb_build_object(
 'ordinal',ordinal,'userId',user_id,'loginId',login_id,'venueId',venue_id,'traderId',trader_id) ORDER BY ordinal))
FROM http_fixture_descriptor;
