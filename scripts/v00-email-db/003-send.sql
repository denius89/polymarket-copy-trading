\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_email_owner;

CREATE FUNCTION v00_email.send_guard(address text, own_admission uuid DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE n15 integer; n60 integer; last_accepted timestamptz; t timestamptz:=clock_timestamp();
BEGIN
  -- Caller holds the address directory row. An unresolved sealed send never expires
  -- into permission for a replacement request, even if its business window elapsed.
  IF EXISTS(SELECT 1 FROM v00_email.send_dispatches d JOIN v00_email.admissions a ON a.id=d.admission_id
    WHERE d.address_digest=address AND d.admission_id IS DISTINCT FROM own_admission
    AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=a.context_id AND r.operation_id=a.operation_id)) THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  IF EXISTS(SELECT 1 FROM v00_email.verify_dispatches d JOIN v00_email.admissions a ON a.id=d.admission_id
    JOIN v00_email.contexts c ON c.id=a.context_id WHERE c.address_digest=address
    AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=a.context_id AND r.operation_id=a.operation_id)) THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  SELECT count(*) FILTER(WHERE o.accepted_at>t-interval '15 minutes'),
    count(*) FILTER(WHERE o.accepted_at>t-interval '1 hour'),max(o.accepted_at)
    INTO n15,n60,last_accepted FROM v00_email.send_dispatches d
    JOIN v00_email.send_observations o ON o.dispatch_id=d.id WHERE d.address_digest=address;
  IF n15>=5 OR n60>=10 OR last_accepted+interval '60 seconds'>t THEN RETURN v00_session.error(429,'RATE_LIMITED'); END IF;
  RETURN NULL;
END $$;

CREATE FUNCTION v00_email.seal_send(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; c v00_email.contexts; a v00_email.admissions; d v00_email.send_dispatches;
  b jsonb; provider_id uuid; previous_generation uuid; s v00_upstream.subjects;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','admission_id','executor_proof','email_binding']);
  IF p->>'action' NOT IN ('C01','C03') THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.replay(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_email.admissions WHERE id=(p->>'admission_id')::uuid
    AND context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN v00_session.error(403,'ACCESS_DENIED'); END IF;
  SELECT * INTO d FROM v00_email.send_dispatches WHERE admission_id=a.id;
  IF FOUND THEN RETURN jsonb_build_object('http',200,'dispatch_allowed',false,'dispatch_id',d.id,
    'email_material',v00_email.email_material(a.context_id),'locale',a.locale); END IF;
  e:=v00_email.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  IF a.locale<>'en' THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=a.context_id;
  e:=v00_email.send_guard(c.address_digest,a.id); IF e IS NOT NULL THEN RETURN e; END IF;
  IF (a.action='C01' AND (c.stage<>'ready' OR c.binding_operation_id IS DISTINCT FROM a.operation_id))
    OR (a.action='C03' AND (c.stage<>'email_verification' OR c.current_email_challenge_id IS DISTINCT FROM a.challenge_id))
    THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  b:=p->'email_binding';
  IF a.action='C01' THEN
    PERFORM v00_upstream.keys(b,ARRAY['address_digest','address_key_id','secret_id','ciphertext','nonce','key_id','cipher_format','reveal_until']);
    IF b->>'address_digest' IS DISTINCT FROM c.address_digest OR (b->>'reveal_until')::timestamptz IS DISTINCT FROM c.expires_at
      OR NOT EXISTS(SELECT 1 FROM v00_email.directory WHERE address_digest=c.address_digest AND address_key_id=b->>'address_key_id') THEN
      RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
    INSERT INTO v00_email.materials VALUES(c.id,(b->>'secret_id')::uuid,b->>'key_id',b->>'cipher_format',b->>'nonce',b->>'ciphertext',(b->>'reveal_until')::timestamptz);
  ELSIF b<>'null'::jsonb THEN RAISE EXCEPTION 'unexpected email binding'; END IF;
  SELECT us.* INTO STRICT s FROM v00_email.directory di JOIN v00_upstream.subjects us ON us.actor_id=di.actor_id WHERE di.address_digest=c.address_digest;
  provider_id:=s.provider_user_id;
  PERFORM 1 FROM auth.users WHERE id=provider_id AND email_confirmed_at IS NOT NULL
    AND (banned_until IS NULL OR banned_until<=clock_timestamp()) FOR SHARE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  SELECT generation_id INTO previous_generation FROM v00_upstream.current_generations WHERE user_id=provider_id AND family='recovery';
  e:=v00_email.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  INSERT INTO v00_email.send_dispatches(admission_id,address_digest,provider_user_id,before_generation_id,sealed_at)
    VALUES(a.id,c.address_digest,provider_id,previous_generation,clock_timestamp()) RETURNING * INTO d;
  RETURN jsonb_build_object('http',200,'dispatch_allowed',true,'dispatch_id',d.id,
    'email_material',v00_email.email_material(c.id),'locale',a.locale);
END $$;

CREATE FUNCTION v00_email.send_observed(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE d v00_email.send_dispatches; a v00_email.admissions; g v00_upstream.generations; n integer;
  accepted timestamptz:=clock_timestamp();
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['dispatch_id']);
  SELECT * INTO d FROM v00_email.send_dispatches WHERE id=(p->>'dispatch_id')::uuid;
  IF NOT FOUND THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  PERFORM 1 FROM v00_upstream.gate WHERE singleton FOR SHARE;
  PERFORM 1 FROM v00_email.directory WHERE address_digest=d.address_digest FOR UPDATE;
  PERFORM 1 FROM v00_session.actors WHERE id=(SELECT actor_id FROM v00_upstream.subjects WHERE provider_user_id=d.provider_user_id) FOR UPDATE;
  SELECT * INTO STRICT a FROM v00_email.admissions WHERE id=d.admission_id;
  PERFORM 1 FROM v00_email.contexts WHERE id=a.context_id FOR UPDATE;
  IF EXISTS(SELECT 1 FROM v00_email.send_observations WHERE dispatch_id=d.id) THEN RETURN jsonb_build_object('http',200,'recorded',false); END IF;
  PERFORM 1 FROM auth.users WHERE id=d.provider_user_id FOR SHARE;
  SELECT count(*) INTO n FROM v00_upstream.generations WHERE user_id=d.provider_user_id
    AND family='recovery' AND issued_at>=d.sealed_at AND id IS DISTINCT FROM d.before_generation_id;
  SELECT ge.* INTO g FROM v00_upstream.current_generations cg JOIN v00_upstream.generations ge ON ge.id=cg.generation_id
    WHERE cg.user_id=d.provider_user_id AND cg.family='recovery';
  IF n<>1 OR g.id IS NULL OR g.state<>'issued' OR g.id IS NOT DISTINCT FROM d.before_generation_id
    OR g.issued_at<d.sealed_at OR g.issued_at>accepted THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  INSERT INTO v00_email.send_observations VALUES(d.id,g.id,accepted,accepted);
  RETURN jsonb_build_object('http',200,'recorded',true);
END $$;

CREATE FUNCTION v00_email.finalize_send(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; c v00_email.contexts; a v00_email.admissions; d v00_email.send_dispatches;
  o v00_email.send_observations; g v00_upstream.generations; challenge uuid:=gen_random_uuid(); result jsonb;
  t timestamptz; next_send timestamptz; old_challenge uuid;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id']);
  IF p->>'action' NOT IN ('C01','C03') THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.replay(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_email.admission_guard(p,false); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO STRICT a FROM v00_email.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=a.context_id;
  SELECT * INTO d FROM v00_email.send_dispatches WHERE admission_id=a.id;
  SELECT * INTO o FROM v00_email.send_observations WHERE dispatch_id=d.id;
  SELECT * INTO g FROM v00_upstream.generations WHERE id=o.generation_id;
  IF o.dispatch_id IS NULL OR g.id IS NULL OR g.state<>'issued' OR NOT EXISTS(SELECT 1 FROM v00_upstream.current_generations WHERE user_id=d.provider_user_id AND family='recovery' AND generation_id=g.id) THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF (a.action='C01' AND c.stage<>'ready') OR (a.action='C03' AND (c.stage<>'email_verification' OR c.current_email_challenge_id IS DISTINCT FROM a.challenge_id)) THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  t:=clock_timestamp(); old_challenge:=c.current_email_challenge_id;
  INSERT INTO v00_email.challenges(id,context_id,send_admission_id,dispatch_id,generation_id,issued_at,expires_at)
    VALUES(challenge,c.id,a.id,d.id,g.id,g.issued_at,LEAST(g.issued_at+interval '10 minutes',c.expires_at));
  IF old_challenge IS NOT NULL THEN UPDATE v00_email.challenges SET replaced_by_id=challenge WHERE id=old_challenge; END IF;
  UPDATE v00_email.contexts SET stage='email_verification',current_email_challenge_id=challenge WHERE id=c.id;
  next_send:=o.accepted_at+interval '60 seconds';
  -- At a full rolling window the earliest eligible send is also bounded by its oldest slot.
  SELECT GREATEST(next_send,COALESCE((SELECT min(x.accepted_at)+interval '15 minutes' FROM
    (SELECT so.accepted_at FROM v00_email.send_observations so JOIN v00_email.send_dispatches sd ON sd.id=so.dispatch_id
      WHERE sd.address_digest=c.address_digest AND so.accepted_at>t-interval '15 minutes' ORDER BY so.accepted_at DESC LIMIT 5) x HAVING count(*)=5),next_send),
    COALESCE((SELECT min(x.accepted_at)+interval '1 hour' FROM
    (SELECT so.accepted_at FROM v00_email.send_observations so JOIN v00_email.send_dispatches sd ON sd.id=so.dispatch_id
      WHERE sd.address_digest=c.address_digest AND so.accepted_at>t-interval '1 hour' ORDER BY so.accepted_at DESC LIMIT 10) x HAVING count(*)=10),next_send)) INTO next_send;
  result:=jsonb_build_object('kind','email_dispatch_accepted','acceptedAt',v00_session.utc(o.accepted_at),
    'challengeId',challenge,'resendNotBeforeAt',v00_session.utc(next_send));
  INSERT INTO v00_email.results VALUES(c.id,a.operation_id,a.action,result,202,t,NULL);
  INSERT INTO v00_email.audit(context_id,operation_id,kind,recorded_at) VALUES(c.id,a.operation_id,'email_dispatch_accepted',t);
  RETURN jsonb_build_object('http',202,'replay',false,'result',result,'resolved_at',v00_session.utc(t),'historical_http_status',202);
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_email FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_email.seal_send(jsonb),v00_email.finalize_send(jsonb) TO v00_email_executor;
GRANT EXECUTE ON FUNCTION v00_email.send_observed(jsonb) TO v00_email_witness;
COMMIT;
