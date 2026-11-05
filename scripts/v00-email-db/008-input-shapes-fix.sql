\set ON_ERROR_STOP on
-- Forward correction for installed 001–007; retain their original hashes/history.
BEGIN;
SET LOCAL ROLE v00_email_owner;

-- Exact names are always required. Only explicitly declared slots may contain
-- JSON null, objects or arrays. All remaining values retain the dependency's
-- nonempty-string/digest rules; its legacy action enum is NOT widened.
CREATE FUNCTION v00_email.keys(p jsonb, names text[], nullable_names text[] DEFAULT '{}',
  object_names text[] DEFAULT '{}', array_names text[] DEFAULT '{}') RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE k text; kind text; scalar_names text[];
BEGIN
  IF jsonb_typeof(p) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'invalid private request fields'; END IF;
  IF (SELECT array_agg(x ORDER BY x) FROM jsonb_object_keys(p) x) IS DISTINCT FROM
    (SELECT array_agg(x ORDER BY x) FROM unnest(names) x) THEN
    RAISE EXCEPTION 'invalid private request fields';
  END IF;
  FOREACH k IN ARRAY names LOOP
    kind:=jsonb_typeof(p->k);
    IF kind='null' AND k=ANY(nullable_names) THEN CONTINUE; END IF;
    IF k=ANY(object_names) THEN
      IF kind<>'object' THEN RAISE EXCEPTION 'invalid private request value'; END IF;
    ELSIF k=ANY(array_names) THEN
      IF kind<>'array' THEN RAISE EXCEPTION 'invalid private request value'; END IF;
    ELSE
      scalar_names:=array_append(scalar_names,k);
    END IF;
  END LOOP;
  PERFORM v00_session.require_keys(
    COALESCE((SELECT jsonb_object_agg(x,p->x) FROM unnest(scalar_names) x),'{}'::jsonb),
    COALESCE(scalar_names,'{}'::text[]));
  IF p ? 'action' AND p->>'action' NOT IN ('C01','C02','C03','AUTH_TOTP_VERIFY') THEN
    RAISE EXCEPTION 'invalid private action';
  END IF;
END $$;
REVOKE ALL ON FUNCTION v00_email.keys(jsonb,text[],text[],text[],text[]) FROM PUBLIC;

CREATE OR REPLACE FUNCTION v00_email.capture(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; c v00_email.contexts; a v00_email.admissions; b jsonb; ch v00_email.challenges;
  t timestamptz; epoch_value bigint;
BEGIN
  PERFORM v00_email.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint',
    'comparison_hmac','comparison_key_id','executor_id','executor_proof_digest','challenge_id','locale','email_binding','request_started_at'],
    ARRAY['challenge_id','locale','email_binding'],ARRAY['email_binding']);
  IF (p->>'action'='C01' AND (p->'challenge_id'<>'null'::jsonb OR jsonb_typeof(p->'email_binding')<>'object'
      OR COALESCE(p->>'locale','') NOT IN ('ru','en')))
    OR (p->>'action'='C03' AND (jsonb_typeof(p->'challenge_id')<>'string' OR p->'email_binding'<>'null'::jsonb
      OR COALESCE(p->>'locale','') NOT IN ('ru','en')))
    OR (p->>'action' IN ('C02','AUTH_TOTP_VERIFY') AND (jsonb_typeof(p->'challenge_id')<>'string'
      OR p->'locale'<>'null'::jsonb OR p->'email_binding'<>'null'::jsonb)) THEN
    RAISE EXCEPTION 'invalid private admission shape';
  END IF;
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

CREATE OR REPLACE FUNCTION v00_email.read_operation(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_email.admissions; r v00_email.results;
BEGIN
  PERFORM v00_email.keys(p,ARRAY['context_id','proof_digest','operation_id','action']);
  e:=v00_email.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_email.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF FOUND AND a.action IS DISTINCT FROM p->>'action' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  SELECT * INTO r FROM v00_email.results WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('http',202,'status','unresolved','result',NULL,'resolved_at',NULL); END IF;
  RETURN jsonb_build_object('http',200,'status','resolved','result',r.result,'resolved_at',v00_session.utc(r.resolved_at));
END $$;

CREATE OR REPLACE FUNCTION v00_email.seal_send(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; c v00_email.contexts; a v00_email.admissions; d v00_email.send_dispatches;
  b jsonb; provider_id uuid; previous_generation uuid; s v00_upstream.subjects;
BEGIN
  PERFORM v00_email.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','admission_id','executor_proof','email_binding'],
    ARRAY['email_binding'],ARRAY['email_binding']);
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

CREATE OR REPLACE FUNCTION v00_email.finalize_send(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; c v00_email.contexts; a v00_email.admissions; d v00_email.send_dispatches;
  o v00_email.send_observations; g v00_upstream.generations; challenge uuid:=gen_random_uuid(); result jsonb;
  t timestamptz; next_send timestamptz; old_challenge uuid;
BEGIN
  PERFORM v00_email.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id']);
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

CREATE OR REPLACE FUNCTION v00_email.seed_directory(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE row_value jsonb; provider_email text; n integer:=0;
BEGIN
  PERFORM v00_email.keys(p,ARRAY['entries'],'{}','{}',ARRAY['entries']);
  IF jsonb_typeof(p->'entries')<>'array' THEN RAISE EXCEPTION 'invalid directory fixture'; END IF;
  FOR row_value IN SELECT value FROM jsonb_array_elements(p->'entries') LOOP
    PERFORM v00_upstream.keys(row_value,ARRAY['actor_id','address_digest','address_key_id','normalized_email']);
    IF EXISTS(SELECT 1 FROM v00_upstream.contexts WHERE actor_id=(row_value->>'actor_id')::uuid)
      OR EXISTS(SELECT 1 FROM v00_session.contexts WHERE actor_id=(row_value->>'actor_id')::uuid)
      THEN RAISE EXCEPTION 'directory requires isolated actor without legacy context'; END IF;
    IF NOT EXISTS(SELECT 1 FROM v00_session.actors WHERE id=(row_value->>'actor_id')::uuid AND fixed_time IS NULL AND NOT blocked) THEN RAISE EXCEPTION 'invalid directory actor'; END IF;
    SELECT u.email INTO provider_email FROM auth.users u JOIN v00_upstream.subjects s ON s.provider_user_id=u.id
      WHERE s.actor_id=(row_value->>'actor_id')::uuid AND u.email_confirmed_at IS NOT NULL
      AND (u.banned_until IS NULL OR u.banned_until<=clock_timestamp());
    IF provider_email IS NULL OR provider_email IS DISTINCT FROM row_value->>'normalized_email'
      OR provider_email IS DISTINCT FROM lower(provider_email COLLATE "C") OR octet_length(provider_email)<>length(provider_email)
      THEN RAISE EXCEPTION 'provider directory source mismatch'; END IF;
    INSERT INTO v00_email.directory(address_digest,address_key_id,actor_id)
      VALUES(row_value->>'address_digest',row_value->>'address_key_id',(row_value->>'actor_id')::uuid);
    n:=n+1;
  END LOOP;
  RETURN jsonb_build_object('entries_inserted',n);
END $$;

-- CREATE OR REPLACE preserves the original owner/SECURITY DEFINER/ACLs.
-- The new validator remains owner-only; no new runtime entry point.
COMMIT;
