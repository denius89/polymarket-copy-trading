CREATE FUNCTION polygon.activity_read_live_v1(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;s polygon.paper_sessions;st polygon_live_activity.stream;i polygon_live_activity.assignments;
 items jsonb;binding jsonb;after_seq bigint;lim integer;water bigint:=0;next_seq bigint;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 IF polygon.exact_keys(p,ARRAY['auth','session_id','after_sequence','limit']) IS DISTINCT FROM true
 OR NOT polygon_live_activity.uuid_value(p->'session_id') OR NOT polygon_live_activity.uint(p->'after_sequence')
 OR jsonb_typeof(p->'limit') IS DISTINCT FROM 'number' OR (p->>'limit' ~ '^[0-9]{1,3}$') IS DISTINCT FROM true
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 IF (p->>'after_sequence')::numeric>9223372036854775807 OR (p->>'limit')::integer NOT BETWEEN 1 AND 100 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 after_seq:=(p->>'after_sequence')::bigint;lim:=(p->>'limit')::integer;
 a:=polygon.guard(p->'auth');IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=(p->>'session_id')::uuid AND user_id=(a->>'user_id')::uuid;
 IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 IF polygon.session_valid(s.id) IS DISTINCT FROM true OR NOT EXISTS(
 SELECT FROM polygon_live_activity.installation x JOIN polygon_live.installation l ON l.database_name=x.database_name AND l.operator_run_id=x.run_id WHERE x.database_name=current_database())
 THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 SELECT * INTO i FROM polygon_live_activity.assignments WHERE session_id=s.id;
 SELECT * INTO st FROM polygon_live_activity.stream WHERE session_id=s.id;
 IF i.session_id IS NULL THEN
  IF st.session_id IS NOT NULL OR EXISTS(SELECT FROM polygon_live_activity.operations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.observations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.decisions WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.calls WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.bound_requests WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.evaluations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.conflicts WHERE session_id=s.id)
  THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 ELSE
  IF polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true
  OR polygon_live_activity.calls_valid(s.id) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  binding:=jsonb_build_object('streamId',i.stream_id,'venueCode','polymarket','catalogSourceId',i.source_id,'traderId',i.trader_id,
  'traderRevisionId',i.revision_id,'externalTraderId',i.owner_address,'bindingRevision',i.binding_revision::text);
 END IF;
 water:=COALESCE(st.high_watermark,0);
 IF after_seq>water THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT COALESCE(jsonb_agg(x.body ORDER BY x.sequence),'[]'),COALESCE(max(x.sequence),after_seq) INTO items,next_seq FROM (
 SELECT ob.sequence,polygon_live_activity.item(ob,d) AS body FROM polygon_live_activity.observations ob
 JOIN polygon_live_activity.decisions d ON d.observation_id=ob.id AND d.session_id=ob.session_id AND d.sequence=ob.sequence
 WHERE ob.session_id=s.id AND ob.sequence>after_seq AND ob.sequence<=water ORDER BY ob.sequence LIMIT lim) x;
 RETURN jsonb_build_object('http',200,'binding',binding,'observation',jsonb_build_object('status',COALESCE(st.status,'not_armed'),
 'armedAt',CASE WHEN st.armed_at IS NULL THEN NULL ELSE v00_session.utc(st.armed_at) END,
 'lastObservedAt',CASE WHEN st.last_observed_at IS NULL THEN NULL ELSE v00_session.utc(st.last_observed_at) END,'completeness','unproven'),
 'items',items,'page',jsonb_build_object('afterSequence',after_seq::text,'nextAfterSequence',next_seq::text,'highWatermark',water::text,'hasMore',next_seq<water),
 'session',polygon.session_body(s));
END $$;
