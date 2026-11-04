\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_session_owner;

CREATE FUNCTION v00_session.lookup_result(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_session.contexts; r v00_session.results; e jsonb;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['context_id','proof_digest','operation_id']);
  c:=v00_session.lock_context((p->>'context_id')::uuid);
  e:=v00_session.context_guard(c,p->>'proof_digest'); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO r FROM v00_session.results WHERE context_id=c.id AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('http',202,'status','unresolved','result',NULL,'resolved_at',NULL); END IF;
  IF v00_session.valid_result(r) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  RETURN jsonb_build_object('http',200,'status','resolved','result',r.result,'resolved_at',v00_session.utc(r.resolved_at));
END $$;

CREATE FUNCTION v00_session.plan_completion(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_session.contexts; r v00_session.results; plan v00_session.completion_plans; e jsonb; t timestamptz;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['context_id','proof_digest','operation_id','fingerprint','login_id','secret_id']);
  c:=v00_session.lock_context((p->>'context_id')::uuid);
  e:=v00_session.context_guard(c,p->>'proof_digest'); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO r FROM v00_session.results WHERE context_id=c.id AND operation_id=(p->>'operation_id')::uuid;
  IF FOUND THEN
    IF v00_session.valid_result(r) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    IF r.fingerprint IS DISTINCT FROM p->>'fingerprint' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
    RETURN jsonb_build_object('http',200,'replay',true,'result',r.result);
  END IF;
  IF c.completed_login_id IS NOT NULL THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  IF (SELECT blocked FROM v00_session.actors WHERE id=c.actor_id) THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  t:=date_trunc('milliseconds',v00_session.now_for(c.actor_id));
  IF LEAST(c.login_expires_at,c.idle_expires_at)<=t THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  INSERT INTO v00_session.completion_plans VALUES(c.id,(p->>'operation_id')::uuid,p->>'fingerprint',
    (p->>'login_id')::uuid,(p->>'secret_id')::uuid,t,LEAST(t+interval '5 minutes',c.expires_at),txid_current()) RETURNING * INTO plan;
  RETURN jsonb_build_object('http',200,'replay',false,
    'metadata',v00_session.metadata(plan.login_id,plan.secret_id,c.id,plan.operation_id,plan.deadline),
    'completed_at',v00_session.utc(t),'login_expires_at',v00_session.utc(c.login_expires_at));
END $$;

CREATE FUNCTION v00_session.complete(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_session.contexts; plan v00_session.completion_plans; e jsonb; result jsonb; t timestamptz;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['context_id','proof_digest','operation_id','fingerprint','cookie_digest','ciphertext','nonce','key_id','credential_key_id']);
  c:=v00_session.lock_context((p->>'context_id')::uuid);
  e:=v00_session.context_guard(c,p->>'proof_digest'); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO plan FROM v00_session.completion_plans WHERE context_id=c.id AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND OR plan.transaction_id<>txid_current() OR plan.fingerprint IS DISTINCT FROM p->>'fingerprint' OR c.completed_login_id IS NOT NULL THEN
    RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT');
  END IF;
  IF (SELECT blocked FROM v00_session.actors WHERE id=c.actor_id) THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  t:=v00_session.now_for(c.actor_id);
  IF LEAST(c.expires_at,c.login_expires_at,c.idle_expires_at)<=t THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  IF plan.deadline<=t THEN RETURN v00_session.error(409,'AUTH_COOKIE_RECOVERY_CLOSED'); END IF;
  IF octet_length(decode(p->>'nonce','base64'))<>24 OR octet_length(decode(p->>'ciphertext','base64'))<16
    OR COALESCE(p->>'key_id','')='' OR COALESCE(p->>'credential_key_id','')='' THEN RAISE EXCEPTION 'invalid private cipher material'; END IF;
  result:=jsonb_build_object('kind','login_completed','completion',jsonb_build_object('authContextId',c.id,
    'authOperationId',plan.operation_id,'loginId',plan.login_id,'realm','user','completedAt',v00_session.utc(plan.completed_at)));
  INSERT INTO v00_session.results VALUES(c.id,plan.operation_id,plan.fingerprint,result,plan.login_id,plan.completed_at,t);
  INSERT INTO v00_session.logins VALUES(plan.login_id,c.actor_id,c.id,plan.operation_id,plan.completed_at,c.login_expires_at,c.idle_expires_at,NULL);
  INSERT INTO v00_session.credentials(login_id,cookie_digest,key_id) VALUES(plan.login_id,p->>'cookie_digest',p->>'credential_key_id');
  INSERT INTO v00_session.secrets(id,login_id,ciphertext,nonce,key_id) VALUES(plan.secret_id,plan.login_id,p->>'ciphertext',p->>'nonce',p->>'key_id');
  INSERT INTO v00_session.windows(login_id,deadline) VALUES(plan.login_id,plan.deadline);
  UPDATE v00_session.contexts SET completed_login_id=plan.login_id,completed_operation_id=plan.operation_id WHERE id=c.id;
  INSERT INTO v00_session.audit(login_id,kind,recorded_at,operation_id) VALUES(plan.login_id,'completion',plan.completed_at,plan.operation_id);
  RETURN jsonb_build_object('http',200,'result',result,'login_expires_at',v00_session.utc(c.login_expires_at));
END $$;

CREATE FUNCTION v00_session.recover(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_session.contexts; l v00_session.logins; r v00_session.results; w v00_session.windows;
  s v00_session.secrets; cr v00_session.credentials; e jsonb; t timestamptz;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['context_id','proof_digest','operation_id']);
  c:=v00_session.lock_context((p->>'context_id')::uuid);
  e:=v00_session.context_guard(c,p->>'proof_digest'); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO r FROM v00_session.results WHERE context_id=c.id AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF v00_session.valid_result(r) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF r.result->>'kind'<>'login_completed' THEN RETURN v00_session.error(409,'AUTH_COOKIE_RECOVERY_NOT_APPLICABLE'); END IF;
  SELECT * INTO l FROM v00_session.logins WHERE id=r.login_id;
  IF NOT FOUND OR c.completed_login_id IS DISTINCT FROM l.id OR l.context_id IS DISTINCT FROM c.id OR l.operation_id IS DISTINCT FROM r.operation_id THEN
    RETURN v00_session.error(503,'RECORD_UNAVAILABLE');
  END IF;
  e:=v00_session.login_guard(l); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO w FROM v00_session.windows WHERE login_id=l.id FOR UPDATE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  SELECT * INTO s FROM v00_session.secrets WHERE login_id=l.id FOR UPDATE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  SELECT * INTO cr FROM v00_session.credentials WHERE login_id=l.id;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  t:=v00_session.now_for(c.actor_id);
  IF w.closed_at IS NOT NULL THEN
    IF s.ciphertext IS NOT NULL OR s.erased_at IS NULL THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    RETURN v00_session.error(409,'AUTH_COOKIE_RECOVERY_CLOSED');
  END IF;
  IF s.ciphertext IS NULL THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF t>=w.deadline THEN
    PERFORM v00_session.close_window(l.id,'deadline',t);
    RETURN v00_session.error(409,'AUTH_COOKIE_RECOVERY_CLOSED');
  END IF;
  RETURN jsonb_build_object('http',200,'result',r.result,'ciphertext',s.ciphertext,'nonce',s.nonce,
    'key_id',s.key_id,'credential_key_id',cr.key_id,'cookie_digest',cr.cookie_digest,
    'metadata',v00_session.metadata(l.id,s.id,c.id,r.operation_id,w.deadline),
    'login_expires_at',v00_session.utc(l.expires_at));
END $$;

CREATE FUNCTION v00_session.q01(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE l v00_session.logins; cr v00_session.credentials; w v00_session.windows; e jsonb; t timestamptz;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['login_id','cookie_digest']);
  l:=v00_session.lock_login((p->>'login_id')::uuid);
  IF l.id IS NULL THEN RETURN v00_session.error(401,'AUTH_REQUIRED'); END IF;
  SELECT * INTO cr FROM v00_session.credentials WHERE login_id=l.id;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF cr.cookie_digest IS DISTINCT FROM p->>'cookie_digest' THEN RETURN v00_session.error(401,'AUTH_REQUIRED'); END IF;
  e:=v00_session.login_guard(l); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO w FROM v00_session.windows WHERE login_id=l.id FOR UPDATE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  t:=v00_session.now_for(l.actor_id);
  PERFORM v00_session.close_window(l.id,CASE WHEN t>=w.deadline THEN 'deadline' ELSE 'first_confirmation' END,t);
  IF w.first_confirmed_at IS NULL THEN
    UPDATE v00_session.windows SET first_confirmed_at=t WHERE login_id=l.id;
    INSERT INTO v00_session.audit(login_id,kind,recorded_at) VALUES(l.id,'first_confirmation',t);
  END IF;
  RETURN jsonb_build_object('http',200,'authenticated',true,'login_id',l.id,'actor_id',l.actor_id);
END $$;

CREATE FUNCTION v00_session.revoke(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE l v00_session.logins; t timestamptz;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['login_id']);
  l:=v00_session.lock_login((p->>'login_id')::uuid);
  IF l.id IS NULL THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  t:=v00_session.now_for(l.actor_id);
  IF l.revoked_at IS NULL THEN
    UPDATE v00_session.logins SET revoked_at=t WHERE id=l.id;
    INSERT INTO v00_session.audit(login_id,kind,recorded_at) VALUES(l.id,'login_revoked',t);
  END IF;
  PERFORM v00_session.close_window(l.id,'login_revoked',t);
  RETURN jsonb_build_object('http',204,'target_login_id',l.id);
END $$;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_session FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_session.lookup_result(jsonb),v00_session.plan_completion(jsonb),v00_session.complete(jsonb),
  v00_session.recover(jsonb),v00_session.q01(jsonb) TO v00_session_executor;
-- Revoke is an operator fixture control, never a caller-authenticated public route.
COMMIT;
