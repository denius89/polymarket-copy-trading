\set ON_ERROR_STOP on
BEGIN READ ONLY;
DO $$ DECLARE role_name text; function_name text; table_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['v00_email_ingress','v00_email_executor','v00_email_witness','v00_email_observer'] LOOP
    FOREACH function_name IN ARRAY ARRAY['v00_email.recover(jsonb)',
      'v00_email.plan_email_before_recovery_quota(jsonb)','v00_email.plan_totp_before_recovery_quota(jsonb)',
      'v00_email.recovery_access(jsonb)','v00_email.recovery_admission_guard(jsonb)',
      'v00_email.record_recovery_replay(jsonb,jsonb)','v00_session.recover(jsonb)','v00_upstream.recover(jsonb)'] LOOP
      IF has_function_privilege(role_name,function_name,'EXECUTE') THEN RAISE EXCEPTION 'raw recovery capability exposed'; END IF;
    END LOOP;
    FOREACH table_name IN ARRAY ARRAY['recovery_quota_scopes','recovery_quota_admissions','recovery_attempts','recovery_uses','recovery_replay_guards'] LOOP
      IF has_table_privilege(role_name,'v00_email.'||table_name,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') THEN
        RAISE EXCEPTION 'direct recovery table capability exposed';
      END IF;
    END LOOP;
    FOREACH function_name IN ARRAY ARRAY['recovery_admit','recovery_seal','recovery_target','recovery_once','recover_completion_replay'] LOOP
      IF has_function_privilege(role_name,'v00_email.'||function_name||'(jsonb)','EXECUTE') IS DISTINCT FROM
        ((role_name='v00_email_ingress' AND function_name IN ('recovery_admit','recovery_seal')) OR
         (role_name='v00_email_executor' AND function_name IN ('recovery_target','recovery_once','recover_completion_replay'))) THEN
        RAISE EXCEPTION 'unexpected narrow recovery capability';
      END IF;
    END LOOP;
    IF has_function_privilege(role_name,'v00_email.recovery_snapshot(uuid)','EXECUTE') IS DISTINCT FROM (role_name='v00_email_observer') THEN
      RAISE EXCEPTION 'incorrect recovery observer capability';
    END IF;
  END LOOP;
  IF NOT has_function_privilege('v00_email_ingress','v00_email.recovery_admit(jsonb)','EXECUTE')
    OR NOT has_function_privilege('v00_email_ingress','v00_email.recovery_seal(jsonb)','EXECUTE')
    OR has_function_privilege('v00_email_executor','v00_email.recovery_admit(jsonb)','EXECUTE')
    OR has_function_privilege('v00_email_executor','v00_email.recovery_seal(jsonb)','EXECUTE')
    OR has_function_privilege('v00_email_ingress','v00_email.recovery_once(jsonb)','EXECUTE')
    OR NOT has_function_privilege('v00_email_executor','v00_email.recovery_once(jsonb)','EXECUTE')
    OR NOT has_function_privilege('v00_email_executor','v00_email.recovery_target(jsonb)','EXECUTE')
    OR NOT has_function_privilege('v00_email_executor','v00_email.recover_completion_replay(jsonb)','EXECUTE')
    OR NOT has_function_privilege('v00_email_executor','v00_email.plan_email(jsonb)','EXECUTE')
    OR NOT has_function_privilege('v00_email_executor','v00_email.plan_totp(jsonb)','EXECUTE') THEN
    RAISE EXCEPTION 'incorrect recovery role matrix';
  END IF;
END $$;
SELECT 'recovery_privilege_matrix_ok';
ROLLBACK;
