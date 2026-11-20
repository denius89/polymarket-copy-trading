-- Exact scoped derivatives; unchanged branches retained.
CREATE OR REPLACE FUNCTION polygon_live_activity.request_shape(p jsonb,kind text) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE v jsonb;
BEGIN
 IF p IS NULL OR jsonb_typeof(p)<>'object' OR octet_length(p::text)>1048576
  OR NOT polygon_live_activity.uuid_value(p->'runId') OR NOT polygon_live_activity.uuid_value(p->'operationId')
  OR NOT polygon_live_activity.uuid_value(p->'sessionId') THEN RETURN false; END IF;
 CASE kind
 WHEN 'lookup' THEN RETURN polygon.exact_keys(p,ARRAY['runId','operationId','sessionId']);
 WHEN 'arm' THEN RETURN polygon.exact_keys(p,ARRAY['runId','operationId','sessionId','baseline','baselineReceivedAt','evidenceSha256'])
  AND polygon_live_activity.header(p->'baseline') AND polygon_live_activity.time_value(p->'baselineReceivedAt')
  AND polygon_live_activity.sha_value(p->'evidenceSha256');
 WHEN 'resume' THEN RETURN polygon.exact_keys(p,ARRAY['runId','operationId','sessionId','expectedLastOperationId','expectedCheckpoint','expectedHighWatermark','evidenceSha256'])
  AND polygon_live_activity.uuid_value(p->'expectedLastOperationId')
  AND polygon_live_activity.checkpoint(p->'expectedCheckpoint')
  AND polygon_live_activity.uint(p->'expectedHighWatermark')
  AND polygon_live_activity.sha_value(p->'evidenceSha256');
 WHEN 'stop' THEN RETURN polygon.exact_keys(p,ARRAY['runId','operationId','sessionId','status','evidenceSha256'])
  AND COALESCE(p->>'status' IN('stopped','source_unavailable','reconciliation_required'),false)
  AND polygon_live_activity.sha_value(p->'evidenceSha256');
 WHEN 'ingest' THEN
  IF polygon.exact_keys(p,ARRAY['runId','operationId','sessionId','previous','baselineCanonicalHash','finalized','headers','observedAt','evidenceSha256','logs']) IS DISTINCT FROM true
   OR NOT polygon_live_activity.checkpoint(p->'previous') OR NOT polygon_live_activity.hash_value(p->'baselineCanonicalHash')
   OR NOT polygon_live_activity.header(p->'finalized') OR NOT polygon_live_activity.time_value(p->'observedAt')
   OR NOT polygon_live_activity.sha_value(p->'evidenceSha256')
   OR jsonb_typeof(p->'headers') IS DISTINCT FROM 'array' OR jsonb_typeof(p->'logs') IS DISTINCT FROM 'array'
  THEN RETURN false; END IF;
  IF jsonb_array_length(p->'headers') NOT BETWEEN 1 AND 64 OR jsonb_array_length(p->'logs')>128 THEN RETURN false; END IF;
  FOR v IN SELECT value FROM jsonb_array_elements(p->'headers') LOOP
   IF NOT polygon_live_activity.header(v) THEN RETURN false; END IF;
  END LOOP;
  FOR v IN SELECT value FROM jsonb_array_elements(p->'logs') LOOP
   IF NOT polygon_live_activity.log_shape(v) THEN RETURN false; END IF;
  END LOOP;
  RETURN true;
 ELSE RETURN false;
 END CASE;
END $$;

CREATE OR REPLACE FUNCTION polygon_live_activity.role_valid(who oid) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM pg_roles r WHERE r.oid=who AND r.rolname::text ~ '^polygon_live_writer_[0-9a-f]{32}$'
 AND to_regprocedure('polygon.live_activity_arm(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_ingest(jsonb)') IS NOT NULL
 AND to_regprocedure('polygon.live_activity_resume(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_stop(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_lookup(jsonb)') IS NOT NULL
 AND r.rolcanlogin AND NOT(r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls)
 AND NOT EXISTS(SELECT FROM pg_auth_members WHERE member=r.oid)
 AND NOT EXISTS(SELECT FROM pg_namespace n WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','v00_session','v00_upstream') AND has_schema_privilege(r.oid,n.oid,'CREATE'))
 AND NOT EXISTS(SELECT FROM pg_namespace n WHERE n.nspname IN('polygon_live','polygon_live_activity','v00_session','v00_upstream') AND has_schema_privilege(r.oid,n.oid,'USAGE'))
 AND NOT EXISTS(SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity') AND has_function_privilege(r.oid,p.oid,'EXECUTE')
 AND (p.oid NOT IN(to_regprocedure('polygon.live_activity_arm(jsonb)'),to_regprocedure('polygon.live_activity_ingest(jsonb)'),
 to_regprocedure('polygon.live_activity_stop(jsonb)'),to_regprocedure('polygon.live_activity_lookup(jsonb)'),to_regprocedure('polygon.live_activity_resume(jsonb)'))
 OR has_function_privilege(r.oid,p.oid,'EXECUTE WITH GRANT OPTION')))
 AND NOT EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','v00_session','v00_upstream') AND c.relkind IN('r','p','v','m','S')
 AND CASE WHEN c.relkind='S' THEN has_sequence_privilege(r.oid,c.oid,'USAGE,SELECT,UPDATE')
 ELSE has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') END))
$$;

CREATE OR REPLACE FUNCTION polygon_live_activity.dispatch(p jsonb,k text) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE b jsonb;a jsonb;sid uuid;op uuid;c polygon_live_activity.calls;o polygon_live_activity.operations;
BEGIN
 IF polygon.exact_keys(p,ARRAY['session_id','request']) IS DISTINCT FROM true
 OR polygon_live_activity.uuid_value(p->'session_id') IS DISTINCT FROM true OR octet_length(p::text)>4194304
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 b:=CASE WHEN k='ingest' THEN p#>'{request,ingest}' ELSE p->'request' END;
 IF polygon_live_activity.request_shape(b,k) IS DISTINCT FROM true OR p->>'session_id' IS DISTINCT FROM b->>'sessionId'
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 sid:=(p->>'session_id')::uuid;op:=(b->>'operationId')::uuid;
 a:=polygon_live_activity.writer_guard(b);IF a->>'http'<>'200' THEN RETURN a; END IF;
 IF k='lookup' THEN RETURN polygon_live_activity.inner_lookup(b); END IF;
 SELECT * INTO c FROM polygon_live_activity.calls WHERE session_id=sid AND operation_id=op;
 IF FOUND THEN
  IF c.kind<>k OR c.wrapper IS DISTINCT FROM p THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409); END IF;
  SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=sid AND id=op;
  RETURN jsonb_build_object('http',200,'result',o.result);
 END IF;
 CASE k
 WHEN 'arm' THEN a:=polygon_live_activity.inner_arm(b);
 WHEN 'ingest' THEN a:=polygon_live_activity.inner_bound(p->'request');
 WHEN 'stop' THEN a:=polygon_live_activity.inner_stop(b);
 WHEN 'resume' THEN a:=polygon_live_activity.inner_resume(b);
 ELSE RETURN polygon.err('INVALID_REQUEST',400);
 END CASE;
 IF a->>'http'='200' THEN
  SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=sid AND id=op;
  INSERT INTO polygon_live_activity.calls VALUES(sid,op,k,p,polygon_live_activity.digest(k||chr(10)||p::text),o.created_at);
 END IF;
 RETURN a;
END $$;

CREATE OR REPLACE FUNCTION polygon_live_activity.stream_update_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'activity stream cannot be deleted' USING ERRCODE='23514'; END IF;
 IF ROW(NEW.session_id,NEW.baseline,NEW.armed_at,NEW.arm_operation_id)
  IS DISTINCT FROM ROW(OLD.session_id,OLD.baseline,OLD.armed_at,OLD.arm_operation_id)
  OR (OLD.status<>'observing' AND NOT (OLD.status='stopped' AND NEW.status='observing'
   AND NEW.last_operation_id<>OLD.last_operation_id
   AND (to_jsonb(NEW)-ARRAY['status','last_operation_id'])=(to_jsonb(OLD)-ARRAY['status','last_operation_id'])))
  OR NEW.high_watermark<OLD.high_watermark
  OR (NEW.checkpoint->>'number')::numeric<(OLD.checkpoint->>'number')::numeric
  OR (OLD.last_observed_at IS NOT NULL AND (NEW.last_observed_at IS NULL OR NEW.last_observed_at<OLD.last_observed_at))
 THEN RAISE EXCEPTION 'activity boundary immutable, terminal state monotone' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION polygon_live_activity.state_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE i polygon_live_activity.assignments;st polygon_live_activity.stream;s polygon.paper_sessions;o polygon_live_activity.operations;
 ob polygon_live_activity.observations;d polygon_live_activity.decisions;c polygon_live_activity.conflicts;
 cp jsonb;expected jsonb;last_id uuid;previous_id uuid;range_id uuid;last_at timestamptz;state text:='observing';ordinal bigint:=0;water bigint:=0;
 ac bigint;ex bigint;du bigint;total bigint;h jsonb;prev jsonb;logrow jsonb;heads jsonb;prior_seen jsonb;preimage text;ident text;
BEGIN
 SELECT * INTO i FROM polygon_live_activity.assignments WHERE session_id=sid;
 IF i.session_id IS NULL OR i.database_name<>current_database()
 OR polygon_live.public_valid(sid) IS DISTINCT FROM true
 OR NOT EXISTS(SELECT FROM polygon_live.public_source p WHERE p.database_name=i.database_name AND p.operator_run_id=i.run_id
 AND ROW(p.source_id,p.venue_id,p.trader_id,p.revision_id)=ROW(i.source_id,i.venue_id,i.trader_id,i.revision_id))
 OR (SELECT external_trader_id FROM polygon.traders WHERE id=i.trader_id) IS DISTINCT FROM i.owner_address THEN RETURN false; END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF s.user_id IS DISTINCT FROM i.user_id OR ROW(s.source_id,s.venue_id,s.trader_id,s.trader_revision_id)
 IS DISTINCT FROM ROW(i.source_id,i.venue_id,i.trader_id,i.revision_id) OR polygon.session_valid(sid) IS DISTINCT FROM true THEN RETURN false; END IF;
 SELECT * INTO st FROM polygon_live_activity.stream WHERE session_id=sid;
 IF NOT FOUND THEN RETURN NOT EXISTS(SELECT FROM polygon_live_activity.operations WHERE session_id=sid)
 AND NOT EXISTS(SELECT FROM polygon_live_activity.observations WHERE session_id=sid)
 AND NOT EXISTS(SELECT FROM polygon_live_activity.decisions WHERE session_id=sid)
 AND NOT EXISTS(SELECT FROM polygon_live_activity.conflicts WHERE session_id=sid); END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=st.session_id;
 IF s.user_id IS DISTINCT FROM i.user_id OR ROW(s.source_id,s.venue_id,s.trader_id,s.trader_revision_id)
  IS DISTINCT FROM ROW(i.source_id,i.venue_id,i.trader_id,i.revision_id) OR polygon.session_valid(s.id) IS DISTINCT FROM true THEN RETURN false; END IF;
 FOR o IN SELECT op.* FROM polygon_live_activity.operations op WHERE op.session_id=sid ORDER BY op.ordinal LOOP
  ordinal:=ordinal+1;
  IF o.ordinal<>ordinal OR o.session_id<>st.session_id OR o.request->>'runId'<>i.run_id::text OR (state<>'observing' AND NOT (state='stopped' AND o.kind='resume')) THEN RETURN false; END IF;
  previous_id:=last_id;last_id:=o.id;
  IF o.kind='arm' THEN
   IF ordinal<>1 OR st.arm_operation_id<>o.id OR st.baseline IS DISTINCT FROM o.request->'baseline' OR st.armed_at<>o.created_at THEN RETURN false; END IF;
   cp:=polygon_live_activity.cp(st.baseline);
   expected:=jsonb_build_object('operationId',o.id,'kind','arm','sessionId',s.id,'armedAt',v00_session.utc(st.armed_at),'checkpoint',cp);
  ELSIF o.kind='resume' THEN
   IF ordinal=1 OR state<>'stopped' OR o.request->>'expectedLastOperationId' IS DISTINCT FROM previous_id::text
    OR o.request->'expectedCheckpoint' IS DISTINCT FROM cp
    OR o.request->>'expectedHighWatermark' IS DISTINCT FROM water::text
    OR NOT EXISTS(SELECT FROM polygon_live_activity.operations prior_stop
      WHERE prior_stop.session_id=sid AND prior_stop.id=previous_id AND prior_stop.kind='stop'
      AND prior_stop.request->>'status'='stopped' AND prior_stop.created_at<=o.created_at)
   THEN RETURN false; END IF;
   state:='observing';
   expected:=jsonb_build_object('operationId',o.id,'kind','resume','sessionId',s.id,
    'resumedAt',v00_session.utc(o.created_at),'checkpoint',cp,'highWatermark',water::text);
  ELSIF ordinal=1 THEN RETURN false;
  ELSIF o.kind='stop' THEN
   state:=o.request->>'status';
   expected:=jsonb_build_object('operationId',o.id,'kind','stop','sessionId',s.id,'status',state);
  ELSIF o.result->>'kind'='ingest_blocked' THEN
   IF o.request->'previous' IS DISTINCT FROM cp THEN RETURN false; END IF;
   SELECT * INTO c FROM polygon_live_activity.conflicts WHERE session_id=sid AND operation_id=o.id AND session_id=s.id;
   IF c.id IS NULL OR c.created_at<>o.created_at OR c.evidence_sha256<>o.request->>'evidenceSha256'
    OR c.code IS DISTINCT FROM c.details#>>'{0,code}' OR EXISTS(SELECT FROM polygon_live_activity.observations WHERE session_id=sid AND operation_id=o.id) THEN RETURN false; END IF;
   state:='reconciliation_required';
   expected:=jsonb_build_object('operationId',o.id,'kind','ingest_blocked','sessionId',s.id,'status',state,'conflictId',c.id,'conflictCode',c.code,
    'checkpoint',cp,'highWatermark',water::text,'evidenceSha256',c.evidence_sha256);
  ELSIF o.kind='ingest' AND o.result->>'kind'='ingest' THEN
   IF o.request->'previous' IS DISTINCT FROM cp OR o.request->'baselineCanonicalHash' IS DISTINCT FROM st.baseline->'hash'
    OR (o.request->>'observedAt')::timestamptz<st.armed_at OR (o.request->>'observedAt')::timestamptz>o.created_at
    OR (o.request->>'observedAt')::timestamptz<last_at THEN RETURN false; END IF;
   heads:='{}';prev:=cp;
   FOR h IN SELECT value FROM jsonb_array_elements(o.request->'headers') LOOP
    IF (h->>'number')::numeric<>(prev->>'number')::numeric+1 OR h->'parentHash' IS DISTINCT FROM prev->'hash'
     OR (h->>'timestampSeconds')::numeric>extract(epoch FROM (o.request->>'observedAt')::timestamptz) THEN RETURN false; END IF;
    heads:=heads||jsonb_build_object(h->>'number',h);prev:=polygon_live_activity.cp(h);
   END LOOP;
   IF h IS DISTINCT FROM o.request->'finalized' THEN RETURN false; END IF;
   prior_seen:='{}';ac:=0;ex:=0;du:=0;
   FOR logrow IN SELECT value FROM jsonb_array_elements(o.request->'logs') ORDER BY (value->>'blockNumber')::numeric,(value->>'logIndex')::numeric LOOP
    h:=heads->(logrow->>'blockNumber');ident:=(logrow->>'transactionHash')||':'||(logrow->>'logIndex');
    IF h IS NULL OR logrow->>'owner'<>i.owner_address OR logrow->'blockHash' IS DISTINCT FROM h->'hash' THEN RETURN false; END IF;
    preimage:=polygon_live_activity.semantic(logrow,h);
    IF prior_seen ? ident THEN
     IF prior_seen->>ident<>preimage THEN RETURN false; END IF;
     du:=du+1;CONTINUE;
    END IF;
    prior_seen:=prior_seen||jsonb_build_object(ident,preimage);
    SELECT * INTO ob FROM polygon_live_activity.observations WHERE session_id=sid AND operation_id=o.id AND transaction_hash=logrow->>'transactionHash'
     AND log_index=(logrow->>'logIndex')::numeric;
    IF ob.id IS NULL OR ob.session_id<>s.id OR ob.semantic_preimage<>preimage OR ob.header IS DISTINCT FROM h
     OR ob.record_hash<>polygon_live_activity.digest(preimage) OR ob.received_at<>(o.request->>'observedAt')::timestamptz
     OR NOT EXISTS(SELECT FROM jsonb_array_elements(o.request->'logs') x WHERE x.value=ob.raw_log) THEN RETURN false; END IF;
    IF (h->>'timestampSeconds')::numeric<=extract(epoch FROM st.armed_at) THEN
     ex:=ex+1;
     IF ob.classification<>'excluded' OR ob.sequence IS NOT NULL OR EXISTS(SELECT FROM polygon_live_activity.decisions WHERE observation_id=ob.id) THEN RETURN false; END IF;
    ELSE
     ac:=ac+1;water:=water+1;
     IF ob.classification<>'accepted' OR ob.sequence IS DISTINCT FROM water THEN RETURN false; END IF;
     SELECT * INTO d FROM polygon_live_activity.decisions WHERE observation_id=ob.id;
     IF d.id IS NULL OR d.session_id<>s.id OR d.sequence<>water OR d.decided_at<>o.created_at
      OR d.settings_revision_id<>s.current_settings_revision_id THEN RETURN false; END IF;
    END IF;
   END LOOP;
   IF (SELECT count(*) FROM polygon_live_activity.observations WHERE session_id=sid AND operation_id=o.id)<>ac+ex
    OR ac+ex+du<>jsonb_array_length(o.request->'logs') THEN RETURN false; END IF;
   cp:=polygon_live_activity.cp(o.request->'finalized');last_at:=(o.request->>'observedAt')::timestamptz;range_id:=o.id;
   expected:=jsonb_build_object('operationId',o.id,'kind','ingest','sessionId',s.id,'checkpoint',cp,
    'accepted',ac::text,'duplicates',du::text,'excluded',ex::text,'highWatermark',water::text);
  ELSE RETURN false;
  END IF;
  IF o.result IS DISTINCT FROM expected THEN RETURN false; END IF;
 END LOOP;
 IF ordinal=0 OR ROW(st.checkpoint,st.high_watermark,st.last_operation_id,st.last_range_operation_id,st.last_observed_at,st.status)
  IS DISTINCT FROM ROW(cp,water,last_id,range_id,last_at,state) THEN RETURN false; END IF;
 IF (SELECT count(*) FROM polygon_live_activity.decisions WHERE session_id=sid)<>water
  OR EXISTS(SELECT FROM polygon_live_activity.observations obs_check JOIN polygon_live_activity.operations op_check ON op_check.id=obs_check.operation_id AND op_check.session_id=obs_check.session_id WHERE obs_check.session_id=sid AND op_check.result->>'kind'<>'ingest')
  OR EXISTS(SELECT FROM polygon_live_activity.conflicts conflict_check JOIN polygon_live_activity.operations op_check ON op_check.id=conflict_check.operation_id AND op_check.session_id=conflict_check.session_id WHERE conflict_check.session_id=sid AND op_check.result->>'kind'<>'ingest_blocked')
 THEN RETURN false; END IF;
 RETURN true;
END $$;
