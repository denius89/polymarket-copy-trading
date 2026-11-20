-- Operator-only recovery for the two enrolled, still-empty demo sessions.
-- Install and rehearse in an isolated database before requesting approval for a live gap.
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout='3s';
SET LOCAL ROLE polygon_owner;

CREATE TABLE polygon_buy.demo_fresh_segments (
    session_id uuid NOT NULL REFERENCES polygon.paper_sessions(id),
    operation_id uuid NOT NULL UNIQUE,
    previous_stop uuid NOT NULL,
    previous_checkpoint jsonb NOT NULL,
    previous_watermark bigint NOT NULL,
    next_checkpoint jsonb NOT NULL,
    anchor_observed_at timestamptz NOT NULL,
    anchor_sha256 text NOT NULL CHECK (anchor_sha256 ~ '^[0-9a-f]{64}$'),
    recorded_by name NOT NULL,
    recorded_at timestamptz NOT NULL,
    PRIMARY KEY (session_id, operation_id),
    FOREIGN KEY (session_id, operation_id) REFERENCES polygon_live_activity.operations(session_id,id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TRIGGER immutable_demo_fresh_segment BEFORE UPDATE OR DELETE ON polygon_buy.demo_fresh_segments
  FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_demo_fresh_segment_truncate BEFORE TRUNCATE ON polygon_buy.demo_fresh_segments
  FOR EACH STATEMENT EXECUTE FUNCTION polygon.immutable_row();
REVOKE ALL ON polygon_buy.demo_fresh_segments FROM PUBLIC,polygon_executor;

CREATE FUNCTION polygon_buy.demo_fresh_gap(sid uuid, op uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog AS $body$
  SELECT jsonb_build_object(
    'kind','outside_copy_window','chainId',137,'after',a.previous_checkpoint,'through',a.next_checkpoint,
    'priorStopId',a.previous_stop,'priorHighWatermark',a.previous_watermark::text,'startOperationId',a.operation_id,
    'finalityEvidenceSha256',a.anchor_sha256
  )
  FROM polygon_buy.demo_fresh_segments a WHERE (a.session_id,a.operation_id)=(sid,op)
$body$;
REVOKE ALL ON FUNCTION polygon_buy.demo_fresh_gap(uuid,uuid) FROM PUBLIC,polygon_executor;

DO $patch$
DECLARE
  guard text:=pg_get_functiondef('polygon_live_activity.stream_update_guard()'::regprocedure);
  history text:=pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure);
  guard_marker text:=$mark$OR (OLD.status<>'observing' AND NOT ($mark$;
  replay_marker text:=$mark$ELSIF o.kind='start_segment' THEN$mark$;
BEGIN
  IF (SELECT bool_and(cardinality(string_to_array(definition,marker))=2)
      FROM (VALUES(guard,guard_marker),(history,replay_marker)) preimage(definition,marker)) IS DISTINCT FROM true
  THEN RAISE EXCEPTION 'Unexpected activity recovery preimage'; END IF;

  guard:=replace(guard,guard_marker,guard_marker||$guard$
    (OLD.status='stopped' AND NEW.status='observing'
     AND (to_jsonb(NEW)-ARRAY['status','checkpoint','last_operation_id'])=(to_jsonb(OLD)-ARRAY['status','checkpoint','last_operation_id'])
     AND EXISTS (
       SELECT FROM polygon_buy.demo_fresh_segments evidence
       WHERE (evidence.session_id,evidence.operation_id,evidence.previous_stop,evidence.previous_checkpoint,
              evidence.previous_watermark,evidence.next_checkpoint) =
             (OLD.session_id,NEW.last_operation_id,OLD.last_operation_id,OLD.checkpoint,OLD.high_watermark,NEW.checkpoint)
     )) OR
  $guard$);
  history:=replace(history,replay_marker,$history$
    ELSIF o.kind='start_segment' AND polygon_buy.demo_fresh_gap(sid,o.id) IS NOT NULL THEN
      IF state<>'stopped' OR ordinal<=1
       OR o.request->'gap' IS DISTINCT FROM polygon_buy.demo_fresh_gap(sid,o.id)
       OR NOT EXISTS (
        SELECT FROM polygon_buy.demo_fresh_segments x
        JOIN polygon_live_activity.operations prior ON (prior.session_id,prior.id)=(x.session_id,x.previous_stop)
        WHERE (x.session_id,x.operation_id,x.previous_stop,x.previous_checkpoint,x.previous_watermark) =
              (sid,o.id,previous_id,cp,water)
         AND prior.kind='stop' AND prior.request->>'status'='stopped' AND prior.created_at<=x.recorded_at
         AND x.recorded_at=o.created_at AND (x.next_checkpoint->>'number')::bigint>(cp->>'number')::bigint
       )
      THEN RETURN false; END IF;
      cp:=o.request#>'{gap,through}';state:='observing';
      expected:=jsonb_build_object('operationId',o.id,'kind','start_segment','sessionId',sid,'checkpoint',cp,
         'highWatermark',water::text,'coverageGap',o.request->'gap');
  $history$||replay_marker);
  EXECUTE guard;
  EXECUTE history;
END
$patch$;

CREATE FUNCTION polygon_buy.open_demo_fresh_segment(input jsonb) RETURNS jsonb
LANGUAGE plpgsql SET search_path=pg_catalog AS $body$
DECLARE
  sid uuid;
  op uuid;
  work polygon_live_activity.stream;
  prior polygon_live_activity.operations;
  assignment polygon_live_activity.assignments;
  snapshot polygon.session_snapshots;
  result jsonb;
  gap jsonb;
  request jsonb;
  wrapper jsonb;
  recorded timestamptz:=date_trunc('milliseconds',clock_timestamp());
  observed timestamptz;
  next_checkpoint jsonb;
BEGIN
  IF current_setting('transaction_isolation')<>'serializable'
    OR NOT polygon.exact_keys(input,ARRAY['sessionId','operationId','expectedStopId','expectedCheckpoint',
        'expectedHighWatermark','finalizedCheckpoint','observedAt','evidenceSha256'])
    OR polygon_live_activity.uuid_value(input->'sessionId') IS DISTINCT FROM true
    OR polygon_live_activity.uuid_value(input->'operationId') IS DISTINCT FROM true
    OR polygon_live_activity.uuid_value(input->'expectedStopId') IS DISTINCT FROM true
    OR polygon_live_activity.checkpoint(input->'expectedCheckpoint') IS DISTINCT FROM true
    OR polygon_live_activity.checkpoint(input->'finalizedCheckpoint') IS DISTINCT FROM true
    OR polygon_live_activity.uint(input->'expectedHighWatermark') IS DISTINCT FROM true
    OR polygon_live_activity.time_value(input->'observedAt') IS DISTINCT FROM true
    OR polygon_live_activity.sha_value(input->'evidenceSha256') IS DISTINCT FROM true
  THEN RAISE EXCEPTION 'Invalid fresh segment request'; END IF;
  sid:=(input->>'sessionId')::uuid;
  op:=(input->>'operationId')::uuid;
  observed:=(input->>'observedAt')::timestamptz;
  next_checkpoint:=input->'finalizedCheckpoint';
  IF observed>recorded OR observed<recorded-interval '5 minutes'
     OR NOT (polygon_buy.decision_gap_scope(sid) IS TRUE OR polygon_buy.pinned_tradecraft(sid) IS TRUE)
     OR polygon_live_activity.new_admission(sid) IS DISTINCT FROM true
  THEN RAISE EXCEPTION 'Session or finalized observation is outside the recovery scope'; END IF;
  PERFORM 1 FROM polygon.paper_sessions s JOIN polygon.user_session_slots sl ON sl.current_session_id=s.id AND sl.user_id=s.user_id
    WHERE s.id=sid AND s.lifecycle='active' AND s.version=1 FOR UPDATE OF s;
  IF NOT FOUND THEN RAISE EXCEPTION 'Demo is no longer the empty current session'; END IF;
  SELECT * INTO STRICT snapshot FROM polygon.session_snapshots WHERE session_id=sid AND version=1;
  SELECT * INTO STRICT work FROM polygon_live_activity.stream WHERE session_id=sid FOR UPDATE;
  SELECT * INTO STRICT assignment FROM polygon_live_activity.assignments WHERE session_id=sid;
  SELECT * INTO STRICT prior FROM polygon_live_activity.operations WHERE session_id=sid AND id=work.last_operation_id;

  IF work.status<>'stopped' OR work.last_operation_id::text<>input->>'expectedStopId'
    OR work.checkpoint IS DISTINCT FROM input->'expectedCheckpoint' OR work.high_watermark::text<>input->>'expectedHighWatermark'
    OR prior.kind<>'stop' OR prior.request->>'status' IS DISTINCT FROM 'stopped' OR prior.result->>'status' IS DISTINCT FROM 'stopped'
    OR prior.created_at>recorded OR (next_checkpoint->>'number')::bigint<=(work.checkpoint->>'number')::bigint
    OR snapshot.trade_count<>0 OR snapshot.position_count<>0 OR snapshot.order_count<>0 OR snapshot.reserved_n<>0
    OR EXISTS(SELECT FROM polygon_buy.admissions WHERE session_id=sid AND expires_at>recorded)
    OR polygon_live_activity.bound_state_valid(sid) IS DISTINCT FROM true
    OR polygon_live_activity.calls_valid(sid) IS DISTINCT FROM true
  THEN RAISE EXCEPTION 'Fresh segment preconditions changed'; END IF;

  INSERT INTO polygon_buy.demo_fresh_segments VALUES(
    sid,op,prior.id,work.checkpoint,work.high_watermark,next_checkpoint,observed,input->>'evidenceSha256',session_user,recorded
  );
  gap:=polygon_buy.demo_fresh_gap(sid,op);
  request:=jsonb_build_object('sessionId',sid,'runId',assignment.run_id,'operationId',op,'gap',gap);
  result:=jsonb_build_object('operationId',op,'kind','start_segment','sessionId',sid,
    'checkpoint',next_checkpoint,'highWatermark',work.high_watermark::text,'coverageGap',gap);
  wrapper:=jsonb_build_object('session_id',sid,'request',request);
  PERFORM polygon_live_activity.save_result(request,'start_segment',result,recorded);
  INSERT INTO polygon_live_activity.calls VALUES(sid,op,'start_segment',wrapper,
    polygon_live_activity.digest('start_segment'||chr(10)||wrapper::text),recorded);
  UPDATE polygon_live_activity.stream SET status='observing',checkpoint=next_checkpoint,last_operation_id=op WHERE session_id=sid;
  IF polygon_live_activity.bound_state_valid(sid) IS DISTINCT FROM true OR polygon_live_activity.calls_valid(sid) IS DISTINCT FROM true
  THEN RAISE EXCEPTION 'Historical audit did not validate after opening the segment'; END IF;
  RETURN result;
END
$body$;
REVOKE ALL ON FUNCTION polygon_buy.open_demo_fresh_segment(jsonb) FROM PUBLIC,polygon_executor;
COMMIT;
