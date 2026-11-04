\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_upstream_owner;

CREATE FUNCTION v00_upstream.make_plan(p jsonb, a v00_upstream.admissions) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE reply jsonb;
BEGIN
  reply:=v00_session.plan_completion(jsonb_build_object('context_id',a.context_id,'proof_digest',p->>'proof_digest',
    'operation_id',a.operation_id,'fingerprint',a.fingerprint,'login_id',p->>'login_id','secret_id',p->>'secret_id'));
  IF reply->>'http'='200' AND reply->>'replay'='false' THEN
    INSERT INTO v00_upstream.plans VALUES(a.context_id,a.operation_id,a.id,a.action,txid_current());
  END IF;
  RETURN reply;
END $$;
CREATE FUNCTION v00_upstream.plan_email(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_upstream.admissions; c v00_upstream.contexts; s v00_upstream.subjects;
  f v00_upstream.factors; provider_factor record; t timestamptz; expiry timestamptz; ch uuid; result jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','login_id','secret_id']);
  IF p->>'action'<>'C02' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  e:=v00_upstream.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_upstream.replay(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_upstream.admission_guard(p,false); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO STRICT a FROM v00_upstream.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  SELECT * INTO STRICT c FROM v00_upstream.contexts WHERE id=a.context_id;
  SELECT * INTO STRICT s FROM v00_upstream.subjects WHERE actor_id=c.actor_id;
  PERFORM 1 FROM auth.users WHERE id=s.provider_user_id AND email_confirmed_at IS NOT NULL FOR SHARE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF c.stage<>'email_verification' THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  IF NOT EXISTS(SELECT 1 FROM v00_upstream.email_seals seal JOIN v00_upstream.email_outcomes o ON o.seal_id=seal.id
    JOIN v00_upstream.consumptions co ON co.seal_id=o.seal_id AND co.provider_txid=o.provider_txid
    JOIN v00_upstream.generations g ON g.id=seal.generation_id
    WHERE seal.admission_id=a.id AND seal.user_id=s.provider_user_id AND co.user_id=seal.user_id AND g.state='consumed') THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  IF s.current_factor IS NULL THEN
    -- A provider factor not represented by the local mapping cannot be bypassed.
    IF EXISTS(SELECT 1 FROM auth.mfa_factors WHERE user_id=s.provider_user_id AND factor_type::text='totp' AND status::text='verified') THEN
      RETURN v00_session.error(503,'RECORD_UNAVAILABLE');
    END IF;
    RETURN v00_upstream.make_plan(p,a);
  END IF;
  SELECT * INTO STRICT f FROM v00_upstream.factors WHERE id=s.current_factor AND actor_id=s.actor_id;
  SELECT id,user_id,status,factor_type INTO provider_factor FROM auth.mfa_factors WHERE id=f.provider_factor_id FOR SHARE;
  IF NOT FOUND OR provider_factor.user_id<>s.provider_user_id OR provider_factor.status::text<>'verified' OR provider_factor.factor_type::text<>'totp' OR NOT f.active THEN
    RETURN v00_session.error(503,'RECORD_UNAVAILABLE');
  END IF;
  PERFORM 1 FROM v00_upstream.factors WHERE id=f.id FOR UPDATE;
  e:=v00_upstream.admission_guard(p,false); IF e IS NOT NULL THEN RETURN e; END IF;
  t:=date_trunc('milliseconds',v00_session.now_for(c.actor_id));
  SELECT least(expires_at,t+interval '5 minutes') INTO STRICT expiry FROM v00_session.contexts WHERE id=c.id;
  IF expiry<=t THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  ch:=gen_random_uuid();
  UPDATE v00_upstream.contexts SET stage='totp_verification',factor_version=f.id,totp_challenge_id=ch,totp_issued_at=t,totp_expires_at=expiry WHERE id=c.id;
  result:=jsonb_build_object('kind','auth_step_required','stage','totp_verification','challengeId',ch,'challengeIssuedAt',v00_session.utc(t),'challengeExpiresAt',v00_session.utc(expiry));
  INSERT INTO v00_upstream.results VALUES(c.id,a.operation_id,a.action,result,t,NULL);
  INSERT INTO v00_upstream.audit(context_id,operation_id,kind,recorded_at) VALUES(c.id,a.operation_id,'email_stage',t);
  RETURN jsonb_build_object('http',200,'replay',false,'result',result);
END $$;

CREATE FUNCTION v00_upstream.plan_totp(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_upstream.admissions; c v00_upstream.contexts; s v00_upstream.subjects; f v00_upstream.factors;
  pf record; t timestamptz; steps bigint[]; count_fail integer; result jsonb; reply jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','challenge_id','code','admission_id','executor_proof','login_id','secret_id']);
  IF p->>'action'<>'AUTH_TOTP_VERIFY' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  IF p->>'code' !~ '^[0-9]{6}$' THEN RETURN v00_session.error(400,'INVALID_REQUEST'); END IF;
  e:=v00_upstream.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_upstream.replay(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_upstream.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO STRICT a FROM v00_upstream.admissions WHERE id=(p->>'admission_id')::uuid;
  SELECT * INTO STRICT c FROM v00_upstream.contexts WHERE id=a.context_id;
  SELECT * INTO STRICT s FROM v00_upstream.subjects WHERE actor_id=c.actor_id;
  PERFORM 1 FROM auth.users WHERE id=s.provider_user_id FOR SHARE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF c.stage<>'totp_verification' OR c.totp_challenge_id IS DISTINCT FROM (p->>'challenge_id')::uuid THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  IF c.factor_version IS NULL OR c.factor_version IS DISTINCT FROM s.current_factor THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  SELECT * INTO STRICT f FROM v00_upstream.factors WHERE id=c.factor_version AND actor_id=c.actor_id;
  SELECT id,user_id,status,factor_type,secret INTO pf FROM auth.mfa_factors WHERE id=f.provider_factor_id FOR SHARE;
  IF NOT FOUND OR pf.user_id<>s.provider_user_id OR pf.status::text<>'verified' OR pf.factor_type::text<>'totp' OR NOT f.active THEN
    RETURN v00_session.error(503,'RECORD_UNAVAILABLE');
  END IF;
  PERFORM 1 FROM v00_upstream.factors WHERE id=f.id FOR UPDATE;
  t:=v00_session.now_for(c.actor_id);
  IF c.totp_expires_at<=t THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  IF s.paused_until>t THEN RETURN v00_session.error(429,'RATE_LIMITED'); END IF;
  BEGIN
    steps:=v00_upstream.matches(pf.secret,p->>'code',t);
  EXCEPTION WHEN OTHERS THEN
    -- Missing/unsupported crypto or seed is technical, never a wrong code.
    RETURN v00_session.error(503,'RECORD_UNAVAILABLE');
  END;
  e:=v00_upstream.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  IF cardinality(steps)=0 OR EXISTS(SELECT 1 FROM v00_upstream.used_steps WHERE factor_version=f.id AND step=ANY(steps)) THEN
    count_fail:=CASE WHEN s.paused_until IS NOT NULL AND s.paused_until<=t THEN 0 ELSE s.failures END+1;
    UPDATE v00_upstream.subjects SET failures=count_fail,paused_until=CASE WHEN count_fail=5 THEN t+interval '15 minutes' END WHERE actor_id=s.actor_id;
    result:=jsonb_build_object('kind','verification_rejected','reasonCode','AUTH_VERIFICATION_FAILED');
    INSERT INTO v00_upstream.results VALUES(c.id,a.operation_id,a.action,result,t,NULL);
    INSERT INTO v00_upstream.audit(context_id,operation_id,kind,recorded_at) VALUES(c.id,a.operation_id,'verification_rejected',t);
    RETURN jsonb_build_object('http',401,'replay',false,'result',result);
  END IF;
  reply:=v00_upstream.make_plan(p,a);
  IF reply->>'http'='200' AND reply->>'replay'='false' THEN
    INSERT INTO v00_upstream.used_steps SELECT f.id,step,c.id,a.operation_id FROM unnest(steps) step;
    UPDATE v00_upstream.subjects SET failures=0,paused_until=NULL WHERE actor_id=s.actor_id;
  END IF;
  RETURN reply;
END $$;

CREATE FUNCTION v00_upstream.complete(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_upstream.admissions; plan v00_upstream.plans; r v00_session.results; reply jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','cookie_digest','ciphertext','nonce','key_id','credential_key_id']);
  e:=v00_upstream.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_upstream.admission_guard(p,false); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO plan FROM v00_upstream.plans WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND OR plan.action<>p->>'action' OR plan.transaction_id<>txid_current() THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  reply:=v00_session.complete(p-ARRAY['action','comparison_hmac','comparison_key_id']);
  IF reply->>'http'<>'200' THEN RETURN reply; END IF;
  SELECT * INTO STRICT r FROM v00_session.results WHERE context_id=plan.context_id AND operation_id=plan.operation_id;
  INSERT INTO v00_upstream.results VALUES(r.context_id,r.operation_id,plan.action,r.result,r.resolved_at,r.login_id);
  UPDATE v00_upstream.contexts SET stage='completed' WHERE id=r.context_id;
  INSERT INTO v00_upstream.audit(context_id,operation_id,kind,recorded_at) VALUES(r.context_id,r.operation_id,'completion',r.resolved_at);
  RETURN reply;
END $$;
CREATE FUNCTION v00_upstream.check_bundle() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE r v00_upstream.results;
BEGIN
  SELECT * INTO r FROM v00_upstream.results WHERE context_id=NEW.context_id AND operation_id=NEW.operation_id;
  IF NOT FOUND OR v00_upstream.valid_result(r) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete upstream result'; END IF;
  IF TG_TABLE_NAME IN ('plans','used_steps') AND r.result->>'kind'<>'login_completed' THEN RAISE EXCEPTION 'incomplete upstream completion'; END IF;
  IF NOT EXISTS(SELECT 1 FROM v00_upstream.audit WHERE context_id=r.context_id AND operation_id=r.operation_id) THEN RAISE EXCEPTION 'missing upstream audit'; END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER result_bundle AFTER INSERT ON v00_upstream.results DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v00_upstream.check_bundle();
CREATE CONSTRAINT TRIGGER plan_bundle AFTER INSERT ON v00_upstream.plans DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v00_upstream.check_bundle();
CREATE CONSTRAINT TRIGGER steps_bundle AFTER INSERT ON v00_upstream.used_steps DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v00_upstream.check_bundle();

CREATE FUNCTION v00_upstream.recover(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r jsonb;
BEGIN
  r:=v00_upstream.read_operation(p);
  IF r->>'http'<>'200' THEN RETURN CASE WHEN r->>'http'='202' THEN v00_session.error(503,'SERVICE_UNAVAILABLE') ELSE r END; END IF;
  IF r->'result'->>'kind'<>'login_completed' THEN RETURN v00_session.error(409,'AUTH_COOKIE_RECOVERY_NOT_APPLICABLE'); END IF;
  RETURN v00_session.recover(p-'action');
END $$;
CREATE FUNCTION v00_upstream.q01(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE g v00_upstream.gate;
BEGIN
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton FOR SHARE;
  IF NOT g.is_open OR NOT g.clock_trusted THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  RETURN v00_session.q01(p);
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_upstream FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_upstream.plan_email(jsonb),v00_upstream.plan_totp(jsonb),v00_upstream.complete(jsonb),v00_upstream.recover(jsonb),v00_upstream.q01(jsonb) TO v00_upstream_executor;
COMMIT;
