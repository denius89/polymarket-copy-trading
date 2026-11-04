\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_upstream_owner;
-- Operator-only, fresh rows only. Does not create or change provider identities/seeds.
CREATE FUNCTION v00_upstream.seed_fixture(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE sub jsonb; ctx jsonb; actor uuid; factor uuid; provider_factor uuid;
BEGIN
  IF jsonb_typeof(p)<>'object' OR (SELECT array_agg(k ORDER BY k) FROM jsonb_object_keys(p) k)<>ARRAY['contexts','subjects']
    OR jsonb_typeof(p->'subjects')<>'array' OR jsonb_typeof(p->'contexts')<>'array' THEN RAISE EXCEPTION 'invalid fixture shape'; END IF;
  FOR sub IN SELECT value FROM jsonb_array_elements(p->'subjects') LOOP
    IF (SELECT array_agg(k ORDER BY k) FROM jsonb_object_keys(sub) k) IS DISTINCT FROM
      ARRAY['actor_id','factor_version','fixed_time','provider_factor_id','provider_user_id'] THEN RAISE EXCEPTION 'invalid fixture subject'; END IF;
    actor:=(sub->>'actor_id')::uuid; factor:=(sub->>'factor_version')::uuid; provider_factor:=(sub->>'provider_factor_id')::uuid;
    IF actor IS NULL OR sub->>'provider_user_id' IS NULL OR (factor IS NULL)<>(provider_factor IS NULL) THEN RAISE EXCEPTION 'invalid fixture binding'; END IF;
    INSERT INTO v00_session.actors(id,fixed_time) VALUES(actor,(sub->>'fixed_time')::timestamptz);
    INSERT INTO v00_upstream.subjects(actor_id,provider_user_id) VALUES(actor,(sub->>'provider_user_id')::uuid);
    -- Subject allowlist now exists; provider RLS can reveal only this supplied subject.
    IF NOT EXISTS(SELECT 1 FROM auth.users WHERE id=(sub->>'provider_user_id')::uuid AND email_confirmed_at IS NOT NULL) THEN RAISE EXCEPTION 'provider fixture user unavailable'; END IF;
    IF factor IS NOT NULL THEN
      IF NOT EXISTS(SELECT 1 FROM auth.mfa_factors WHERE id=provider_factor AND user_id=(sub->>'provider_user_id')::uuid AND factor_type::text='totp' AND status::text='verified') THEN
        RAISE EXCEPTION 'provider fixture factor unavailable';
      END IF;
      INSERT INTO v00_upstream.factors(id,actor_id,provider_factor_id,active) VALUES(factor,actor,provider_factor,true);
      UPDATE v00_upstream.subjects SET current_factor=factor WHERE actor_id=actor;
    END IF;
  END LOOP;
  FOR ctx IN SELECT value FROM jsonb_array_elements(p->'contexts') LOOP
    PERFORM v00_upstream.keys(ctx,ARRAY['id','actor_id','proof_digest','email_challenge_id','expires_at','login_expires_at','idle_expires_at']);
    IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(p->'subjects') z WHERE z->>'actor_id'=ctx->>'actor_id') THEN RAISE EXCEPTION 'foreign fixture actor'; END IF;
    INSERT INTO v00_session.contexts(id,actor_id,proof_digest,expires_at,login_expires_at,idle_expires_at)
      VALUES((ctx->>'id')::uuid,(ctx->>'actor_id')::uuid,ctx->>'proof_digest',(ctx->>'expires_at')::timestamptz,(ctx->>'login_expires_at')::timestamptz,(ctx->>'idle_expires_at')::timestamptz);
    INSERT INTO v00_upstream.contexts(id,actor_id,email_challenge_id) VALUES((ctx->>'id')::uuid,(ctx->>'actor_id')::uuid,(ctx->>'email_challenge_id')::uuid);
  END LOOP;
  RETURN jsonb_build_object('subjects_inserted',jsonb_array_length(p->'subjects'),'contexts_inserted',jsonb_array_length(p->'contexts'));
END $$;
REVOKE ALL ON FUNCTION v00_upstream.seed_fixture(jsonb) FROM PUBLIC;
COMMIT;
