\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout='2s';
SET LOCAL statement_timeout='20s';

CREATE TEMP TABLE recovery_target (
    session_id uuid, stop_id uuid, expected_checkpoint jsonb, watermark bigint, snapshot_id uuid, proof_sha text
) ON COMMIT DROP;
INSERT INTO recovery_target VALUES (
  :'session_id'::uuid, :'stop_id'::uuid, :'checkpoint'::jsonb,
  :'watermark'::bigint, :'snapshot_id'::uuid, :'proof_sha'
);
GRANT SELECT ON recovery_target TO polygon_owner;
SET LOCAL ROLE polygon_owner;

-- Previous recovery entries remain immutable. Key new evidence by the exact terminal operation.
DO $key$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid='polygon_buy.tradecraft_source_recovery'::regclass
          AND contype='p' AND pg_get_constraintdef(oid)='PRIMARY KEY (session_id)'
    ) THEN
        ALTER TABLE polygon_buy.tradecraft_source_recovery DROP CONSTRAINT tradecraft_source_recovery_pkey,
            ADD PRIMARY KEY (session_id, stop_op);
    ELSIF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid='polygon_buy.tradecraft_source_recovery'::regclass
          AND contype='p' AND pg_get_constraintdef(oid)='PRIMARY KEY (session_id, stop_op)'
    ) THEN
        RAISE EXCEPTION 'Unexpected Tradecraft recovery key';
    END IF;
END
$key$;

DO $operation$
DECLARE target pg_temp.recovery_target;
        session_row polygon.paper_sessions;
        stream polygon_live_activity.stream;
        stop polygon_live_activity.operations;
        snapshot polygon.session_snapshots;
        assignment polygon_live_activity.assignments;
        recovery_id uuid:=gen_random_uuid();
        requested_at timestamptz:=date_trunc('milliseconds',clock_timestamp());
        request jsonb; wrapper jsonb; receipt jsonb;
BEGIN
    SELECT * INTO STRICT target FROM pg_temp.recovery_target;
    SELECT * INTO STRICT session_row FROM polygon.paper_sessions WHERE id=target.session_id FOR UPDATE;
    SELECT * INTO STRICT stream FROM polygon_live_activity.stream WHERE session_id=target.session_id FOR UPDATE;
    SELECT * INTO STRICT snapshot FROM polygon.session_snapshots
      WHERE session_id=target.session_id AND version=session_row.current_snapshot_version;
    SELECT * INTO STRICT assignment FROM polygon_live_activity.assignments WHERE session_id=target.session_id;
    SELECT * INTO STRICT stop FROM polygon_live_activity.operations WHERE id=target.stop_id AND session_id=target.session_id;
    IF NOT polygon_buy.pinned_tradecraft(target.session_id) OR NOT polygon_live_activity.new_admission(target.session_id)
       OR polygon_live_activity.bound_state_valid(target.session_id) IS DISTINCT FROM true
       OR polygon_live_activity.calls_valid(target.session_id) IS DISTINCT FROM true
       OR session_row.lifecycle<>'active' OR session_row.version<>1 OR snapshot.id<>target.snapshot_id
       OR snapshot.trade_count<>0 OR snapshot.position_count<>0 OR snapshot.reserved_n<>0
       OR stream.status<>'source_unavailable' OR stream.last_operation_id<>target.stop_id
       OR stream.checkpoint IS DISTINCT FROM target.expected_checkpoint OR stream.high_watermark<>target.watermark
       OR stop.kind<>'stop' OR stop.request->>'status' IS DISTINCT FROM 'source_unavailable'
       OR stop.result->>'status' IS DISTINCT FROM 'source_unavailable' OR stop.created_at>requested_at
       OR NOT EXISTS (SELECT FROM polygon_live_activity.calls WHERE session_id=target.session_id AND operation_id=stop.id AND kind='stop')
       OR EXISTS (SELECT FROM polygon_buy.admissions WHERE session_id=target.session_id AND expires_at>requested_at)
    THEN RAISE EXCEPTION 'Tradecraft recovery prerequisites changed'; END IF;

    INSERT INTO polygon_buy.tradecraft_source_recovery VALUES (
      target.session_id, stop.id, recovery_id, stream.checkpoint, stream.high_watermark,
      stream.last_range_operation_id, snapshot.id, target.proof_sha, SESSION_USER, requested_at);
    UPDATE polygon_live_activity.stream SET status='observing',last_operation_id=recovery_id WHERE session_id=target.session_id;
    request:=jsonb_build_object('runId',assignment.run_id,'operationId',recovery_id,'sessionId',target.session_id,
       'expectedLastOperationId',stop.id,'expectedCheckpoint',stream.checkpoint,
       'expectedHighWatermark',stream.high_watermark::text,'evidenceSha256',target.proof_sha);
    IF polygon_live_activity.request_shape(request,'resume') IS DISTINCT FROM true
    THEN RAISE EXCEPTION 'Invalid recovery evidence'; END IF;
    receipt:=jsonb_build_object('operationId',recovery_id,'kind','resume','sessionId',target.session_id,
       'resumedAt',v00_session.utc(requested_at),'checkpoint',stream.checkpoint,'highWatermark',stream.high_watermark::text);
    PERFORM polygon_live_activity.save_result(request,'resume',receipt,requested_at);
    wrapper:=jsonb_build_object('session_id',target.session_id,'request',request);
    INSERT INTO polygon_live_activity.calls VALUES (
      target.session_id,recovery_id,'resume',wrapper,polygon_live_activity.digest('resume'||chr(10)||wrapper::text),requested_at);
    IF polygon_live_activity.bound_state_valid(target.session_id) IS DISTINCT FROM true
       OR polygon_live_activity.calls_valid(target.session_id) IS DISTINCT FROM true
       OR polygon.session_valid(target.session_id) IS DISTINCT FROM true
    THEN RAISE EXCEPTION 'Tradecraft recovery did not preserve integrity'; END IF;
END
$operation$;
SET CONSTRAINTS ALL IMMEDIATE;
COMMIT;
