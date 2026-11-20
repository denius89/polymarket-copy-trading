-- Current direct LOGIN/OID binding, then global gates, then this session, then stream.
-- Session-row lock is also the assignment/empty-completion exclusion boundary.
CREATE FUNCTION polygon_live_activity.writer_guard(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE i polygon_live_activity.assignments;g v00_upstream.gate;pr polygon.profile;s polygon.paper_sessions;r pg_roles;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 SELECT * INTO i FROM polygon_live_activity.assignments WHERE session_id=(p->>'sessionId')::uuid;
 SELECT * INTO r FROM pg_roles WHERE rolname=session_user;
 IF i.session_id IS NULL OR r.oid IS DISTINCT FROM i.writer_oid OR r.rolname IS DISTINCT FROM i.writer_role
 OR polygon_live_activity.role_valid(r.oid) IS DISTINCT FROM true
 OR current_database()<>i.database_name OR p->>'runId'<>i.run_id::text
 THEN RETURN polygon.err('ACCESS_DENIED',403); END IF;
 SELECT * INTO g FROM v00_upstream.gate WHERE singleton FOR SHARE;
 SELECT * INTO pr FROM polygon.profile WHERE singleton FOR SHARE;
 IF g.singleton IS NULL OR pr.singleton IS NULL OR NOT g.is_open OR NOT g.clock_trusted OR NOT pr.enabled
 THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 PERFORM 1 FROM polygon.paper_controls WHERE singleton FOR SHARE;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=i.session_id AND user_id=i.user_id FOR UPDATE;
 IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 IF ROW(s.source_id,s.venue_id,s.trader_id,s.trader_revision_id) IS DISTINCT FROM ROW(i.source_id,i.venue_id,i.trader_id,i.revision_id)
 OR polygon.session_valid(s.id) IS DISTINCT FROM true OR polygon_live.public_valid(s.id) IS DISTINCT FROM true
 OR NOT EXISTS(SELECT FROM polygon_live_activity.installation x WHERE x.database_name=i.database_name AND x.run_id=i.run_id)
 THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 PERFORM 1 FROM polygon_live_activity.stream WHERE session_id=s.id FOR UPDATE;
 IF polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true
 OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true
 OR polygon_live_activity.calls_valid(s.id) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 RETURN jsonb_build_object('http',200);
END $$;
