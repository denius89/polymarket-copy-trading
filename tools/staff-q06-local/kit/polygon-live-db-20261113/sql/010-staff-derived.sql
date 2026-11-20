-- Existing staff target scopes and audit evidence retained. Initial audit is linked to snapshot1.
CREATE OR REPLACE FUNCTION polygon.pilot_staff_snapshot(sid uuid) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; sn polygon.session_snapshots; au polygon.audit_events; body jsonb; pc polygon.profile;
BEGIN
 SELECT * INTO STRICT pc FROM polygon.profile WHERE singleton FOR SHARE;
 IF NOT pc.enabled OR pc.environment<>'shadow-polygon-synthetic-v1' THEN RAISE EXCEPTION 'paper unavailable' USING ERRCODE='55000'; END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF polygon.session_valid(sid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete paper source' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=s.current_snapshot_version;
 SELECT * INTO STRICT au FROM polygon.audit_events WHERE session_id=s.id;
 IF s.current_settings_revision_id<>sn.settings_revision_id OR au.snapshot_id IS DISTINCT FROM (SELECT id FROM polygon.session_snapshots WHERE session_id=s.id AND version=1) OR au.receipt_id<>s.start_receipt_id
 OR au.actor_user_id<>s.user_id OR au.kind<>'paper_session.started' OR au.outcome<>'succeeded' OR au.created_at<>s.started_at
 OR sn.data_origin NOT IN('synthetic','public_api') OR sn.content_state<>'EMPTY' OR sn.coverage_state<>'no_trade_data'
 THEN RAISE EXCEPTION 'inconsistent paper projection' USING ERRCODE='23514'; END IF;
 body:=polygon.session_body(s);
 RETURN jsonb_build_object('user_id',s.user_id,'session_id',s.id,'snapshot_id',sn.id,'snapshot_version',sn.version,
  'settings_revision_id',sn.settings_revision_id,'session',body,
  'event',jsonb_build_object('eventId',au.id,'sessionId',s.id,'kind',au.kind,'occurredAt',v00_session.utc(au.created_at)));
END $$;
