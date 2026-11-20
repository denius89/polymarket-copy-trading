CREATE FUNCTION polygon_live.reply(rid uuid,lookup boolean) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE r polygon_live.results;c polygon_live.completions;body jsonb;
BEGIN
 SELECT * INTO r FROM polygon_live.results WHERE id=rid;
 IF polygon_live.result_valid(rid) IS DISTINCT FROM true OR polygon.session_valid(r.session_id) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 IF r.outcome='committed' THEN
  SELECT * INTO STRICT c FROM polygon_live.completions WHERE result_id=rid;
  body:=jsonb_build_object('completionId',c.id,'sessionId',c.session_id,'sessionVersion','2','snapshotVersion','2',
  'completedAt',v00_session.utc(c.completed_at),'releasedSlotGeneration',c.after_generation::text);
 END IF;
 RETURN jsonb_build_object('http',CASE WHEN lookup OR r.outcome='committed' THEN 200 ELSE 409 END,'status',r.outcome,
 'clientCommandId',r.client_command_id,'completion',body,'reasonCode',r.reason_code);
END $$;
CREATE FUNCTION polygon_live.empty_admitted(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE present boolean; s polygon.paper_sessions;
BEGIN
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF s.id IS NULL OR s.lifecycle<>'active' OR s.version<>1 OR s.control_state<>'copying_not_connected'
 OR polygon.session_valid(sid) IS DISTINCT FROM true THEN RETURN false; END IF;
 -- Only this frozen no-execution profile is supported. No unknown sidecar is treated as zero.
 IF (SELECT array_agg(c.relname::text ORDER BY c.relname::text) FROM pg_class c WHERE c.relnamespace='polygon'::regnamespace AND c.relkind IN('r','p'))
 IS DISTINCT FROM ARRAY['audit_events','catalog_sources','command_keys','command_receipt_details','command_receipts','draft_ownerships','drafts','funding_flows','journal_entries','journals','outbox_events','paper_controls','paper_policy_versions','paper_sessions','profile','read_scopes','scope_sources','session_snapshots','settings_revisions','setup_reviews','start_plans','trader_revisions','traders','user_session_slots','users','venues']::text[] THEN RAISE EXCEPTION 'unknown polygon storage profile' USING ERRCODE='55000'; END IF;
 IF to_regnamespace('polygon_activity') IS NOT NULL OR to_regnamespace('polygon_bound') IS NOT NULL
 OR to_regnamespace('polygon_buy') IS NOT NULL OR to_regnamespace('polygon_execution') IS NOT NULL
 THEN RAISE EXCEPTION 'unsupported execution/activity profile' USING ERRCODE='55000'; END IF;
 IF to_regnamespace('polygon_live_activity') IS NOT NULL THEN
  IF to_regprocedure('polygon_live_activity.has_binding(uuid)') IS NULL THEN RAISE EXCEPTION 'missing activity boundary' USING ERRCODE='55000'; END IF;
  EXECUTE 'SELECT polygon_live_activity.has_binding($1)' INTO present USING sid;
  IF present IS DISTINCT FROM false THEN RETURN false; END IF;
 END IF;
 RETURN true;
END $$;
CREATE FUNCTION polygon.complete_empty_lookup_v1(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;r polygon_live.results;
BEGIN
 IF polygon.exact_keys(p,ARRAY['auth','client_command_id']) IS DISTINCT FROM true OR jsonb_typeof(p->'client_command_id') IS DISTINCT FROM 'string'
 OR polygon.uuid_text(p->>'client_command_id') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO r FROM polygon_live.results WHERE user_id=(a->>'user_id')::uuid AND client_command_id=(p->>'client_command_id')::uuid;
 IF r.id IS NULL THEN RETURN jsonb_build_object('http',202,'status','pending','clientCommandId',p->>'client_command_id','completion',NULL,'reasonCode',NULL); END IF;
 RETURN polygon_live.reply(r.id,true);
END $$;
CREATE FUNCTION polygon.complete_empty_v1(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;b jsonb:=p->'request';s polygon.paper_sessions;sl polygon.user_session_slots;r polygon_live.results;
 sn polygon.session_snapshots;cid uuid:=gen_random_uuid();rid uuid:=gen_random_uuid();new_sn uuid:=gen_random_uuid();t timestamptz;reason text;uid uuid;
BEGIN
 IF polygon.exact_keys(p,ARRAY['auth','session_id','request']) IS DISTINCT FROM true
 OR jsonb_typeof(p->'session_id') IS DISTINCT FROM 'string' OR polygon.uuid_text(p->>'session_id') IS DISTINCT FROM true
 OR polygon.exact_keys(b,ARRAY['requestSchemaVersion','clientCommandId','expectedSessionVersion']) IS DISTINCT FROM true
 OR b->>'requestSchemaVersion' IS DISTINCT FROM 'v1' OR jsonb_typeof(b->'clientCommandId') IS DISTINCT FROM 'string'
 OR polygon.uuid_text(b->>'clientCommandId') IS DISTINCT FROM true OR jsonb_typeof(b->'expectedSessionVersion') IS DISTINCT FROM 'string'
 OR polygon.version_text(b->>'expectedSessionVersion') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;uid:=(a->>'user_id')::uuid;
 SELECT * INTO sl FROM polygon.user_session_slots WHERE user_id=uid FOR UPDATE;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=(p->>'session_id')::uuid AND user_id=uid FOR UPDATE;
 IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 SELECT * INTO r FROM polygon_live.results WHERE user_id=uid AND client_command_id=(b->>'clientCommandId')::uuid;
 IF r.id IS NOT NULL THEN
  IF r.session_id<>s.id OR r.request IS DISTINCT FROM b THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409); END IF;
  RETURN polygon_live.reply(r.id,false);
 END IF;
 IF polygon.session_valid(s.id) IS DISTINCT FROM true OR sl.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 IF b->>'expectedSessionVersion'<>s.version::text OR s.lifecycle<>'active' THEN reason:='VERSION_CONFLICT';
 ELSIF polygon_live.empty_admitted(s.id) IS DISTINCT FROM true THEN reason:='SESSION_NOT_SETTLED'; END IF;
 t:=date_trunc('milliseconds',clock_timestamp());
 INSERT INTO polygon_live.results VALUES(rid,uid,(b->>'clientCommandId')::uuid,s.id,(a->>'login_id')::uuid,b,
 encode(sha256(convert_to('complete-empty-v1'||chr(10)||uid::text||chr(10)||s.id::text||chr(10)||b::text,'UTF8')),'hex'),
 CASE WHEN reason IS NULL THEN 'committed' ELSE 'rejected' END,reason,t);
 INSERT INTO polygon_live.audit VALUES(rid,uid,s.id,(a->>'login_id')::uuid,'paper_session.complete_empty',t);
 IF reason IS NULL THEN
  SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=1;
  INSERT INTO polygon_live.completions VALUES(cid,s.id,uid,rid,sl.id,sl.generation,sl.generation+1,sn.id,new_sn,t);
  sn.id:=new_sn;sn.version:=2;sn.session_version:=2;sn.lifecycle:='completed';sn.calculation_version:='paper-empty-completion-v1';sn.as_of:=t;sn.created_at:=t;
  INSERT INTO polygon.session_snapshots SELECT sn.*;
  UPDATE polygon.paper_sessions SET version=2,lifecycle='completed',current_snapshot_version=2,updated_at=t WHERE id=s.id;
  UPDATE polygon.user_session_slots SET current_session_id=NULL,generation=generation+1 WHERE id=sl.id;
 END IF;
 RETURN polygon_live.reply(rid,false);
END $$;
