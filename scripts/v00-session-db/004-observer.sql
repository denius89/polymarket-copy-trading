\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_session_owner;
CREATE FUNCTION v00_session.snapshot(actor uuid) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
SELECT jsonb_build_object(
 'actor_id',a.id,'fixed_time',v00_session.utc(a.fixed_time),'blocked',a.blocked,
 'contexts',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',c.id,'expires_at',v00_session.utc(c.expires_at),
   'revoked_at',v00_session.utc(c.revoked_at),'completed_login_id',c.completed_login_id,'completed_operation_id',c.completed_operation_id) ORDER BY c.id)
   FROM v00_session.contexts c WHERE c.actor_id=a.id),'[]'::jsonb),
 'logins',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',l.id,'context_id',l.context_id,'operation_id',l.operation_id,
   'completed_at',v00_session.utc(l.completed_at),'expires_at',v00_session.utc(l.expires_at),'idle_expires_at',v00_session.utc(l.idle_expires_at),
   'revoked_at',v00_session.utc(l.revoked_at),'deadline',v00_session.utc(w.deadline),'first_confirmed_at',v00_session.utc(w.first_confirmed_at),
   'closed_at',v00_session.utc(w.closed_at),'close_reason',w.close_reason,'secret_present',s.ciphertext IS NOT NULL,
   'secret_row_present',s.login_id IS NOT NULL,'erased_at',v00_session.utc(s.erased_at),
   'credential_present',EXISTS(SELECT 1 FROM v00_session.credentials cr WHERE cr.login_id=l.id)) ORDER BY l.id)
   FROM v00_session.logins l LEFT JOIN v00_session.windows w ON w.login_id=l.id LEFT JOIN v00_session.secrets s ON s.login_id=l.id WHERE l.actor_id=a.id),'[]'::jsonb),
 'results',COALESCE((SELECT jsonb_agg(jsonb_build_object('context_id',r.context_id,'operation_id',r.operation_id,'login_id',r.login_id,
   'resolved_at',v00_session.utc(r.resolved_at),'valid',v00_session.valid_result(r),'result',CASE WHEN v00_session.valid_result(r) THEN r.result ELSE NULL END) ORDER BY r.context_id,r.operation_id)
   FROM v00_session.results r JOIN v00_session.contexts c ON c.id=r.context_id WHERE c.actor_id=a.id),'[]'::jsonb),
 'plans',(SELECT count(*) FROM v00_session.completion_plans p JOIN v00_session.contexts c ON c.id=p.context_id WHERE c.actor_id=a.id),
 'logout_contexts',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',c.id,'target_login_id',c.target_login_id,
   'authorization_login_id',c.authorization_login_id,'source_context_id',c.source_context_id,'created_at',v00_session.utc(c.created_at),
   'expires_at',v00_session.utc(c.expires_at),'revoked_at',v00_session.utc(c.revoked_at)) ORDER BY c.id)
   FROM v00_session.logout_contexts c WHERE c.actor_id=a.id),'[]'::jsonb),
 'logout_results',COALESCE((SELECT jsonb_agg(jsonb_build_object('context_id',r.context_id,'operation_id',r.operation_id,
   'target_login_id',r.target_login_id,'confirmed_at',v00_session.utc(r.confirmed_at),'valid',v00_session.valid_logout_result(r,c)) ORDER BY r.context_id,r.operation_id)
   FROM v00_session.logout_results r JOIN v00_session.logout_contexts c ON c.id=r.context_id WHERE c.actor_id=a.id),'[]'::jsonb),
 'audit',COALESCE((SELECT jsonb_agg(jsonb_build_object('login_id',u.login_id,'kind',u.kind,'recorded_at',v00_session.utc(u.recorded_at),
   'reason',u.reason,'operation_id',u.operation_id) ORDER BY u.ordinal)
   FROM v00_session.audit u JOIN v00_session.logins l ON l.id=u.login_id WHERE l.actor_id=a.id),'[]'::jsonb))
FROM v00_session.actors a WHERE a.id=actor
$$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_session FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_session.snapshot(uuid) TO v00_session_observer;
COMMIT;
