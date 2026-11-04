\set ON_ERROR_STOP on
-- Test-only instrumentation of Supabase Auth 2.197.0. Operator installs once.
-- Do not use this migration unless actual provider columns/transaction boundaries match.
BEGIN;
SET LOCAL ROLE v00_db_owner;
CREATE TABLE v00_db.email_seals (
  operation_id uuid PRIMARY KEY,
  user_id uuid NOT NULL UNIQUE, -- One synthetic user per operation; deliberately no reseal.
  token_digest text NOT NULL CHECK(token_digest ~ '^[0-9a-f]{64}$'),
  fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
  sealed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE v00_db.email_confirmations (
  operation_id uuid PRIMARY KEY REFERENCES v00_db.email_seals,
  user_id uuid NOT NULL,
  provider_txid bigint NOT NULL,
  confirmed_at timestamptz NOT NULL,
  UNIQUE (user_id,provider_txid)
);
CREATE TABLE v00_db.email_outcomes (
  operation_id uuid PRIMARY KEY REFERENCES v00_db.email_confirmations,
  provider_txid bigint NOT NULL,
  session_id uuid NOT NULL UNIQUE,
  observed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER immutable_seal BEFORE UPDATE OR DELETE ON v00_db.email_seals
  FOR EACH ROW EXECUTE FUNCTION v00_db.immutable_row();
CREATE TRIGGER immutable_confirmation BEFORE UPDATE OR DELETE ON v00_db.email_confirmations
  FOR EACH ROW EXECUTE FUNCTION v00_db.immutable_row();
CREATE TRIGGER immutable_outcome BEFORE UPDATE OR DELETE ON v00_db.email_outcomes
  FOR EACH ROW EXECUTE FUNCTION v00_db.immutable_row();

CREATE FUNCTION v00_db.seal_email(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = pg_catalog AS $$
DECLARE r v00_db.email_seals; u record;
BEGIN
  -- Same order as provider UPDATE: user first, then immutable seal/confirmation.
  SELECT id,email_confirmed_at,confirmation_token INTO u FROM auth.users WHERE id=(p->>'user_id')::uuid FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'synthetic provider user missing'; END IF;
  SELECT * INTO r FROM v00_db.email_seals WHERE operation_id=(p->>'operation_id')::uuid;
  IF FOUND THEN
    IF r.user_id IS DISTINCT FROM (p->>'user_id')::uuid OR r.fingerprint IS DISTINCT FROM p->>'fingerprint'
      OR r.token_digest IS DISTINCT FROM p->>'token_digest' THEN
      RETURN jsonb_build_object('http',409,'reason','payload_conflict','dispatch_allowed',false);
    END IF;
    RETURN jsonb_build_object('http',200,'seal_id',r.operation_id,'dispatch_allowed',false);
  END IF;
  IF u.email_confirmed_at IS NOT NULL OR u.confirmation_token IS NULL OR u.confirmation_token=''
    OR encode(sha256(convert_to(u.confirmation_token,'UTF8')),'hex') IS DISTINCT FROM p->>'token_digest' THEN
    RETURN jsonb_build_object('http',409,'reason','provider_prestate_mismatch','dispatch_allowed',false);
  END IF;
  INSERT INTO v00_db.email_seals(operation_id,user_id,token_digest,fingerprint)
    VALUES((p->>'operation_id')::uuid,u.id,p->>'token_digest',p->>'fingerprint') RETURNING * INTO r;
  RETURN jsonb_build_object('http',200,'seal_id',r.operation_id,'dispatch_allowed',true);
END $$;

CREATE FUNCTION v00_db.observe_confirmation() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = pg_catalog AS $$
DECLARE s v00_db.email_seals;
BEGIN
  IF OLD.email_confirmed_at IS NULL AND NEW.email_confirmed_at IS NOT NULL THEN
    SELECT * INTO s FROM v00_db.email_seals WHERE user_id=NEW.id
      AND token_digest=encode(sha256(convert_to(OLD.confirmation_token,'UTF8')),'hex');
    IF FOUND THEN
      INSERT INTO v00_db.email_confirmations(operation_id,user_id,provider_txid,confirmed_at)
        VALUES(s.operation_id,NEW.id,txid_current(),NEW.email_confirmed_at);
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION v00_db.observe_session() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = pg_catalog AS $$
DECLARE c v00_db.email_confirmations;
BEGIN
  SELECT * INTO c FROM v00_db.email_confirmations WHERE user_id=NEW.user_id AND provider_txid=txid_current();
  IF FOUND THEN
    INSERT INTO v00_db.email_outcomes(operation_id,provider_txid,session_id) VALUES(c.operation_id,c.provider_txid,NEW.id);
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION v00_db.read_email_outcome(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = pg_catalog AS $$
DECLARE o v00_db.email_outcomes;
BEGIN
  SELECT * INTO o FROM v00_db.email_outcomes WHERE operation_id=(p->>'operation_id')::uuid;
  IF NOT FOUND THEN RETURN jsonb_build_object('status','uncertain','http',202,'dispatch_allowed',false); END IF;
  RETURN jsonb_build_object('status','confirmed_effect','http',200,'operation_id',o.operation_id,
    'session_id',o.session_id,'provider_txid',o.provider_txid,'observed_at',o.observed_at,'dispatch_allowed',false);
END $$;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_db FROM PUBLIC;
GRANT SELECT ON v00_db.email_confirmations,v00_db.email_outcomes TO v00_db_observer;
-- token digest intentionally omitted from observer grants/evidence.
GRANT SELECT(operation_id,user_id,fingerprint,sealed_at) ON v00_db.email_seals TO v00_db_observer;
GRANT EXECUTE ON FUNCTION v00_db.seal_email(jsonb),v00_db.read_email_outcome(jsonb) TO v00_db_executor;
GRANT EXECUTE ON FUNCTION v00_db.read_email_outcome(jsonb) TO v00_db_observer;
RESET ROLE;
GRANT USAGE ON SCHEMA auth TO v00_db_owner;
GRANT SELECT(id,email_confirmed_at,confirmation_token), UPDATE(id) ON auth.users TO v00_db_owner;
CREATE TRIGGER v00_confirmation_witness AFTER UPDATE OF email_confirmed_at ON auth.users
  FOR EACH ROW EXECUTE FUNCTION v00_db.observe_confirmation();
CREATE TRIGGER v00_session_witness AFTER INSERT ON auth.sessions
  FOR EACH ROW EXECUTE FUNCTION v00_db.observe_session();
COMMIT;
