\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_email_owner;
CREATE FUNCTION v00_email.recovery_snapshot(cid uuid) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
SELECT jsonb_build_object('schema','v00-email-recovery-snapshot-v1','context_id',cid,
  'email',v00_email.snapshot(cid),
  'scope',(SELECT to_jsonb(q) FROM v00_email.recovery_quota_scopes q WHERE q.context_id=cid),
  'admissions',COALESCE((SELECT jsonb_agg((to_jsonb(a)-'executor_proof_digest')||jsonb_build_object(
    'row_sha256',encode(v00_upstream_crypto.digest(convert_to(to_jsonb(a)::text,'UTF8'),'sha256'),'hex')) ORDER BY a.admitted_at,a.admission_token)
    FROM v00_email.recovery_quota_admissions a WHERE a.context_id=cid),'[]'::jsonb),
  'attempts',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY s.sealed_at,s.admission_token)
    FROM v00_email.recovery_attempts s JOIN v00_email.recovery_quota_admissions a USING(admission_token) WHERE a.context_id=cid),'[]'::jsonb),
  'uses',COALESCE((SELECT jsonb_agg(to_jsonb(u) ORDER BY u.entered_at,u.admission_token)
    FROM v00_email.recovery_uses u JOIN v00_email.recovery_quota_admissions a USING(admission_token) WHERE a.context_id=cid),'[]'::jsonb),
  'replay_guards',COALESCE((SELECT jsonb_agg(to_jsonb(g) ORDER BY g.target_txid,g.operation_id)
    FROM v00_email.recovery_replay_guards g WHERE g.context_id=cid),'[]'::jsonb));
$$;
REVOKE ALL ON FUNCTION v00_email.recovery_snapshot(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_email.recovery_snapshot(uuid) TO v00_email_observer;
COMMIT;
