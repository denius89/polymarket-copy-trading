-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE FUNCTION polygon_live_activity.inner_bound(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE b jsonb;a jsonb;e jsonb;old polygon_live_activity.bound_requests;o polygon_live_activity.operations;st polygon_live_activity.stream;version text;
BEGIN
 IF polygon.exact_keys(p,ARRAY['ingest','expectedSnapshotVersion','evaluations']) IS DISTINCT FROM true OR octet_length(p::text)>4194304
  OR polygon_live_activity.request_shape(p->'ingest','ingest') IS DISTINCT FROM true
  OR COALESCE(p->>'expectedSnapshotVersion' IN('1'),false)=false
  OR jsonb_typeof(p->'expectedSnapshotVersion') IS DISTINCT FROM 'string' OR jsonb_typeof(p->'evaluations') IS DISTINCT FROM 'array'
 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 IF jsonb_array_length(p->'evaluations')>128 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 FOR e IN SELECT value FROM jsonb_array_elements(p->'evaluations') LOOP
  IF polygon.exact_keys(e,ARRAY['transactionHash','logIndex','evidence']) IS DISTINCT FROM true
   OR NOT polygon_live_activity.hash_value(e->'transactionHash') OR NOT polygon_live_activity.uint(e->'logIndex')
   OR polygon_live_activity.evidence_shape(e->'evidence') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(p->'evaluations') x GROUP BY x.value->>'transactionHash',x.value->>'logIndex' HAVING count(*)>1)
 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 b:=p->'ingest';a:=polygon_live_activity.writer_guard(b);IF a->>'http'<>'200' THEN RETURN a;END IF;
 IF polygon_live_activity.bound_state_valid((b->>'sessionId')::uuid) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 SELECT * INTO old FROM polygon_live_activity.bound_requests WHERE session_id=(b->>'sessionId')::uuid AND operation_id=(b->>'operationId')::uuid;
 IF FOUND THEN
  IF old.request IS DISTINCT FROM p THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409);END IF;
  SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=old.session_id AND id=old.operation_id;
  RETURN jsonb_build_object('http',200,'result',o.result);
 END IF;
 IF EXISTS(SELECT FROM polygon_live_activity.operations WHERE session_id=(b->>'sessionId')::uuid AND id=(b->>'operationId')::uuid) THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409);END IF;
 version:='1';
 IF version<>p->>'expectedSnapshotVersion' THEN RETURN polygon.err('VERSION_CONFLICT',409);END IF;
 a:=polygon_live_activity.bound_ingest(b,p->'evaluations');IF a->>'http'<>'200' THEN RETURN a;END IF;
 SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=(b->>'sessionId')::uuid AND id=(b->>'operationId')::uuid;
 IF a#>>'{result,kind}'='ingest' THEN
  IF jsonb_array_length(p->'evaluations')<>(SELECT count(*) FROM polygon_live_activity.observations WHERE session_id=o.session_id AND operation_id=o.id AND classification='accepted')
   OR EXISTS(SELECT FROM jsonb_array_elements(p->'evaluations') x WHERE NOT EXISTS(
    SELECT FROM polygon_live_activity.observations ob WHERE ob.session_id=o.session_id AND ob.operation_id=o.id AND ob.classification='accepted'
     AND ob.transaction_hash=x.value->>'transactionHash' AND ob.log_index=(x.value->>'logIndex')::numeric))
  THEN RAISE EXCEPTION 'BUY evaluation set differs from accepted logs' USING ERRCODE='22023';END IF;
 END IF;
 INSERT INTO polygon_live_activity.bound_requests VALUES(o.id,o.session_id,p,polygon_live_activity.digest('paper-bound-skip-envelope-v1'||chr(10)||p::text),o.created_at);
 RETURN a;
END $$;
