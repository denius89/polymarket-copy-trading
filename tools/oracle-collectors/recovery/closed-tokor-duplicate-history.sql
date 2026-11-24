-- Apply to the dedicated closed Tokor database. Pass -v revert=true to restore the previous body.
\set ON_ERROR_STOP on
\if :{?revert}
\else
  \set revert false
\endif
BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '4s';
SELECT set_config('tokor.revert_history_patch', :'revert', true);
DO $patch$
DECLARE
    old_hash constant text := '4e69be6ef36146db3d1a8c3df1cd566f';
    new_hash constant text := '36afce24c2ff1067ed080833ed97beb5';
    old_check constant text := 'IF polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true
 OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true';
    new_check constant text := 'IF polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true';
    guard_oid constant oid := 'polygon_live_activity.writer_guard(jsonb)'::regprocedure;
    original text := pg_get_functiondef(guard_oid);
    reverting boolean := current_setting('tokor.revert_history_patch')::boolean;
    target_hash text := CASE WHEN reverting THEN old_hash ELSE new_hash END;
    definition text;
BEGIN
    IF current_database() <> 'shadow_v00' OR NOT EXISTS (
        SELECT FROM polygon_live_activity.assignments
        WHERE session_id = '1c6d9f24-0f84-4a13-82f2-e712ff6919cf'
          AND owner_address = '0xa19cbababc312f9df185e49d7004c249ed1ade6b'
    ) THEN
        RAISE EXCEPTION 'closed Tokor session mismatch';
    END IF;
    IF md5(pg_get_functiondef('polygon_live_activity.bound_state_valid(uuid)'::regprocedure))
            <> '98ac915d4b726892c275049a50b8b2a0'
       OR md5(pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure))
            <> '75695dab148d25f20bc1e4ffd728a3e7' THEN
        RAISE EXCEPTION 'history validators changed';
    END IF;
    IF md5(original) = target_hash THEN
        RETURN;
    END IF;
    IF md5(original) <> (CASE WHEN reverting THEN new_hash ELSE old_hash END) THEN
        RAISE EXCEPTION 'closed writer guard changed';
    END IF;
    definition := CASE WHEN reverting THEN replace(original, new_check, old_check)
                       ELSE replace(original, old_check, new_check) END;
    IF md5(definition) <> target_hash THEN
        RAISE EXCEPTION 'writer guard replacement mismatch';
    END IF;
    EXECUTE definition;
    IF md5(pg_get_functiondef(guard_oid)) <> target_hash THEN
        RAISE EXCEPTION 'installed writer guard mismatch';
    END IF;
END
$patch$;
COMMIT;
