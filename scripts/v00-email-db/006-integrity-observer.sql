\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_email_owner;
ALTER TABLE v00_email.challenges ADD FOREIGN KEY(replaced_by_id,context_id)
  REFERENCES v00_email.challenges(id,context_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE v00_email.challenges ADD FOREIGN KEY(context_id,consumed_by_operation_id)
  REFERENCES v00_email.results(context_id,operation_id) DEFERRABLE INITIALLY DEFERRED;
CREATE FUNCTION v00_email.proved_email(admission uuid) RETURNS boolean LANGUAGE sql SET search_path=pg_catalog AS $$
SELECT EXISTS(SELECT 1 FROM v00_email.verify_dispatches d
 JOIN v00_email.consumptions co ON co.dispatch_id=d.id AND co.provider_user_id=d.provider_user_id
 JOIN v00_email.verify_observations o ON o.dispatch_id=d.id AND o.provider_txid=co.provider_txid
 JOIN v00_upstream.generations g ON g.id=d.generation_id AND g.user_id=d.provider_user_id AND g.family='recovery'
 WHERE d.admission_id=admission AND g.state='consumed')
$$;
CREATE FUNCTION v00_email.valid_result(r v00_email.results) RETURNS boolean LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a v00_email.admissions; c v00_email.contexts; ch v00_email.challenges; n v00_email.negative_proofs;
  sr v00_session.results; so v00_email.send_observations; kind text:=r.result->>'kind'; expected_kind text;
BEGIN
  SELECT * INTO a FROM v00_email.admissions WHERE context_id=r.context_id AND operation_id=r.operation_id AND action=r.action;
  SELECT * INTO c FROM v00_email.contexts WHERE id=r.context_id;
  IF a.id IS NULL OR c.id IS NULL THEN RETURN false; END IF;
  expected_kind:=CASE kind WHEN 'auth_step_required' THEN 'email_stage' WHEN 'login_completed' THEN 'completion' ELSE kind END;
  IF NOT EXISTS(SELECT 1 FROM v00_email.audit au WHERE au.context_id=r.context_id AND au.operation_id=r.operation_id
    AND au.kind=expected_kind AND au.recorded_at=r.resolved_at) THEN RETURN false; END IF;
  IF kind='email_dispatch_accepted' THEN
    SELECT * INTO ch FROM v00_email.challenges WHERE send_admission_id=a.id;
    SELECT * INTO so FROM v00_email.send_observations WHERE dispatch_id=ch.dispatch_id;
    RETURN a.action IN ('C01','C03') AND r.historical_http_status=202 AND ch.id IS NOT NULL AND ch.context_id=c.id
      AND so.dispatch_id IS NOT NULL AND so.generation_id=ch.generation_id
      AND r.result=jsonb_build_object('kind',kind,'acceptedAt',v00_session.utc(so.accepted_at),'challengeId',ch.id,
        'resendNotBeforeAt',r.result->>'resendNotBeforeAt')
      AND (r.result->>'resendNotBeforeAt')::timestamptz>=date_trunc('milliseconds',so.accepted_at)+interval '60 seconds'
      AND r.login_id IS NULL;
  ELSIF kind='verification_rejected' THEN
    IF r.historical_http_status<>401 OR r.login_id IS NOT NULL OR r.result<>jsonb_build_object('kind',kind,'reasonCode','AUTH_VERIFICATION_FAILED')
      OR EXISTS(SELECT 1 FROM v00_email.plans WHERE context_id=r.context_id AND operation_id=r.operation_id)
      OR EXISTS(SELECT 1 FROM v00_email.used_steps WHERE context_id=r.context_id AND operation_id=r.operation_id) THEN RETURN false; END IF;
    IF a.action='C02' THEN
      SELECT * INTO n FROM v00_email.negative_proofs WHERE admission_id=a.id;
      SELECT * INTO ch FROM v00_email.challenges WHERE id=n.challenge_id AND context_id=c.id;
      RETURN n.admission_id IS NOT NULL AND ch.id=a.challenge_id AND n.generation_id=ch.generation_id
        AND n.context_id=r.context_id AND n.operation_id=r.operation_id AND n.checked_at=r.resolved_at
        AND ((n.kind='expired_current' AND n.checked_at>=ch.expires_at) OR (n.kind='live_mismatch' AND n.checked_at<ch.expires_at))
        AND NOT EXISTS(SELECT 1 FROM v00_email.verify_dispatches WHERE admission_id=a.id);
    END IF;
    RETURN a.action='AUTH_TOTP_VERIFY' AND c.actor_id IS NOT NULL;
  ELSIF kind='auth_step_required' THEN
    RETURN a.action='C02' AND r.historical_http_status=200 AND c.actor_id IS NOT NULL AND c.factor_version IS NOT NULL
      AND EXISTS(SELECT 1 FROM v00_session.contexts dc WHERE dc.id=c.id AND dc.actor_id=c.actor_id AND dc.expires_at=c.expires_at)
      AND v00_email.proved_email(a.id) AND r.login_id IS NULL
      AND r.result=jsonb_build_object('kind',kind,'stage','totp_verification','challengeId',c.totp_challenge_id,
        'challengeIssuedAt',v00_session.utc(c.totp_issued_at),'challengeExpiresAt',v00_session.utc(c.totp_expires_at));
  ELSIF kind='login_completed' THEN
    SELECT * INTO sr FROM v00_session.results WHERE context_id=r.context_id AND operation_id=r.operation_id;
    IF sr.login_id IS NULL OR sr.login_id IS DISTINCT FROM r.login_id OR sr.result IS DISTINCT FROM r.result
      OR sr.resolved_at IS DISTINCT FROM r.resolved_at OR v00_session.valid_result(sr) IS DISTINCT FROM true
      OR c.stage<>'completed' OR NOT EXISTS(SELECT 1 FROM v00_session.contexts dc WHERE dc.id=c.id AND dc.actor_id=c.actor_id)
      OR r.historical_http_status<>200 OR NOT EXISTS(SELECT 1 FROM v00_email.plans pl WHERE pl.context_id=c.id
        AND pl.operation_id=a.operation_id AND pl.admission_id=a.id AND pl.action=a.action) THEN RETURN false; END IF;
    IF a.action='C02' THEN RETURN v00_email.proved_email(a.id); END IF;
    RETURN a.action='AUTH_TOTP_VERIFY' AND EXISTS(SELECT 1 FROM v00_email.used_steps st WHERE st.context_id=c.id AND st.operation_id=a.operation_id)
      AND NOT EXISTS(SELECT 1 FROM v00_email.used_steps st WHERE st.context_id=c.id AND st.operation_id=a.operation_id AND st.factor_version<>c.factor_version)
      AND EXISTS(SELECT 1 FROM v00_email.results er WHERE er.context_id=c.id AND er.action='C02' AND er.result->>'kind'='auth_step_required');
  END IF;
  RETURN false;
EXCEPTION WHEN OTHERS THEN RETURN false;
END $$;

CREATE FUNCTION v00_email.check_bundle() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE cid uuid; c v00_email.contexts; checked_result v00_email.results;
BEGIN
  cid:=COALESCE(to_jsonb(NEW)->>'context_id',to_jsonb(NEW)->>'id')::uuid;
  SELECT * INTO STRICT c FROM v00_email.contexts WHERE id=cid;
  FOR checked_result IN SELECT * FROM v00_email.results WHERE context_id=cid LOOP
    IF v00_email.valid_result(checked_result) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete email entry result'; END IF;
  END LOOP;
  IF EXISTS(SELECT 1 FROM v00_email.challenges ch JOIN v00_email.admissions a ON a.id=ch.send_admission_id
    WHERE ch.context_id=cid AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=cid AND r.operation_id=a.operation_id AND r.result->>'kind'='email_dispatch_accepted'))
    OR EXISTS(SELECT 1 FROM v00_email.plans pl WHERE pl.context_id=cid AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=cid AND r.operation_id=pl.operation_id AND r.result->>'kind'='login_completed'))
    OR EXISTS(SELECT 1 FROM v00_email.used_steps st WHERE st.context_id=cid AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=cid AND r.operation_id=st.operation_id AND r.action='AUTH_TOTP_VERIFY' AND r.result->>'kind'='login_completed')) THEN
    RAISE EXCEPTION 'incomplete email entry children'; END IF;
  IF c.stage<>'ready' AND NOT EXISTS(SELECT 1 FROM v00_email.materials m WHERE m.context_id=cid AND m.reveal_until=c.expires_at) THEN RAISE EXCEPTION 'missing bound address material'; END IF;
  IF c.stage='email_verification' AND c.current_email_challenge_id IS NULL THEN RAISE EXCEPTION 'missing current email challenge'; END IF;
  IF c.stage='totp_verification' AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=cid AND r.result->>'kind'='auth_step_required') THEN RAISE EXCEPTION 'missing email stage result'; END IF;
  IF c.stage='completed' AND NOT EXISTS(SELECT 1 FROM v00_email.results r WHERE r.context_id=cid AND r.result->>'kind'='login_completed') THEN RAISE EXCEPTION 'missing full login result'; END IF;
  RETURN NULL;
END $$;
DO $$ DECLARE tab text; BEGIN
  FOREACH tab IN ARRAY ARRAY['contexts','challenges','negative_proofs','results','plans','used_steps','audit'] LOOP
    EXECUTE format('CREATE CONSTRAINT TRIGGER complete_bundle AFTER INSERT OR UPDATE ON v00_email.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v00_email.check_bundle()',tab);
  END LOOP;
END $$;

CREATE FUNCTION v00_email.guard_context_history() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable context history'; END IF;
  IF (NEW.id,NEW.proof_digest,NEW.created_at,NEW.expires_at) IS DISTINCT FROM (OLD.id,OLD.proof_digest,OLD.created_at,OLD.expires_at)
    OR (OLD.access_confirmed AND NOT NEW.access_confirmed)
    OR (OLD.address_digest IS NOT NULL AND (NEW.address_digest,NEW.binding_operation_id) IS DISTINCT FROM (OLD.address_digest,OLD.binding_operation_id))
    OR (OLD.actor_id IS NOT NULL AND NEW.actor_id IS DISTINCT FROM OLD.actor_id)
    OR (OLD.totp_challenge_id IS NOT NULL AND (NEW.factor_version,NEW.totp_challenge_id,NEW.totp_issued_at,NEW.totp_expires_at) IS DISTINCT FROM (OLD.factor_version,OLD.totp_challenge_id,OLD.totp_issued_at,OLD.totp_expires_at)) THEN
    RAISE EXCEPTION 'immutable context history'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER context_history BEFORE UPDATE OR DELETE ON v00_email.contexts FOR EACH ROW EXECUTE FUNCTION v00_email.guard_context_history();
CREATE TRIGGER material_history BEFORE UPDATE OR DELETE ON v00_email.materials FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable();
CREATE FUNCTION v00_email.guard_challenge_history() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable challenge history'; END IF;
  IF (NEW.id,NEW.context_id,NEW.send_admission_id,NEW.dispatch_id,NEW.generation_id,NEW.issued_at,NEW.expires_at)
    IS DISTINCT FROM (OLD.id,OLD.context_id,OLD.send_admission_id,OLD.dispatch_id,OLD.generation_id,OLD.issued_at,OLD.expires_at)
    OR (OLD.replaced_by_id IS NOT NULL AND NEW.replaced_by_id IS DISTINCT FROM OLD.replaced_by_id)
    OR (OLD.consumed_by_operation_id IS NOT NULL AND NEW.consumed_by_operation_id IS DISTINCT FROM OLD.consumed_by_operation_id)
    THEN RAISE EXCEPTION 'immutable challenge history'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER challenge_history BEFORE UPDATE OR DELETE ON v00_email.challenges FOR EACH ROW EXECUTE FUNCTION v00_email.guard_challenge_history();

CREATE FUNCTION v00_email.snapshot(cid uuid) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
SELECT jsonb_build_object('schema','v00-email-entry-snapshot-v1','context',to_jsonb(c)-ARRAY['proof_digest','address_digest'],
 'material',CASE WHEN m.context_id IS NULL THEN NULL ELSE jsonb_build_object('context_id',m.context_id,'secret_id',m.secret_id,'cipher_present',m.ciphertext IS NOT NULL,'reveal_until',m.reveal_until,'cipher_format',m.cipher_format) END,
 'directory_enabled',di.enabled,
 'generations',COALESCE((SELECT jsonb_agg(to_jsonb(g) ORDER BY g.issued_at,g.id) FROM v00_upstream.generations g
   JOIN v00_upstream.subjects s ON s.provider_user_id=g.user_id WHERE s.actor_id=di.actor_id),'[]'::jsonb),
 'gate',(SELECT jsonb_build_object('epoch',epoch,'open',is_open,'clock_trusted',clock_trusted) FROM v00_upstream.gate WHERE singleton),
 'admissions',COALESCE((SELECT jsonb_agg(to_jsonb(a)-ARRAY['fingerprint','comparison_hmac','comparison_key_id','executor_proof_digest'] ORDER BY a.captured_at,a.id) FROM v00_email.admissions a WHERE a.context_id=cid),'[]'::jsonb),
 'results',COALESCE((SELECT jsonb_agg(to_jsonb(r)||jsonb_build_object('valid',v00_email.valid_result(r)) ORDER BY r.resolved_at,r.operation_id) FROM v00_email.results r WHERE r.context_id=cid),'[]'::jsonb),
 'challenges',COALESCE((SELECT jsonb_agg(to_jsonb(ch) ORDER BY ch.issued_at,ch.id) FROM v00_email.challenges ch WHERE ch.context_id=cid),'[]'::jsonb),
 'sends',COALESCE((SELECT jsonb_agg(to_jsonb(d)-'address_digest' ORDER BY d.sealed_at,d.id) FROM v00_email.send_dispatches d JOIN v00_email.admissions a ON a.id=d.admission_id WHERE a.context_id=cid),'[]'::jsonb),
 'send_observations',COALESCE((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.observed_at,o.dispatch_id) FROM v00_email.send_observations o JOIN v00_email.send_dispatches d ON d.id=o.dispatch_id JOIN v00_email.admissions a ON a.id=d.admission_id WHERE a.context_id=cid),'[]'::jsonb),
 'verifies',COALESCE((SELECT jsonb_agg(to_jsonb(d) ORDER BY d.sealed_at,d.id) FROM v00_email.verify_dispatches d JOIN v00_email.admissions a ON a.id=d.admission_id WHERE a.context_id=cid),'[]'::jsonb),
 'consumptions',COALESCE((SELECT jsonb_agg(to_jsonb(co) ORDER BY co.observed_at,co.dispatch_id) FROM v00_email.consumptions co JOIN v00_email.verify_dispatches d ON d.id=co.dispatch_id JOIN v00_email.admissions a ON a.id=d.admission_id WHERE a.context_id=cid),'[]'::jsonb),
 'verify_observations',COALESCE((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.observed_at,o.dispatch_id) FROM v00_email.verify_observations o JOIN v00_email.verify_dispatches d ON d.id=o.dispatch_id JOIN v00_email.admissions a ON a.id=d.admission_id WHERE a.context_id=cid),'[]'::jsonb),
 'negative_proofs',COALESCE((SELECT jsonb_agg(to_jsonb(n) ORDER BY n.checked_at,n.admission_id) FROM v00_email.negative_proofs n WHERE n.context_id=cid),'[]'::jsonb),
 'plans',COALESCE((SELECT jsonb_agg(to_jsonb(pl)) FROM v00_email.plans pl WHERE pl.context_id=cid),'[]'::jsonb),
 'steps',COALESCE((SELECT jsonb_agg(to_jsonb(st) ORDER BY st.step) FROM v00_email.used_steps st WHERE st.context_id=cid),'[]'::jsonb),
 'audit',COALESCE((SELECT jsonb_agg(to_jsonb(au) ORDER BY au.ordinal) FROM v00_email.audit au WHERE au.context_id=cid),'[]'::jsonb),
 'address_sends',COALESCE((SELECT jsonb_agg(jsonb_build_object('dispatch_id',sd.id,'admission_id',sd.admission_id,'sealed_at',sd.sealed_at,'accepted_at',so.accepted_at,'resolved',EXISTS(SELECT 1 FROM v00_email.results rr WHERE rr.context_id=sa.context_id AND rr.operation_id=sa.operation_id)) ORDER BY sd.sealed_at,sd.id)
   FROM v00_email.send_dispatches sd JOIN v00_email.admissions sa ON sa.id=sd.admission_id LEFT JOIN v00_email.send_observations so ON so.dispatch_id=sd.id WHERE sd.address_digest=c.address_digest),'[]'::jsonb),
 'dependency',CASE WHEN c.actor_id IS NULL THEN NULL ELSE v00_session.snapshot(c.actor_id) END)
FROM v00_email.contexts c LEFT JOIN v00_email.directory di ON di.address_digest=c.address_digest LEFT JOIN v00_email.materials m ON m.context_id=c.id WHERE c.id=cid
$$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_email FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_email.snapshot(uuid) TO v00_email_observer;
COMMIT;
