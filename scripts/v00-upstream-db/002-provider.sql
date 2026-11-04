\set ON_ERROR_STOP on
-- Operator-only instrumentation. Auth 2.197.0 actual PC metadata is prerequisite.
-- Existing-user recovery-family path only; no SMTP/C01/delivery guarantee.
BEGIN;
SET LOCAL ROLE v00_upstream_owner;
CREATE TABLE v00_upstream.generations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES v00_upstream.subjects(provider_user_id),
  family text NOT NULL CHECK(family IN ('confirmation','recovery')),
  issued_at timestamptz NOT NULL,
  issuing_txid bigint NOT NULL,
  state text NOT NULL CHECK(state IN ('issued','replaced','consumed','ambiguous')),
  UNIQUE(id,user_id,family)
);
CREATE TABLE v00_upstream.current_generations (
  user_id uuid NOT NULL REFERENCES v00_upstream.subjects(provider_user_id),
  family text NOT NULL CHECK(family IN ('confirmation','recovery')),
  generation_id uuid NOT NULL,
  PRIMARY KEY(user_id,family),
  FOREIGN KEY(generation_id,user_id,family) REFERENCES v00_upstream.generations(id,user_id,family)
);
CREATE TABLE v00_upstream.email_seals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  admission_id uuid NOT NULL UNIQUE REFERENCES v00_upstream.admissions,
  generation_id uuid NOT NULL UNIQUE,
  user_id uuid NOT NULL,
  family text NOT NULL,
  sealed_at timestamptz NOT NULL,
  FOREIGN KEY(generation_id,user_id,family) REFERENCES v00_upstream.generations(id,user_id,family)
);
CREATE TABLE v00_upstream.consumptions (
  seal_id uuid PRIMARY KEY REFERENCES v00_upstream.email_seals,
  user_id uuid NOT NULL,
  provider_txid bigint NOT NULL,
  observed_at timestamptz NOT NULL,
  UNIQUE(user_id,provider_txid),
  UNIQUE(seal_id,provider_txid)
);
CREATE TABLE v00_upstream.email_outcomes (
  seal_id uuid PRIMARY KEY,
  provider_txid bigint NOT NULL,
  provider_session_id uuid NOT NULL UNIQUE,
  observed_at timestamptz NOT NULL,
  FOREIGN KEY(seal_id,provider_txid) REFERENCES v00_upstream.consumptions(seal_id,provider_txid)
  -- Deliberately no provider session FK: evidence survives provider session deletion.
);
CREATE TRIGGER immutable_seal BEFORE UPDATE OR DELETE ON v00_upstream.email_seals FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();
CREATE TRIGGER immutable_consumption BEFORE UPDATE OR DELETE ON v00_upstream.consumptions FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();
CREATE TRIGGER immutable_outcome BEFORE UPDATE OR DELETE ON v00_upstream.email_outcomes FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();

CREATE FUNCTION v00_upstream.token_transition(uid uuid, fam text, old_token text, new_token text, old_sent timestamptz, new_sent timestamptz)
RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE current_gen v00_upstream.generations; fresh_id uuid; s v00_upstream.email_seals;
BEGIN
  IF NOT EXISTS(SELECT 1 FROM v00_upstream.subjects WHERE provider_user_id=uid) THEN RETURN; END IF;
  SELECT g.* INTO current_gen FROM v00_upstream.current_generations c JOIN v00_upstream.generations g ON g.id=c.generation_id
    WHERE c.user_id=uid AND c.family=fam FOR UPDATE OF c,g;
  IF COALESCE(new_token,'')<>'' THEN
    IF old_token IS DISTINCT FROM new_token OR old_sent IS DISTINCT FROM new_sent THEN
      IF current_gen.id IS NOT NULL THEN UPDATE v00_upstream.generations SET state='replaced' WHERE id=current_gen.id AND state='issued'; END IF;
      INSERT INTO v00_upstream.generations(user_id,family,issued_at,issuing_txid,state)
        VALUES(uid,fam,COALESCE(new_sent,clock_timestamp()),txid_current(),CASE WHEN new_sent IS NULL THEN 'ambiguous' ELSE 'issued' END) RETURNING id INTO fresh_id;
      INSERT INTO v00_upstream.current_generations VALUES(uid,fam,fresh_id)
        ON CONFLICT(user_id,family) DO UPDATE SET generation_id=excluded.generation_id;
    ELSE
      -- This hook is invoked only for a write of this family's token/issued columns.
      -- Identical bytes AND timestamp cannot distinguish issuance: fail closed.
      IF current_gen.id IS NOT NULL THEN UPDATE v00_upstream.generations SET state='ambiguous' WHERE id=current_gen.id; END IF;
    END IF;
  ELSIF COALESCE(old_token,'')<>'' AND current_gen.id IS NOT NULL THEN
    IF current_gen.state<>'issued' THEN RETURN; END IF;
    UPDATE v00_upstream.generations SET state='consumed' WHERE id=current_gen.id;
    SELECT * INTO s FROM v00_upstream.email_seals WHERE generation_id=current_gen.id;
    IF FOUND THEN
      INSERT INTO v00_upstream.consumptions VALUES(s.id,uid,txid_current(),clock_timestamp());
    END IF;
  END IF;
END $$;
CREATE FUNCTION v00_upstream.observe_recovery() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  PERFORM v00_upstream.token_transition(NEW.id,'recovery',OLD.recovery_token,NEW.recovery_token,OLD.recovery_sent_at,NEW.recovery_sent_at);
  RETURN NEW;
END $$;
CREATE FUNCTION v00_upstream.observe_confirmation() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  PERFORM v00_upstream.token_transition(NEW.id,'confirmation',OLD.confirmation_token,NEW.confirmation_token,OLD.confirmation_sent_at,NEW.confirmation_sent_at);
  RETURN NEW;
END $$;
CREATE FUNCTION v00_upstream.observe_session() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c v00_upstream.consumptions;
BEGIN
  SELECT * INTO c FROM v00_upstream.consumptions WHERE user_id=NEW.user_id AND provider_txid=txid_current();
  IF FOUND THEN
    -- A second session in the same transaction conflicts, never picks an arbitrary one.
    INSERT INTO v00_upstream.email_outcomes VALUES(c.seal_id,c.provider_txid,NEW.id,clock_timestamp());
  END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION v00_upstream.seal_email(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE e jsonb; a v00_upstream.admissions; c v00_upstream.contexts; s v00_upstream.subjects;
  u record; g v00_upstream.generations; seal v00_upstream.email_seals;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','challenge_id','admission_id','executor_proof']);
  IF p->>'action'<>'C02' THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
  e:=v00_upstream.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  e:=v00_upstream.replay(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_upstream.admissions WHERE id=(p->>'admission_id')::uuid;
  IF NOT FOUND OR a.context_id IS DISTINCT FROM (p->>'context_id')::uuid OR a.operation_id IS DISTINCT FROM (p->>'operation_id')::uuid THEN
    RETURN v00_session.error(403,'ACCESS_DENIED');
  END IF;
  -- Repeated sealed attempt cannot receive another permit, even after budget expiry.
  SELECT * INTO seal FROM v00_upstream.email_seals WHERE admission_id=a.id;
  IF FOUND THEN
    IF a.action<>p->>'action' OR a.fingerprint<>p->>'fingerprint' OR NOT EXISTS(SELECT 1 FROM v00_upstream.comparisons z
       WHERE z.admission_id=a.id AND z.hmac=p->>'comparison_hmac' AND z.key_id=p->>'comparison_key_id') THEN RETURN v00_session.error(409,'KEY_REUSE_CONFLICT'); END IF;
    RETURN jsonb_build_object('http',200,'dispatch_allowed',false,'dispatch_id',seal.id);
  END IF;
  e:=v00_upstream.admission_guard(p,true); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO STRICT c FROM v00_upstream.contexts WHERE id=a.context_id;
  SELECT * INTO STRICT s FROM v00_upstream.subjects WHERE actor_id=c.actor_id;
  SELECT id,email_confirmed_at,recovery_token,recovery_sent_at INTO u FROM auth.users WHERE id=s.provider_user_id FOR UPDATE;
  IF NOT FOUND THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
  IF c.stage<>'email_verification' OR c.email_challenge_id IS DISTINCT FROM (p->>'challenge_id')::uuid THEN RETURN v00_session.error(409,'AUTH_CONTEXT_STATE_CONFLICT'); END IF;
  -- Initial confirmation/signup remains a separately documented capability case.
  IF u.email_confirmed_at IS NULL OR COALESCE(u.recovery_token,'')='' OR u.recovery_sent_at IS NULL THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  SELECT z.* INTO g FROM v00_upstream.current_generations cg JOIN v00_upstream.generations z ON z.id=cg.generation_id
    WHERE cg.user_id=u.id AND cg.family='recovery' FOR UPDATE OF cg,z;
  IF NOT FOUND OR g.state<>'issued' OR g.issued_at IS DISTINCT FROM u.recovery_sent_at OR clock_timestamp()>=g.issued_at+interval '10 minutes' THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  IF EXISTS(SELECT 1 FROM v00_upstream.email_seals WHERE generation_id=g.id) THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  INSERT INTO v00_upstream.email_seals(admission_id,generation_id,user_id,family,sealed_at)
    VALUES(a.id,g.id,u.id,g.family,clock_timestamp()) RETURNING * INTO seal;
  RETURN jsonb_build_object('http',200,'dispatch_allowed',true,'dispatch_id',seal.id);
END $$;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_upstream FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_upstream.seal_email(jsonb) TO v00_upstream_executor;
RESET ROLE;
GRANT USAGE ON SCHEMA auth TO v00_upstream_owner;
GRANT SELECT(id,email_confirmed_at,confirmation_token,confirmation_sent_at,recovery_token,recovery_sent_at), UPDATE(id)
  ON auth.users TO v00_upstream_owner;
GRANT SELECT(id,user_id,factor_type,status,secret,created_at,updated_at), UPDATE(id) ON auth.mfa_factors TO v00_upstream_owner;
-- Preserve provider RLS. Only this isolated allowlisted synthetic subset is readable.
CREATE POLICY v00_upstream_users ON auth.users FOR SELECT TO v00_upstream_owner
  USING (EXISTS(SELECT 1 FROM v00_upstream.subjects s WHERE s.provider_user_id=auth.users.id));
CREATE POLICY v00_upstream_factors ON auth.mfa_factors FOR SELECT TO v00_upstream_owner
  USING (EXISTS(SELECT 1 FROM v00_upstream.subjects s WHERE s.provider_user_id=auth.mfa_factors.user_id));
CREATE POLICY v00_upstream_users_lock ON auth.users FOR UPDATE TO v00_upstream_owner
  USING (EXISTS(SELECT 1 FROM v00_upstream.subjects s WHERE s.provider_user_id=auth.users.id))
  WITH CHECK (EXISTS(SELECT 1 FROM v00_upstream.subjects s WHERE s.provider_user_id=auth.users.id));
CREATE POLICY v00_upstream_factors_lock ON auth.mfa_factors FOR UPDATE TO v00_upstream_owner
  USING (EXISTS(SELECT 1 FROM v00_upstream.subjects s WHERE s.provider_user_id=auth.mfa_factors.user_id))
  WITH CHECK (EXISTS(SELECT 1 FROM v00_upstream.subjects s WHERE s.provider_user_id=auth.mfa_factors.user_id));
CREATE TRIGGER v00_upstream_recovery AFTER UPDATE OF recovery_token,recovery_sent_at ON auth.users
  FOR EACH ROW EXECUTE FUNCTION v00_upstream.observe_recovery();
CREATE TRIGGER v00_upstream_confirmation AFTER UPDATE OF confirmation_token,confirmation_sent_at ON auth.users
  FOR EACH ROW EXECUTE FUNCTION v00_upstream.observe_confirmation();
CREATE TRIGGER v00_upstream_session AFTER INSERT ON auth.sessions
  FOR EACH ROW EXECUTE FUNCTION v00_upstream.observe_session();
COMMIT;
