-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
-- Derived v2 range logic; only name/signature and final skip writer differ.
CREATE FUNCTION polygon_live_activity.bound_ingest(p jsonb,es jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
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
