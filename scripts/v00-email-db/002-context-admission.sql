\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_email_owner;

CREATE FUNCTION v00_email.lock_scope(p jsonb, proposed_address text DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_email.contexts; d v00_email.directory; g v00_upstream.gate; address text;
BEGIN
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton FOR SHARE;
  IF NOT g.is_open OR NOT g.clock_trusted THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  SELECT * INTO c FROM v00_email.contexts WHERE id=(p->>'context_id')::uuid;
  IF NOT FOUND OR c.proof_digest IS DISTINCT FROM p->>'proof_digest' THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  address:=COALESCE(c.address_digest,proposed_address);
  IF address IS NOT NULL THEN
    SELECT * INTO d FROM v00_email.directory WHERE address_digest=address FOR UPDATE;
    IF NOT FOUND OR NOT d.enabled THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    PERFORM 1 FROM v00_session.actors WHERE id=d.actor_id FOR UPDATE;
    IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    IF (SELECT blocked FROM v00_session.actors WHERE id=d.actor_id) THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  END IF;
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=c.id FOR UPDATE;
  -- A competing first C01 may bind the previously empty context while we waited.
  -- Do not acquire its new address/actor locks out of order; no effect in this T.
  IF c.address_digest IS NOT NULL AND c.address_digest IS DISTINCT FROM address THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF c.revoked_at IS NOT NULL THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  IF c.expires_at<=clock_timestamp() THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  RETURN NULL;
END $$;

CREATE FUNCTION v00_email.public_context(cid uuid) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c v00_email.contexts; ch v00_email.challenges; recovery_deadline timestamptz;
BEGIN
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=cid;
  IF c.stage='email_verification' THEN
    SELECT * INTO STRICT ch FROM v00_email.challenges WHERE id=c.current_email_challenge_id AND context_id=c.id;
  END IF;
  IF c.stage='completed' THEN
    SELECT w.deadline INTO STRICT recovery_deadline FROM v00_session.contexts dc
      JOIN v00_session.windows w ON w.login_id=dc.completed_login_id WHERE dc.id=c.id;
  END IF;
  RETURN jsonb_build_object('authContextId',c.id,'stage',c.stage,'accessConfirmed',c.access_confirmed,
    'createdAt',v00_session.utc(c.created_at),'expiresAt',v00_session.utc(c.expires_at),
    'emailCodeIssuedAt',v00_session.utc(ch.issued_at),'emailCodeExpiresAt',v00_session.utc(ch.expires_at),
    'currentEmailChallengeId',ch.id,
    'currentTotpChallengeId',CASE WHEN c.stage='totp_verification' THEN c.totp_challenge_id END,
    'totpChallengeIssuedAt',CASE WHEN c.stage='totp_verification' THEN v00_session.utc(c.totp_issued_at) END,
    'totpChallengeExpiresAt',CASE WHEN c.stage='totp_verification' THEN v00_session.utc(c.totp_expires_at) END,
    'loginCookieRecoveryDeadlineAt',v00_session.utc(recovery_deadline));
END $$;
CREATE FUNCTION v00_email.context_reply(cid uuid, status integer) RETURNS jsonb LANGUAGE sql SET search_path=pg_catalog AS $$
SELECT jsonb_build_object('http',status,'auth_context',v00_email.public_context(c.id),
  'observed_at',v00_session.utc(clock_timestamp()),
  'paused_until',v00_session.utc(CASE WHEN c.stage='totp_verification' THEN s.paused_until ELSE c.paused_until END),
  'pending_operation',EXISTS(SELECT 1 FROM v00_email.admissions a WHERE a.context_id=c.id
    AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=a.context_id AND r.operation_id=a.operation_id)))
FROM v00_email.contexts c LEFT JOIN v00_upstream.subjects s ON s.actor_id=c.actor_id WHERE c.id=cid
$$;
CREATE FUNCTION v00_email.context_create(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE t timestamptz; g v00_upstream.gate;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest']);
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton FOR SHARE;
  IF NOT g.is_open OR NOT g.clock_trusted THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  t:=date_trunc('milliseconds',clock_timestamp());
  INSERT INTO v00_email.contexts(id,proof_digest,created_at,expires_at)
    VALUES((p->>'context_id')::uuid,p->>'proof_digest',t,t+interval '30 minutes');
  RETURN v00_email.context_reply((p->>'context_id')::uuid,201);
END $$;
CREATE FUNCTION v00_email.context_read(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest']);
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  UPDATE v00_email.contexts SET access_confirmed=true WHERE id=(p->>'context_id')::uuid AND NOT access_confirmed;
  RETURN v00_email.context_reply((p->>'context_id')::uuid,200);
END $$;
CREATE FUNCTION v00_email.context_for_send(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest']);
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  IF NOT (SELECT access_confirmed FROM v00_email.contexts WHERE id=(p->>'context_id')::uuid) THEN
    RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT');
  END IF;
  RETURN v00_email.context_reply((p->>'context_id')::uuid,200);
END $$;

CREATE FUNCTION v00_email.replay(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a v00_email.admissions; r v00_email.results;
BEGIN
  SELECT * INTO a FROM v00_email.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF a.action IS DISTINCT FROM p->>'action' OR a.fingerprint IS DISTINCT FROM p->>'fingerprint'
    OR a.comparison_hmac IS DISTINCT FROM p->>'comparison_hmac' OR a.comparison_key_id IS DISTINCT FROM p->>'comparison_key_id'
    THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  SELECT * INTO r FROM v00_email.results WHERE context_id=a.context_id AND operation_id=a.operation_id;
  IF NOT FOUND THEN RETURN NULL; END IF;
  RETURN jsonb_build_object('http',200,'replay',true,'result',r.result,
    'resolved_at',v00_session.utc(r.resolved_at),'historical_http_status',r.historical_http_status);
END $$;

CREATE FUNCTION v00_email.capture(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; c v00_email.contexts; a v00_email.admissions; b jsonb; ch v00_email.challenges;
  t timestamptz; epoch_value bigint;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint',
    'comparison_hmac','comparison_key_id','executor_id','executor_proof_digest','challenge_id','locale','email_binding','request_started_at']);
  t:=(p->>'request_started_at')::timestamptz;
  IF t IS NULL OR t>clock_timestamp() OR t+interval '10 seconds'<=clock_timestamp() THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  b:=p->'email_binding';
  IF p->>'action'='C01' THEN
    PERFORM v00_upstream.keys(b,ARRAY['address_digest','address_key_id']);
  ELSIF b<>'null'::jsonb THEN RAISE EXCEPTION 'unexpected email binding'; END IF;
  SELECT epoch INTO STRICT epoch_value FROM v00_upstream.gate WHERE singleton;
  e:=v00_email.lock_scope(p,b->>'address_digest'); IF e IS NOT NULL THEN RETURN e; END IF;
  IF t+interval '10 seconds'<=clock_timestamp() OR epoch_value<>(SELECT epoch FROM v00_upstream.gate WHERE singleton) THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=(p->>'context_id')::uuid;
  IF NOT c.access_confirmed THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  SELECT * INTO a FROM v00_email.admissions WHERE context_id=c.id AND operation_id=(p->>'operation_id')::uuid;
  IF FOUND THEN
    IF a.action IS DISTINCT FROM p->>'action' OR a.fingerprint IS DISTINCT FROM p->>'fingerprint'
      OR a.comparison_hmac IS DISTINCT FROM p->>'comparison_hmac' OR a.comparison_key_id IS DISTINCT FROM p->>'comparison_key_id'
      OR a.challenge_id IS DISTINCT FROM (p->>'challenge_id')::uuid OR a.locale IS DISTINCT FROM p->>'locale'
      THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
    RETURN jsonb_build_object('http',200,'admission_id',a.id,'created',false,'context_expires_at',v00_session.utc(c.expires_at));
  END IF;
  IF EXISTS(SELECT 1 FROM v00_email.admissions x WHERE x.context_id=c.id
    AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=x.context_id AND r.operation_id=x.operation_id)) THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  IF p->>'action' IN ('C01','C03') THEN
    e:=v00_email.send_guard(COALESCE(c.address_digest,b->>'address_digest'));
    IF e IS NOT NULL THEN RETURN e; END IF;
  END IF;
  IF p->>'action'='C01' THEN
    IF c.stage<>'ready' OR c.address_digest IS NOT NULL THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
    IF NOT EXISTS(SELECT 1 FROM v00_email.directory WHERE address_digest=b->>'address_digest' AND address_key_id=b->>'address_key_id')
      THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    UPDATE v00_email.contexts SET address_digest=b->>'address_digest',binding_operation_id=(p->>'operation_id')::uuid WHERE id=c.id;
  ELSIF p->>'action' IN ('C02','C03') THEN
    SELECT * INTO ch FROM v00_email.challenges WHERE id=(p->>'challenge_id')::uuid AND context_id=c.id;
    IF NOT FOUND AND p->>'action'='C02' THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
    IF c.stage<>'email_verification' OR c.current_email_challenge_id IS DISTINCT FROM (p->>'challenge_id')::uuid THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
    IF p->>'action'='C02' AND c.paused_until>clock_timestamp() THEN RETURN v00_session.error(429,'RATE_LIMITED'); END IF;
  ELSIF p->>'action'='AUTH_TOTP_VERIFY' THEN
    IF c.stage<>'totp_verification' OR c.totp_challenge_id IS DISTINCT FROM (p->>'challenge_id')::uuid THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  ELSE RAISE EXCEPTION 'unsupported admission action'; END IF;
  INSERT INTO v00_email.admissions(context_id,operation_id,action,fingerprint,comparison_hmac,comparison_key_id,
    executor_id,executor_proof_digest,epoch,captured_at,deadline_at,challenge_id,locale)
    VALUES(c.id,(p->>'operation_id')::uuid,p->>'action',p->>'fingerprint',p->>'comparison_hmac',p->>'comparison_key_id',
    (p->>'executor_id')::uuid,p->>'executor_proof_digest',epoch_value,t,t+interval '10 seconds',(p->>'challenge_id')::uuid,p->>'locale') RETURNING * INTO a;
  RETURN jsonb_build_object('http',201,'admission_id',a.id,'created',true,'context_expires_at',v00_session.utc(c.expires_at));
END $$;

CREATE FUNCTION v00_email.admission_guard(p jsonb, require_executor boolean) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a v00_email.admissions; g v00_upstream.gate;
BEGIN
  SELECT * INTO a FROM v00_email.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF a.action IS DISTINCT FROM p->>'action' OR a.fingerprint IS DISTINCT FROM p->>'fingerprint'
    OR a.comparison_hmac IS DISTINCT FROM p->>'comparison_hmac' OR a.comparison_key_id IS DISTINCT FROM p->>'comparison_key_id'
    THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  IF require_executor AND (a.id IS DISTINCT FROM (p->>'admission_id')::uuid OR
    a.executor_proof_digest IS DISTINCT FROM encode(v00_upstream_crypto.digest(convert_to(p->>'executor_proof','UTF8'),'sha256'),'hex')) THEN
    RETURN v00_session.error(403,'ACCESS_DENIED');
  END IF;
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton;
  IF NOT g.is_open OR NOT g.clock_trusted OR g.epoch<>a.epoch OR clock_timestamp()>=a.deadline_at THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  RETURN NULL;
END $$;

CREATE FUNCTION v00_email.email_material(cid uuid) RETURNS jsonb LANGUAGE sql SET search_path=pg_catalog AS $$
SELECT jsonb_build_object('context_id',c.id,'address_digest',c.address_digest,'address_key_id',d.address_key_id,
  'secret_id',m.secret_id,'ciphertext',m.ciphertext,'nonce',m.nonce,'key_id',m.key_id,
  'cipher_format',m.cipher_format,'reveal_until',v00_session.utc(m.reveal_until))
FROM v00_email.contexts c JOIN v00_email.materials m ON m.context_id=c.id
JOIN v00_email.directory d ON d.address_digest=c.address_digest WHERE c.id=cid
$$;
CREATE FUNCTION v00_email.read_operation(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_email.admissions; r v00_email.results;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action']);
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_email.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF FOUND AND a.action IS DISTINCT FROM p->>'action' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  SELECT * INTO r FROM v00_email.results WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('http',202,'status','unresolved','result',NULL,'resolved_at',NULL); END IF;
  RETURN jsonb_build_object('http',200,'status','resolved','result',r.result,'resolved_at',v00_session.utc(r.resolved_at));
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_email FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_email.context_create(jsonb),v00_email.capture(jsonb) TO v00_email_ingress;
GRANT EXECUTE ON FUNCTION v00_email.context_read(jsonb),v00_email.read_operation(jsonb) TO v00_email_executor;
GRANT EXECUTE ON FUNCTION v00_email.context_for_send(jsonb) TO v00_email_executor;
COMMIT;
