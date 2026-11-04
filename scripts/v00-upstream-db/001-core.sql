\set ON_ERROR_STOP on
-- Install once in the separate upstream test DB, after v00-session-db 001..004.
-- No provider reads, extension installation or network effect in this file.
BEGIN;
CREATE ROLE v00_upstream_owner NOLOGIN;
CREATE ROLE v00_upstream_ingress NOLOGIN;
CREATE ROLE v00_upstream_executor NOLOGIN;
CREATE ROLE v00_upstream_observer NOLOGIN;
GRANT v00_session_owner TO v00_upstream_owner;
CREATE SCHEMA v00_upstream AUTHORIZATION v00_upstream_owner;
REVOKE ALL ON SCHEMA v00_upstream FROM PUBLIC;
SET LOCAL ROLE v00_upstream_owner;
ALTER DEFAULT PRIVILEGES IN SCHEMA v00_upstream REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

CREATE TABLE v00_upstream.gate (
  singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
  epoch bigint NOT NULL CHECK(epoch>0),
  is_open boolean NOT NULL,
  clock_trusted boolean NOT NULL
);
INSERT INTO v00_upstream.gate VALUES(true,1,true,true);
CREATE TABLE v00_upstream.subjects (
  actor_id uuid PRIMARY KEY REFERENCES v00_session.actors,
  provider_user_id uuid NOT NULL UNIQUE,
  current_factor uuid,
  failures integer NOT NULL DEFAULT 0 CHECK(failures BETWEEN 0 AND 5),
  paused_until timestamptz
);
CREATE TABLE v00_upstream.factors (
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL REFERENCES v00_upstream.subjects,
  provider_factor_id uuid NOT NULL UNIQUE,
  active boolean NOT NULL,
  profile text NOT NULL DEFAULT 'user-totp-login-v1' CHECK(profile='user-totp-login-v1'),
  UNIQUE(id,actor_id)
);
ALTER TABLE v00_upstream.subjects ADD FOREIGN KEY(current_factor,actor_id)
  REFERENCES v00_upstream.factors(id,actor_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE v00_upstream.contexts (
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL REFERENCES v00_upstream.subjects,
  stage text NOT NULL DEFAULT 'email_verification' CHECK(stage IN ('email_verification','totp_verification','completed','closed')),
  email_challenge_id uuid NOT NULL UNIQUE,
  factor_version uuid,
  totp_challenge_id uuid UNIQUE,
  totp_issued_at timestamptz,
  totp_expires_at timestamptz,
  FOREIGN KEY(id,actor_id) REFERENCES v00_session.contexts(id,actor_id),
  FOREIGN KEY(factor_version,actor_id) REFERENCES v00_upstream.factors(id,actor_id),
  CHECK((totp_challenge_id IS NULL)=(totp_issued_at IS NULL)),
  CHECK((totp_challenge_id IS NULL)=(totp_expires_at IS NULL)),
  CHECK(totp_expires_at IS NULL OR (factor_version IS NOT NULL AND totp_expires_at>totp_issued_at)),
  CHECK(stage<>'totp_verification' OR totp_challenge_id IS NOT NULL)
);
CREATE TABLE v00_upstream.admissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  context_id uuid NOT NULL REFERENCES v00_upstream.contexts,
  operation_id uuid NOT NULL,
  action text NOT NULL CHECK(action IN ('C02','AUTH_TOTP_VERIFY')),
  fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
  executor_id uuid NOT NULL,
  executor_proof_digest text NOT NULL CHECK(executor_proof_digest ~ '^[0-9a-f]{64}$'),
  epoch bigint NOT NULL CHECK(epoch>0),
  captured_at timestamptz NOT NULL,
  deadline_at timestamptz NOT NULL,
  UNIQUE(context_id,operation_id),
  UNIQUE(id,context_id,operation_id,action),
  UNIQUE(context_id,operation_id,action),
  CHECK(deadline_at=captured_at+interval '10 seconds')
);
CREATE TABLE v00_upstream.comparisons (
  admission_id uuid PRIMARY KEY REFERENCES v00_upstream.admissions,
  hmac text NOT NULL CHECK(hmac ~ '^[0-9a-f]{64}$'),
  key_id text NOT NULL CHECK(key_id<>''),
  expires_at timestamptz NOT NULL
);
CREATE TABLE v00_upstream.results (
  context_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  action text NOT NULL,
  result jsonb NOT NULL,
  resolved_at timestamptz NOT NULL,
  login_id uuid UNIQUE,
  PRIMARY KEY(context_id,operation_id),
  FOREIGN KEY(context_id,operation_id,action) REFERENCES v00_upstream.admissions(context_id,operation_id,action),
  FOREIGN KEY(context_id,operation_id,login_id) REFERENCES v00_session.results(context_id,operation_id,login_id) DEFERRABLE INITIALLY DEFERRED,
  CHECK(result->>'kind' IS NOT NULL AND result->>'kind' IN ('auth_step_required','verification_rejected','login_completed','auth_completion_not_issued')),
  CHECK((result->>'kind'='login_completed')=(login_id IS NOT NULL))
);
CREATE TABLE v00_upstream.used_steps (
  factor_version uuid NOT NULL REFERENCES v00_upstream.factors,
  step bigint NOT NULL CHECK(step>=0),
  context_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  PRIMARY KEY(factor_version,step),
  FOREIGN KEY(context_id,operation_id) REFERENCES v00_upstream.results DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE v00_upstream.plans (
  context_id uuid PRIMARY KEY REFERENCES v00_upstream.contexts,
  operation_id uuid NOT NULL,
  admission_id uuid NOT NULL UNIQUE REFERENCES v00_upstream.admissions,
  action text NOT NULL,
  transaction_id bigint NOT NULL,
  FOREIGN KEY(admission_id,context_id,operation_id,action) REFERENCES v00_upstream.admissions(id,context_id,operation_id,action),
  FOREIGN KEY(context_id,operation_id) REFERENCES v00_upstream.results DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY(context_id) REFERENCES v00_session.completion_plans(context_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE v00_upstream.audit (
  ordinal bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  context_id uuid NOT NULL REFERENCES v00_upstream.contexts,
  operation_id uuid NOT NULL,
  kind text NOT NULL CHECK(kind IN ('email_stage','completion','verification_rejected')),
  recorded_at timestamptz NOT NULL,
  UNIQUE(context_id,operation_id),
  FOREIGN KEY(context_id,operation_id) REFERENCES v00_upstream.results DEFERRABLE INITIALLY DEFERRED
);

CREATE FUNCTION v00_upstream.immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'immutable upstream evidence'; END $$;
CREATE TRIGGER immutable_admission BEFORE UPDATE OR DELETE ON v00_upstream.admissions FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();
CREATE TRIGGER immutable_comparison BEFORE UPDATE OR DELETE ON v00_upstream.comparisons FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();
CREATE TRIGGER immutable_result BEFORE UPDATE OR DELETE ON v00_upstream.results FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();
CREATE TRIGGER immutable_steps BEFORE UPDATE OR DELETE ON v00_upstream.used_steps FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();
CREATE TRIGGER immutable_plan BEFORE UPDATE OR DELETE ON v00_upstream.plans FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();
CREATE TRIGGER immutable_audit BEFORE UPDATE OR DELETE ON v00_upstream.audit FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();

CREATE FUNCTION v00_upstream.keys(p jsonb, names text[]) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  PERFORM v00_session.require_keys(p,names);
  IF p ? 'action' AND p->>'action' NOT IN ('C02','AUTH_TOTP_VERIFY') THEN RAISE EXCEPTION 'invalid private action'; END IF;
END $$;
CREATE FUNCTION v00_upstream.lock_scope(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE g v00_upstream.gate; c v00_session.contexts; e jsonb;
BEGIN
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton FOR SHARE;
  IF NOT g.is_open OR NOT g.clock_trusted THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  c:=v00_session.lock_context((p->>'context_id')::uuid);
  e:=v00_session.context_guard(c,p->>'proof_digest'); IF e IS NOT NULL THEN RETURN e; END IF;
  IF NOT EXISTS(SELECT 1 FROM v00_upstream.contexts WHERE id=c.id AND actor_id=c.actor_id) THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  IF (SELECT blocked FROM v00_session.actors WHERE id=c.actor_id) THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  PERFORM 1 FROM v00_upstream.contexts WHERE id=c.id FOR UPDATE;
  RETURN NULL;
END $$;
CREATE FUNCTION v00_upstream.capture(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE started timestamptz:=clock_timestamp(); initial_epoch bigint; g v00_upstream.gate;
  a v00_upstream.admissions; cmp v00_upstream.comparisons; r v00_upstream.results; e jsonb; expiry timestamptz;
BEGIN
  -- This role is called before the trusted ingress queues/dispatches the handler.
  SELECT epoch INTO STRICT initial_epoch FROM v00_upstream.gate WHERE singleton;
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','executor_id','executor_proof_digest']);
  IF p->>'comparison_hmac' !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'invalid comparison'; END IF;
  e:=v00_upstream.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_upstream.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF FOUND THEN
    SELECT * INTO r FROM v00_upstream.results WHERE context_id=a.context_id AND operation_id=a.operation_id;
    IF FOUND AND v00_upstream.valid_result(r) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    SELECT * INTO STRICT cmp FROM v00_upstream.comparisons WHERE admission_id=a.id;
    IF a.action<>p->>'action' OR a.fingerprint<>p->>'fingerprint' OR cmp.hmac<>p->>'comparison_hmac' OR cmp.key_id<>p->>'comparison_key_id' THEN
      RETURN v00_session.error(409,'KEY_REUSE_CONFLICT');
    END IF;
    RETURN jsonb_build_object('http',200,'admission_id',a.id,'created',false);
  END IF;
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton;
  IF initial_epoch<>g.epoch OR clock_timestamp()>=started+interval '10 seconds' THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  -- An unresolved earlier attempt on this actor cannot be bypassed with a new scope.
  IF EXISTS(SELECT 1 FROM v00_upstream.admissions x JOIN v00_upstream.contexts xc ON xc.id=x.context_id
     JOIN v00_upstream.contexts own ON own.id=(p->>'context_id')::uuid
     WHERE xc.actor_id=own.actor_id AND NOT EXISTS(SELECT 1 FROM v00_upstream.results r WHERE r.context_id=x.context_id AND r.operation_id=x.operation_id)) THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  SELECT expires_at INTO STRICT expiry FROM v00_session.contexts WHERE id=(p->>'context_id')::uuid;
  INSERT INTO v00_upstream.admissions(context_id,operation_id,action,fingerprint,executor_id,executor_proof_digest,epoch,captured_at,deadline_at)
    VALUES((p->>'context_id')::uuid,(p->>'operation_id')::uuid,p->>'action',p->>'fingerprint',(p->>'executor_id')::uuid,p->>'executor_proof_digest',
      initial_epoch,started,started+interval '10 seconds') RETURNING * INTO a;
  INSERT INTO v00_upstream.comparisons VALUES(a.id,p->>'comparison_hmac',p->>'comparison_key_id',expiry);
  RETURN jsonb_build_object('http',201,'admission_id',a.id,'created',true);
END $$;

CREATE FUNCTION v00_upstream.admission_guard(p jsonb, proof_required boolean) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a v00_upstream.admissions; cmp v00_upstream.comparisons; g v00_upstream.gate; proof text;
BEGIN
  SELECT * INTO a FROM v00_upstream.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  SELECT * INTO STRICT cmp FROM v00_upstream.comparisons WHERE admission_id=a.id;
  IF a.action<>p->>'action' OR a.fingerprint<>p->>'fingerprint' OR cmp.hmac<>p->>'comparison_hmac' OR cmp.key_id<>p->>'comparison_key_id' THEN
    RETURN v00_session.error(409,'KEY_REUSE_CONFLICT');
  END IF;
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton;
  IF a.epoch<>g.epoch OR NOT g.is_open OR NOT g.clock_trusted OR clock_timestamp()>=a.deadline_at OR clock_timestamp()>=cmp.expires_at THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  IF proof_required THEN
    proof:=p->>'executor_proof';
    IF a.id IS DISTINCT FROM (p->>'admission_id')::uuid OR proof IS NULL OR proof !~ '^[A-Za-z0-9_-]{43}$'
      OR right(proof,1) !~ '^[AEIMQUYcgkosw048]$'
      OR encode(sha256(convert_to(proof,'UTF8')),'hex')<>a.executor_proof_digest THEN RETURN v00_session.error(403,'ACCESS_DENIED'); END IF;
  END IF;
  RETURN NULL;
END $$;

CREATE FUNCTION v00_upstream.valid_result(r v00_upstream.results) RETURNS boolean LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE s v00_session.results; c v00_upstream.contexts;
BEGIN
  IF r.result=jsonb_build_object('kind','verification_rejected','reasonCode','AUTH_VERIFICATION_FAILED') THEN RETURN r.login_id IS NULL; END IF;
  IF r.result->>'kind'='login_completed' THEN
    SELECT * INTO s FROM v00_session.results WHERE context_id=r.context_id AND operation_id=r.operation_id;
    RETURN s.login_id=r.login_id AND s.result=r.result AND s.resolved_at=r.resolved_at AND v00_session.valid_result(s);
  END IF;
  IF r.result->>'kind'='auth_step_required' THEN
    SELECT * INTO c FROM v00_upstream.contexts WHERE id=r.context_id;
    RETURN r.action='C02' AND r.login_id IS NULL AND c.totp_challenge_id IS NOT NULL
      AND r.result=jsonb_build_object('kind','auth_step_required','stage','totp_verification','challengeId',c.totp_challenge_id,
        'challengeIssuedAt',v00_session.utc(c.totp_issued_at),'challengeExpiresAt',v00_session.utc(c.totp_expires_at));
  END IF;
  -- Late-result reconciliation is not implemented by this narrow first core.
  RETURN false;
END $$;
CREATE FUNCTION v00_upstream.read_operation(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a v00_upstream.admissions; r v00_upstream.results; e jsonb;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action']);
  e:=v00_upstream.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_upstream.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF FOUND AND a.action<>p->>'action' THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  SELECT * INTO r FROM v00_upstream.results WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('http',202,'status','unresolved','result',NULL,'resolved_at',NULL); END IF;
  IF v00_upstream.valid_result(r) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  RETURN jsonb_build_object('http',200,'status','resolved','result',r.result,'resolved_at',v00_session.utc(r.resolved_at));
END $$;
CREATE FUNCTION v00_upstream.replay(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a v00_upstream.admissions; cmp v00_upstream.comparisons; r v00_upstream.results;
BEGIN
  SELECT * INTO a FROM v00_upstream.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF a.action<>p->>'action' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  SELECT * INTO r FROM v00_upstream.results WHERE context_id=a.context_id AND operation_id=a.operation_id;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF v00_upstream.valid_result(r) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  SELECT * INTO STRICT cmp FROM v00_upstream.comparisons WHERE admission_id=a.id;
  IF clock_timestamp()>=cmp.expires_at THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF a.fingerprint<>p->>'fingerprint' OR cmp.hmac<>p->>'comparison_hmac' OR cmp.key_id<>p->>'comparison_key_id' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  RETURN jsonb_build_object('http',200,'replay',true,'result',r.result);
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA v00_upstream FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_upstream FROM PUBLIC;
GRANT USAGE ON SCHEMA v00_upstream TO v00_upstream_ingress,v00_upstream_executor,v00_upstream_observer;
GRANT EXECUTE ON FUNCTION v00_upstream.capture(jsonb) TO v00_upstream_ingress;
GRANT EXECUTE ON FUNCTION v00_upstream.read_operation(jsonb) TO v00_upstream_executor;
COMMIT;
