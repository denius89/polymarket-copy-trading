\set ON_ERROR_STOP on
-- SERVER OPERATOR ONLY, disposable offline clone, never the permanent PG target.
-- Caller must assert container label/name, --network none, no TCP listen, then
-- set PGOPTIONS=-c polygon.disposable_test=offline-clone. Every fixture rolls back.
BEGIN ISOLATION LEVEL SERIALIZABLE;
DO $$ BEGIN
 IF current_setting('polygon.disposable_test',true) IS DISTINCT FROM 'offline-clone' THEN
  RAISE EXCEPTION 'explicit disposable clone marker required'; END IF;
 IF (SELECT count(*) FROM polygon.users)<>2 OR EXISTS(SELECT 1 FROM polygon.command_keys) THEN
  RAISE EXCEPTION 'fresh additive paper schema required'; END IF;
END $$;
UPDATE polygon.profile SET enabled=true;
UPDATE polygon.paper_controls SET enabled=true,version=version+1;
SELECT set_config('polygon.test_tzdb',timezone_database_version,true) FROM polygon.profile;
CREATE TEMP TABLE checks(label text PRIMARY KEY);
CREATE FUNCTION pg_temp.assert_true(ok boolean, label text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'assertion failed: %',label; END IF; INSERT INTO checks VALUES(label); END $$;
CREATE TEMP TABLE fixture(n integer PRIMARY KEY, user_id uuid, auth jsonb, venue_id uuid, trader_id uuid);
DO $$
DECLARE u record; n integer:=0; ctx uuid; login uuid; op uuid; secret uuid; p jsonb; r jsonb; venue uuid; trader uuid;
BEGIN
 FOR u IN SELECT * FROM polygon.users ORDER BY id LOOP
  n:=n+1; ctx:=gen_random_uuid(); login:=gen_random_uuid(); op:=gen_random_uuid(); secret:=gen_random_uuid();
  INSERT INTO v00_session.contexts(id,actor_id,proof_digest,expires_at,login_expires_at,idle_expires_at)
   VALUES(ctx,u.auth_actor_id,repeat('a',64),clock_timestamp()+interval '1 hour',clock_timestamp()+interval '1 hour',clock_timestamp()+interval '1 hour');
  p:=jsonb_build_object('context_id',ctx,'proof_digest',repeat('a',64),'operation_id',op,'fingerprint',repeat('b',64));
  r:=v00_session.plan_completion(p||jsonb_build_object('login_id',login,'secret_id',secret));
  PERFORM pg_temp.assert_true(r->>'http'='200','fixture_plan_'||n);
  r:=v00_session.complete(p||jsonb_build_object('cookie_digest',repeat('c',64),'ciphertext',encode(decode(repeat('11',16),'hex'),'base64'),
   'nonce',encode(decode(repeat('22',24),'hex'),'base64'),'key_id','disposable-only','credential_key_id','disposable-only'));
  PERFORM pg_temp.assert_true(r->>'http'='200','fixture_completion_'||n);
  SELECT v.id,t.id INTO venue,trader FROM polygon.venues v JOIN polygon.traders t ON t.venue_id=v.id
   WHERE v.code=CASE n WHEN 1 THEN 'polymarket' ELSE 'limitless' END ORDER BY t.id LIMIT 1;
  INSERT INTO fixture VALUES(n,u.id,jsonb_build_object('login_id',login,'cookie_digest',repeat('c',64)),venue,trader);
 END LOOP;
END $$;
CREATE TEMP TABLE observations(n integer PRIMARY KEY, create_request jsonb, create_reply jsonb, update_receipt uuid,
 draft_id uuid, review_reply jsonb, start_request jsonb, start_reply jsonb);
GRANT SELECT ON fixture TO polygon_executor;
GRANT SELECT,INSERT,UPDATE ON observations TO polygon_executor;
GRANT INSERT ON checks TO polygon_executor;
SET LOCAL ROLE polygon_executor;
DO $$
DECLARE f record; b jsonb; p jsonb; r jsonb; old_r jsonb; d uuid; updated uuid; q jsonb; prep jsonb; start_b jsonb; rid uuid;
BEGIN
 FOR f IN SELECT * FROM fixture ORDER BY n LOOP
  r:=polygon.current_identity(jsonb_build_object('auth',f.auth));
  PERFORM pg_temp.assert_true(r->>'user_id'=f.user_id::text,'identity_'||f.n);
  r:=polygon.catalog_read(jsonb_build_object('auth',f.auth,'venue_code',CASE f.n WHEN 1 THEN 'polymarket' ELSE 'limitless' END));
  PERFORM pg_temp.assert_true(r->>'http'='200' AND jsonb_array_length(r->'items')=2,'catalog_'||f.n);
  r:=polygon.q04_session(jsonb_build_object('auth',f.auth,'session_id',NULL));
  PERFORM pg_temp.assert_true(r='{"http":200,"session":null}'::jsonb,'empty_current_'||f.n);
  b:=jsonb_build_object('requestSchemaVersion','v1','clientCommandId',gen_random_uuid(),'locale','ru','step','configure','entryContext','catalog',
   'venueId',f.venue_id,'traderId',f.trader_id,'selectedMode',CASE f.n WHEN 1 THEN 'fixed' ELSE 'percent' END,
   'rawBudget',CASE f.n WHEN 1 THEN 'MjAw' ELSE 'MTAw' END, -- 200 / 100
   'rawFixedAmount','MjA=','rawCopyPercent',CASE f.n WHEN 1 THEN 'anVuaw==' ELSE 'Myw1' END, -- ignored junk / 3,5
   'rawMarketLimitPercent',CASE f.n WHEN 1 THEN 'MTA=' ELSE 'NQ==' END,
   'rawDailyBuyLimitPercent',CASE f.n WHEN 1 THEN 'MTU=' ELSE 'MTA=' END,'proposedTimezone','UTC');
  p:=jsonb_build_object('auth',f.auth,'draft_id',NULL,'raw_encoding','utf8-base64-v1','request',b);
  r:=polygon.c04_save(p); old_r:=r; d:=(r#>>'{receipt,result,draftId}')::uuid;
  PERFORM pg_temp.assert_true(r->>'http'='201' AND r#>'{receipt,fieldErrors}'='[]'::jsonb,'create_'||f.n);
  PERFORM pg_temp.assert_true(polygon.c04_save(p)=r,'exact_create_replay_'||f.n);
  INSERT INTO observations(n,create_request,create_reply,draft_id) VALUES(f.n,p,r,d);
  IF f.n=1 THEN
   b:=b||jsonb_build_object('clientCommandId',gen_random_uuid(),'expectedDraftVersion','1','rawBudget','MzAw'); -- 300
   p:=p||jsonb_build_object('draft_id',d,'request',b); r:=polygon.c04_save(p); updated:=(r#>>'{receipt,receiptId}')::uuid;
   PERFORM pg_temp.assert_true(r#>>'{receipt,result,draftVersion}'='2','real_update_version');
   PERFORM pg_temp.assert_true(polygon.c04_save((SELECT create_request FROM observations WHERE n=1))=old_r,'replay_after_later_edit');
   b:=b||jsonb_build_object('clientCommandId',gen_random_uuid(),'expectedDraftVersion','2');
   r:=polygon.c04_save(p||jsonb_build_object('request',b));
   PERFORM pg_temp.assert_true(r#>>'{receipt,result,changeKind}'='unchanged' AND r#>>'{receipt,result,draftVersion}'='2','new_key_unchanged');
   q:=polygon.q03_draft(jsonb_build_object('auth',f.auth,'draft_id',d));
   PERFORM pg_temp.assert_true(q#>>'{field_errors_source,receiptId}'=updated::text AND q#>>'{draft,rawBudget}'='MzAw','unchanged_preserves_input_receipt');
   b:=b||jsonb_build_object('clientCommandId',gen_random_uuid(),'expectedDraftVersion','1');
   r:=polygon.c04_save(p||jsonb_build_object('request',b));
   PERFORM pg_temp.assert_true(r->>'http'='409' AND r#>>'{receipt,reasonCode}'='VERSION_CONFLICT','stale_durable_rejection');
   q:=polygon.q05_command(jsonb_build_object('auth',f.auth,'actor_realm','user','actor_id',f.user_id,'command_type','C04','client_command_id',b->>'clientCommandId'));
   PERFORM pg_temp.assert_true(q->>'http'='200' AND q->>'status'='rejected' AND q->'receipt'=r->'receipt','q05_reads_rejection_200');
   UPDATE observations SET update_receipt=updated WHERE n=1;
  END IF;
  q:=polygon.c05_validate(jsonb_build_object('auth',f.auth,'request',jsonb_build_object('requestSchemaVersion','v1','draftId',d,
   'expectedDraftVersion',CASE f.n WHEN 1 THEN '2' ELSE '1' END,'proposedTimezone','UTC')));
  PERFORM pg_temp.assert_true(q->>'http'='200' AND q#>>'{review,allowedToStart}'='true','review_'||f.n);
  PERFORM pg_temp.assert_true(q#>'{review,effectiveMarketLimit}'=CASE f.n WHEN 1 THEN '{"n":"30","d":"1"}'::jsonb ELSE '{"n":"5","d":"1"}'::jsonb END,'exact_market_'||f.n);
  PERFORM pg_temp.assert_true(q#>'{review,effectiveDailyBuyLimit}'=CASE f.n WHEN 1 THEN '{"n":"45","d":"1"}'::jsonb ELSE '{"n":"10","d":"1"}'::jsonb END,'exact_daily_'||f.n);
  start_b:=jsonb_build_object('requestSchemaVersion','v1','clientCommandId',gen_random_uuid(),'reviewId',q#>>'{review,reviewId}',
   'expectedDraftVersion',q#>>'{review,draftVersion}','expectedSlot',q#>'{review,expectedSlot}');
  prep:=polygon.c06_prepare(jsonb_build_object('auth',f.auth,'request',start_b));
  PERFORM pg_temp.assert_true(prep->>'prepared'='true','start_prepare_'||f.n);
  -- UTC golden case only, independent of backend's future DST calculator.
  r:=polygon.c06_finish(jsonb_build_object('auth',f.auth,'ticket_id',prep->>'ticket_id',
   'evaluation_deadline_at',to_char(((prep->>'started_at')::timestamptz+interval '14 days') AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
   'deadline_calculation_version','paper-evaluation-deadline-v1','timezone_database_version',current_setting('polygon.test_tzdb')));
  PERFORM pg_temp.assert_true(r->>'http'='201','start_finish_'||f.n);
  PERFORM pg_temp.assert_true(polygon.c06_prepare(jsonb_build_object('auth',f.auth,'request',start_b))=r,'start_replay_'||f.n);
  q:=polygon.q04_session(jsonb_build_object('auth',f.auth,'session_id',NULL));
  PERFORM pg_temp.assert_true(q#>>'{session,summary,sessionId}'=r#>>'{receipt,result,sessionId}'
   AND q#>>'{session,financialSnapshot,contentState}'='EMPTY','current_same_session_'||f.n);
  UPDATE observations SET start_request=start_b,start_reply=r WHERE n=f.n;
 END LOOP;
 SELECT * INTO f FROM fixture WHERE n=2;
 q:=polygon.q03_draft(jsonb_build_object('auth',f.auth,'draft_id',(SELECT draft_id FROM observations WHERE n=1)));
 PERFORM pg_temp.assert_true(q->>'http'='404','cross_user_draft_denied');
 q:=polygon.q04_session(jsonb_build_object('auth',f.auth,'session_id',(SELECT start_reply#>>'{receipt,result,sessionId}' FROM observations WHERE n=1)));
 PERFORM pg_temp.assert_true(q->>'http'='404','cross_user_session_denied');
 q:=polygon.q05_command(jsonb_build_object('auth',f.auth,'actor_realm','user','actor_id',(SELECT user_id FROM fixture WHERE n=1),
 'command_type','C06','client_command_id',(SELECT start_request->>'clientCommandId' FROM observations WHERE n=1)));
 PERFORM pg_temp.assert_true(q->>'http'='404','cross_user_result_denied');
 q:=polygon.c06_prepare(jsonb_build_object('auth',f.auth,'request',(SELECT start_request FROM observations WHERE n=2)||jsonb_build_object('clientCommandId',gen_random_uuid())));
 PERFORM pg_temp.assert_true(q#>>'{receipt,reasonCode}'='DRAFT_USED','used_priority_over_current_session');
END $$;
SET CONSTRAINTS ALL IMMEDIATE;
RESET ROLE;
-- Independent aggregate expected values, not session_valid checking itself.
SELECT pg_temp.assert_true((SELECT count(*)=2 FROM polygon.paper_sessions),'two_sessions');
SELECT pg_temp.assert_true((SELECT count(*)=2 FROM polygon.funding_flows),'two_fundings');
SELECT pg_temp.assert_true((SELECT count(*)=4 AND sum(amount_n/amount_d)=0 FROM polygon.journal_entries),'four_balanced_entries');
SELECT pg_temp.assert_true((SELECT sum(initial_funding_n/initial_funding_d)=400 AND sum(free_n/free_d)=400 AND sum(equity_n/equity_d)=400 FROM polygon.session_snapshots),'total_funding_free_equity_400');
SELECT pg_temp.assert_true((SELECT count(*)=2 FROM polygon.audit_events),'one_audit_per_start');
SELECT pg_temp.assert_true((SELECT count(*)=2 FROM polygon.outbox_events),'one_outbox_per_start');
SELECT pg_temp.assert_true(NOT has_table_privilege('polygon_executor','polygon.command_keys','INSERT'),'runtime_no_direct_key_write');
SELECT pg_temp.assert_true(NOT has_function_privilege('polygon_executor','v00_session.polygon_identity(jsonb)','EXECUTE'),'runtime_no_auth_bridge_access');
SELECT pg_temp.assert_true(NOT has_function_privilege('polygon_executor','polygon.numeric_settings(jsonb,polygon.paper_policy_versions)','EXECUTE'),'runtime_no_internal_helper_access');
-- Check effective rights across the whole namespace, not only one sampled helper.
SELECT pg_temp.assert_true((SELECT bool_and(has_function_privilege('polygon_executor',p.oid,'EXECUTE') =
 (p.oid = ANY(ARRAY[
 'polygon.current_identity(jsonb)'::regprocedure,'polygon.catalog_read(jsonb)'::regprocedure,
 'polygon.c04_save(jsonb)'::regprocedure,'polygon.c05_validate(jsonb)'::regprocedure,
 'polygon.c06_prepare(jsonb)'::regprocedure,'polygon.c06_finish(jsonb)'::regprocedure,
 'polygon.q03_draft(jsonb)'::regprocedure,'polygon.q04_session(jsonb)'::regprocedure,
 'polygon.q05_command(jsonb)'::regprocedure]::oid[])))
 FROM pg_proc p WHERE p.pronamespace='polygon'::regnamespace),'runtime_exact_nine_function_whitelist');
SELECT pg_temp.assert_true(NOT EXISTS(SELECT 1 FROM pg_proc p
 WHERE p.pronamespace='polygon'::regnamespace
 AND has_function_privilege('polygon_executor',p.oid,'EXECUTE WITH GRANT OPTION')),'runtime_no_function_grant_option');
SELECT pg_temp.assert_true(NOT EXISTS(SELECT 1 FROM pg_proc p
 CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
 WHERE (p.pronamespace='polygon'::regnamespace OR p.oid='v00_session.polygon_identity(jsonb)'::regprocedure)
 AND a.grantee=0 AND a.privilege_type='EXECUTE'),'no_public_polygon_or_bridge_execute');
SELECT pg_temp.assert_true(NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(
 (SELECT defaclacl FROM pg_default_acl WHERE defaclrole='polygon_owner'::regrole AND defaclnamespace=0 AND defaclobjtype='f'),
 acldefault('f','polygon_owner'::regrole))) a WHERE a.grantee=0 AND a.privilege_type='EXECUTE')
 AND NOT EXISTS(SELECT 1 FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) a
 WHERE d.defaclrole='polygon_owner'::regrole AND d.defaclobjtype='f'
 AND d.defaclnamespace='polygon'::regnamespace AND a.grantee=0 AND a.privilege_type='EXECUTE'),
 'owner_future_function_defaults_private');
SELECT jsonb_build_object('suite','polygon-paper-db-disposable-v1','passed',count(*),'labels',jsonb_agg(label ORDER BY label),'behavior','local SQL, UTC deadline only; rollback fixtures, no HTTP/provider/DST/P04 proof') FROM checks;
ROLLBACK;
