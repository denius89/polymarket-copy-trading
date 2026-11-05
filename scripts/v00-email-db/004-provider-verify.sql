\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_email_owner;
CREATE FUNCTION v00_email.observe_recovery() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE d v00_email.verify_dispatches;
BEGIN
  IF COALESCE(OLD.recovery_token,'')<>'' AND COALESCE(NEW.recovery_token,'')='' THEN
    SELECT vd.* INTO d FROM v00_email.verify_dispatches vd
      JOIN v00_upstream.generations g ON g.id=vd.generation_id
      JOIN v00_upstream.current_generations cg ON cg.generation_id=g.id
      WHERE vd.provider_user_id=NEW.id AND g.user_id=NEW.id AND g.family='recovery'
        AND cg.user_id=NEW.id AND cg.family='recovery' AND g.issued_at=OLD.recovery_sent_at
        AND g.state IN ('issued','consumed');
    IF FOUND THEN INSERT INTO v00_email.consumptions VALUES(d.id,NEW.id,txid_current(),clock_timestamp()); END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION v00_email.observe_session() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_email.consumptions;
BEGIN
  SELECT * INTO c FROM v00_email.consumptions WHERE provider_user_id=NEW.user_id AND provider_txid=txid_current();
  IF FOUND THEN INSERT INTO v00_email.verify_observations VALUES(c.dispatch_id,c.provider_txid,NEW.id,clock_timestamp()); END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION v00_email.disable_changed_address() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF OLD.email IS DISTINCT FROM NEW.email THEN
    UPDATE v00_email.directory SET enabled=false WHERE actor_id IN
      (SELECT actor_id FROM v00_upstream.subjects WHERE provider_user_id=NEW.id);
  END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION v00_email.negative_result(a v00_email.admissions, ch v00_email.challenges, kind_value text, checked_time timestamptz) RETURNS jsonb
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE t timestamptz:=checked_time; n integer; result jsonb;
BEGIN
  IF kind_value NOT IN ('live_mismatch','expired_current') THEN RAISE EXCEPTION 'unsupported negative proof'; END IF;
  IF kind_value='live_mismatch' THEN
    SELECT CASE WHEN paused_until IS NOT NULL AND paused_until<=t THEN 0 ELSE failures END+1 INTO STRICT n
      FROM v00_email.contexts WHERE id=a.context_id;
    UPDATE v00_email.contexts SET failures=n,paused_until=CASE WHEN n=5 THEN t+interval '15 minutes' END WHERE id=a.context_id;
  END IF;
  result:=jsonb_build_object('kind','verification_rejected','reasonCode','AUTH_VERIFICATION_FAILED');
  INSERT INTO v00_email.results VALUES(a.context_id,a.operation_id,a.action,result,401,t,NULL);
  INSERT INTO v00_email.negative_proofs VALUES(a.id,a.context_id,a.operation_id,ch.id,ch.generation_id,kind_value,t,txid_current());
  INSERT INTO v00_email.audit(context_id,operation_id,kind,recorded_at) VALUES(a.context_id,a.operation_id,'verification_rejected',t);
  RETURN jsonb_build_object('http',401,'replay',false,'result',result,'resolved_at',v00_session.utc(t),'historical_http_status',401);
END $$;

CREATE FUNCTION v00_email.seal_verify(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_email.admissions; c v00_email.contexts; ch v00_email.challenges;
  d v00_email.verify_dispatches; s v00_upstream.subjects; g v00_upstream.generations; u record;
  t timestamptz; computed text; recovery_match boolean; other_match boolean;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','admission_id','executor_proof','code']);
  IF p->>'action'<>'C02' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  IF p->>'code' IS NULL OR p->>'code' !~ '^[0-9]{6}$' THEN RETURN v00_session.error(400,'INVALID_REQUEST'); END IF;
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.replay(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_email.admissions WHERE id=(p->>'admission_id')::uuid
    AND context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN v00_session.error(403,'ACCESS_DENIED'); END IF;
  SELECT * INTO d FROM v00_email.verify_dispatches WHERE admission_id=a.id;
  IF FOUND THEN RETURN jsonb_build_object('http',200,'dispatch_allowed',false,'dispatch_id',d.id,
    'email_material',v00_email.email_material(a.context_id)); END IF;
  e:=v00_email.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=a.context_id;
  SELECT * INTO ch FROM v00_email.challenges WHERE id=a.challenge_id AND context_id=c.id;
  IF NOT FOUND THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  IF c.stage<>'email_verification' OR c.current_email_challenge_id IS DISTINCT FROM ch.id OR ch.replaced_by_id IS NOT NULL OR ch.consumed_by_operation_id IS NOT NULL THEN
    RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  IF c.paused_until>clock_timestamp() THEN RETURN v00_session.error(429,'RATE_LIMITED'); END IF;
  IF EXISTS(SELECT 1 FROM v00_email.send_dispatches sd JOIN v00_email.admissions sa ON sa.id=sd.admission_id
    WHERE sd.address_digest=c.address_digest AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=sa.context_id AND r.operation_id=sa.operation_id))
    OR EXISTS(SELECT 1 FROM v00_email.verify_dispatches vd JOIN v00_email.admissions va ON va.id=vd.admission_id
      JOIN v00_email.contexts vc ON vc.id=va.context_id WHERE vc.address_digest=c.address_digest
      AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=va.context_id AND r.operation_id=va.operation_id)) THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  SELECT us.* INTO STRICT s FROM v00_email.directory di JOIN v00_upstream.subjects us ON us.actor_id=di.actor_id WHERE di.address_digest=c.address_digest;
  SELECT id,email,email_confirmed_at,banned_until,recovery_token,recovery_sent_at,confirmation_token,confirmation_sent_at INTO u
    FROM auth.users WHERE id=s.provider_user_id FOR SHARE;
  IF NOT FOUND OR u.email IS NULL OR u.email_confirmed_at IS NULL OR (u.banned_until IS NOT NULL AND u.banned_until>clock_timestamp()) THEN
    RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  SELECT ge.* INTO g FROM v00_upstream.current_generations cg JOIN v00_upstream.generations ge ON ge.id=cg.generation_id
    WHERE cg.user_id=u.id AND cg.family='recovery' FOR SHARE OF cg,ge;
  IF NOT FOUND OR g.id IS DISTINCT FROM ch.generation_id OR g.state<>'issued' OR g.issued_at IS DISTINCT FROM u.recovery_sent_at THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF u.recovery_token IS NULL OR u.recovery_token !~ '^(pkce_)?[0-9a-f]{56}$'
    OR (COALESCE(u.confirmation_token,'')<>'' AND (u.confirmation_token !~ '^(pkce_)?[0-9a-f]{56}$' OR u.confirmation_sent_at IS NULL)) THEN
    RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  t:=clock_timestamp();
  IF u.recovery_sent_at>t OR (u.confirmation_sent_at IS NOT NULL AND u.confirmation_sent_at>t) THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  e:=v00_email.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  IF ch.expires_at<=t THEN RETURN v00_email.negative_result(a,ch,'expired_current',t); END IF;
  computed:=encode(v00_upstream_crypto.digest(convert_to(u.email || (p->>'code'),'UTF8'),'sha224'),'hex');
  recovery_match:=u.recovery_token IN (computed,'pkce_' || computed);
  other_match:=COALESCE(u.confirmation_token IN (computed,'pkce_' || computed)
    AND u.confirmation_sent_at+interval '10 minutes'>=t,false);
  -- Provider email verification tries confirmation first. Never call it when another
  -- family could win instead of the exact current recovery generation.
  IF other_match THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF NOT recovery_match THEN RETURN v00_email.negative_result(a,ch,'live_mismatch',t); END IF;
  e:=v00_email.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  INSERT INTO v00_email.verify_dispatches(admission_id,challenge_id,generation_id,provider_user_id,sealed_at)
    VALUES(a.id,ch.id,g.id,u.id,clock_timestamp()) RETURNING * INTO d;
  RETURN jsonb_build_object('http',200,'dispatch_allowed',true,'dispatch_id',d.id,
    'email_material',v00_email.email_material(c.id));
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_email FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_email.seal_verify(jsonb) TO v00_email_executor;
RESET ROLE;
CREATE TRIGGER v00_email_recovery AFTER UPDATE OF recovery_token,recovery_sent_at ON auth.users
  FOR EACH ROW EXECUTE FUNCTION v00_email.observe_recovery();
CREATE TRIGGER v00_email_session AFTER INSERT ON auth.sessions
  FOR EACH ROW EXECUTE FUNCTION v00_email.observe_session();
CREATE TRIGGER v00_email_address AFTER UPDATE OF email ON auth.users
  FOR EACH ROW EXECUTE FUNCTION v00_email.disable_changed_address();
COMMIT;
