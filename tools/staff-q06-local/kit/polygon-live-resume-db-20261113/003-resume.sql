CREATE FUNCTION polygon_live_activity.inner_resume(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE checked jsonb;st polygon_live_activity.stream;prior polygon_live_activity.operations;
 sid uuid;t timestamptz;result jsonb;
BEGIN
 IF polygon_live_activity.request_shape(p,'resume') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 checked:=polygon_live_activity.writer_guard(p);IF checked->>'http'<>'200' THEN RETURN checked; END IF;
 checked:=polygon_live_activity.old_result(p,'resume');IF checked IS NOT NULL THEN RETURN checked; END IF;
 sid:=(p->>'sessionId')::uuid;
 IF NOT EXISTS(SELECT FROM polygon_live_activity.resume_patch patch
   JOIN polygon_live_activity.assignments bind ON bind.session_id=patch.session_id
   WHERE patch.session_id=sid AND patch.run_id=(p->>'runId')::uuid
   AND patch.writer_oid=bind.writer_oid AND patch.writer_role=bind.writer_role)
 THEN RETURN polygon.err('ACCESS_DENIED',403); END IF;
 IF polygon_live_activity.new_admission(sid) IS DISTINCT FROM true THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 SELECT * INTO st FROM polygon_live_activity.stream WHERE session_id=sid;
 IF st.session_id IS NULL OR st.status<>'stopped'
 OR st.last_operation_id::text IS DISTINCT FROM p->>'expectedLastOperationId'
 OR st.checkpoint IS DISTINCT FROM p->'expectedCheckpoint'
 OR st.high_watermark::text IS DISTINCT FROM p->>'expectedHighWatermark'
 THEN RETURN polygon.err('VERSION_CONFLICT',409); END IF;
 SELECT * INTO prior FROM polygon_live_activity.operations WHERE session_id=sid AND id=st.last_operation_id;
 t:=date_trunc('milliseconds',clock_timestamp());
 IF prior.id IS NULL OR prior.kind<>'stop' OR prior.request->>'status' IS DISTINCT FROM 'stopped'
 OR prior.result->>'status' IS DISTINCT FROM 'stopped' OR prior.created_at>t
 THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 UPDATE polygon_live_activity.stream SET status='observing',last_operation_id=(p->>'operationId')::uuid WHERE session_id=sid;
 result:=jsonb_build_object('operationId',p->'operationId','kind','resume','sessionId',p->'sessionId',
 'resumedAt',v00_session.utc(t),'checkpoint',st.checkpoint,'highWatermark',st.high_watermark::text);
 RETURN polygon_live_activity.save_result(p,'resume',result,t);
END $$;
CREATE FUNCTION polygon.live_activity_resume(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT polygon_live_activity.dispatch(p,'resume')
$$;
REVOKE ALL ON FUNCTION polygon_live_activity.inner_resume(jsonb),polygon.live_activity_resume(jsonb) FROM PUBLIC,polygon_executor;
