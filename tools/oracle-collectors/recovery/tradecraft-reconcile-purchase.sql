\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout='2s';
SET LOCAL statement_timeout='20s';

CREATE TEMP TABLE recovery_target (
    session_id uuid, stop_id uuid, expected_checkpoint jsonb, watermark bigint, snapshot_id uuid, proof_sha text, execution_id text, ingest_id uuid
) ON COMMIT DROP;
INSERT INTO recovery_target VALUES (
  :'session_id'::uuid, :'stop_id'::uuid, :'checkpoint'::jsonb,
  :'watermark'::bigint, :'snapshot_id'::uuid, :'proof_sha', :'execution_id', :'ingest_id'::uuid
);
GRANT SELECT ON recovery_target TO polygon_owner;
SET LOCAL ROLE polygon_owner;

CREATE TABLE polygon_buy.tradecraft_purchase_reconciliations (
    session_id uuid NOT NULL,
    stop_id uuid NOT NULL,
    resume_id uuid NOT NULL,
    admission_id uuid NOT NULL,
    ingest_id uuid NOT NULL,
    reconciled_at timestamptz NOT NULL,
    PRIMARY KEY (session_id, stop_id),
    UNIQUE (session_id, resume_id),
    FOREIGN KEY (session_id, admission_id) REFERENCES polygon_buy.admissions(session_id,id),
    FOREIGN KEY (session_id, stop_id) REFERENCES polygon_live_activity.operations(session_id,id),
    FOREIGN KEY (session_id, resume_id) REFERENCES polygon_live_activity.operations(session_id,id)
        DEFERRABLE INITIALLY DEFERRED
);
CREATE TRIGGER immutable_purchase_reconciliation BEFORE UPDATE OR DELETE ON polygon_buy.tradecraft_purchase_reconciliations
    FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_purchase_reconciliation_truncate BEFORE TRUNCATE ON polygon_buy.tradecraft_purchase_reconciliations
    FOR EACH STATEMENT EXECUTE FUNCTION polygon.immutable_row();
REVOKE ALL ON polygon_buy.tradecraft_purchase_reconciliations FROM PUBLIC, polygon_executor;

DO $scope$
DECLARE
    guard text := pg_get_functiondef('polygon_live_activity.stream_update_guard()'::regprocedure);
    history text := pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure);
    old_status text := $fragment$OLD.status='source_unavailable' AND NEW.status='observing'$fragment$;
    history_gate text := $fragment$state='source_unavailable' AND o.kind='resume' AND EXISTS ($fragment$;
    history_resume text := $fragment$state='source_unavailable' AND EXISTS ($fragment$;
    reconciled_history text := $allow$
      (state='source_unavailable' OR (state='reconciliation_required' AND EXISTS(
         SELECT FROM polygon_buy.tradecraft_purchase_reconciliations r
         WHERE (r.session_id,r.resume_id)=(sid,o.id))))
    $allow$;
BEGIN
    IF cardinality(string_to_array(guard,old_status))<>2
       OR cardinality(string_to_array(history,history_gate))<>2
       OR cardinality(string_to_array(history,history_resume))<>2
    THEN RAISE EXCEPTION 'Unexpected Tradecraft reconciliation history'; END IF;
    EXECUTE replace(guard,old_status,$allow$
      (OLD.status='source_unavailable' OR (OLD.status='reconciliation_required' AND EXISTS(
         SELECT FROM polygon_buy.tradecraft_purchase_reconciliations r
         WHERE (r.session_id,r.stop_id,r.resume_id)=(OLD.session_id,OLD.last_operation_id,NEW.last_operation_id))))
      AND NEW.status='observing'
    $allow$);
    history := replace(history,history_gate,reconciled_history||' AND o.kind=''resume'' AND EXISTS (');
    EXECUTE replace(history,history_resume,reconciled_history||' AND EXISTS (');
END
$scope$;

DO $operation$
DECLARE target pg_temp.recovery_target;
        session_row polygon.paper_sessions;
        stream polygon_live_activity.stream;
        stop polygon_live_activity.operations;
        snapshot polygon.session_snapshots;
        assignment polygon_live_activity.assignments;
        quoted polygon_buy.verified_quotes;
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
    SELECT * INTO STRICT quoted FROM polygon_buy.verified_quotes
      WHERE session_id=target.session_id AND execution_id=target.execution_id;
    IF NOT polygon_buy.pinned_tradecraft(target.session_id) OR NOT polygon_live_activity.new_admission(target.session_id)
       OR polygon_live_activity.bound_state_valid(target.session_id) IS DISTINCT FROM true
       OR polygon_live_activity.calls_valid(target.session_id) IS DISTINCT FROM true
       OR session_row.lifecycle<>'active' OR session_row.version<>1 OR snapshot.id<>target.snapshot_id
       OR snapshot.trade_count<>0 OR snapshot.position_count<>0 OR snapshot.reserved_n<>0
       OR stream.status<>'reconciliation_required' OR stream.last_operation_id<>target.stop_id
       OR stream.checkpoint IS DISTINCT FROM target.expected_checkpoint OR stream.high_watermark<>target.watermark
       OR stop.kind<>'stop' OR stop.request->>'status' IS DISTINCT FROM 'reconciliation_required'
       OR stop.result->>'status' IS DISTINCT FROM 'reconciliation_required' OR stop.created_at>requested_at
       OR NOT EXISTS (SELECT FROM polygon_live_activity.calls WHERE session_id=target.session_id AND operation_id=stop.id AND kind='stop')
       OR EXISTS (SELECT FROM polygon_buy.admissions WHERE session_id=target.session_id AND expires_at>requested_at)
       OR NOT EXISTS (SELECT FROM polygon_buy.admissions a WHERE (a.session_id,a.id)=(target.session_id,quoted.reserve_id)
                      AND a.kind='reserve' AND a.expires_at<=requested_at)
       OR EXISTS (SELECT FROM polygon_buy.admissions a WHERE (a.session_id,a.id)=(target.session_id,quoted.settle_id))
       OR EXISTS (SELECT FROM polygon_live_activity.calls c WHERE (c.session_id,c.operation_id)=(target.session_id,target.ingest_id))
       OR EXISTS (SELECT FROM polygon_live_activity.operations o WHERE (o.session_id,o.id)=(target.session_id,target.ingest_id))
       OR EXISTS (SELECT FROM live_buy_core.intents i WHERE i.session_id=target.session_id)
       OR EXISTS (SELECT FROM live_buy_core.receipts r WHERE r.session_id=target.session_id)
       OR EXISTS (SELECT FROM live_buy_core.executions e WHERE e.session_id=target.session_id)
    THEN RAISE EXCEPTION 'Tradecraft reconciliation prerequisites changed'; END IF;

    INSERT INTO polygon_buy.tradecraft_purchase_reconciliations VALUES (
      target.session_id,stop.id,recovery_id,quoted.reserve_id,target.ingest_id,requested_at);

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
