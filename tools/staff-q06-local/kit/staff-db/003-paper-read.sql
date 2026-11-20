\set ON_ERROR_STOP on
-- New disposable run only, after the pinned real polygon source is installed.
BEGIN;
SET LOCAL ROLE polygon_owner;
ALTER TABLE polygon.session_snapshots ADD UNIQUE(session_id,id,version,settings_revision_id);
GRANT REFERENCES ON polygon.users,polygon.paper_sessions,polygon.session_snapshots TO pilot_staff_owner;
CREATE FUNCTION polygon.pilot_staff_snapshot(sid uuid) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; sn polygon.session_snapshots; au polygon.audit_events; body jsonb; pc polygon.profile;
BEGIN
 SELECT * INTO STRICT pc FROM polygon.profile WHERE singleton FOR SHARE;
 IF NOT pc.enabled OR pc.environment<>'shadow-polygon-synthetic-v1' THEN RAISE EXCEPTION 'paper unavailable' USING ERRCODE='55000'; END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF polygon.session_valid(sid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete paper source' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=s.current_snapshot_version;
 SELECT * INTO STRICT au FROM polygon.audit_events WHERE session_id=s.id;
 IF s.current_settings_revision_id<>sn.settings_revision_id OR au.snapshot_id<>sn.id OR au.receipt_id<>s.start_receipt_id
 OR au.actor_user_id<>s.user_id OR au.kind<>'paper_session.started' OR au.outcome<>'succeeded' OR au.created_at<>s.started_at
 OR sn.data_origin<>'synthetic' OR sn.content_state<>'EMPTY' OR sn.coverage_state<>'no_trade_data'
 THEN RAISE EXCEPTION 'inconsistent paper projection' USING ERRCODE='23514'; END IF;
 body:=polygon.session_body(s);
 RETURN jsonb_build_object('user_id',s.user_id,'session_id',s.id,'snapshot_id',sn.id,'snapshot_version',sn.version,
  'settings_revision_id',sn.settings_revision_id,'session',body,
  'event',jsonb_build_object('eventId',au.id,'sessionId',s.id,'kind',au.kind,'occurredAt',v00_session.utc(au.created_at)));
END $$;
REVOKE ALL ON FUNCTION polygon.pilot_staff_snapshot(uuid) FROM PUBLIC;
GRANT USAGE ON SCHEMA polygon TO pilot_staff_owner;
GRANT EXECUTE ON FUNCTION polygon.pilot_staff_snapshot(uuid) TO pilot_staff_owner;
RESET ROLE;
SET LOCAL ROLE pilot_staff_owner;
ALTER TABLE pilot_staff.targets ADD FOREIGN KEY(user_id) REFERENCES polygon.users(id);
ALTER TABLE pilot_staff.targets ADD FOREIGN KEY(session_id,user_id) REFERENCES polygon.paper_sessions(id,user_id);
ALTER TABLE pilot_staff.read_evidence ADD FOREIGN KEY(session_id,snapshot_id,snapshot_version,settings_revision_id)
 REFERENCES polygon.session_snapshots(session_id,id,version,settings_revision_id);
CREATE FUNCTION pilot_staff._evidence(aid uuid,target pilot_staff.targets,b jsonb,group_name text) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE e pilot_staff.read_evidence;
BEGIN
 SELECT * INTO e FROM pilot_staff.read_evidence WHERE audit_id=aid AND session_id=target.session_id AND granted_group=group_name;
 IF FOUND THEN
  IF ROW(e.target_ordinal,e.snapshot_id,e.snapshot_version,e.settings_revision_id) IS DISTINCT FROM
   ROW(target.ordinal,(b->>'snapshot_id')::uuid,(b->>'snapshot_version')::bigint,(b->>'settings_revision_id')::uuid)
  THEN RAISE EXCEPTION 'evidence conflict' USING ERRCODE='23514'; END IF;
 ELSE
  INSERT INTO pilot_staff.read_evidence VALUES(aid,target.ordinal,target.session_id,(b->>'snapshot_id')::uuid,(b->>'snapshot_version')::bigint,(b->>'settings_revision_id')::uuid,group_name);
 END IF;
END $$;
CREATE FUNCTION pilot_staff._source(target pilot_staff.targets) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE b jsonb;
BEGIN
 IF target.session_id IS NULL THEN PERFORM pilot_staff._fail('RECORD_UNAVAILABLE',503); END IF;
 b:=polygon.pilot_staff_snapshot(target.session_id);
 IF b IS NULL OR b->>'user_id'<>target.user_id::text OR b->>'session_id'<>target.session_id::text
 THEN PERFORM pilot_staff._fail('RECORD_UNAVAILABLE',503); END IF;
 RETURN b;
END $$;
CREATE FUNCTION pilot_staff._read_paper(route text,p jsonb,l pilot_staff.logins) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE target pilot_staff.targets; b jsonb; aid uuid; group_name text; groups text[]; rows jsonb:='[]';
BEGIN
 IF NOT EXISTS(SELECT FROM pilot_staff.assignments WHERE principal_id=l.principal_id AND enabled AND
  scopes @> CASE route WHEN 'session_read' THEN ARRAY['session.summary','session.settings','session.financial_snapshot']
  WHEN 'session_list' THEN ARRAY['pilot.sessions.list'] ELSE ARRAY['pilot.session.events'] END)
 THEN PERFORM pilot_staff._fail('RESOURCE_NOT_FOUND',404); END IF;
 IF route='session_list' THEN
  IF (SELECT count(*) FROM pilot_staff.targets WHERE session_id IS NOT NULL)<>2 THEN PERFORM pilot_staff._fail('RECORD_UNAVAILABLE',503); END IF;
  aid:=pilot_staff._audit((p->>'request_id')::uuid,route,l.principal_id,l.id,NULL,NULL,NULL,NULL);
  FOR target IN SELECT * FROM pilot_staff.targets ORDER BY ordinal LOOP
   b:=pilot_staff._source(target);
   rows:=rows||jsonb_build_array(jsonb_build_object('displayLabel',target.display_label,'sessionId',target.session_id));
   PERFORM pilot_staff._evidence(aid,target,b,'pilot.sessions.list');
  END LOOP;
  RETURN jsonb_build_object('sessions',rows);
 END IF;
 SELECT * INTO target FROM pilot_staff.targets WHERE session_id=(p->>'session_id')::uuid;
 IF NOT FOUND THEN PERFORM pilot_staff._fail('RESOURCE_NOT_FOUND',404); END IF;
 b:=pilot_staff._source(target);
 aid:=pilot_staff._audit((p->>'request_id')::uuid,route,l.principal_id,l.id,NULL,NULL,target.session_id,(b->>'snapshot_version')::bigint);
 groups:=CASE route WHEN 'session_read' THEN ARRAY['session.summary','session.settings','session.financial_snapshot'] ELSE ARRAY['pilot.session.events'] END;
 FOREACH group_name IN ARRAY groups LOOP
  PERFORM pilot_staff._evidence(aid,target,b,group_name);
 END LOOP;
 IF route='session_events' THEN RETURN jsonb_build_object('events',jsonb_build_array(b->'event')); END IF;
 RETURN jsonb_build_object('session',b->'session','restrictedGroups',jsonb_build_array('user.minimal_context'));
END $$;
COMMIT;
