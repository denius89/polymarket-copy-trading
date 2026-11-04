\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_upstream_owner;
CREATE FUNCTION v00_upstream.open_gate() RETURNS boolean LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE g v00_upstream.gate;
BEGIN
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton FOR SHARE;
  RETURN g.is_open AND g.clock_trusted;
END $$;
CREATE FUNCTION v00_upstream.logout_prepare(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF NOT v00_upstream.open_gate() THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  RETURN v00_session.logout_prepare(p);
END $$;
CREATE FUNCTION v00_upstream.logout_continue(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF NOT v00_upstream.open_gate() THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  RETURN v00_session.logout_continue(p);
END $$;
CREATE FUNCTION v00_upstream.logout(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF NOT v00_upstream.open_gate() THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  RETURN v00_session.logout(p);
END $$;
CREATE FUNCTION v00_upstream.logout_result(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
  IF NOT v00_upstream.open_gate() THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  RETURN v00_session.logout_result(p);
END $$;
CREATE FUNCTION v00_upstream.snapshot(actor uuid) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
SELECT jsonb_build_object('schema','v00-upstream-snapshot-v1','actor_id',s.actor_id,
  'current_factor',s.current_factor,'failures',s.failures,'paused_until',s.paused_until,
  'gate',(SELECT jsonb_build_object('epoch',epoch,'open',is_open,'clock_trusted',clock_trusted) FROM v00_upstream.gate WHERE singleton),
  'dependency',v00_session.snapshot(actor),
  'contexts',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',c.id,'stage',c.stage,'factor_version',c.factor_version,
    'email_challenge_id',c.email_challenge_id,'totp_challenge_id',c.totp_challenge_id,'totp_issued_at',c.totp_issued_at,'totp_expires_at',c.totp_expires_at) ORDER BY c.id)
    FROM v00_upstream.contexts c WHERE c.actor_id=actor),'[]'::jsonb),
  'admissions',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',a.id,'context_id',a.context_id,'operation_id',a.operation_id,'action',a.action,
    'executor_id',a.executor_id,'epoch',a.epoch,'captured_at',a.captured_at,'deadline_at',a.deadline_at) ORDER BY a.id)
    FROM v00_upstream.admissions a JOIN v00_upstream.contexts c ON c.id=a.context_id WHERE c.actor_id=actor),'[]'::jsonb),
  'results',COALESCE((SELECT jsonb_agg(jsonb_build_object('context_id',r.context_id,'operation_id',r.operation_id,'action',r.action,'login_id',r.login_id,
    'result',CASE WHEN v00_upstream.valid_result(r) THEN r.result ELSE NULL END,'valid',v00_upstream.valid_result(r),'resolved_at',r.resolved_at) ORDER BY r.context_id,r.operation_id)
    FROM v00_upstream.results r JOIN v00_upstream.contexts c ON c.id=r.context_id WHERE c.actor_id=actor),'[]'::jsonb),
  'steps',COALESCE((SELECT jsonb_agg(jsonb_build_object('factor_version',u.factor_version,'step',u.step,'context_id',u.context_id,'operation_id',u.operation_id) ORDER BY u.factor_version,u.step)
    FROM v00_upstream.used_steps u JOIN v00_upstream.factors f ON f.id=u.factor_version WHERE f.actor_id=actor),'[]'::jsonb),
  'plans',COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.context_id) FROM v00_upstream.plans p JOIN v00_upstream.contexts c ON c.id=p.context_id WHERE c.actor_id=actor),'[]'::jsonb),
  'generations',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',g.id,'family',g.family,'state',g.state,'issued_at',g.issued_at,'issuing_txid',g.issuing_txid) ORDER BY g.id)
    FROM v00_upstream.generations g WHERE g.user_id=s.provider_user_id),'[]'::jsonb),
  'email_outcomes',COALESCE((SELECT jsonb_agg(jsonb_build_object('seal_id',es.id,'admission_id',es.admission_id,'generation_id',es.generation_id,
    'family',es.family,'sealed_at',es.sealed_at,'consumption_txid',co.provider_txid,'outcome_txid',eo.provider_txid,'provider_session_id',eo.provider_session_id,'observed_at',eo.observed_at) ORDER BY es.id)
    FROM v00_upstream.email_seals es LEFT JOIN v00_upstream.consumptions co ON co.seal_id=es.id LEFT JOIN v00_upstream.email_outcomes eo ON eo.seal_id=es.id
    WHERE es.user_id=s.provider_user_id),'[]'::jsonb),
  'audit',COALESCE((SELECT jsonb_agg(to_jsonb(u) ORDER BY u.ordinal) FROM v00_upstream.audit u JOIN v00_upstream.contexts c ON c.id=u.context_id WHERE c.actor_id=actor),'[]'::jsonb))
FROM v00_upstream.subjects s WHERE s.actor_id=actor
$$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_upstream FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_upstream.logout_prepare(jsonb),v00_upstream.logout_continue(jsonb),v00_upstream.logout(jsonb),v00_upstream.logout_result(jsonb) TO v00_upstream_executor;
GRANT EXECUTE ON FUNCTION v00_upstream.snapshot(uuid) TO v00_upstream_observer;
COMMIT;
