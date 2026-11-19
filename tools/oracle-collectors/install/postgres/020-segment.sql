BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout='3s';
SET LOCAL ROLE polygon_owner;
SET LOCAL search_path=pg_catalog;
CREATE TABLE polygon_buy.segment_starts(
 session_id uuid PRIMARY KEY REFERENCES polygon_buy.personal_start_blocks,
 operation_id uuid NOT NULL UNIQUE,
 FOREIGN KEY(session_id,operation_id) REFERENCES polygon_live_activity.operations(session_id,id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TRIGGER immutable_start BEFORE UPDATE OR DELETE ON polygon_buy.segment_starts
 FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE FUNCTION polygon_buy.coverage_gap(sid uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('kind','outside_copy_window','chainId',b.chain_id,
 'after',b.previous_checkpoint,'through',jsonb_build_object('number',b.block_number::text,'hash',b.block_hash),
 'priorStopId',b.previous_operation,'priorHighWatermark',b.previous_watermark::text,
 'startOperationId',g.operation_id,'finalityEvidenceSha256',b.evidence_sha256)
 FROM polygon_buy.segment_starts g JOIN polygon_buy.personal_start_blocks b USING(session_id) WHERE g.session_id=sid
$$;
ALTER TABLE polygon_live_activity.operations DROP CONSTRAINT operations_kind_check,
 ADD CONSTRAINT operations_kind_check CHECK(kind IN('arm','ingest','stop','resume','start_segment'));
ALTER TABLE polygon_live_activity.calls DROP CONSTRAINT calls_kind_check,
 ADD CONSTRAINT calls_kind_check CHECK(kind IN('arm','ingest','stop','resume','start_segment'));
DO $patch$
DECLARE d text; n text; replacement text;
BEGIN
 d:=pg_get_functiondef('polygon_live_activity.request_shape(jsonb,text)'::regprocedure);
 n:='WHEN ''resume'' THEN';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'request shape mismatch'; END IF;
 EXECUTE replace(d,n,$branch$WHEN 'start_segment' THEN RETURN polygon.exact_keys(p,ARRAY['sessionId','runId','operationId','gap'])
 AND jsonb_typeof(p->'gap')='object';
 $branch$||n);
 d:=pg_get_functiondef('polygon_live_activity.stream_update_guard()'::regprocedure);
 n:='OR (OLD.status<>''observing'' AND NOT (';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'stream guard mismatch'; END IF;
 replacement:=$branch$OR (OLD.status<>'observing' AND NOT (
 (OLD.status='stopped' AND NEW.status='observing'
 AND (to_jsonb(OLD)-ARRAY['status','checkpoint','last_operation_id'])=(to_jsonb(NEW)-ARRAY['status','checkpoint','last_operation_id'])
 AND EXISTS(SELECT FROM polygon_buy.segment_starts g JOIN polygon_buy.personal_start_blocks a USING(session_id)
 WHERE g.session_id=OLD.session_id AND g.operation_id=NEW.last_operation_id AND a.previous_operation=OLD.last_operation_id
 AND a.previous_checkpoint=OLD.checkpoint AND a.previous_watermark=OLD.high_watermark
 AND NEW.checkpoint=jsonb_build_object('number',a.block_number::text,'hash',a.block_hash))) OR $branch$;
 EXECUTE replace(d,n,replacement);
 d:=pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure);
 n:='state=''stopped'' AND o.kind=''resume''';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'history guard mismatch'; END IF;
 d:=replace(d,n,'state=''stopped'' AND o.kind IN (''resume'',''start_segment'')');
 n:='ELSIF o.kind=''resume'' THEN';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'history replay mismatch'; END IF;
 replacement:=$branch$ELSIF o.kind='start_segment' THEN
   IF state<>'stopped' OR ordinal=1 OR o.request->'gap' IS DISTINCT FROM polygon_buy.coverage_gap(sid)
    OR NOT EXISTS(SELECT FROM polygon_buy.personal_start_blocks a JOIN polygon_buy.segment_starts g USING(session_id)
      JOIN polygon_live_activity.operations old ON old.session_id=a.session_id AND old.id=a.previous_operation
      WHERE a.session_id=sid AND g.operation_id=o.id AND old.kind='stop' AND a.previous_operation=previous_id
      AND a.previous_checkpoint=cp AND a.previous_watermark=water AND a.block_number>(cp->>'number')::bigint
      AND a.attached_at>=old.created_at AND o.created_at>=a.attached_at)
   THEN RETURN false; END IF;
   cp:=o.request#>'{gap,through}';state:='observing';
   expected:=jsonb_build_object('operationId',o.id,'kind','start_segment','sessionId',sid,'checkpoint',cp,
     'highWatermark',water::text,'coverageGap',o.request->'gap');
 $branch$;
 EXECUTE replace(d,n,replacement||n);
 d:=pg_get_functiondef('polygon.personal_quote_scope_v1(uuid)'::regprocedure);
 n:='''personalStart'',polygon_buy.start_receipt(sid)';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'scope preimage mismatch'; END IF;
 EXECUTE replace(d,n,n||',''coverageGap'',polygon_buy.coverage_gap(sid)');
 d:=pg_get_functiondef('polygon.buy_activity_read_v1(jsonb)'::regprocedure);
 n:='''completeness'',''unproven''';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'Activity preimage mismatch'; END IF;
 EXECUTE replace(d,n,n||$view$,'coverageGap',(SELECT jsonb_build_object('chainId',ab.chain_id,'afterBlock',ab.previous_checkpoint->>'number','throughBlock',ab.block_number::text) FROM polygon_buy.personal_start_blocks ab JOIN polygon_buy.segment_starts sg USING(session_id) WHERE ab.session_id=s.id)$view$);
END $patch$;
CREATE FUNCTION polygon_buy.start_segment(sid uuid, expected_user uuid, op uuid, proof_sha text)
RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $fn$
DECLARE s polygon.paper_sessions; a polygon_buy.personal_start_blocks; old polygon_live_activity.stream;
 binding polygon_live_activity.assignments; existing polygon_buy.segment_starts; gap jsonb; req jsonb;
 payload jsonb; wrapper jsonb; t timestamptz; oldop polygon_live_activity.operations;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' OR op IS NULL THEN RAISE EXCEPTION 'invalid segment transaction'; END IF;
 SELECT ps.* INTO STRICT s FROM polygon.paper_sessions ps JOIN polygon.user_session_slots sl
 ON (sl.user_id,sl.current_session_id)=(ps.user_id,ps.id)
 JOIN polygon_buy.enrolled e ON (e.session_id,e.user_id,e.revision_id)=(ps.id,ps.user_id,ps.trader_revision_id)
 JOIN polygon.traders tr ON (tr.id,tr.source_id,tr.venue_id,tr.external_trader_id)=(ps.trader_id,ps.source_id,ps.venue_id,e.wallet)
 JOIN polygon.catalog_sources c ON c.id=ps.source_id AND c.data_origin='public_api'
 JOIN polygon.venues v ON v.id=ps.venue_id AND v.code='polymarket'
 WHERE ps.id=sid AND ps.user_id=expected_user AND ps.lifecycle='active'
 AND e.wallet='0xf0318c32136c2db7fec88b84869aee6a1106c80c' AND polygon_live.public_valid(sid)
 FOR UPDATE OF ps;
 SELECT * INTO STRICT a FROM polygon_buy.personal_start_blocks WHERE session_id=sid AND evidence_sha256=proof_sha;
 SELECT * INTO existing FROM polygon_buy.segment_starts WHERE session_id=sid;
 IF FOUND THEN
  IF existing.operation_id<>op THEN RAISE EXCEPTION 'segment key conflict'; END IF;
  SELECT * INTO STRICT oldop FROM polygon_live_activity.operations WHERE session_id=sid AND id=op AND kind='start_segment';
  RETURN oldop.result;
 END IF;
 SELECT i.* INTO STRICT binding FROM polygon_live_activity.assignments i JOIN polygon_buy.bindings b USING(session_id,run_id)
 JOIN polygon_live_activity.release_record r ON r.run_id=i.run_id AND r.database_name=current_database() AND r.database_oid=polygon_buy.database_oid()
 WHERE i.session_id=sid AND i.user_id=s.user_id AND i.revision_id=s.trader_revision_id AND i.owner_address='0xf0318c32136c2db7fec88b84869aee6a1106c80c';
 SELECT * INTO STRICT old FROM polygon_live_activity.stream WHERE session_id=sid AND status='stopped' FOR UPDATE;
 IF NOT EXISTS(SELECT FROM polygon_live_activity.operations WHERE session_id=sid AND id=old.last_operation_id AND kind='stop' AND request->>'status'='stopped')
 OR old.checkpoint IS DISTINCT FROM a.previous_checkpoint OR old.high_watermark<>a.previous_watermark OR old.last_operation_id<>a.previous_operation
 OR clock_timestamp() NOT BETWEEN a.attached_at AND a.attached_at+interval '30 seconds'
 OR a.block_number<=(old.checkpoint->>'number')::bigint OR s.version<>1 OR s.control_state<>'copying_not_connected'
 OR NOT EXISTS(SELECT FROM polygon.session_snapshots WHERE session_id=sid AND version=1 AND content_state='EMPTY' AND trade_count=0 AND position_count=0 AND order_count=0)
 OR EXISTS(SELECT FROM polygon_buy.verified_quotes WHERE session_id=sid)
 OR polygon.session_valid(sid) IS DISTINCT FROM true OR polygon_live_activity.new_admission(sid) IS DISTINCT FROM true
 OR polygon_live_activity.bound_state_valid(sid) IS DISTINCT FROM true OR polygon_live_activity.calls_valid(sid) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'segment baseline conflict'; END IF;
 INSERT INTO polygon_buy.segment_starts VALUES(sid,op);
 gap:=polygon_buy.coverage_gap(sid); t:=clock_timestamp();
 req:=jsonb_build_object('sessionId',sid,'operationId',op,'runId',binding.run_id,'gap',gap);
 payload:=jsonb_build_object('operationId',op,'kind','start_segment','sessionId',sid,
 'checkpoint',gap->'through','highWatermark',old.high_watermark::text,'coverageGap',gap);
 wrapper:=jsonb_build_object('session_id',sid,'request',req);
 PERFORM polygon_live_activity.save_result(req,'start_segment',payload,t);
 INSERT INTO polygon_live_activity.calls VALUES(sid,op,'start_segment',wrapper,polygon_live_activity.digest('start_segment'||chr(10)||wrapper::text),t);
 UPDATE polygon_live_activity.stream SET status='observing',checkpoint=gap->'through',last_operation_id=op WHERE session_id=sid;
 IF polygon_live_activity.bound_state_valid(sid) IS DISTINCT FROM true OR polygon_live_activity.calls_valid(sid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'segment replay failed'; END IF;
 RETURN payload;
END $fn$;
REVOKE ALL ON FUNCTION polygon_buy.start_segment(uuid,uuid,uuid,text),polygon_buy.coverage_gap(uuid) FROM PUBLIC,polygon_executor;
COMMIT;
