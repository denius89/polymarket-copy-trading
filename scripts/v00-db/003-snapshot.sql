\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_db_owner;
CREATE FUNCTION v00_db.snapshot(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = pg_catalog AS $$
DECLARE tables jsonb := '{}'::jsonb; rows jsonb; name text;
BEGIN
  -- Only synthetic probe tables. No provider token, cookie, email, factor seed or key.
  FOREACH name IN ARRAY ARRAY['actors','factors','contexts','challenges','totp_results','used_steps','email_confirmations','email_outcomes'] LOOP
    EXECUTE format('SELECT COALESCE(jsonb_agg(r ORDER BY r::text),''[]''::jsonb) FROM (SELECT to_jsonb(t) r FROM v00_db.%I t) q',name) INTO rows;
    tables := tables || jsonb_build_object(name,rows);
  END LOOP;
  SELECT COALESCE(jsonb_agg(to_jsonb(q) ORDER BY operation_id),'[]'::jsonb) INTO rows FROM
    (SELECT operation_id,user_id,fingerprint,sealed_at FROM v00_db.email_seals) q;
  tables := tables || jsonb_build_object('email_seals_redacted',rows);
  SELECT COALESCE(jsonb_agg(to_jsonb(q) ORDER BY operation_id,session_id),'[]'::jsonb) INTO rows FROM
    (SELECT s.operation_id,s.user_id,u.email_confirmed_at,x.id AS session_id
      FROM v00_db.email_seals s LEFT JOIN auth.users u ON u.id=s.user_id
      LEFT JOIN auth.sessions x ON x.user_id=s.user_id) q;
  tables := tables || jsonb_build_object('provider_observations',rows);
  RETURN jsonb_build_object('profile','v00-db-snapshot-v1','captured_at',clock_timestamp(),
    'wal_lsn',CASE WHEN pg_is_in_recovery() THEN pg_last_wal_replay_lsn()::text ELSE pg_current_wal_lsn()::text END,'is_recovery',pg_is_in_recovery(),
    'server_version',current_setting('server_version'),'tables',tables,
    'integrity',jsonb_build_object(
      'used_step_wrong_result',(SELECT count(*) FROM v00_db.used_steps s JOIN v00_db.totp_results r USING(context_id,operation_id)
        WHERE r.result->>'kind'<>'totp_consumed' OR NOT (r.result->'consumed_steps' @> to_jsonb(ARRAY[s.step]))),
      'success_step_count_mismatch',(SELECT count(*) FROM v00_db.totp_results r WHERE r.result->>'kind'='totp_consumed'
        AND jsonb_array_length(r.result->'consumed_steps')<>(SELECT count(*) FROM v00_db.used_steps s WHERE s.context_id=r.context_id AND s.operation_id=r.operation_id)),
      'outcome_wrong_txid',(SELECT count(*) FROM v00_db.email_outcomes o JOIN v00_db.email_confirmations c USING(operation_id) WHERE o.provider_txid<>c.provider_txid),
      'confirmation_wrong_user',(SELECT count(*) FROM v00_db.email_confirmations c JOIN v00_db.email_seals s USING(operation_id) WHERE c.user_id<>s.user_id),
      'outcome_missing_provider_session',(SELECT count(*) FROM v00_db.email_outcomes o JOIN v00_db.email_seals s USING(operation_id)
        LEFT JOIN auth.sessions x ON x.id=o.session_id AND x.user_id=s.user_id WHERE x.id IS NULL)
    ));
END $$;
REVOKE ALL ON FUNCTION v00_db.snapshot(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_db.snapshot(jsonb) TO v00_db_observer;
RESET ROLE;
GRANT SELECT(id,user_id) ON auth.sessions TO v00_db_owner;
COMMIT;
