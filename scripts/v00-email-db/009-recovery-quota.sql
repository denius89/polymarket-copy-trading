\set ON_ERROR_STOP on
-- New isolated profile, after unchanged 001..008. No existing contexts migrated.
BEGIN;
SET LOCAL ROLE v00_email_owner;
DO $$ BEGIN
  IF EXISTS(SELECT 1 FROM v00_email.contexts) THEN
    RAISE EXCEPTION 'recovery quota requires fresh email contexts';
  END IF;
END $$;

CREATE TABLE v00_email.recovery_quota_scopes (
  context_id uuid PRIMARY KEY REFERENCES v00_email.contexts,
  environment text NOT NULL DEFAULT 'v00-d03-07' CHECK(environment='v00-d03-07'),
  purpose text NOT NULL DEFAULT 'user/login/cookie_recovery' CHECK(purpose='user/login/cookie_recovery'),
  limit_count integer NOT NULL DEFAULT 3 CHECK(limit_count=3),
  window_seconds integer NOT NULL DEFAULT 60 CHECK(window_seconds=60),
  created_at timestamptz NOT NULL,
  UNIQUE(environment,context_id,purpose)
);
CREATE TABLE v00_email.recovery_quota_admissions (
  admission_token uuid PRIMARY KEY,
  context_id uuid NOT NULL REFERENCES v00_email.recovery_quota_scopes,
  operation_id uuid NOT NULL,
  action text NOT NULL CHECK(action IN ('C02','AUTH_TOTP_VERIFY')),
  executor_id uuid NOT NULL,
  executor_proof_digest text NOT NULL CHECK(executor_proof_digest ~ '^[0-9a-f]{64}$'),
  admitted_epoch bigint NOT NULL CHECK(admitted_epoch>0),
  request_started_at timestamptz NOT NULL,
  admitted_at timestamptz NOT NULL,
  deadline_at timestamptz NOT NULL,
  CHECK(deadline_at=request_started_at+interval '5 seconds'),
  CHECK(request_started_at<=admitted_at AND admitted_at<deadline_at)
);
CREATE INDEX recovery_quota_window ON v00_email.recovery_quota_admissions(context_id,admitted_at);
CREATE TABLE v00_email.recovery_attempts (
  admission_token uuid PRIMARY KEY REFERENCES v00_email.recovery_quota_admissions,
  target_pid integer NOT NULL CHECK(target_pid>0),
  target_txid bigint NOT NULL CHECK(target_txid>0),
  sealed_at timestamptz NOT NULL,
  UNIQUE(target_pid,target_txid),
  UNIQUE(admission_token,target_pid,target_txid)
);
CREATE TABLE v00_email.recovery_uses (
  admission_token uuid PRIMARY KEY REFERENCES v00_email.recovery_attempts,
  target_pid integer NOT NULL,
  target_txid bigint NOT NULL,
  entered_at timestamptz NOT NULL,
  FOREIGN KEY(admission_token,target_pid,target_txid) REFERENCES v00_email.recovery_attempts(admission_token,target_pid,target_txid)
);
CREATE TABLE v00_email.recovery_replay_guards (
  target_txid bigint NOT NULL,
  context_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  used_at timestamptz,
  PRIMARY KEY(target_txid,context_id,operation_id),
  FOREIGN KEY(context_id,operation_id) REFERENCES v00_email.results
);
DO $$ DECLARE tab text; BEGIN
  FOREACH tab IN ARRAY ARRAY['recovery_quota_scopes','recovery_quota_admissions','recovery_attempts','recovery_uses'] LOOP
    EXECUTE format('CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON v00_email.%I FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable()',tab);
  END LOOP;
END $$;

CREATE FUNCTION v00_email.require_recovery_scope() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF NOT EXISTS(SELECT 1 FROM v00_email.recovery_quota_scopes q WHERE q.context_id=NEW.id AND q.created_at=NEW.created_at) THEN
    RAISE EXCEPTION 'missing expected recovery quota scope';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER recovery_scope_required AFTER INSERT ON v00_email.contexts
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v00_email.require_recovery_scope();
CREATE OR REPLACE FUNCTION v00_email.context_create(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE g v00_upstream.gate; t timestamptz;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest']);
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton FOR SHARE;
  IF NOT g.is_open OR NOT g.clock_trusted THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  t:=date_trunc('milliseconds',clock_timestamp());
  INSERT INTO v00_email.contexts(id,proof_digest,created_at,expires_at)
    VALUES((p->>'context_id')::uuid,p->>'proof_digest',t,t+interval '30 minutes');
  INSERT INTO v00_email.recovery_quota_scopes(context_id,created_at) VALUES((p->>'context_id')::uuid,t);
  RETURN v00_email.context_reply((p->>'context_id')::uuid,201);
END $$;

-- Read-only precheck: no address/actor/context row locks and no operation lookup.
CREATE FUNCTION v00_email.recovery_access(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c v00_email.contexts; d v00_email.directory; g v00_upstream.gate; blocked boolean;
BEGIN
  SELECT * INTO g FROM v00_upstream.gate WHERE singleton;
  IF g.singleton IS NULL OR NOT g.is_open OR NOT g.clock_trusted THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  SELECT * INTO c FROM v00_email.contexts WHERE id=(p->>'context_id')::uuid;
  IF NOT FOUND OR c.proof_digest IS DISTINCT FROM p->>'proof_digest' THEN RETURN v00_session.error(404,'RESOURCE_NOT_FOUND'); END IF;
  IF c.address_digest IS NOT NULL THEN
    SELECT * INTO d FROM v00_email.directory WHERE address_digest=c.address_digest;
    IF NOT FOUND OR NOT d.enabled THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    SELECT a.blocked INTO blocked FROM v00_session.actors a WHERE a.id=d.actor_id;
    IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    IF blocked THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  END IF;
  IF c.revoked_at IS NOT NULL THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
  IF c.expires_at<=clock_timestamp() THEN RETURN v00_session.error(401,'AUTH_EXPIRED'); END IF;
  RETURN NULL;
END $$;

CREATE FUNCTION v00_email.recovery_admit(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; q v00_email.recovery_quota_scopes; g v00_upstream.gate; started timestamptz; t timestamptz;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','admission_token','executor_id','executor_proof_digest','request_started_at']);
  IF p->>'request_started_at' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$' THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  started:=(p->>'request_started_at')::timestamptz;
  IF v00_session.utc(started) IS DISTINCT FROM p->>'request_started_at' THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF NOT isfinite(started) OR started>clock_timestamp() OR clock_timestamp()>=started+interval '5 seconds' THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  e:=v00_email.recovery_access(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO q FROM v00_email.recovery_quota_scopes WHERE context_id=(p->>'context_id')::uuid FOR UPDATE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  e:=v00_email.recovery_access(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton;
  t:=clock_timestamp();
  IF t>=started+interval '5 seconds' OR NOT g.is_open OR NOT g.clock_trusted THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF t<q.created_at OR EXISTS(SELECT 1 FROM v00_email.recovery_quota_admissions WHERE context_id=q.context_id AND admitted_at>t) THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  IF EXISTS(SELECT 1 FROM v00_email.recovery_quota_admissions WHERE admission_token=(p->>'admission_token')::uuid) THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF (SELECT count(*) FROM v00_email.recovery_quota_admissions WHERE context_id=q.context_id AND admitted_at>t-interval '60 seconds')>=q.limit_count THEN
    RETURN v00_session.error(429,'RATE_LIMITED');
  END IF;
  INSERT INTO v00_email.recovery_quota_admissions VALUES((p->>'admission_token')::uuid,q.context_id,
    (p->>'operation_id')::uuid,p->>'action',(p->>'executor_id')::uuid,p->>'executor_proof_digest',g.epoch,started,t,started+interval '5 seconds');
  RETURN jsonb_build_object('http',201,'admission_token',p->>'admission_token','deadline_at',v00_session.utc(started+interval '5 seconds'));
END $$;

CREATE FUNCTION v00_email.recovery_target(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  PERFORM v00_session.require_keys(p,'{}');
  IF current_setting('transaction_isolation')<>'read committed' OR current_setting('transaction_read_only')<>'off' THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  RETURN jsonb_build_object('http',200,'target_pid',pg_backend_pid(),'target_txid',txid_current()::text);
END $$;

CREATE FUNCTION v00_email.recovery_admission_guard(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a v00_email.recovery_quota_admissions; g v00_upstream.gate; e jsonb;
BEGIN
  IF p->>'executor_proof' !~ '^[A-Za-z0-9_-]{43}$' THEN RETURN v00_session.error(403,'ACCESS_DENIED'); END IF;
  SELECT * INTO a FROM v00_email.recovery_quota_admissions WHERE admission_token=(p->>'admission_token')::uuid;
  IF NOT FOUND THEN RETURN v00_session.error(403,'ACCESS_DENIED'); END IF;
  IF (a.context_id,a.operation_id,a.action,a.executor_id) IS DISTINCT FROM
    ((p->>'context_id')::uuid,(p->>'operation_id')::uuid,p->>'action',(p->>'executor_id')::uuid)
    OR a.executor_proof_digest IS DISTINCT FROM encode(v00_upstream_crypto.digest(convert_to(p->>'executor_proof','UTF8'),'sha256'),'hex') THEN
    RETURN v00_session.error(403,'ACCESS_DENIED');
  END IF;
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton;
  IF NOT g.is_open OR NOT g.clock_trusted OR g.epoch<>a.admitted_epoch OR clock_timestamp()>=a.deadline_at THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  e:=v00_email.recovery_access(p); IF e IS NOT NULL THEN RETURN e; END IF;
  RETURN NULL;
END $$;

CREATE FUNCTION v00_email.recovery_seal(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; pid integer; xid bigint; t timestamptz;
BEGIN
  PERFORM v00_upstream.keys(p-'target_pid',ARRAY['context_id','proof_digest','operation_id','action','admission_token','executor_id','executor_proof','target_txid']);
  IF jsonb_typeof(p->'target_pid') IS DISTINCT FROM 'number' OR p->>'target_pid' !~ '^[1-9][0-9]*$'
    OR p->>'target_txid' !~ '^[1-9][0-9]*$' THEN RAISE EXCEPTION 'invalid recovery target'; END IF;
  pid:=(p->>'target_pid')::integer; xid:=(p->>'target_txid')::bigint;
  IF pid=pg_backend_pid() OR xid=txid_current() THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  e:=v00_email.recovery_admission_guard(p); IF e IS NOT NULL THEN RETURN e; END IF;
  PERFORM 1 FROM v00_email.recovery_quota_admissions WHERE admission_token=(p->>'admission_token')::uuid FOR UPDATE;
  e:=v00_email.recovery_admission_guard(p); IF e IS NOT NULL THEN RETURN e; END IF;
  IF EXISTS(SELECT 1 FROM v00_email.recovery_attempts WHERE admission_token=(p->>'admission_token')::uuid
    OR (target_pid=pid AND target_txid=xid)) THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  t:=clock_timestamp();
  IF t>=(SELECT deadline_at FROM v00_email.recovery_quota_admissions WHERE admission_token=(p->>'admission_token')::uuid) THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  INSERT INTO v00_email.recovery_attempts VALUES((p->>'admission_token')::uuid,pid,xid,t);
  RETURN jsonb_build_object('http',200,'sealed',true,'admission_token',p->>'admission_token','target_pid',pid,'target_txid',xid::text);
END $$;

CREATE FUNCTION v00_email.recovery_once(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_email.recovery_attempts; t timestamptz;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','admission_token','executor_id','executor_proof']);
  -- First subject lock: hold the gate epoch stable through raw recovery/COMMIT.
  -- Admission and seal remain separate transactions without subject locks.
  PERFORM 1 FROM v00_upstream.gate WHERE singleton FOR SHARE;
  e:=v00_email.recovery_admission_guard(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_email.recovery_attempts WHERE admission_token=(p->>'admission_token')::uuid;
  IF NOT FOUND OR a.target_pid<>pg_backend_pid() OR a.target_txid<>txid_current()
    OR current_setting('transaction_isolation')<>'read committed' THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  IF EXISTS(SELECT 1 FROM v00_email.recovery_uses WHERE admission_token=a.admission_token) THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  t:=clock_timestamp();
  IF t>=(SELECT deadline_at FROM v00_email.recovery_quota_admissions WHERE admission_token=a.admission_token) THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  INSERT INTO v00_email.recovery_uses VALUES(a.admission_token,a.target_pid,a.target_txid,t);
  RETURN v00_email.recover(p-ARRAY['admission_token','executor_id','executor_proof']);
END $$;

-- Original recovery is owner-only. Legal command replay obtains a same-T guard
-- only from the real plan path after its original fingerprint/HMAC validation.
REVOKE EXECUTE ON FUNCTION v00_email.recover(jsonb) FROM v00_email_executor;
ALTER FUNCTION v00_email.plan_email(jsonb) RENAME TO plan_email_before_recovery_quota;
ALTER FUNCTION v00_email.plan_totp(jsonb) RENAME TO plan_totp_before_recovery_quota;
REVOKE EXECUTE ON FUNCTION v00_email.plan_email_before_recovery_quota(jsonb),v00_email.plan_totp_before_recovery_quota(jsonb) FROM v00_email_executor;
CREATE FUNCTION v00_email.record_recovery_replay(p jsonb, reply jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF reply->>'replay'='true' AND reply->'result'->>'kind'='login_completed' THEN
    IF EXISTS(SELECT 1 FROM v00_email.recovery_replay_guards WHERE target_txid=txid_current()
      AND context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid) THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
    INSERT INTO v00_email.recovery_replay_guards VALUES(txid_current(),(p->>'context_id')::uuid,(p->>'operation_id')::uuid,NULL);
  END IF;
  RETURN reply;
END $$;
CREATE FUNCTION v00_email.plan_email(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN RETURN v00_email.record_recovery_replay(p,v00_email.plan_email_before_recovery_quota(p)); END $$;
CREATE FUNCTION v00_email.plan_totp(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN RETURN v00_email.record_recovery_replay(p,v00_email.plan_totp_before_recovery_quota(p)); END $$;
CREATE FUNCTION v00_email.recover_completion_replay(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action']);
  UPDATE v00_email.recovery_replay_guards SET used_at=clock_timestamp()
    WHERE target_txid=txid_current() AND context_id=(p->>'context_id')::uuid
      AND operation_id=(p->>'operation_id')::uuid AND used_at IS NULL;
  IF NOT FOUND THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  RETURN v00_email.recover(p);
END $$;
CREATE FUNCTION v00_email.guard_recovery_replay_history() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable replay authorization'; END IF;
  IF (NEW.target_txid,NEW.context_id,NEW.operation_id) IS DISTINCT FROM (OLD.target_txid,OLD.context_id,OLD.operation_id)
    OR OLD.used_at IS NOT NULL OR NEW.used_at IS NULL THEN RAISE EXCEPTION 'one-use replay authorization'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER recovery_replay_history BEFORE UPDATE OR DELETE ON v00_email.recovery_replay_guards
  FOR EACH ROW EXECUTE FUNCTION v00_email.guard_recovery_replay_history();
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_email FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_email.recovery_admit(jsonb),v00_email.recovery_seal(jsonb) TO v00_email_ingress;
GRANT EXECUTE ON FUNCTION v00_email.recovery_target(jsonb),v00_email.recovery_once(jsonb),
  v00_email.recover_completion_replay(jsonb),v00_email.plan_email(jsonb),v00_email.plan_totp(jsonb) TO v00_email_executor;
COMMIT;
