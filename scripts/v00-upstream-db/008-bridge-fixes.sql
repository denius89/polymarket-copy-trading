\set ON_ERROR_STOP on
-- Forward-only corrections after007. No runtime grants or data rewrites.
BEGIN;
SET LOCAL ROLE v00_upstream_owner;
CREATE OR REPLACE FUNCTION v00_upstream.token_transition(uid uuid, fam text, old_token text, new_token text, old_sent timestamptz, new_sent timestamptz)
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
CREATE OR REPLACE FUNCTION v00_upstream.check_bundle() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE r v00_upstream.results;
BEGIN
  SELECT * INTO r FROM v00_upstream.results WHERE context_id=NEW.context_id AND operation_id=NEW.operation_id;
  IF NOT FOUND OR v00_upstream.valid_result(r) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete upstream result'; END IF;
  IF TG_TABLE_NAME IN ('plans','used_steps') AND r.result->>'kind'<>'login_completed' THEN RAISE EXCEPTION 'incomplete upstream completion'; END IF;
  IF NOT EXISTS(SELECT 1 FROM v00_upstream.audit WHERE context_id=r.context_id AND operation_id=r.operation_id) THEN RAISE EXCEPTION 'missing upstream audit'; END IF;
  RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION v00_upstream.check_bundle() FROM PUBLIC;
COMMIT;
