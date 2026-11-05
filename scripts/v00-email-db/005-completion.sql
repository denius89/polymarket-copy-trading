\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_email_owner;
CREATE FUNCTION v00_email.make_plan(p jsonb, a v00_email.admissions) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE reply jsonb;
BEGIN
  reply:=v00_session.plan_completion(jsonb_build_object('context_id',a.context_id,'proof_digest',p->>'proof_digest',
    'operation_id',a.operation_id,'fingerprint',a.fingerprint,'login_id',p->>'login_id','secret_id',p->>'secret_id'));
  IF reply->>'http'='200' AND reply->>'replay'='false' THEN
    INSERT INTO v00_email.plans VALUES(a.context_id,a.operation_id,a.id,a.action,txid_current());
    UPDATE v00_session.contexts SET login_expires_at=(reply->>'completed_at')::timestamptz+interval '30 days',
      idle_expires_at=(reply->>'completed_at')::timestamptz+interval '7 days' WHERE id=a.context_id;
    reply:=reply||jsonb_build_object('login_expires_at',v00_session.utc((reply->>'completed_at')::timestamptz+interval '30 days'));
  END IF;
  RETURN reply;
END $$;

CREATE FUNCTION v00_email.plan_email(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; c v00_email.contexts; a v00_email.admissions; d v00_email.verify_dispatches;
  s v00_upstream.subjects; f v00_upstream.factors; pf record; t timestamptz; expiry timestamptz;
  challenge uuid:=gen_random_uuid(); result jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','login_id','secret_id']);
  IF p->>'action'<>'C02' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.replay(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.admission_guard(p,false); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=(p->>'context_id')::uuid;
  SELECT * INTO STRICT a FROM v00_email.admissions WHERE context_id=c.id AND operation_id=(p->>'operation_id')::uuid;
  SELECT * INTO d FROM v00_email.verify_dispatches WHERE admission_id=a.id;
  IF c.stage<>'email_verification' OR c.current_email_challenge_id IS DISTINCT FROM a.challenge_id THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  SELECT us.* INTO STRICT s FROM v00_email.directory di JOIN v00_upstream.subjects us ON us.actor_id=di.actor_id WHERE di.address_digest=c.address_digest;
  PERFORM 1 FROM auth.users WHERE id=s.provider_user_id AND email_confirmed_at IS NOT NULL
    AND (banned_until IS NULL OR banned_until<=clock_timestamp()) FOR SHARE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF d.id IS NULL OR d.provider_user_id<>s.provider_user_id OR NOT EXISTS(
    SELECT 1 FROM v00_email.verify_observations o JOIN v00_email.consumptions co
      ON co.dispatch_id=o.dispatch_id AND co.provider_txid=o.provider_txid
    JOIN v00_upstream.generations g ON g.id=d.generation_id
    WHERE o.dispatch_id=d.id AND co.provider_user_id=d.provider_user_id AND g.user_id=d.provider_user_id AND g.state='consumed') THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF s.current_factor IS NOT NULL THEN
    SELECT * INTO STRICT f FROM v00_upstream.factors WHERE id=s.current_factor AND actor_id=s.actor_id;
    SELECT id,user_id,status,factor_type INTO pf FROM auth.mfa_factors WHERE id=f.provider_factor_id FOR SHARE;
    IF NOT FOUND OR pf.user_id<>s.provider_user_id OR pf.status::text<>'verified' OR pf.factor_type::text<>'totp' OR NOT f.active THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    PERFORM 1 FROM v00_upstream.factors WHERE id=f.id FOR UPDATE;
  ELSIF EXISTS(SELECT 1 FROM auth.mfa_factors WHERE user_id=s.provider_user_id AND factor_type::text='totp' AND status::text='verified') THEN
    RETURN v00_session.error(503,'RECORD_UNAVAILABLE');
  END IF;
  e:=v00_email.admission_guard(p,false); IF e IS NOT NULL THEN RETURN e; END IF;
  t:=date_trunc('milliseconds',clock_timestamp());
  IF t>=c.expires_at THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  -- First dependency subject binding only after the exact provider consumption/session.
  INSERT INTO v00_session.contexts(id,actor_id,proof_digest,expires_at,login_expires_at,idle_expires_at)
    VALUES(c.id,s.actor_id,c.proof_digest,c.expires_at,t+interval '30 days',t+interval '7 days');
  UPDATE v00_email.challenges SET consumed_by_operation_id=a.operation_id WHERE id=a.challenge_id;
  IF s.current_factor IS NULL THEN RETURN v00_email.make_plan(p,a); END IF;
  expiry:=LEAST(t+interval '5 minutes',c.expires_at);
  UPDATE v00_email.contexts SET actor_id=s.actor_id,stage='totp_verification',factor_version=f.id,
    totp_challenge_id=challenge,totp_issued_at=t,totp_expires_at=expiry WHERE id=c.id;
  result:=jsonb_build_object('kind','auth_step_required','stage','totp_verification','challengeId',challenge,
    'challengeIssuedAt',v00_session.utc(t),'challengeExpiresAt',v00_session.utc(expiry));
  INSERT INTO v00_email.results VALUES(c.id,a.operation_id,a.action,result,200,t,NULL);
  INSERT INTO v00_email.audit(context_id,operation_id,kind,recorded_at) VALUES(c.id,a.operation_id,'email_stage',t);
  RETURN jsonb_build_object('http',200,'replay',false,'result',result,'resolved_at',v00_session.utc(t),'historical_http_status',200);
END $$;

CREATE FUNCTION v00_email.plan_totp(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_email.admissions; c v00_email.contexts; s v00_upstream.subjects;
  f v00_upstream.factors; pf record; t timestamptz; steps bigint[]; n integer; result jsonb; reply jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','admission_id','executor_proof','code','login_id','secret_id']);
  IF p->>'action'<>'AUTH_TOTP_VERIFY' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  IF p->>'code' IS NULL OR p->>'code' !~ '^[0-9]{6}$' THEN RETURN v00_session.error(400,'INVALID_REQUEST'); END IF;
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.replay(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO STRICT a FROM v00_email.admissions WHERE id=(p->>'admission_id')::uuid;
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=a.context_id;
  SELECT * INTO STRICT s FROM v00_upstream.subjects WHERE actor_id=c.actor_id;
  IF c.stage<>'totp_verification' OR c.totp_challenge_id IS DISTINCT FROM a.challenge_id
    OR c.factor_version IS NULL OR c.factor_version IS DISTINCT FROM s.current_factor THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  PERFORM 1 FROM auth.users WHERE id=s.provider_user_id AND (banned_until IS NULL OR banned_until<=clock_timestamp()) FOR SHARE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  SELECT * INTO STRICT f FROM v00_upstream.factors WHERE id=c.factor_version AND actor_id=c.actor_id;
  SELECT id,user_id,status,factor_type,secret INTO pf FROM auth.mfa_factors WHERE id=f.provider_factor_id FOR SHARE;
  IF NOT FOUND OR pf.user_id<>s.provider_user_id OR pf.status::text<>'verified' OR pf.factor_type::text<>'totp' OR NOT f.active THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  PERFORM 1 FROM v00_upstream.factors WHERE id=f.id FOR UPDATE;
  t:=clock_timestamp();
  IF c.totp_expires_at<=t THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  IF s.paused_until>t THEN RETURN v00_session.error(429,'RATE_LIMITED'); END IF;
  BEGIN steps:=v00_upstream.matches(pf.secret,p->>'code',t);
  EXCEPTION WHEN OTHERS THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END;
  e:=v00_email.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  IF cardinality(steps)=0 OR EXISTS(SELECT 1 FROM v00_email.used_steps WHERE factor_version=f.id AND step=ANY(steps))
    OR EXISTS(SELECT 1 FROM v00_upstream.used_steps WHERE factor_version=f.id AND step=ANY(steps)) THEN
    n:=CASE WHEN s.paused_until IS NOT NULL AND s.paused_until<=t THEN 0 ELSE s.failures END+1;
    UPDATE v00_upstream.subjects SET failures=n,paused_until=CASE WHEN n=5 THEN t+interval '15 minutes' END WHERE actor_id=s.actor_id;
    result:=jsonb_build_object('kind','verification_rejected','reasonCode','AUTH_VERIFICATION_FAILED');
    INSERT INTO v00_email.results VALUES(c.id,a.operation_id,a.action,result,401,t,NULL);
    INSERT INTO v00_email.audit(context_id,operation_id,kind,recorded_at) VALUES(c.id,a.operation_id,'verification_rejected',t);
    RETURN jsonb_build_object('http',401,'replay',false,'result',result,'resolved_at',v00_session.utc(t),'historical_http_status',401);
  END IF;
  -- Set absolute/idle lifetime at actual full completion, not at the preceding email stage.
  UPDATE v00_session.contexts SET login_expires_at=date_trunc('milliseconds',t)+interval '30 days',
    idle_expires_at=date_trunc('milliseconds',t)+interval '7 days' WHERE id=c.id AND completed_login_id IS NULL;
  reply:=v00_email.make_plan(p,a);
  IF reply->>'http'='200' AND reply->>'replay'='false' THEN
    INSERT INTO v00_email.used_steps SELECT f.id,step,c.id,a.operation_id FROM unnest(steps) step;
    UPDATE v00_upstream.subjects SET failures=0,paused_until=NULL WHERE actor_id=s.actor_id;
  END IF;
  RETURN reply;
END $$;

CREATE FUNCTION v00_email.complete(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; plan v00_email.plans; r v00_session.results; reply jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','cookie_digest','ciphertext','nonce','key_id','credential_key_id']);
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.admission_guard(p,false); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO plan FROM v00_email.plans WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND OR plan.action<>p->>'action' OR plan.transaction_id<>txid_current() THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  reply:=v00_session.complete(p-ARRAY['action','comparison_hmac','comparison_key_id']);
  IF reply->>'http'<>'200' THEN RETURN reply; END IF;
  SELECT * INTO STRICT r FROM v00_session.results WHERE context_id=plan.context_id AND operation_id=plan.operation_id;
  INSERT INTO v00_email.results VALUES(r.context_id,r.operation_id,plan.action,r.result,200,r.resolved_at,r.login_id);
  UPDATE v00_email.contexts SET stage='completed',actor_id=(SELECT actor_id FROM v00_session.contexts WHERE id=r.context_id) WHERE id=r.context_id;
  INSERT INTO v00_email.audit(context_id,operation_id,kind,recorded_at) VALUES(r.context_id,r.operation_id,'completion',r.resolved_at);
  RETURN reply;
END $$;
CREATE FUNCTION v00_email.recover(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r jsonb;
BEGIN
  r:=v00_email.read_operation(p);
  IF r->>'http'<>'200' THEN RETURN CASE WHEN r->>'http'='202' THEN v00_session.error(503,'SERVICE_UNAVAILABLE') ELSE r END; END IF;
  IF r->'result'->>'kind'<>'login_completed' THEN RETURN v00_session.error(409,'AUTH_COOKIE_RECOVERY_NOT_APPLICABLE'); END IF;
  RETURN v00_session.recover(p-'action');
END $$;
CREATE FUNCTION v00_email.q01(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT v00_upstream.q01(p) $$;
CREATE FUNCTION v00_email.logout_prepare(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT v00_upstream.logout_prepare(p) $$;
CREATE FUNCTION v00_email.logout_continue(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT v00_upstream.logout_continue(p) $$;
CREATE FUNCTION v00_email.logout(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT v00_upstream.logout(p) $$;
CREATE FUNCTION v00_email.logout_result(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT v00_upstream.logout_result(p) $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_email FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_email.plan_email(jsonb),v00_email.plan_totp(jsonb),v00_email.complete(jsonb),v00_email.recover(jsonb),
  v00_email.q01(jsonb),v00_email.logout_prepare(jsonb),v00_email.logout_continue(jsonb),v00_email.logout(jsonb),v00_email.logout_result(jsonb) TO v00_email_executor;
COMMIT;
