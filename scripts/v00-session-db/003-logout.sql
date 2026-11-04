\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_session_owner;
ALTER TABLE v00_session.logins ADD UNIQUE(id,actor_id);
ALTER TABLE v00_session.logout_contexts ADD UNIQUE(id,actor_id,target_login_id);
ALTER TABLE v00_session.logout_contexts ADD FOREIGN KEY(target_login_id,actor_id) REFERENCES v00_session.logins(id,actor_id);
ALTER TABLE v00_session.logout_contexts ADD FOREIGN KEY(authorization_login_id,actor_id) REFERENCES v00_session.logins(id,actor_id);
ALTER TABLE v00_session.logout_contexts ADD FOREIGN KEY(source_context_id,actor_id,target_login_id)
  REFERENCES v00_session.logout_contexts(id,actor_id,target_login_id);
ALTER TABLE v00_session.logout_contexts ADD UNIQUE(id,target_login_id);
ALTER TABLE v00_session.logout_results ADD FOREIGN KEY(context_id,target_login_id) REFERENCES v00_session.logout_contexts(id,target_login_id);

CREATE FUNCTION v00_session.logout_view(c v00_session.logout_contexts) RETURNS jsonb LANGUAGE sql SET search_path=pg_catalog AS $$
  SELECT jsonb_build_object('http',201,'logout_context_id',c.id,'target_login_id',c.target_login_id,
    'source_context_id',c.source_context_id,'created_at',v00_session.utc(c.created_at),'expires_at',v00_session.utc(c.expires_at))
$$;
CREATE FUNCTION v00_session.logout_prepare(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE l v00_session.logins; cr v00_session.credentials; c v00_session.logout_contexts; t timestamptz;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['logout_context_id','login_id','cookie_digest','logout_proof_digest']);
  l:=v00_session.lock_login((p->>'login_id')::uuid);
  IF l.id IS NULL THEN RETURN v00_session.error(401,'AUTH_REQUIRED'); END IF;
  SELECT * INTO cr FROM v00_session.credentials WHERE login_id=l.id;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF cr.cookie_digest IS DISTINCT FROM p->>'cookie_digest' THEN RETURN v00_session.error(401,'AUTH_REQUIRED'); END IF;
  -- Deliberately no full-login guard: this credential proves only the original logout target.
  t:=v00_session.now_for(l.actor_id);
  INSERT INTO v00_session.logout_contexts VALUES((p->>'logout_context_id')::uuid,l.actor_id,l.id,l.id,NULL,
    p->>'logout_proof_digest',t,t+interval '15 minutes',NULL) RETURNING * INTO c;
  RETURN v00_session.logout_view(c);
END $$;

CREATE FUNCTION v00_session.logout_continue(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_session.logout_contexts; src v00_session.logout_contexts; a v00_session.logins;
  cr v00_session.credentials; initial_actor uuid; target uuid; e jsonb; t timestamptz;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['logout_context_id','source_context_id','authorization_login_id','cookie_digest','authorization_mode','logout_proof_digest']);
  IF p->>'authorization_mode' NOT IN ('original_login','current_user') OR p->>'authorization_mode' IS NULL THEN
    RAISE EXCEPTION 'invalid logout authorization mode';
  END IF;
  SELECT * INTO src FROM v00_session.logout_contexts WHERE id=(p->>'source_context_id')::uuid;
  SELECT * INTO a FROM v00_session.logins WHERE id=(p->>'authorization_login_id')::uuid;
  IF src.id IS NULL OR a.id IS NULL OR src.actor_id IS DISTINCT FROM a.actor_id THEN
    RETURN v00_session.error(404,'RESOURCE_NOT_FOUND');
  END IF;
  initial_actor:=src.actor_id; target:=src.target_login_id;
  PERFORM 1 FROM v00_session.actors WHERE id=initial_actor FOR UPDATE;
  PERFORM 1 FROM v00_session.logins WHERE id IN (target,a.id) ORDER BY id FOR UPDATE;
  PERFORM 1 FROM v00_session.contexts WHERE id IN
    (SELECT context_id FROM v00_session.logins WHERE id IN (target,a.id)) ORDER BY id FOR UPDATE;
  SELECT * INTO src FROM v00_session.logout_contexts WHERE id=(p->>'source_context_id')::uuid FOR UPDATE;
  SELECT * INTO a FROM v00_session.logins WHERE id=(p->>'authorization_login_id')::uuid;
  IF src.id IS NULL OR a.id IS NULL OR src.actor_id IS DISTINCT FROM initial_actor OR a.actor_id IS DISTINCT FROM initial_actor
    OR src.target_login_id IS DISTINCT FROM target THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  IF src.revoked_at IS NOT NULL THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  SELECT * INTO cr FROM v00_session.credentials WHERE login_id=a.id;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF cr.cookie_digest IS DISTINCT FROM p->>'cookie_digest' THEN RETURN v00_session.error(401,'AUTH_REQUIRED'); END IF;
  IF p->>'authorization_mode'='original_login' THEN
    IF a.id<>target THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  ELSE
    e:=v00_session.login_guard(a); IF e IS NOT NULL THEN RETURN e; END IF;
  END IF;
  -- Expired source context may be continued; its old proof/operation/result is never copied.
  t:=v00_session.now_for(initial_actor);
  INSERT INTO v00_session.logout_contexts VALUES((p->>'logout_context_id')::uuid,initial_actor,target,a.id,src.id,
    p->>'logout_proof_digest',t,t+interval '15 minutes',NULL) RETURNING * INTO c;
  RETURN v00_session.logout_view(c);
END $$;

CREATE FUNCTION v00_session.lock_logout(ctx uuid) RETURNS v00_session.logout_contexts LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c v00_session.logout_contexts; l v00_session.logins; initial_actor uuid; target uuid;
BEGIN
  SELECT * INTO c FROM v00_session.logout_contexts WHERE id=ctx;
  IF NOT FOUND THEN RETURN NULL; END IF;
  initial_actor:=c.actor_id; target:=c.target_login_id;
  l:=v00_session.lock_login(target);
  SELECT * INTO c FROM v00_session.logout_contexts WHERE id=ctx FOR UPDATE;
  IF c.actor_id IS DISTINCT FROM initial_actor OR c.target_login_id IS DISTINCT FROM target OR l.actor_id IS DISTINCT FROM initial_actor THEN
    RAISE EXCEPTION 'logout fixture binding changed';
  END IF;
  RETURN c;
END $$;
CREATE FUNCTION v00_session.logout_guard(c v00_session.logout_contexts, proof text) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF c.id IS NULL OR c.proof_digest IS DISTINCT FROM proof THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  IF c.revoked_at IS NOT NULL THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  IF c.expires_at<=v00_session.now_for(c.actor_id) THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  RETURN NULL;
END $$;
CREATE FUNCTION v00_session.valid_logout_result(r v00_session.logout_results, c v00_session.logout_contexts) RETURNS boolean
  LANGUAGE sql SET search_path=pg_catalog AS $$
  SELECT r.target_login_id=c.target_login_id AND r.result=jsonb_build_object('logout_context_id',c.id,
    'operation_id',r.operation_id,'target_login_id',c.target_login_id,'confirmed_at',v00_session.utc(r.confirmed_at))
    AND EXISTS(SELECT 1 FROM v00_session.logins WHERE id=c.target_login_id AND revoked_at IS NOT NULL)
$$;
CREATE FUNCTION v00_session.logout(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_session.logout_contexts; r v00_session.logout_results; e jsonb; t timestamptz; result jsonb;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['logout_context_id','proof_digest','operation_id','fingerprint']);
  c:=v00_session.lock_logout((p->>'logout_context_id')::uuid);
  e:=v00_session.logout_guard(c,p->>'proof_digest'); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO r FROM v00_session.logout_results WHERE context_id=c.id AND operation_id=(p->>'operation_id')::uuid;
  IF FOUND THEN
    IF v00_session.valid_logout_result(r,c) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    IF r.fingerprint IS DISTINCT FROM p->>'fingerprint' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
    RETURN jsonb_build_object('http',204,'result',r.result);
  END IF;
  PERFORM v00_session.revoke(jsonb_build_object('login_id',c.target_login_id));
  t:=v00_session.now_for(c.actor_id);
  result:=jsonb_build_object('logout_context_id',c.id,'operation_id',(p->>'operation_id')::uuid,
    'target_login_id',c.target_login_id,'confirmed_at',v00_session.utc(t));
  INSERT INTO v00_session.logout_results VALUES(c.id,(p->>'operation_id')::uuid,p->>'fingerprint',c.target_login_id,t,result);
  INSERT INTO v00_session.audit(login_id,kind,recorded_at,operation_id)
    VALUES(c.target_login_id,'logout_confirmed',t,(p->>'operation_id')::uuid);
  RETURN jsonb_build_object('http',204,'result',result);
END $$;
CREATE FUNCTION v00_session.logout_result(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_session.logout_contexts; r v00_session.logout_results; e jsonb;
BEGIN
  PERFORM v00_session.require_keys(p,ARRAY['logout_context_id','proof_digest','operation_id']);
  c:=v00_session.lock_logout((p->>'logout_context_id')::uuid);
  e:=v00_session.logout_guard(c,p->>'proof_digest'); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO r FROM v00_session.logout_results WHERE context_id=c.id AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('http',202,'status','unresolved','result',NULL,'target_login_id',c.target_login_id); END IF;
  IF v00_session.valid_logout_result(r,c) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  RETURN jsonb_build_object('http',200,'status','completed','result',r.result,'target_login_id',c.target_login_id);
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_session FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_session.logout_prepare(jsonb),v00_session.logout_continue(jsonb),
  v00_session.logout(jsonb),v00_session.logout_result(jsonb) TO v00_session_executor;
COMMIT;
