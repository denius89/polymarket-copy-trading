\set ON_ERROR_STOP on
-- Install once, operator only, in the separate D03-07 test database.
BEGIN;
CREATE ROLE v00_session_owner NOLOGIN;
CREATE ROLE v00_session_executor NOLOGIN;
CREATE ROLE v00_session_observer NOLOGIN;
CREATE SCHEMA v00_session AUTHORIZATION v00_session_owner;
REVOKE ALL ON SCHEMA v00_session FROM PUBLIC;
SET LOCAL ROLE v00_session_owner;
ALTER DEFAULT PRIVILEGES IN SCHEMA v00_session REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

CREATE TABLE v00_session.actors (
  id uuid PRIMARY KEY,
  fixed_time timestamptz,
  blocked boolean NOT NULL DEFAULT false
);
CREATE TABLE v00_session.contexts (
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL REFERENCES v00_session.actors,
  proof_digest text NOT NULL CHECK(proof_digest ~ '^[0-9a-f]{64}$'),
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  login_expires_at timestamptz NOT NULL,
  idle_expires_at timestamptz NOT NULL,
  completed_login_id uuid,
  completed_operation_id uuid,
  CHECK((completed_login_id IS NULL)=(completed_operation_id IS NULL)),
  UNIQUE(id,actor_id)
);
CREATE TABLE v00_session.results (
  context_id uuid NOT NULL REFERENCES v00_session.contexts,
  operation_id uuid NOT NULL,
  fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
  result jsonb NOT NULL,
  login_id uuid UNIQUE,
  completed_at timestamptz,
  resolved_at timestamptz NOT NULL,
  PRIMARY KEY(context_id,operation_id),
  UNIQUE(context_id,operation_id,login_id),
  UNIQUE(context_id,operation_id,login_id,completed_at),
  UNIQUE(context_id,operation_id,fingerprint),
  CHECK((login_id IS NULL)=(completed_at IS NULL)),
  CHECK(completed_at IS NULL OR resolved_at>=completed_at),
  CHECK(result->>'kind' IS NOT NULL AND result->>'kind' IN ('login_completed','verification_rejected')),
  CHECK((result->>'kind'='login_completed')=(login_id IS NOT NULL))
);
CREATE TABLE v00_session.logins (
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL REFERENCES v00_session.actors,
  context_id uuid NOT NULL UNIQUE,
  operation_id uuid NOT NULL,
  completed_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  idle_expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  FOREIGN KEY(context_id,actor_id) REFERENCES v00_session.contexts(id,actor_id),
  FOREIGN KEY(context_id,operation_id,id,completed_at) REFERENCES v00_session.results(context_id,operation_id,login_id,completed_at) DEFERRABLE INITIALLY DEFERRED,
  UNIQUE(id,context_id,operation_id)
);
ALTER TABLE v00_session.contexts ADD FOREIGN KEY(completed_login_id,id,completed_operation_id)
  REFERENCES v00_session.logins(id,context_id,operation_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE v00_session.results ADD FOREIGN KEY(login_id) REFERENCES v00_session.logins DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE v00_session.credentials (
  login_id uuid PRIMARY KEY REFERENCES v00_session.logins,
  cookie_digest text NOT NULL CHECK(cookie_digest ~ '^[0-9a-f]{64}$'),
  key_id text NOT NULL,
  format text NOT NULL DEFAULT 'v00-test-login-cookie-v1' CHECK(format='v00-test-login-cookie-v1')
);
CREATE TABLE v00_session.secrets (
  id uuid NOT NULL UNIQUE,
  login_id uuid PRIMARY KEY REFERENCES v00_session.logins,
  ciphertext text,
  nonce text NOT NULL,
  key_id text NOT NULL,
  erased_at timestamptz,
  UNIQUE(login_id,id),
  CHECK((ciphertext IS NULL)=(erased_at IS NOT NULL))
);
CREATE TABLE v00_session.windows (
  login_id uuid PRIMARY KEY REFERENCES v00_session.logins,
  deadline timestamptz NOT NULL,
  first_confirmed_at timestamptz,
  closed_at timestamptz,
  close_reason text CHECK(close_reason IN ('first_confirmation','deadline','login_revoked','context_revoked')),
  UNIQUE(login_id,deadline),
  CHECK((closed_at IS NULL)=(close_reason IS NULL))
);
ALTER TABLE v00_session.logins ADD FOREIGN KEY(id) REFERENCES v00_session.credentials(login_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE v00_session.logins ADD FOREIGN KEY(id) REFERENCES v00_session.secrets(login_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE v00_session.logins ADD FOREIGN KEY(id) REFERENCES v00_session.windows(login_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE v00_session.completion_plans (
  context_id uuid PRIMARY KEY REFERENCES v00_session.contexts,
  operation_id uuid NOT NULL,
  fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
  login_id uuid NOT NULL UNIQUE,
  secret_id uuid NOT NULL UNIQUE,
  completed_at timestamptz NOT NULL,
  deadline timestamptz NOT NULL,
  transaction_id bigint NOT NULL,
  FOREIGN KEY(context_id,operation_id,login_id,completed_at) REFERENCES v00_session.results(context_id,operation_id,login_id,completed_at) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY(context_id,operation_id,fingerprint) REFERENCES v00_session.results(context_id,operation_id,fingerprint) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY(login_id,secret_id) REFERENCES v00_session.secrets(login_id,id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY(login_id,deadline) REFERENCES v00_session.windows(login_id,deadline) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE v00_session.logout_contexts (
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL REFERENCES v00_session.actors,
  target_login_id uuid NOT NULL REFERENCES v00_session.logins,
  authorization_login_id uuid NOT NULL REFERENCES v00_session.logins,
  source_context_id uuid REFERENCES v00_session.logout_contexts,
  proof_digest text NOT NULL CHECK(proof_digest ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  CHECK(expires_at=created_at+interval '15 minutes')
);
CREATE TABLE v00_session.logout_results (
  context_id uuid NOT NULL REFERENCES v00_session.logout_contexts,
  operation_id uuid NOT NULL,
  fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
  target_login_id uuid NOT NULL REFERENCES v00_session.logins,
  confirmed_at timestamptz NOT NULL,
  result jsonb NOT NULL,
  PRIMARY KEY(context_id,operation_id)
);
CREATE TABLE v00_session.audit (
  ordinal bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  login_id uuid NOT NULL REFERENCES v00_session.logins,
  kind text NOT NULL CHECK(kind IN ('completion','window_closed','first_confirmation','login_revoked','logout_confirmed')),
  recorded_at timestamptz NOT NULL,
  reason text,
  operation_id uuid
);

CREATE FUNCTION v00_session.immutable_row() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'immutable D03-07 history'; END $$;
CREATE TRIGGER immutable_result BEFORE UPDATE OR DELETE ON v00_session.results FOR EACH ROW EXECUTE FUNCTION v00_session.immutable_row();
CREATE TRIGGER immutable_credential BEFORE UPDATE OR DELETE ON v00_session.credentials FOR EACH ROW EXECUTE FUNCTION v00_session.immutable_row();
CREATE TRIGGER immutable_logout_result BEFORE UPDATE OR DELETE ON v00_session.logout_results FOR EACH ROW EXECUTE FUNCTION v00_session.immutable_row();
CREATE TRIGGER immutable_audit BEFORE UPDATE OR DELETE ON v00_session.audit FOR EACH ROW EXECUTE FUNCTION v00_session.immutable_row();
CREATE TRIGGER immutable_plan BEFORE UPDATE OR DELETE ON v00_session.completion_plans FOR EACH ROW EXECUTE FUNCTION v00_session.immutable_row();

CREATE FUNCTION v00_session.now_for(actor uuid) RETURNS timestamptz LANGUAGE sql SET search_path=pg_catalog AS $$
  SELECT COALESCE(fixed_time,clock_timestamp()) FROM v00_session.actors WHERE id=actor
$$;
CREATE FUNCTION v00_session.error(status integer, reason text) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
  SELECT jsonb_build_object('http',status,'reason',reason)
$$;
CREATE FUNCTION v00_session.utc(t timestamptz) RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
  SELECT to_char(t AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
$$;
CREATE FUNCTION v00_session.require_keys(p jsonb, names text[]) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR
    (SELECT array_agg(k ORDER BY k) FROM jsonb_object_keys(p) k) IS DISTINCT FROM
    (SELECT array_agg(k ORDER BY k) FROM unnest(names) k) THEN
    RAISE EXCEPTION 'invalid private request fields';
  END IF;
  IF EXISTS(SELECT 1 FROM jsonb_each(p) e WHERE jsonb_typeof(e.value)<>'string' OR e.value='""'::jsonb)
    OR EXISTS(SELECT 1 FROM jsonb_each_text(p) e WHERE (e.key LIKE '%digest' OR e.key='fingerprint') AND e.value !~ '^[0-9a-f]{64}$') THEN
    RAISE EXCEPTION 'invalid private request value';
  END IF;
END $$;
CREATE FUNCTION v00_session.metadata(lid uuid, sid uuid, ctx uuid, op uuid, deadline timestamptz) RETURNS jsonb
  LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
  SELECT jsonb_build_object('environment','v00-d03-07','realm','user','login_id',lid,'secret_id',sid,
    'source_context_id',ctx,'source_operation_id',op,'owner_kind','login','owner_id',lid,'purpose','login_cookie',
    'cipher_format','v00-test-short-secret-xchacha20poly1305-v1','credential_format','v00-test-login-cookie-v1',
    'reveal_until',v00_session.utc(deadline))
$$;
CREATE FUNCTION v00_session.valid_result(r v00_session.results) RETURNS boolean LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE l v00_session.logins; c v00_session.contexts; w v00_session.windows; s v00_session.secrets;
BEGIN
  IF r.resolved_at IS NULL THEN RETURN false; END IF;
  IF r.result=jsonb_build_object('kind','verification_rejected','reasonCode','AUTH_VERIFICATION_FAILED') THEN
    RETURN r.login_id IS NULL AND r.completed_at IS NULL;
  END IF;
  IF r.login_id IS NULL OR r.completed_at IS NULL THEN RETURN false; END IF;
  IF r.result IS DISTINCT FROM jsonb_build_object('kind','login_completed','completion',jsonb_build_object(
    'authContextId',r.context_id,'authOperationId',r.operation_id,'loginId',r.login_id,'realm','user',
    'completedAt',v00_session.utc(r.completed_at))) THEN RETURN false; END IF;
  SELECT * INTO l FROM v00_session.logins WHERE id=r.login_id;
  SELECT * INTO c FROM v00_session.contexts WHERE id=r.context_id;
  SELECT * INTO w FROM v00_session.windows WHERE login_id=r.login_id;
  SELECT * INTO s FROM v00_session.secrets WHERE login_id=r.login_id;
  RETURN l.id IS NOT NULL AND c.id IS NOT NULL AND w.login_id IS NOT NULL AND s.login_id IS NOT NULL
    AND l.context_id=r.context_id AND l.operation_id=r.operation_id AND l.completed_at=r.completed_at
    AND c.actor_id=l.actor_id AND c.completed_login_id=l.id AND c.completed_operation_id=r.operation_id
    AND w.deadline=LEAST(r.completed_at+interval '5 minutes',c.expires_at)
    AND ((w.closed_at IS NULL AND s.ciphertext IS NOT NULL AND s.erased_at IS NULL)
      OR (w.closed_at IS NOT NULL AND s.ciphertext IS NULL AND s.erased_at IS NOT NULL))
    AND EXISTS(SELECT 1 FROM v00_session.credentials WHERE login_id=l.id)
    AND EXISTS(SELECT 1 FROM v00_session.completion_plans WHERE context_id=c.id AND operation_id=r.operation_id
      AND fingerprint=r.fingerprint AND login_id=l.id AND secret_id=s.id AND completed_at=r.completed_at AND deadline=w.deadline);
END $$;
-- Internal helpers run under an outer SECURITY DEFINER invocation, not public grants.
CREATE FUNCTION v00_session.lock_context(ctx uuid) RETURNS v00_session.contexts LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c v00_session.contexts; initial_actor uuid;
BEGIN
  SELECT * INTO c FROM v00_session.contexts WHERE id=ctx;
  IF NOT FOUND THEN RETURN NULL; END IF;
  initial_actor:=c.actor_id;
  PERFORM 1 FROM v00_session.actors WHERE id=initial_actor FOR UPDATE;
  SELECT * INTO c FROM v00_session.contexts WHERE id=ctx;
  IF c.actor_id IS DISTINCT FROM initial_actor THEN RAISE EXCEPTION 'fixture binding changed'; END IF;
  IF c.completed_login_id IS NOT NULL THEN PERFORM 1 FROM v00_session.logins WHERE id=c.completed_login_id FOR UPDATE; END IF;
  SELECT * INTO c FROM v00_session.contexts WHERE id=ctx FOR UPDATE;
  IF c.actor_id IS DISTINCT FROM initial_actor THEN RAISE EXCEPTION 'fixture binding changed'; END IF;
  RETURN c;
END $$;
CREATE FUNCTION v00_session.context_guard(c v00_session.contexts, proof text) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF c.id IS NULL OR c.proof_digest IS DISTINCT FROM proof THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  IF c.revoked_at IS NOT NULL THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  IF c.expires_at<=v00_session.now_for(c.actor_id) THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  RETURN NULL;
END $$;
CREATE FUNCTION v00_session.lock_login(lid uuid) RETURNS v00_session.logins LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE l v00_session.logins; initial_actor uuid;
BEGIN
  SELECT * INTO l FROM v00_session.logins WHERE id=lid;
  IF NOT FOUND THEN RETURN NULL; END IF;
  initial_actor:=l.actor_id;
  PERFORM 1 FROM v00_session.actors WHERE id=initial_actor FOR UPDATE;
  SELECT * INTO l FROM v00_session.logins WHERE id=lid FOR UPDATE;
  PERFORM 1 FROM v00_session.contexts WHERE id=l.context_id FOR UPDATE;
  IF l.actor_id IS DISTINCT FROM initial_actor THEN RAISE EXCEPTION 'fixture binding changed'; END IF;
  RETURN l;
END $$;
CREATE FUNCTION v00_session.login_guard(l v00_session.logins) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF l.id IS NULL THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  IF l.revoked_at IS NOT NULL OR (SELECT blocked FROM v00_session.actors WHERE id=l.actor_id) THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  IF LEAST(l.expires_at,l.idle_expires_at)<=v00_session.now_for(l.actor_id) THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  RETURN NULL;
END $$;
CREATE FUNCTION v00_session.close_window(lid uuid, why text, t timestamptz) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE w v00_session.windows; s v00_session.secrets;
BEGIN
  SELECT * INTO STRICT w FROM v00_session.windows WHERE login_id=lid FOR UPDATE;
  SELECT * INTO STRICT s FROM v00_session.secrets WHERE login_id=lid FOR UPDATE;
  IF w.closed_at IS NULL THEN
    IF s.ciphertext IS NULL THEN RAISE EXCEPTION 'missing recovery ciphertext before lawful close'; END IF;
    UPDATE v00_session.windows SET closed_at=t,close_reason=why WHERE login_id=lid;
    UPDATE v00_session.secrets SET ciphertext=NULL,erased_at=t WHERE login_id=lid;
    INSERT INTO v00_session.audit(login_id,kind,recorded_at,reason) VALUES(lid,'window_closed',t,why);
  ELSIF s.ciphertext IS NOT NULL OR s.erased_at IS NULL THEN
    RAISE EXCEPTION 'incomplete recovery erasure';
  END IF;
END $$;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_session FROM PUBLIC;
GRANT USAGE ON SCHEMA v00_session TO v00_session_executor,v00_session_observer;
COMMIT;
