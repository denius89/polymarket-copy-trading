CREATE FUNCTION polygon_buy.pending_shape(e jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(polygon.exact_keys(e,ARRAY['schemaVersion','kind','admissionId','binding','evidenceSha256']) AND e->>'schemaVersion'='paper-buy-pending-v1'
 AND e->>'kind'='candidate' AND polygon.uuid_text(e->>'admissionId') AND polygon_live_activity.binding_shape(e->'binding') AND e->'binding'<>'null'::jsonb
 AND polygon_live_activity.sha_value(e->'evidenceSha256'),false)
$$;
CREATE OR REPLACE FUNCTION polygon_live_activity.evidence_shape(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(polygon.exact_keys(v,ARRAY['schemaVersion','kind','reason','evidenceSha256','binding'])
 AND v->>'schemaVersion'='paper-buy-evidence-v1' AND v->>'kind'='skip' AND polygon_live_activity.reason(v->>'reason')
 AND polygon_live_activity.sha_value(v->'evidenceSha256') AND polygon_live_activity.binding_shape(v->'binding'),false) OR polygon_buy.pending_shape(v)
$$;
ALTER TABLE polygon_live_activity.decisions DROP CONSTRAINT decisions_status_check,DROP CONSTRAINT decisions_reason_code_check,
 DROP CONSTRAINT bound_skip_detail,DROP CONSTRAINT bound_skip_policy;
ALTER TABLE polygon_live_activity.decisions ALTER COLUMN reason_code DROP NOT NULL,ALTER COLUMN detail_code DROP NOT NULL;
ALTER TABLE polygon_live_activity.decisions ADD CONSTRAINT closed_buy_decision CHECK(
 (status='skipped' AND reason_code='context_invalid' AND polygon_live_activity.reason(detail_code) AND policy_version='paper-bound-skip-v1') OR
 (status='pending' AND reason_code IS NULL AND detail_code IS NULL AND policy_version='paper-buy-queued-v1'));
CREATE FUNCTION polygon_buy.pending_valid(oid uuid,e jsonb,t timestamptz) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE ob polygon_live_activity.observations;a polygon_buy.admissions;b polygon_buy.bindings;
BEGIN
 IF polygon_buy.pending_shape(e) IS DISTINCT FROM true THEN RETURN false;END IF;
 SELECT * INTO ob FROM polygon_live_activity.observations WHERE id=oid;
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=ob.session_id;
 SELECT * INTO a FROM polygon_buy.admissions WHERE id=(e->>'admissionId')::uuid AND session_id=ob.session_id;
 RETURN ob.id IS NOT NULL AND b.session_id IS NOT NULL AND a.id IS NOT NULL AND ob.sequence>=b.first_sequence
 AND a.run_id=b.run_id AND a.kind='reserve' AND ob.classification='accepted' AND ob.raw_log->>'side'='BUY'
 AND a.request->>'observationId'=oid::text AND a.transaction_hash=ob.transaction_hash AND a.log_index=ob.log_index
 AND a.token_id=ob.raw_log->>'tokenId' AND a.token_id=e#>>'{binding,tokenId}' AND a.condition_id=e#>>'{binding,conditionId}'
 AND t>=a.issued_at AND t<a.expires_at;
END $$;
CREATE OR REPLACE FUNCTION polygon_live_activity.write_decision(oid uuid,es jsonb,t timestamptz) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ob polygon_live_activity.observations;e jsonb;did uuid:=gen_random_uuid();pending boolean;
BEGIN
 SELECT * INTO STRICT ob FROM polygon_live_activity.observations WHERE id=oid;
 SELECT value->'evidence' INTO STRICT e FROM jsonb_array_elements(es) WHERE value->>'transactionHash'=ob.transaction_hash AND (value->>'logIndex')::numeric=ob.log_index;
 pending:=polygon_buy.pending_shape(e);
 IF polygon_live_activity.evidence_shape(e) IS DISTINCT FROM true OR (e->'binding'<>'null'::jsonb AND e#>>'{binding,tokenId}'<>ob.raw_log->>'tokenId')
 OR (pending AND polygon_buy.pending_valid(oid,e,t) IS DISTINCT FROM true) THEN RAISE EXCEPTION 'invalid admitted observation' USING ERRCODE='22023';END IF;
 INSERT INTO polygon_live_activity.decisions SELECT did,ob.id,ob.session_id,ob.sequence,t,current_settings_revision_id,
 CASE WHEN pending THEN 'pending' ELSE 'skipped' END,CASE WHEN pending THEN NULL ELSE 'context_invalid' END,CASE WHEN pending THEN NULL ELSE e->>'reason' END,
 CASE WHEN pending THEN 'paper-buy-queued-v1' ELSE 'paper-bound-skip-v1' END,
 jsonb_build_object('evidence',e,'executionAdmission',CASE WHEN pending THEN 'queued' ELSE 'blocked' END) FROM polygon.paper_sessions WHERE id=ob.session_id;
 INSERT INTO polygon_live_activity.evaluations VALUES(ob.id,ob.session_id,ob.operation_id,ob.sequence,did,e,t);
END $$;
-- Old immutable envelopes remain valid; new envelopes pin the actual initial
-- financial version once for the entire ingest command, not once per event.
DO $$DECLARE c record;n int:=0;BEGIN
 FOR c IN SELECT conname FROM pg_constraint WHERE conrelid='polygon_live_activity.bound_requests'::regclass AND contype='c' AND pg_get_constraintdef(oid) LIKE '%expectedSnapshotVersion%' LOOP
 n:=n+1;EXECUTE format('ALTER TABLE polygon_live_activity.bound_requests DROP CONSTRAINT %I',c.conname);END LOOP;
 IF n<>1 THEN RAISE EXCEPTION 'unexpected bound version constraint';END IF;
END $$;
ALTER TABLE polygon_live_activity.bound_requests ADD CONSTRAINT bound_version CHECK(jsonb_typeof(request->'expectedSnapshotVersion')='string' AND polygon.version_text(request->>'expectedSnapshotVersion'));

-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
-- Derived v2 range logic; only name/signature and final skip writer differ.
CREATE OR REPLACE FUNCTION polygon_live_activity.bound_ingest(p jsonb,es jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;st polygon_live_activity.stream;i polygon_live_activity.assignments;sid uuid;op uuid;t timestamptz;ot timestamptz;
 h jsonb;v jsonb;prev jsonb;hs jsonb:='{}';seen jsonb:='{}';first_v jsonb;sem text;key text;row_n numeric;row_i numeric;
 errs jsonb:='[]';sorted_errs jsonb;code text;cid uuid;oid uuid;old polygon_live_activity.observations;r jsonb;
 accepted bigint:=0;excluded bigint:=0;duplicates bigint:=0;seq bigint;class text;ns bigint;
BEGIN
 IF polygon_live_activity.request_shape(p,'ingest') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon_live_activity.writer_guard(p); IF a->>'http'<>'200' THEN RETURN a; END IF;
 a:=polygon_live_activity.old_result(p,'ingest'); IF a IS NOT NULL THEN RETURN a; END IF;
 sid:=(p->>'sessionId')::uuid;op:=(p->>'operationId')::uuid;
 SELECT * INTO st FROM polygon_live_activity.stream WHERE session_id=sid;
 IF st.session_id IS NULL OR st.status<>'observing' OR st.checkpoint IS DISTINCT FROM p->'previous'
 THEN RETURN polygon.err('VERSION_CONFLICT',409); END IF;
 IF NOT polygon_live_activity.new_admission(sid) THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 t:=date_trunc('milliseconds',clock_timestamp());ot:=(p->>'observedAt')::timestamptz;
 IF ot<st.armed_at OR ot>t OR ot<st.last_observed_at THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT * INTO STRICT i FROM polygon_live_activity.assignments WHERE session_id=sid;
 IF p->'baselineCanonicalHash' IS DISTINCT FROM st.baseline->'hash' THEN
  errs:=errs||jsonb_build_array(jsonb_build_object('code','baseline_hash_mismatch','expected',st.baseline->'hash','actual',p->'baselineCanonicalHash'));
 END IF;
 prev:=p->'previous';
 FOR h IN SELECT value FROM jsonb_array_elements(p->'headers') LOOP
  IF (h->>'number')::numeric<>(prev->>'number')::numeric+1 OR h->'parentHash' IS DISTINCT FROM prev->'hash' THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','canonical_chain_mismatch','blockNumber',h->'number','logIndex',NULL,'expectedPrevious',prev,'actualHeader',h));
  END IF;
  IF (h->>'timestampSeconds')::numeric>extract(epoch FROM ot) THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','future_source_timestamp','blockNumber',h->'number','logIndex',NULL,'timestampSeconds',h->'timestampSeconds','observedAt',p->'observedAt'));
  END IF;
  IF hs ? (h->>'number') THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','canonical_chain_mismatch','blockNumber',h->'number','logIndex',NULL,'duplicateHeader',h));
  END IF;
  hs:=hs||jsonb_build_object(h->>'number',h); prev:=polygon_live_activity.cp(h);
 END LOOP;
 IF h IS DISTINCT FROM p->'finalized' THEN
  errs:=errs||jsonb_build_array(jsonb_build_object('code','canonical_chain_mismatch','expectedFinalized',p->'finalized','actualLastHeader',h));
 END IF;
 -- Validate every log and detect all bounded conflicts BEFORE inserting any observation.
 FOR v IN SELECT value FROM jsonb_array_elements(p->'logs') ORDER BY (value->>'blockNumber')::numeric,(value->>'logIndex')::numeric LOOP
  IF v->>'owner'<>i.owner_address THEN RETURN polygon.err('ACCESS_DENIED',403); END IF;
  h:=hs->(v->>'blockNumber'); key:=(v->>'transactionHash')||':'||(v->>'logIndex');
  IF h IS NULL OR h->'hash' IS DISTINCT FROM v->'blockHash' THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','canonical_chain_mismatch','blockNumber',v->'blockNumber','logIndex',v->'logIndex',
    'expectedHeader',h,'actualLog',v)); CONTINUE;
  END IF;
  sem:=polygon_live_activity.semantic(v,h);
  first_v:=seen->key;
  IF first_v IS NOT NULL AND first_v->>'semantic'<>sem THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','log_identity_conflict','blockNumber',v->'blockNumber','logIndex',v->'logIndex',
    'identity',key,'existingObservationId',NULL,'expectedPreimage',first_v->'semantic','actualPreimage',sem));
  END IF;
  IF first_v IS NULL THEN seen:=seen||jsonb_build_object(key,jsonb_build_object('semantic',sem)); END IF;
  SELECT * INTO old FROM polygon_live_activity.observations WHERE session_id=sid AND transaction_hash=v->>'transactionHash' AND log_index=(v->>'logIndex')::numeric;
  IF FOUND AND old.semantic_preimage<>sem THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','log_identity_conflict','blockNumber',v->'blockNumber','logIndex',v->'logIndex',
    'identity',key,'existingObservationId',old.id,'expectedPreimage',old.semantic_preimage,'actualPreimage',sem));
  END IF;
 END LOOP;
 IF jsonb_array_length(errs)>0 THEN
  SELECT jsonb_agg(value ORDER BY CASE value->>'code' WHEN 'baseline_hash_mismatch' THEN 1 WHEN 'canonical_chain_mismatch' THEN 2
   WHEN 'future_source_timestamp' THEN 3 ELSE 4 END,(value->>'blockNumber')::numeric NULLS FIRST,(value->>'logIndex')::numeric NULLS FIRST,value::text)
   INTO sorted_errs FROM jsonb_array_elements(errs);
  code:=sorted_errs#>>'{0,code}';cid:=gen_random_uuid();
  INSERT INTO polygon_live_activity.conflicts VALUES(cid,op,sid,code,sorted_errs,p->>'evidenceSha256',t);
  UPDATE polygon_live_activity.stream SET status='reconciliation_required',last_operation_id=op WHERE session_id=sid;
  r:=jsonb_build_object('operationId',op,'kind','ingest_blocked','sessionId',sid,'status','reconciliation_required','conflictId',cid,
   'conflictCode',code,'checkpoint',st.checkpoint,'highWatermark',st.high_watermark::text,'evidenceSha256',p->'evidenceSha256');
  RETURN polygon_live_activity.save_result(p,'ingest',r,t);
 END IF;
 -- Valid range. No previous accepted range can overlap this one. Duplicate rows within this batch share one observation.
 seen:='{}';seq:=st.high_watermark;
 FOR v IN SELECT value FROM jsonb_array_elements(p->'logs') ORDER BY (value->>'blockNumber')::numeric,(value->>'logIndex')::numeric LOOP
  key:=(v->>'transactionHash')||':'||(v->>'logIndex');
  IF seen ? key THEN duplicates:=duplicates+1;CONTINUE; END IF;
  seen:=seen||jsonb_build_object(key,true);h:=hs->(v->>'blockNumber');sem:=polygon_live_activity.semantic(v,h);oid:=gen_random_uuid();
  IF EXISTS(SELECT FROM polygon_live_activity.observations WHERE session_id=sid AND transaction_hash=v->>'transactionHash' AND log_index=(v->>'logIndex')::numeric)
  THEN RAISE EXCEPTION 'nonoverlapping range unexpectedly repeats a stored log' USING ERRCODE='23514'; END IF;
  IF (h->>'timestampSeconds')::numeric<=extract(epoch FROM st.armed_at) THEN
   class:='excluded';ns:=NULL;excluded:=excluded+1;
  ELSE class:='accepted';seq:=seq+1;ns:=seq;accepted:=accepted+1; END IF;
  IF class='accepted' THEN
   SELECT COALESCE((ad.request->>'observationId')::uuid,oid) INTO oid FROM (SELECT 1) one_row
   LEFT JOIN LATERAL (SELECT value->'evidence' evidence FROM jsonb_array_elements(es) WHERE value->>'transactionHash'=v->>'transactionHash' AND value->>'logIndex'=v->>'logIndex') ev ON true
   LEFT JOIN polygon_buy.admissions ad ON polygon_buy.pending_shape(ev.evidence) AND ad.id=(CASE WHEN polygon_buy.pending_shape(ev.evidence) THEN ev.evidence->>'admissionId' END)::uuid AND ad.session_id=sid;
  END IF;
  INSERT INTO polygon_live_activity.observations VALUES(oid,sid,op,v->>'transactionHash',(v->>'logIndex')::numeric,v,h,sem,polygon_live_activity.digest(sem),ot,ns,class);
  IF class='accepted' THEN
   PERFORM polygon_live_activity.write_decision(oid,es,t);
  END IF;
 END LOOP;
 UPDATE polygon_live_activity.stream SET checkpoint=polygon_live_activity.cp(p->'finalized'),high_watermark=seq,last_observed_at=ot,last_operation_id=op,last_range_operation_id=op WHERE session_id=sid;
 r:=jsonb_build_object('operationId',op,'kind','ingest','sessionId',sid,'checkpoint',polygon_live_activity.cp(p->'finalized'),
  'accepted',accepted::text,'duplicates',duplicates::text,'excluded',excluded::text,'highWatermark',seq::text);
 RETURN polygon_live_activity.save_result(p,'ingest',r,t);
END $$;

-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE OR REPLACE FUNCTION polygon_live_activity.inner_bound(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE b jsonb;a jsonb;e jsonb;old polygon_live_activity.bound_requests;o polygon_live_activity.operations;st polygon_live_activity.stream;version text;
BEGIN
 IF polygon.exact_keys(p,ARRAY['ingest','expectedSnapshotVersion','evaluations']) IS DISTINCT FROM true OR octet_length(p::text)>4194304
  OR polygon_live_activity.request_shape(p->'ingest','ingest') IS DISTINCT FROM true
  OR polygon.version_text(p->>'expectedSnapshotVersion') IS DISTINCT FROM true
  OR jsonb_typeof(p->'expectedSnapshotVersion') IS DISTINCT FROM 'string' OR jsonb_typeof(p->'evaluations') IS DISTINCT FROM 'array'
 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 IF jsonb_array_length(p->'evaluations')>128 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 FOR e IN SELECT value FROM jsonb_array_elements(p->'evaluations') LOOP
  IF polygon.exact_keys(e,ARRAY['transactionHash','logIndex','evidence']) IS DISTINCT FROM true
   OR NOT polygon_live_activity.hash_value(e->'transactionHash') OR NOT polygon_live_activity.uint(e->'logIndex')
   OR polygon_live_activity.evidence_shape(e->'evidence') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(p->'evaluations') x GROUP BY x.value->>'transactionHash',x.value->>'logIndex' HAVING count(*)>1)
 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 b:=p->'ingest';a:=polygon_live_activity.writer_guard(b);IF a->>'http'<>'200' THEN RETURN a;END IF;
 IF polygon_live_activity.bound_state_valid((b->>'sessionId')::uuid) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 SELECT * INTO old FROM polygon_live_activity.bound_requests WHERE session_id=(b->>'sessionId')::uuid AND operation_id=(b->>'operationId')::uuid;
 IF FOUND THEN
  IF old.request IS DISTINCT FROM p THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409);END IF;
  SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=old.session_id AND id=old.operation_id;
  RETURN jsonb_build_object('http',200,'result',o.result);
 END IF;
 IF EXISTS(SELECT FROM polygon_live_activity.operations WHERE session_id=(b->>'sessionId')::uuid AND id=(b->>'operationId')::uuid) THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409);END IF;
 SELECT current_snapshot_version::text INTO STRICT version FROM polygon.paper_sessions WHERE id=(b->>'sessionId')::uuid;
 IF version<>p->>'expectedSnapshotVersion' THEN RETURN polygon.err('VERSION_CONFLICT',409);END IF;
 a:=polygon_live_activity.bound_ingest(b,p->'evaluations');IF a->>'http'<>'200' THEN RETURN a;END IF;
 SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=(b->>'sessionId')::uuid AND id=(b->>'operationId')::uuid;
 IF a#>>'{result,kind}'='ingest' THEN
  IF jsonb_array_length(p->'evaluations')<>(SELECT count(*) FROM polygon_live_activity.observations WHERE session_id=o.session_id AND operation_id=o.id AND classification='accepted')
   OR EXISTS(SELECT FROM jsonb_array_elements(p->'evaluations') x WHERE NOT EXISTS(
    SELECT FROM polygon_live_activity.observations ob WHERE ob.session_id=o.session_id AND ob.operation_id=o.id AND ob.classification='accepted'
     AND ob.transaction_hash=x.value->>'transactionHash' AND ob.log_index=(x.value->>'logIndex')::numeric))
  THEN RAISE EXCEPTION 'BUY evaluation set differs from accepted logs' USING ERRCODE='22023';END IF;
 END IF;
 INSERT INTO polygon_live_activity.bound_requests VALUES(o.id,o.session_id,p,polygon_live_activity.digest('paper-bound-skip-envelope-v1'||chr(10)||p::text),o.created_at);
 RETURN a;
END $$;

-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE OR REPLACE FUNCTION polygon_live_activity.bound_state_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE rq polygon_live_activity.bound_requests;op polygon_live_activity.operations;ev polygon_live_activity.evaluations;ob polygon_live_activity.observations;de polygon_live_activity.decisions;
BEGIN
 IF polygon_live_activity.state_valid(sid) IS DISTINCT FROM true THEN RETURN false;END IF;
 IF EXISTS(SELECT FROM polygon_live_activity.operations o WHERE o.session_id=sid AND o.kind='ingest' AND NOT EXISTS(SELECT FROM polygon_live_activity.bound_requests r WHERE r.session_id=sid AND r.operation_id=o.id)) THEN RETURN false;END IF;
 FOR rq IN SELECT * FROM polygon_live_activity.bound_requests WHERE session_id=sid LOOP
  SELECT * INTO op FROM polygon_live_activity.operations WHERE session_id=sid AND id=rq.operation_id;
  IF op.id IS NULL OR op.kind<>'ingest' OR op.request IS DISTINCT FROM rq.request->'ingest' OR op.created_at<>rq.created_at OR op.session_id<>rq.session_id THEN RETURN false;END IF;
  IF op.result->>'kind'='ingest' AND jsonb_array_length(rq.request->'evaluations')<>(SELECT count(*) FROM polygon_live_activity.evaluations WHERE session_id=sid AND operation_id=op.id) THEN RETURN false;END IF;
 END LOOP;
 IF (SELECT count(*) FROM polygon_live_activity.evaluations WHERE session_id=sid)<>(SELECT count(*) FROM polygon_live_activity.observations WHERE session_id=sid AND classification='accepted') THEN RETURN false;END IF;
 FOR ev IN SELECT * FROM polygon_live_activity.evaluations WHERE session_id=sid LOOP
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE id=ev.observation_id;
  SELECT * INTO de FROM polygon_live_activity.decisions WHERE id=ev.decision_id;
  SELECT * INTO op FROM polygon_live_activity.operations WHERE session_id=sid AND id=ev.operation_id;
  SELECT * INTO rq FROM polygon_live_activity.bound_requests WHERE session_id=sid AND operation_id=ev.operation_id;
  IF de.id IS NULL OR op.id IS NULL OR rq.operation_id IS NULL OR ob.classification<>'accepted'
   OR ROW(ev.sequence,ev.session_id,ev.created_at,ev.operation_id) IS DISTINCT FROM ROW(ob.sequence,ob.session_id,op.created_at,ob.operation_id)
   OR ROW(de.observation_id,de.session_id,de.sequence,de.decided_at) IS DISTINCT FROM ROW(ob.id,ob.session_id,ob.sequence,ev.created_at)
   OR NOT ((de.policy_version='paper-bound-skip-v1' AND de.status='skipped' AND de.reason_code='context_invalid'
     AND de.detail_code=ev.evidence->>'reason' AND de.checks=jsonb_build_object('evidence',ev.evidence,'executionAdmission','blocked'))
    OR (de.policy_version='paper-buy-queued-v1' AND de.status='pending' AND de.reason_code IS NULL AND de.detail_code IS NULL
     AND de.checks=jsonb_build_object('evidence',ev.evidence,'executionAdmission','queued') AND polygon_buy.pending_valid(ob.id,ev.evidence,ev.created_at)))
   OR (ev.evidence->'binding'<>'null'::jsonb AND ev.evidence#>>'{binding,tokenId}' IS DISTINCT FROM ob.raw_log->>'tokenId')
   OR (SELECT count(*) FROM jsonb_array_elements(rq.request->'evaluations') x WHERE x.value->>'transactionHash'=ob.transaction_hash
    AND x.value->>'logIndex'=ob.log_index::text AND x.value->'evidence'=ev.evidence)<>1 THEN RETURN false;END IF;
 END LOOP;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION polygon_live_activity.role_valid(who oid) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM pg_roles r WHERE r.oid=who AND r.rolname::text ~ '^polygon_live_writer_[0-9a-f]{32}$'
 AND to_regprocedure('polygon.live_activity_arm(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_ingest(jsonb)') IS NOT NULL
 AND to_regprocedure('polygon.live_activity_resume(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_stop(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_lookup(jsonb)') IS NOT NULL
 AND r.rolcanlogin AND NOT(r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls)
 AND NOT EXISTS(SELECT FROM pg_auth_members WHERE member=r.oid)
 AND NOT EXISTS(SELECT FROM pg_namespace n WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','polygon_buy','live_buy_core','v00_session','v00_upstream') AND has_schema_privilege(r.oid,n.oid,'CREATE'))
 AND NOT EXISTS(SELECT FROM pg_namespace n WHERE n.nspname IN('polygon_live','polygon_live_activity','polygon_buy','live_buy_core','v00_session','v00_upstream') AND has_schema_privilege(r.oid,n.oid,'USAGE'))
 AND NOT EXISTS(SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','polygon_buy','live_buy_core') AND has_function_privilege(r.oid,p.oid,'EXECUTE')
 AND (p.oid NOT IN(to_regprocedure('polygon.live_activity_arm(jsonb)'),to_regprocedure('polygon.live_activity_ingest(jsonb)'),
 to_regprocedure('polygon.live_activity_stop(jsonb)'),to_regprocedure('polygon.live_activity_lookup(jsonb)'),to_regprocedure('polygon.live_activity_resume(jsonb)'),to_regprocedure('polygon.live_buy_reserve_v1(jsonb)'),to_regprocedure('polygon.live_buy_settle_v1(jsonb)'),to_regprocedure('polygon.live_buy_lookup_v1(jsonb)'))
 OR has_function_privilege(r.oid,p.oid,'EXECUTE WITH GRANT OPTION')))
 AND NOT EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','polygon_buy','live_buy_core','v00_session','v00_upstream') AND c.relkind IN('r','p','v','m','S')
 AND CASE WHEN c.relkind='S' THEN has_sequence_privilege(r.oid,c.oid,'USAGE,SELECT,UPDATE')
 ELSE has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') END))
$$;
