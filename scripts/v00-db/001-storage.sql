\set ON_ERROR_STOP on
-- Isolated V00 only. Install once as the stand operator; never a production migration.
BEGIN;
CREATE ROLE v00_db_owner NOLOGIN;
CREATE ROLE v00_db_executor NOLOGIN;
CREATE ROLE v00_db_observer NOLOGIN;
CREATE SCHEMA v00_db AUTHORIZATION v00_db_owner;
REVOKE ALL ON SCHEMA v00_db FROM PUBLIC;
SET LOCAL ROLE v00_db_owner;
ALTER DEFAULT PRIVILEGES IN SCHEMA v00_db REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

CREATE TABLE v00_db.actors (
  id uuid PRIMARY KEY,
  fixed_time timestamptz, -- Explicit administrator-only deterministic fixture clock.
  failures integer NOT NULL DEFAULT 0 CHECK (failures BETWEEN 0 AND 5),
  blocked_until timestamptz
);
CREATE TABLE v00_db.factors (
  id uuid PRIMARY KEY, -- The ID is the immutable factor VERSION in this narrow probe.
  actor_id uuid NOT NULL REFERENCES v00_db.actors,
  active boolean NOT NULL DEFAULT true,
  UNIQUE (id, actor_id)
);
CREATE TABLE v00_db.contexts (
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL REFERENCES v00_db.actors,
  factor_version uuid NOT NULL,
  expires_at timestamptz NOT NULL,
  stage text NOT NULL DEFAULT 'totp_verification' CHECK (stage IN ('totp_verification','completed','revoked')),
  current_challenge_id uuid,
  FOREIGN KEY (factor_version, actor_id) REFERENCES v00_db.factors(id, actor_id)
);
CREATE TABLE v00_db.challenges (
  id uuid PRIMARY KEY,
  context_id uuid NOT NULL REFERENCES v00_db.contexts,
  expires_at timestamptz NOT NULL,
  UNIQUE (id, context_id)
);
ALTER TABLE v00_db.contexts ADD CONSTRAINT current_challenge_parent
  FOREIGN KEY (current_challenge_id, id) REFERENCES v00_db.challenges(id, context_id)
  DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE v00_db.totp_results (
  context_id uuid NOT NULL REFERENCES v00_db.contexts,
  operation_id uuid NOT NULL,
  fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
  result jsonb NOT NULL CHECK (jsonb_typeof(result) = 'object'),
  PRIMARY KEY (context_id, operation_id)
);
CREATE TABLE v00_db.used_steps (
  factor_version uuid NOT NULL REFERENCES v00_db.factors,
  step bigint NOT NULL CHECK (step >= 0),
  context_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  PRIMARY KEY (factor_version, step),
  FOREIGN KEY (context_id, operation_id) REFERENCES v00_db.totp_results DEFERRABLE INITIALLY DEFERRED
);

CREATE FUNCTION v00_db.immutable_row() RETURNS trigger LANGUAGE plpgsql
  SET search_path = pg_catalog AS $$
BEGIN RAISE EXCEPTION 'immutable V00 evidence'; END $$;
CREATE TRIGGER immutable_result BEFORE UPDATE OR DELETE ON v00_db.totp_results
  FOR EACH ROW EXECUTE FUNCTION v00_db.immutable_row();
CREATE TRIGGER immutable_steps BEFORE UPDATE OR DELETE ON v00_db.used_steps
  FOR EACH ROW EXECUTE FUNCTION v00_db.immutable_row();

CREATE FUNCTION v00_db.lookup_totp(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = pg_catalog AS $$
DECLARE r v00_db.totp_results;
BEGIN
  SELECT * INTO r FROM v00_db.totp_results WHERE context_id=(p->>'context_id')::uuid
    AND operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF r.fingerprint IS DISTINCT FROM p->>'fingerprint' THEN
    RETURN jsonb_build_object('status','rejected_precheck','http',409,'reason','payload_conflict');
  END IF;
  RETURN r.result;
END $$;

CREATE FUNCTION v00_db.read_totp_clock(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = pg_catalog AS $$
DECLARE t timestamptz; fixed boolean;
BEGIN
  SELECT COALESCE(a.fixed_time,clock_timestamp()),a.fixed_time IS NOT NULL INTO t,fixed
    FROM v00_db.contexts c JOIN v00_db.actors a ON a.id=c.actor_id WHERE c.id=(p->>'context_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('http',404,'reason','context_missing'); END IF;
  RETURN jsonb_build_object('unix_seconds',floor(extract(epoch FROM t))::bigint,'evaluation_step',floor(extract(epoch FROM t)/30)::bigint,
    'clock_mode',CASE WHEN fixed THEN 'fixed_fixture' ELSE 'wall' END);
END $$;

CREATE FUNCTION v00_db.verify_totp(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = pg_catalog AS $$
DECLARE
  c v00_db.contexts; a v00_db.actors; f v00_db.factors; ch v00_db.challenges;
  t timestamptz; op uuid := (p->>'operation_id')::uuid; ctx uuid := (p->>'context_id')::uuid;
  fp text := p->>'fingerprint'; step_now bigint; steps bigint[]; r jsonb; n integer; failed boolean;
BEGIN
  IF fp IS NULL OR fp !~ '^[0-9a-f]{64}$' OR op IS NULL OR ctx IS NULL THEN
    RAISE EXCEPTION 'invalid trusted executor input';
  END IF;
  -- Actor is the shared counter lock across contexts/devices/factor versions.
  SELECT * INTO c FROM v00_db.contexts WHERE id=ctx;
  IF NOT FOUND THEN RETURN jsonb_build_object('status','rejected_precheck','http',404,'reason','context_missing'); END IF;
  SELECT * INTO a FROM v00_db.actors WHERE id=c.actor_id FOR UPDATE;
  SELECT * INTO f FROM v00_db.factors WHERE id=c.factor_version FOR UPDATE;
  SELECT * INTO c FROM v00_db.contexts WHERE id=ctx FOR UPDATE;
  IF c.actor_id IS DISTINCT FROM a.id OR c.factor_version IS DISTINCT FROM f.id THEN
    RETURN jsonb_build_object('status','rejected_precheck','http',503,'reason','fixture_binding_changed');
  END IF;
  r := v00_db.lookup_totp(p);
  IF r IS NOT NULL THEN RETURN r; END IF;
  t := COALESCE(a.fixed_time,clock_timestamp());
  IF c.expires_at <= t OR c.stage='revoked' THEN
    RETURN jsonb_build_object('status','rejected_precheck','http',401,'reason','context_unavailable');
  END IF;
  SELECT * INTO ch FROM v00_db.challenges WHERE id=(p->>'challenge_id')::uuid AND context_id=ctx FOR UPDATE;
  IF NOT FOUND THEN RETURN jsonb_build_object('status','rejected_precheck','http',404,'reason','foreign_challenge'); END IF;
  t := COALESCE(a.fixed_time,clock_timestamp());
  IF c.expires_at<=t THEN RETURN jsonb_build_object('status','rejected_precheck','http',401,'reason','context_unavailable'); END IF;
  IF c.stage <> 'totp_verification' OR c.current_challenge_id IS DISTINCT FROM ch.id OR ch.expires_at<=t OR NOT f.active
    OR f.id IS DISTINCT FROM (p->>'factor_version')::uuid THEN
    RETURN jsonb_build_object('status','rejected_precheck','http',409,'reason','challenge_unavailable');
  END IF;
  IF a.blocked_until>t THEN RETURN jsonb_build_object('status','rejected_precheck','http',429,'reason','verification_paused'); END IF;
  IF p->>'clock_trusted' IS DISTINCT FROM 'true' THEN
    RETURN jsonb_build_object('status','rejected_precheck','http',503,'reason','clock_untrusted');
  END IF;
  -- Re-read time after every lock; a stale computed window is not a wrong code.
  t := COALESCE(a.fixed_time,clock_timestamp());
  step_now := floor(extract(epoch FROM t)/30)::bigint;
  IF (p->>'evaluation_step')::bigint IS DISTINCT FROM step_now THEN
    RETURN jsonb_build_object('status','rejected_precheck','http',503,'reason','evaluation_window_changed');
  END IF;
  IF jsonb_typeof(p->'matched_steps') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'matched_steps must be array'; END IF;
  SELECT COALESCE(array_agg(value::bigint ORDER BY value::bigint),'{}') INTO steps
    FROM jsonb_array_elements_text(p->'matched_steps');
  IF cardinality(steps)>3 OR cardinality(steps)<>(SELECT count(DISTINCT s) FROM unnest(steps) s)
    OR EXISTS(SELECT 1 FROM unnest(steps) s WHERE s<0 OR s<step_now-1 OR s>step_now+1) THEN
    RAISE EXCEPTION 'invalid matching window';
  END IF;
  failed := cardinality(steps)=0 OR EXISTS(SELECT 1 FROM v00_db.used_steps u
    WHERE u.factor_version=f.id AND u.step=ANY(steps));
  n := CASE WHEN a.blocked_until IS NOT NULL AND a.blocked_until<=t THEN 0 ELSE a.failures END;
  IF failed THEN
    n := n+1;
    UPDATE v00_db.actors SET failures=n,blocked_until=CASE WHEN n=5 THEN t+interval '15 minutes' END WHERE id=a.id;
    r := jsonb_build_object('status','resolved','http',401,'kind','verification_rejected',
      'reason','AUTH_VERIFICATION_FAILED','consumed_steps','[]'::jsonb,'resolved_at',t);
  ELSE
    INSERT INTO v00_db.used_steps SELECT f.id,s,ctx,op FROM unnest(steps) s;
    UPDATE v00_db.actors SET failures=0,blocked_until=NULL WHERE id=a.id;
    UPDATE v00_db.contexts SET stage='completed' WHERE id=ctx;
    r := jsonb_build_object('status','resolved','http',200,'kind','totp_consumed',
      'consumed_steps',to_jsonb(steps),'resolved_at',t);
  END IF;
  INSERT INTO v00_db.totp_results VALUES(ctx,op,fp,r);
  RETURN r;
END $$;

REVOKE ALL ON ALL TABLES IN SCHEMA v00_db FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_db FROM PUBLIC;
GRANT USAGE ON SCHEMA v00_db TO v00_db_executor,v00_db_observer;
GRANT EXECUTE ON FUNCTION v00_db.lookup_totp(jsonb),v00_db.read_totp_clock(jsonb),v00_db.verify_totp(jsonb) TO v00_db_executor;
GRANT SELECT ON ALL TABLES IN SCHEMA v00_db TO v00_db_observer;
COMMIT;
