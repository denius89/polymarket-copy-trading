\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE pilot_staff_owner;
CREATE FUNCTION pilot_staff._utc(t timestamptz) RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT to_char(t AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') $$;
CREATE FUNCTION pilot_staff._hash(p jsonb) RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT encode(sha256(convert_to(p::text,'UTF8')),'hex') $$;
CREATE FUNCTION pilot_staff._exact(p jsonb,keys text[]) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_typeof(p)='object' AND (SELECT array_agg(k ORDER BY k) FROM jsonb_object_keys(p) k)=(SELECT array_agg(k ORDER BY k) FROM unnest(keys) k) $$;
CREATE FUNCTION pilot_staff._fail(code text,http integer) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION USING ERRCODE='PS001', MESSAGE=code, DETAIL=http::text; END $$;
CREATE FUNCTION pilot_staff._ok(data jsonb) RETURNS jsonb LANGUAGE sql VOLATILE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('status','ok','data',data,'observed_at',pilot_staff._utc(clock_timestamp())) $$;
CREATE FUNCTION pilot_staff._barrier(active_required boolean) RETURNS pilot_staff.control LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c pilot_staff.control;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001'; END IF;
 SELECT * INTO c FROM pilot_staff.control WHERE singleton FOR UPDATE;
 IF NOT FOUND OR c.deployment_digest IS DISTINCT FROM current_setting('pilot_staff.expected_deployment_digest',true)
 THEN PERFORM pilot_staff._fail('SERVICE_UNAVAILABLE',503); END IF;
 IF active_required AND (NOT c.enabled OR c.closed_at IS NOT NULL OR clock_timestamp()>=c.cutoff_at)
 THEN PERFORM pilot_staff._fail('SERVICE_UNAVAILABLE',503); END IF;
 RETURN c;
END $$;
CREATE FUNCTION pilot_staff._context(id uuid,proof text) RETURNS pilot_staff.contexts LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE x pilot_staff.contexts;
BEGIN
 SELECT * INTO x FROM pilot_staff.contexts WHERE contexts.id=_context.id;
 IF NOT FOUND OR x.proof_digest<>proof THEN PERFORM pilot_staff._fail('AUTH_REQUIRED',401); END IF;
 IF x.expires_at<=clock_timestamp() THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_EXPIRED',409); END IF;
 RETURN x;
END $$;
CREATE FUNCTION pilot_staff._login(id uuid,proof text,live boolean) RETURNS pilot_staff.logins LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE l pilot_staff.logins; c pilot_staff.control; pe pilot_staff.permits; pr pilot_staff.principals; a pilot_staff.assignments; sl pilot_staff.slots;
BEGIN
 SELECT * INTO l FROM pilot_staff.logins WHERE logins.id=_login.id;
 IF NOT FOUND OR l.cookie_digest<>proof THEN PERFORM pilot_staff._fail('AUTH_REQUIRED',401); END IF;
 IF NOT EXISTS(SELECT FROM pilot_staff.operations o WHERE o.context_id=l.context_id AND o.operation_id=l.operation_id AND o.login_id=l.id AND o.outcome='succeeded')
 THEN PERFORM pilot_staff._fail('RECORD_UNAVAILABLE',503); END IF;
 IF live THEN
  SELECT * INTO STRICT c FROM pilot_staff.control WHERE singleton;
  SELECT * INTO STRICT pe FROM pilot_staff.permits WHERE permits.id=l.permit_id;
  SELECT * INTO STRICT pr FROM pilot_staff.principals WHERE principals.id=l.principal_id;
  SELECT * INTO STRICT a FROM pilot_staff.assignments WHERE principal_id=l.principal_id;
  SELECT * INTO STRICT sl FROM pilot_staff.slots WHERE principal_id=l.principal_id;
  IF NOT c.enabled OR c.closed_at IS NOT NULL OR clock_timestamp()>=c.cutoff_at THEN PERFORM pilot_staff._fail('SERVICE_UNAVAILABLE',503); END IF;
  IF l.revoked_at IS NOT NULL OR pe.revoked_at IS NOT NULL OR pr.current_permit_id<>pe.id OR NOT a.enabled OR sl.login_id IS DISTINCT FROM l.id OR l.epoch<>c.epoch
  THEN PERFORM pilot_staff._fail('AUTH_REVOKED',401); END IF;
  IF clock_timestamp()>=LEAST(l.absolute_expires_at,l.idle_expires_at,pe.expires_at,c.cutoff_at) THEN PERFORM pilot_staff._fail('AUTH_EXPIRED',401); END IF;
 END IF;
 RETURN l;
END $$;
CREATE FUNCTION pilot_staff._audit(rid uuid,kind text,pid uuid,lid uuid,ctx uuid,op uuid,sid uuid,sver bigint) RETURNS uuid LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE aid uuid; c pilot_staff.control;
BEGIN
 SELECT * INTO STRICT c FROM pilot_staff.control WHERE singleton;
 SELECT id INTO aid FROM pilot_staff.audit WHERE request_id=rid AND action=kind;
 IF FOUND THEN
  IF NOT EXISTS(SELECT FROM pilot_staff.audit WHERE id=aid AND ROW(principal_id,login_id,context_id,operation_id,target_session_id,snapshot_version)
    IS NOT DISTINCT FROM ROW(pid,lid,ctx,op,sid,sver)) THEN RAISE EXCEPTION 'audit binding mismatch' USING ERRCODE='23514'; END IF;
  RETURN aid;
 END IF;
 INSERT INTO pilot_staff.audit(request_id,action,principal_id,login_id,context_id,operation_id,target_session_id,snapshot_version,profile_epoch,assignment_version,recorded_at)
 VALUES(rid,kind,pid,lid,ctx,op,sid,sver,c.epoch,CASE WHEN pid IS NULL THEN NULL ELSE 1 END,clock_timestamp()) RETURNING id INTO aid;
 RETURN aid;
END $$;
CREATE FUNCTION pilot_staff._revoke(lid uuid,t timestamptz) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 UPDATE pilot_staff.logins SET revoked_at=coalesce(revoked_at,t),cookie_envelope=NULL,envelope_erased_at=coalesce(envelope_erased_at,t) WHERE id=lid;
 UPDATE pilot_staff.slots SET login_id=NULL,generation=generation+1 WHERE login_id=lid;
END $$;
CREATE FUNCTION pilot_staff._erase_expired(rid uuid) RETURNS integer LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE t timestamptz:=clock_timestamp(); l pilot_staff.logins; aid uuid; count_erased integer:=0;
BEGIN
 FOR l IN SELECT * FROM pilot_staff.logins WHERE cookie_envelope IS NOT NULL AND delivery_deadline<=t ORDER BY id LOOP
  IF aid IS NULL THEN aid:=pilot_staff._audit(rid,'cookie_windows_expired',NULL,NULL,NULL,NULL,NULL,NULL); END IF;
  UPDATE pilot_staff.logins SET cookie_envelope=NULL,envelope_erased_at=t WHERE id=l.id;
  INSERT INTO pilot_staff.cookie_erasures VALUES(l.id,aid,t,'deadline');
  count_erased:=count_erased+1;
 END LOOP;
 RETURN count_erased;
END $$;
CREATE FUNCTION pilot_staff._charge(route text,p jsonb,scope text,network text) RETURNS timestamptz LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE r pilot_staff.requests; t timestamptz:=clock_timestamp(); deadline timestamptz; fingerprint text; binding text; limit_count integer; routes text[];
BEGIN
 deadline:=statement_timestamp()+(p->>'remaining_ms')::integer*interval '1 millisecond';
 IF t>=deadline THEN RAISE EXCEPTION 'request deadline' USING ERRCODE='57014'; END IF;
 fingerprint:=pilot_staff._hash(jsonb_build_object('route',route,'input',p-ARRAY['remaining_ms','request_proof_digest','login_id','cookie_digest','cookie_envelope']));
 -- Generated login fields are excluded ONLY for login_execute.
 IF route<>'login_execute' THEN fingerprint:=pilot_staff._hash(jsonb_build_object('route',route,'input',p-ARRAY['remaining_ms','request_proof_digest'])); END IF;
 binding:=pilot_staff._hash(jsonb_build_array(p->'context_id',p->'context_proof_digest',p->'operation_id'));
 SELECT * INTO r FROM pilot_staff.requests WHERE id=(p->>'request_id')::uuid;
 IF FOUND THEN
  IF r.proof_digest<>p->>'request_proof_digest' OR t>=r.deadline_at OR NOT
    ((r.route=route AND r.fingerprint=fingerprint) OR (route='cookie_recover' AND r.route='login_execute' AND r.binding_digest=binding))
  THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
  RETURN LEAST(r.deadline_at,deadline);
 END IF;
 routes:=ARRAY[route]; limit_count:=30;
 IF route='context_prepare' THEN limit_count:=3;
 ELSIF route='login_execute' THEN limit_count:=10;
 ELSIF route IN('logout_prepare','logout_continue') THEN routes:=ARRAY['logout_prepare','logout_continue'];limit_count:=3;
 ELSIF route='logout_execute' THEN limit_count:=NULL;
 ELSIF route IN('own_me','session_list','session_read','session_events') THEN routes:=ARRAY['own_me','session_list','session_read','session_events'];
 ELSIF route IN('operation_read','cookie_recover') THEN routes:=ARRAY['operation_read','cookie_recover'];
 END IF;
 IF (SELECT count(*) FROM pilot_staff.requests q WHERE q.route=ANY(routes) AND q.scope=_charge.scope AND q.admitted_at>t-interval '60 seconds')>=limit_count
 THEN PERFORM pilot_staff._fail('RATE_LIMITED',429); END IF;
 IF route='context_prepare' AND (
  (SELECT count(*) FROM pilot_staff.requests q WHERE q.route='context_prepare' AND q.network_digest=network AND q.admitted_at>t-interval '15 minutes')>=20 OR
  (SELECT count(*) FROM pilot_staff.requests q WHERE q.route='context_prepare' AND q.admitted_at>t-interval '15 minutes')>=1000)
 THEN PERFORM pilot_staff._fail('RATE_LIMITED',429); END IF;
 INSERT INTO pilot_staff.requests VALUES((p->>'request_id')::uuid,p->>'request_proof_digest',fingerprint,route,scope,network,binding,t,LEAST(deadline,t+interval '5 seconds'));
 RETURN deadline;
END $$;
CREATE FUNCTION pilot_staff._shape(route text,p jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ks text[]; k text; env jsonb;
BEGIN
 ks:=CASE route
 WHEN 'context_prepare' THEN ARRAY['context_id','context_proof_digest','network_digest']
 WHEN 'login_execute' THEN ARRAY['context_id','context_proof_digest','operation_id','permit_id','permit_digest','login_id','cookie_digest','cookie_envelope']
 WHEN 'operation_read' THEN ARRAY['context_id','context_proof_digest','operation_id']
 WHEN 'cookie_recover' THEN ARRAY['context_id','context_proof_digest','operation_id']
 WHEN 'own_me' THEN ARRAY['login_id','cookie_digest']
 WHEN 'logout_prepare' THEN ARRAY['login_id','cookie_digest','logout_context_id','logout_proof_digest']
 WHEN 'logout_continue' THEN ARRAY['source_context_id','mode','login_id','cookie_digest','logout_context_id','logout_proof_digest']
 WHEN 'logout_execute' THEN ARRAY['logout_context_id','logout_proof_digest','operation_id']
 WHEN 'logout_read' THEN ARRAY['logout_context_id','logout_proof_digest','operation_id']
 WHEN 'session_list' THEN ARRAY['login_id','cookie_digest']
 WHEN 'session_read' THEN ARRAY['login_id','cookie_digest','session_id']
 WHEN 'session_events' THEN ARRAY['login_id','cookie_digest','session_id'] END;
 IF ks IS NULL OR pilot_staff._exact(p,ks||ARRAY['request_id','request_proof_digest','remaining_ms']) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'invalid RPC shape' USING ERRCODE='22023'; END IF;
 FOR k IN SELECT jsonb_object_keys(p) LOOP
  IF k LIKE '%\_id' ESCAPE '\' AND (jsonb_typeof(p->k)<>'string' OR (p->>k) !~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
  THEN RAISE EXCEPTION 'invalid UUID' USING ERRCODE='22023'; END IF;
  IF k LIKE '%\_digest' ESCAPE '\' AND (jsonb_typeof(p->k)<>'string' OR (p->>k) !~ '^[0-9a-f]{64}$')
  THEN RAISE EXCEPTION 'invalid digest' USING ERRCODE='22023'; END IF;
  IF p->k='null'::jsonb THEN RAISE EXCEPTION 'null field' USING ERRCODE='22023'; END IF;
 END LOOP;
 IF jsonb_typeof(p->'remaining_ms')<>'number' OR p->>'remaining_ms' !~ '^[1-9][0-9]{0,3}$' OR (p->>'remaining_ms')::integer>5000
 THEN RAISE EXCEPTION 'invalid budget' USING ERRCODE='22023'; END IF;
 IF route='logout_continue' AND p->>'mode' NOT IN('original_login','current_staff') THEN RAISE EXCEPTION 'invalid mode' USING ERRCODE='22023'; END IF;
 IF route='login_execute' THEN
  env:=p->'cookie_envelope';
  IF pilot_staff._exact(env,ARRAY['key_id','nonce','ciphertext']) IS DISTINCT FROM true OR jsonb_typeof(env->'key_id')<>'string'
   OR env->>'key_id' !~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
   OR jsonb_typeof(env->'nonce')<>'string' OR env->>'nonce' !~ '^[0-9a-f]{48}$'
   OR jsonb_typeof(env->'ciphertext')<>'string' OR env->>'ciphertext' !~ '^[0-9a-f]{96}$'
  THEN RAISE EXCEPTION 'invalid envelope' USING ERRCODE='22023'; END IF;
 END IF;
END $$;
CREATE FUNCTION pilot_staff._business(route text,p jsonb,c pilot_staff.control,deadline timestamptz) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE x pilot_staff.contexts; o pilot_staff.operations; l pilot_staff.logins; pe pilot_staff.permits;
 pr pilot_staff.principals; sl pilot_staff.slots; lc pilot_staff.logout_contexts; prior pilot_staff.logout_contexts;
 lr pilot_staff.logout_results; t timestamptz; rid uuid; cid uuid; oid uuid; lid uuid; fingerprint text;
 result jsonb; data jsonb; old_id uuid; aid uuid; label text; expected_role text; code text; detail text;
BEGIN
 rid:=(p->>'request_id')::uuid; t:=date_trunc('milliseconds',clock_timestamp());
 IF route='context_prepare' THEN
  SELECT * INTO x FROM pilot_staff.contexts WHERE id=(p->>'context_id')::uuid;
  IF FOUND THEN
   IF x.proof_digest<>p->>'context_proof_digest' OR x.network_digest<>p->>'network_digest' OR x.expires_at<=t OR x.epoch<>c.epoch
   THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
  ELSE
   INSERT INTO pilot_staff.contexts VALUES((p->>'context_id')::uuid,p->>'context_proof_digest',p->>'network_digest',t,LEAST(t+interval '10 minutes',c.cutoff_at),c.epoch) RETURNING * INTO x;
  END IF;
  PERFORM pilot_staff._audit(rid,'context_prepared',NULL,NULL,x.id,NULL,NULL,NULL);
  data:=jsonb_build_object('contextId',x.id,'expiresAt',pilot_staff._utc(x.expires_at));
 ELSIF route IN('login_execute','operation_read','cookie_recover') THEN
  x:=pilot_staff._context((p->>'context_id')::uuid,p->>'context_proof_digest'); oid:=(p->>'operation_id')::uuid;
  IF x.epoch<>c.epoch THEN PERFORM pilot_staff._fail('AUTH_REVOKED',401); END IF;
  SELECT * INTO o FROM pilot_staff.operations WHERE context_id=x.id;
  IF o.context_id IS NOT NULL AND o.operation_id<>oid THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
  IF route='login_execute' THEN
   fingerprint:=pilot_staff._hash(jsonb_build_array(x.id,oid,p->'permit_id',p->'permit_digest'));
   IF o.context_id IS NOT NULL THEN
    IF o.fingerprint<>fingerprint THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
   ELSE
    SELECT * INTO pe FROM pilot_staff.permits WHERE id=(p->>'permit_id')::uuid;
    SELECT * INTO pr FROM pilot_staff.principals WHERE id=pe.principal_id;
    IF pe.id IS NULL OR pe.digest<>p->>'permit_digest' OR pe.revoked_at IS NOT NULL OR pe.expires_at<=t OR pr.current_permit_id IS DISTINCT FROM pe.id
     OR NOT EXISTS(SELECT FROM pilot_staff.assignments WHERE principal_id=pr.id AND enabled) THEN
     result:=jsonb_build_object('kind','pilot_login_rejected','operationId',oid,'reasonCode','AUTH_REQUIRED','completedAt',pilot_staff._utc(t));
     INSERT INTO pilot_staff.operations VALUES(x.id,oid,fingerprint,(p->>'permit_id')::uuid,NULL,'rejected',result,t) RETURNING * INTO o;
     PERFORM pilot_staff._audit(rid,'login_rejected',NULL,NULL,x.id,oid,NULL,NULL);
    ELSE
     lid:=(p->>'login_id')::uuid;
     SELECT * INTO STRICT sl FROM pilot_staff.slots WHERE principal_id=pr.id;
     old_id:=sl.login_id;
     IF old_id IS NOT NULL THEN
      PERFORM pilot_staff._revoke(old_id,t);
      PERFORM pilot_staff._audit(rid,'login_replaced',pr.id,old_id,x.id,oid,NULL,NULL);
     END IF;
     result:=jsonb_build_object('kind','pilot_login_completed','operationId',oid,'loginId',lid,'completedAt',pilot_staff._utc(t));
     INSERT INTO pilot_staff.operations VALUES(x.id,oid,fingerprint,pe.id,lid,'succeeded',result,t) RETURNING * INTO o;
     INSERT INTO pilot_staff.logins VALUES(lid,pr.id,pe.id,x.id,oid,'pilot_secret',t,t+interval '8 hours',t+interval '30 minutes',p->>'cookie_digest',
      LEAST(t+interval '5 minutes',x.expires_at,c.cutoff_at,pe.expires_at),p->'cookie_envelope',NULL,NULL,NULL,c.epoch);
     INSERT INTO pilot_staff.envelope_nonces VALUES((p#>>'{cookie_envelope,key_id}')::uuid,p#>>'{cookie_envelope,nonce}',lid);
     UPDATE pilot_staff.slots SET login_id=lid,generation=generation+1 WHERE principal_id=pr.id;
     PERFORM pilot_staff._audit(rid,'login_completed',pr.id,lid,x.id,oid,NULL,NULL);
    END IF;
   END IF;
   data:=jsonb_build_object('state','resolved','result',o.result);
  ELSIF route='operation_read' THEN
   IF o.outcome='succeeded' AND NOT EXISTS(SELECT FROM pilot_staff.permits pm JOIN pilot_staff.principals principal_source ON principal_source.id=pm.principal_id
      JOIN pilot_staff.assignments assignment_source ON assignment_source.principal_id=principal_source.id WHERE pm.id=o.permit_id AND pm.revoked_at IS NULL
      AND pm.expires_at>clock_timestamp() AND principal_source.current_permit_id=pm.id AND assignment_source.enabled)
   THEN PERFORM pilot_staff._fail('AUTH_REVOKED',401); END IF;
   PERFORM pilot_staff._audit(rid,'login_outcome_read',NULL,NULL,x.id,oid,NULL,NULL);
   data:=CASE WHEN o.context_id IS NULL THEN jsonb_build_object('state','unresolved') ELSE jsonb_build_object('state','resolved','result',o.result) END;
  ELSE
   IF o.context_id IS NULL OR o.outcome<>'succeeded' THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
   SELECT * INTO STRICT l FROM pilot_staff.logins WHERE id=o.login_id;
   l:=pilot_staff._login(l.id,l.cookie_digest,true);
   IF l.cookie_envelope IS NULL OR l.confirmed_at IS NOT NULL OR l.delivery_deadline<=clock_timestamp() THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_EXPIRED',409); END IF;
   SELECT * INTO STRICT pe FROM pilot_staff.permits WHERE id=l.permit_id;
   PERFORM pilot_staff._audit(rid,'cookie_recovered',l.principal_id,l.id,x.id,oid,NULL,NULL);
   data:=jsonb_build_object('loginId',l.id,'cookieEnvelope',l.cookie_envelope,'deliveryDeadline',pilot_staff._utc(l.delivery_deadline),
    'cookieExpiresAt',pilot_staff._utc(LEAST(l.absolute_expires_at,c.cutoff_at,pe.expires_at)));
  END IF;
 ELSIF route IN('own_me','session_list','session_read','session_events') THEN
  l:=pilot_staff._login((p->>'login_id')::uuid,p->>'cookie_digest',true);
  IF route='own_me' THEN
   UPDATE pilot_staff.logins SET cookie_envelope=NULL,envelope_erased_at=coalesce(envelope_erased_at,t),confirmed_at=coalesce(confirmed_at,t) WHERE id=l.id;
   SELECT display_label INTO STRICT label FROM pilot_staff.principals WHERE id=l.principal_id;
   PERFORM pilot_staff._audit(rid,'own_me',l.principal_id,l.id,NULL,NULL,NULL,NULL);
   data:=jsonb_build_object('staffId',l.principal_id,'loginId',l.id,'observedAt',pilot_staff._utc(t),'displayLabel',label,
    'absoluteExpiresAt',pilot_staff._utc(l.absolute_expires_at),'idleExpiresAt',pilot_staff._utc(l.idle_expires_at),'pilotExpiresAt',pilot_staff._utc(c.cutoff_at));
  ELSE
   data:=pilot_staff._read_paper(route,p,l);
  END IF;
 ELSIF route IN('logout_prepare','logout_continue') THEN
  l:=pilot_staff._login((p->>'login_id')::uuid,p->>'cookie_digest',route='logout_continue' AND p->>'mode'='current_staff');
  lid:=l.id;
  IF route='logout_continue' THEN
   SELECT * INTO prior FROM pilot_staff.logout_contexts WHERE id=(p->>'source_context_id')::uuid;
   IF NOT FOUND OR NOT EXISTS(SELECT FROM pilot_staff.logins WHERE id=prior.target_login_id AND principal_id=l.principal_id)
   OR (p->>'mode'='original_login' AND prior.target_login_id<>l.id) THEN PERFORM pilot_staff._fail('AUTH_REQUIRED',401); END IF;
   lid:=prior.target_login_id;
  END IF;
  SELECT * INTO lc FROM pilot_staff.logout_contexts WHERE id=(p->>'logout_context_id')::uuid;
  IF FOUND THEN
   IF lc.proof_digest<>p->>'logout_proof_digest' OR lc.target_login_id<>lid OR lc.authorizing_login_id<>l.id OR lc.source_context_id IS DISTINCT FROM prior.id
    OR lc.mode<>coalesce(p->>'mode','original_login') OR lc.expires_at<=t THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
  ELSE
   INSERT INTO pilot_staff.logout_contexts VALUES((p->>'logout_context_id')::uuid,p->>'logout_proof_digest',lid,l.id,prior.id,coalesce(p->>'mode','original_login'),t,t+interval '15 minutes') RETURNING * INTO lc;
  END IF;
  PERFORM pilot_staff._audit(rid,CASE route WHEN 'logout_prepare' THEN 'logout_prepared' ELSE 'logout_continued' END,l.principal_id,lid,lc.id,NULL,NULL,NULL);
  data:=jsonb_build_object('logoutContextId',lc.id,'loginId',lc.target_login_id,'realm','staff','createdAt',pilot_staff._utc(lc.created_at),'expiresAt',pilot_staff._utc(lc.expires_at));
  IF route='logout_continue' THEN data:=data||jsonb_build_object('sourceLogoutContextId',lc.source_context_id); END IF;
 ELSE
  SELECT * INTO lc FROM pilot_staff.logout_contexts WHERE id=(p->>'logout_context_id')::uuid;
  IF NOT FOUND OR lc.proof_digest<>p->>'logout_proof_digest' THEN PERFORM pilot_staff._fail('AUTH_REQUIRED',401); END IF;
  IF lc.expires_at<=t THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_EXPIRED',409); END IF;
  oid:=(p->>'operation_id')::uuid;
  SELECT * INTO lr FROM pilot_staff.logout_results WHERE context_id=lc.id;
  IF FOUND AND lr.operation_id<>oid THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
  SELECT * INTO STRICT l FROM pilot_staff.logins WHERE id=lc.target_login_id;
  IF route='logout_execute' AND lr.context_id IS NULL THEN
   PERFORM pilot_staff._revoke(l.id,t);
   result:=jsonb_build_object('kind','logout_completed','operationId',oid,'targetLoginId',l.id,'completedAt',pilot_staff._utc(t));
   INSERT INTO pilot_staff.logout_results VALUES(lc.id,oid,l.id,result,t) RETURNING * INTO lr;
   PERFORM pilot_staff._audit(rid,'logout_completed',l.principal_id,l.id,lc.id,oid,NULL,NULL);
  ELSIF route='logout_read' THEN
   PERFORM pilot_staff._audit(rid,'logout_outcome_read',l.principal_id,l.id,lc.id,oid,NULL,NULL);
  END IF;
  data:=CASE WHEN lr.context_id IS NULL THEN jsonb_build_object('state','unresolved','targetLoginId',lc.target_login_id) ELSE jsonb_build_object('state','resolved','targetLoginId',lc.target_login_id,'result',lr.result) END;
 END IF;
 IF route IN('own_me','session_list','session_read','session_events','cookie_recover') THEN
  PERFORM pilot_staff._login(l.id,l.cookie_digest,true);
 END IF;
 IF route='cookie_recover' AND l.delivery_deadline<=clock_timestamp() THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_EXPIRED',409); END IF;
 IF route='login_execute' AND (clock_timestamp()>=c.cutoff_at OR clock_timestamp()>=x.expires_at) THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_EXPIRED',409); END IF;
 IF clock_timestamp()>=deadline THEN RAISE EXCEPTION 'business deadline' USING ERRCODE='57014'; END IF;
 RETURN pilot_staff._ok(data);
EXCEPTION WHEN SQLSTATE 'PS001' THEN
 GET STACKED DIAGNOSTICS code=MESSAGE_TEXT,detail=PG_EXCEPTION_DETAIL;
 RETURN jsonb_build_object('status','error','http',detail::integer,'reason_code',code);
END $$;
CREATE FUNCTION pilot_staff._dispatch(route text,p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c pilot_staff.control; x pilot_staff.contexts; l pilot_staff.logins; lc pilot_staff.logout_contexts;
 who text; scope text; network text; deadline timestamptz; code text; detail text; answer jsonb;
BEGIN
 who:=CASE WHEN route IN('context_prepare','login_execute','operation_read','cookie_recover') THEN 'pilot_staff_auth' ELSE 'pilot_staff_reader' END;
 IF NOT pg_has_role(session_user,who,'USAGE') THEN RAISE EXCEPTION 'isolated role required' USING ERRCODE='42501'; END IF;
 PERFORM pilot_staff._shape(route,p);
 c:=pilot_staff._barrier(route NOT IN('logout_prepare','logout_continue','logout_execute','logout_read'));
 IF route='context_prepare' THEN scope:=p->>'network_digest';network:=scope;
 ELSIF route IN('login_execute','operation_read','cookie_recover') THEN
  x:=pilot_staff._context((p->>'context_id')::uuid,p->>'context_proof_digest');
  IF x.epoch<>c.epoch THEN PERFORM pilot_staff._fail('AUTH_REVOKED',401); END IF;
  scope:=CASE WHEN route='login_execute' THEN p->>'permit_id' ELSE x.id::text END;network:=x.network_digest;
 ELSIF route IN('logout_execute','logout_read') THEN
  SELECT * INTO lc FROM pilot_staff.logout_contexts WHERE id=(p->>'logout_context_id')::uuid;
  IF NOT FOUND OR lc.proof_digest<>p->>'logout_proof_digest' THEN PERFORM pilot_staff._fail('AUTH_REQUIRED',401); END IF;
  IF lc.expires_at<=clock_timestamp() THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_EXPIRED',409); END IF;
  scope:=lc.id::text;
 ELSE
  l:=pilot_staff._login((p->>'login_id')::uuid,p->>'cookie_digest',route NOT IN('logout_prepare','logout_continue') OR coalesce(p->>'mode'='current_staff',false));
  scope:=l.id::text;
  IF route='logout_continue' THEN
   SELECT * INTO lc FROM pilot_staff.logout_contexts WHERE id=(p->>'source_context_id')::uuid;
   IF NOT FOUND OR NOT EXISTS(SELECT FROM pilot_staff.logins WHERE id=lc.target_login_id AND principal_id=l.principal_id) OR (p->>'mode'='original_login' AND lc.target_login_id<>l.id) THEN PERFORM pilot_staff._fail('AUTH_REQUIRED',401); END IF;
   scope:=lc.target_login_id::text;
  END IF;
 END IF;
 deadline:=pilot_staff._charge(route,p,scope,network);
 PERFORM pilot_staff._erase_expired((p->>'request_id')::uuid);
 -- _business catches only declared denials in its OWN subtransaction.
 -- The admitted request remains outside that rollback. Fatal SQL/audit/unknown
 -- failures still abort the whole transaction and never release response data.
 answer:=pilot_staff._business(route,p,c,deadline);
 IF answer->>'status'='error' THEN
  PERFORM pilot_staff._audit((p->>'request_id')::uuid,'access_denied',l.principal_id,l.id,x.id,NULL,NULL,NULL);
 END IF;
 RETURN answer;
EXCEPTION WHEN SQLSTATE 'PS001' THEN
 GET STACKED DIAGNOSTICS code=MESSAGE_TEXT,detail=PG_EXCEPTION_DETAIL;
 RETURN jsonb_build_object('status','error','http',detail::integer,'reason_code',code);
END $$;
DO $$DECLARE r text; who text; BEGIN
 FOREACH r IN ARRAY ARRAY['context_prepare','login_execute','operation_read','cookie_recover','own_me','logout_prepare','logout_continue','logout_execute','logout_read','session_list','session_read','session_events'] LOOP
  who:=CASE WHEN r IN('context_prepare','login_execute','operation_read','cookie_recover') THEN 'pilot_staff_auth' ELSE 'pilot_staff_reader' END;
  EXECUTE format('CREATE FUNCTION pilot_staff.%I(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS %L',r,format('SELECT pilot_staff._dispatch(%L,p)',r));
  EXECUTE format('REVOKE ALL ON FUNCTION pilot_staff.%I(jsonb) FROM PUBLIC',r);
  EXECUTE format('GRANT EXECUTE ON FUNCTION pilot_staff.%I(jsonb) TO %I',r,who);
 END LOOP;
END $$;
COMMIT;
