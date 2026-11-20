-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE FUNCTION polygon_live_activity.old_result(p jsonb,k text) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE o polygon_live_activity.operations;
BEGIN
 SELECT * INTO o FROM polygon_live_activity.operations WHERE id=(p->>'operationId')::uuid AND session_id=(p->>'sessionId')::uuid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF o.kind<>k OR o.request IS DISTINCT FROM p OR o.request_digest<>polygon_live_activity.digest(k||chr(10)||p::text)
 THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409); END IF;
 RETURN jsonb_build_object('http',200,'result',o.result);
END $$;
CREATE FUNCTION polygon_live_activity.new_admission(sid uuid) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM polygon.paper_controls WHERE singleton AND enabled)
  AND EXISTS(SELECT FROM polygon.paper_sessions WHERE id=sid AND lifecycle='active' AND evaluation_deadline_at>clock_timestamp())
$$;
CREATE FUNCTION polygon_live_activity.save_result(p jsonb,k text,r jsonb,t timestamptz) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 INSERT INTO polygon_live_activity.operations VALUES((p->>'operationId')::uuid,(p->>'sessionId')::uuid,
  (SELECT COALESCE(max(ordinal),0)+1 FROM polygon_live_activity.operations WHERE session_id=(p->>'sessionId')::uuid),k,p,
  polygon_live_activity.digest(k||chr(10)||p::text),r,t);
 RETURN jsonb_build_object('http',200,'result',r);
END $$;
CREATE FUNCTION polygon_live_activity.inner_arm(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; t timestamptz; sid uuid; r jsonb;
BEGIN
 IF polygon_live_activity.request_shape(p,'arm') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon_live_activity.writer_guard(p); IF a->>'http'<>'200' THEN RETURN a; END IF;
 a:=polygon_live_activity.old_result(p,'arm'); IF a IS NOT NULL THEN RETURN a; END IF;
 IF EXISTS(SELECT FROM polygon_live_activity.stream WHERE session_id=(p->>'sessionId')::uuid) THEN RETURN polygon.err('VERSION_CONFLICT',409); END IF;
 sid:=(p->>'sessionId')::uuid; t:=date_trunc('milliseconds',clock_timestamp());
 IF NOT polygon_live_activity.new_admission(sid) THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 IF (p->>'baselineReceivedAt')::timestamptz>t OR (p->>'baselineReceivedAt')::timestamptz<t-interval '30 seconds'
  OR (p->>'baselineReceivedAt')::timestamptz<(SELECT started_at FROM polygon.paper_sessions WHERE id=sid)
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 INSERT INTO polygon_live_activity.stream(session_id,baseline,armed_at,arm_operation_id,last_operation_id,checkpoint,status)
 VALUES(sid,p->'baseline',t,(p->>'operationId')::uuid,(p->>'operationId')::uuid,polygon_live_activity.cp(p->'baseline'),'observing');
 r:=jsonb_build_object('operationId',p->'operationId','kind','arm','sessionId',p->'sessionId','armedAt',v00_session.utc(t),'checkpoint',polygon_live_activity.cp(p->'baseline'));
 RETURN polygon_live_activity.save_result(p,'arm',r,t);
END $$;
CREATE FUNCTION polygon_live_activity.inner_lookup(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;o polygon_live_activity.operations;
BEGIN
 IF polygon_live_activity.request_shape(p,'lookup') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon_live_activity.writer_guard(p); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO o FROM polygon_live_activity.operations WHERE id=(p->>'operationId')::uuid AND session_id=(p->>'sessionId')::uuid;
 IF NOT FOUND THEN RETURN jsonb_build_object('http',200,'status','not_found','result',NULL); END IF;
 RETURN jsonb_build_object('http',200,'status','committed','result',o.result);
END $$;
CREATE FUNCTION polygon_live_activity.inner_stop(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;st polygon_live_activity.stream;t timestamptz:=date_trunc('milliseconds',clock_timestamp());r jsonb;
BEGIN
 IF polygon_live_activity.request_shape(p,'stop') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon_live_activity.writer_guard(p); IF a->>'http'<>'200' THEN RETURN a; END IF;
 a:=polygon_live_activity.old_result(p,'stop'); IF a IS NOT NULL THEN RETURN a; END IF;
 SELECT * INTO st FROM polygon_live_activity.stream WHERE session_id=(p->>'sessionId')::uuid;
 IF st.session_id IS NULL OR st.status<>'observing' THEN RETURN polygon.err('VERSION_CONFLICT',409); END IF;
 UPDATE polygon_live_activity.stream SET status=p->>'status',last_operation_id=(p->>'operationId')::uuid WHERE session_id=(p->>'sessionId')::uuid;
 r:=jsonb_build_object('operationId',p->'operationId','kind','stop','sessionId',p->'sessionId','status',p->'status');
 RETURN polygon_live_activity.save_result(p,'stop',r,t);
END $$;
