\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_email_owner;
CREATE FUNCTION v00_email.seed_directory(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE row_value jsonb; provider_email text; n integer:=0;
BEGIN
  PERFORM v00_upstream.keys(p,ARRAY['entries']);
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
REVOKE ALL ON FUNCTION v00_email.seed_directory(jsonb) FROM PUBLIC;
COMMIT;
