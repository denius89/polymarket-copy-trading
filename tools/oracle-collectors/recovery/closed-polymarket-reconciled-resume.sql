\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='25s';

CREATE TEMP TABLE recovery_input ON COMMIT DROP AS SELECT
  :'session_id'::uuid AS session_id, :'run_id'::uuid AS run_id,
  :'stop_id'::uuid AS stop_id, :'resume_id'::uuid AS resume_id,
  :'range_id'::uuid AS range_id, :'checkpoint'::jsonb AS checkpoint,
  :'watermark'::bigint AS watermark, :'execution_id'::text AS execution_id,
  :'ingestion_id'::uuid AS ingestion_id, :'observation_id'::uuid AS observation_id,
  :'intent_id'::uuid AS intent_id, :'commands'::uuid[] AS commands,
  :'admissions'::uuid[] AS admissions, :'wallet'::text AS wallet,
  :'core_version'::bigint AS core_version, :'cash'::jsonb AS cash, :'witnesses'::jsonb AS witnesses;
GRANT SELECT ON recovery_input TO polygon_owner;

CREATE TEMP TABLE before_recovery ON COMMIT DROP AS
SELECT to_jsonb(s) AS session_row, to_jsonb(st) AS stream_row, sn.data AS snapshot,
       (SELECT count(*) FROM polygon_live_activity.operations WHERE session_id=s.id) AS operations,
       (SELECT count(*) FROM polygon_live_activity.calls WHERE session_id=s.id) AS calls
FROM recovery_input i JOIN polygon.paper_sessions s ON s.id=i.session_id
JOIN polygon_live_activity.stream st ON st.session_id=s.id
JOIN live_buy_core.heads h ON h.session_id=s.id
JOIN live_buy_core.snapshots sn ON (sn.session_id,sn.version)=(h.session_id,h.version);
GRANT SELECT ON before_recovery TO polygon_owner;

SET LOCAL ROLE polygon_owner;

CREATE TABLE polygon_live_activity.reconciled_resume_proofs (
    session_id uuid NOT NULL REFERENCES polygon.paper_sessions(id),
    stop_id uuid NOT NULL,
    resume_id uuid NOT NULL,
    range_id uuid NOT NULL,
    checkpoint jsonb NOT NULL CHECK (polygon_live_activity.checkpoint(checkpoint)),
    watermark bigint NOT NULL CHECK (watermark>=0),
    execution_id text NOT NULL CHECK (execution_id ~ '^[a-f0-9]{64}$'),
    evidence jsonb NOT NULL,
    evidence_sha256 text NOT NULL CHECK (evidence_sha256=polygon_live_activity.digest(evidence::text)),
    approved_by name NOT NULL DEFAULT session_user,
    approved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (session_id,stop_id),
    UNIQUE (session_id,resume_id),
    UNIQUE (session_id,execution_id),
    FOREIGN KEY (session_id,stop_id) REFERENCES polygon_live_activity.operations(session_id,id),
    FOREIGN KEY (session_id,range_id) REFERENCES polygon_live_activity.operations(session_id,id),
    FOREIGN KEY (session_id,resume_id) REFERENCES polygon_live_activity.operations(session_id,id)
      DEFERRABLE INITIALLY DEFERRED,
    CHECK (stop_id<>resume_id)
);
REVOKE ALL ON polygon_live_activity.reconciled_resume_proofs FROM PUBLIC, polygon_executor;
CREATE TRIGGER immutable_reconciled_resume BEFORE UPDATE OR DELETE
  ON polygon_live_activity.reconciled_resume_proofs FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_reconciled_resume_truncate BEFORE TRUNCATE
  ON polygon_live_activity.reconciled_resume_proofs FOR EACH STATEMENT EXECUTE FUNCTION polygon.immutable_row();

DO $proof$
DECLARE
    i pg_temp.recovery_input;
    a polygon_live_activity.assignments;
    s polygon.paper_sessions;
    st polygon_live_activity.stream;
    o polygon_live_activity.operations;
    sn live_buy_core.snapshots;
    evidence jsonb;
BEGIN
    SELECT * INTO STRICT i FROM pg_temp.recovery_input;
    SELECT * INTO STRICT s FROM polygon.paper_sessions WHERE id=i.session_id FOR UPDATE;
    SELECT * INTO STRICT st FROM polygon_live_activity.stream WHERE session_id=i.session_id FOR UPDATE;
    SELECT * INTO STRICT a FROM polygon_live_activity.assignments WHERE session_id=i.session_id;
    SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=i.session_id AND id=i.stop_id;
    SELECT snap.* INTO STRICT sn FROM live_buy_core.heads h JOIN live_buy_core.snapshots snap USING(session_id,version)
        WHERE h.session_id=i.session_id FOR SHARE OF h;
    IF current_database()<>'shadow_v00'
       OR a.run_id<>i.run_id OR a.database_name<>current_database() OR a.owner_address<>i.wallet
       OR a.writer_role::text::regrole::oid<>a.writer_oid
       OR NOT EXISTS (SELECT FROM polygon.venues WHERE id=s.venue_id AND code='polymarket')
       OR NOT EXISTS (SELECT FROM polygon.user_session_slots
                      WHERE user_id=s.user_id AND current_session_id=s.id)
       OR polygon_live_activity.new_admission(s.id) IS DISTINCT FROM true
       OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true
       OR polygon_live_activity.calls_valid(s.id) IS DISTINCT FROM true
       OR polygon.session_valid(s.id) IS DISTINCT FROM true
       OR st.status<>'reconciliation_required' OR st.last_operation_id<>i.stop_id
       OR st.last_range_operation_id IS DISTINCT FROM i.range_id
       OR st.checkpoint<>i.checkpoint OR st.high_watermark<>i.watermark
       OR o.kind<>'stop' OR o.request->>'status' IS DISTINCT FROM st.status
       OR o.result->>'status' IS DISTINCT FROM st.status
       OR NOT EXISTS (SELECT FROM polygon_live_activity.calls
                      WHERE session_id=s.id AND operation_id=o.id AND kind='stop')
       OR sn.version<>i.core_version OR sn.data->'cash' IS DISTINCT FROM i.cash
       OR sn.data->'reservedCash' IS DISTINCT FROM live_buy_core.q(0,1)
       OR jsonb_array_length(sn.data->'positions')<>1
       OR cardinality(i.commands)<>2 OR i.commands[1] IS NULL OR i.commands[2] IS NULL OR i.commands[1]=i.commands[2]
       OR cardinality(i.admissions)<>2 OR i.admissions[1] IS NULL OR i.admissions[2] IS NULL OR i.admissions[1]=i.admissions[2]
       OR EXISTS (SELECT FROM polygon_buy.verified_quotes
                  WHERE session_id=s.id AND execution_id=i.execution_id)
       OR EXISTS (SELECT FROM polygon_buy.admissions WHERE session_id=s.id
                  AND (id=ANY(i.admissions) OR expires_at>clock_timestamp()))
       OR EXISTS (SELECT FROM polygon_buy.commands WHERE session_id=s.id
                  AND (command_id=ANY(i.commands) OR admission_id=ANY(i.admissions)))
       OR EXISTS (SELECT FROM live_buy_core.receipts WHERE session_id=s.id AND command_id=ANY(i.commands))
       OR EXISTS (SELECT FROM live_buy_core.intents WHERE session_id=s.id
                  AND (id=i.intent_id OR observation_id=i.observation_id OR command_id=ANY(i.commands)))
       OR EXISTS (SELECT FROM live_buy_core.executions WHERE session_id=s.id
                  AND (intent_id=i.intent_id OR command_id=ANY(i.commands)))
       OR EXISTS (SELECT FROM polygon_live_activity.operations WHERE session_id=s.id AND id=i.ingestion_id)
       OR EXISTS (SELECT FROM polygon_live_activity.calls WHERE session_id=s.id AND operation_id=i.ingestion_id)
       OR EXISTS (SELECT FROM polygon_live_activity.observations WHERE session_id=s.id AND id=i.observation_id)
    THEN RAISE EXCEPTION 'Closed Polymarket reconciliation prerequisites changed'; END IF;

    IF (SELECT count(DISTINCT item->>'provider')>=2 AND count(DISTINCT item->>'nextHash')=1
                AND bool_and((item->>'provider' IN ('https://polygon.drpc.org','https://polygon-bor-rpc.publicnode.com',
                   'https://polygon.gateway.tenderly.co') AND item->'chainId'='137'::jsonb
                  AND (item->>'finalized')::bigint>=(i.checkpoint->>'number')::bigint+1
                  AND item->>'block'=i.checkpoint->>'number'
                  AND item->>'hash'=i.checkpoint->>'hash'
                  AND (item->>'nextBlock')::bigint=(i.checkpoint->>'number')::bigint+1
                  AND item->>'nextParent'=i.checkpoint->>'hash'
                  AND item->>'nextHash' ~ '^0x[a-f0-9]{64}$') IS TRUE)
        FROM jsonb_array_elements(i.witnesses->'witnesses') item) IS DISTINCT FROM true
    THEN RAISE EXCEPTION 'Finalized Polygon witnesses do not match the saved checkpoint'; END IF;

    evidence:=to_jsonb(i)||jsonb_build_object('snapshotId',sn.id,
       'snapshotSha256',polygon_live_activity.digest(sn.data::text),'stopEvidence',o.request->>'evidenceSha256');
    INSERT INTO polygon_live_activity.reconciled_resume_proofs
        (session_id,stop_id,resume_id,range_id,checkpoint,watermark,execution_id,evidence,evidence_sha256)
    VALUES (s.id,o.id,i.resume_id,i.range_id,i.checkpoint,i.watermark,i.execution_id,evidence,
           polygon_live_activity.digest(evidence::text));
END
$proof$;

CREATE FUNCTION pg_temp.replace_resume_clause(body text, old text, replacement text)
RETURNS text LANGUAGE plpgsql SET search_path=pg_catalog AS $replace$
BEGIN
    IF cardinality(string_to_array(body,old))<>2 THEN RAISE EXCEPTION 'Unexpected resume function clause'; END IF;
    RETURN replace(body,old,replacement);
END
$replace$;

DO $guards$
DECLARE body text;
BEGIN
    IF md5(pg_get_functiondef('polygon_live_activity.source_resume_evidence(uuid,uuid,uuid,jsonb,bigint)'::regprocedure))
          <> '2a795852aaa6dce6cccacf737feacb6c'
       OR md5(pg_get_functiondef('polygon_live_activity.inner_resume(jsonb)'::regprocedure))<>'62e3de9c02d9de3ee52eebdb7fb721f8'
       OR md5(pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure))<>'448f1bd4e30e261b76c02a16c6fe94b8'
       OR md5(pg_get_functiondef('polygon_live_activity.stream_update_guard()'::regprocedure))<>'f7ebf87ed865beabc661dd14687d6d56'
    THEN RAISE EXCEPTION 'Unexpected installed recovery contract'; END IF;

    body:=pg_get_functiondef('polygon_live_activity.source_resume_evidence(uuid,uuid,uuid,jsonb,bigint)'::regprocedure);
    EXECUTE pg_temp.replace_resume_clause(body,
      $old$AND stop.result->>'status'='source_unavailable'$old$,
      $new$AND stop.result->>'status'='source_unavailable'
    UNION ALL
    SELECT proof.evidence_sha256
    FROM polygon_live_activity.reconciled_resume_proofs proof
    JOIN polygon_live_activity.operations stop
      ON (stop.session_id,stop.id)=(proof.session_id,proof.stop_id)
    WHERE (proof.session_id,proof.stop_id,proof.resume_id,proof.checkpoint,proof.watermark)
          =(sid,stopped_op,resumed_op,saved_checkpoint,saved_watermark)
      AND stop.kind='stop' AND stop.request->>'status'='reconciliation_required'
      AND stop.result->>'status'='reconciliation_required'$new$);

    body:=pg_get_functiondef('polygon_live_activity.inner_resume(jsonb)'::regprocedure);
    EXECUTE pg_temp.replace_resume_clause(body,$old$st.status='source_unavailable'$old$,
      $new$st.status IN ('source_unavailable','reconciliation_required')$new$);

    body:=pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure);
    body:=pg_temp.replace_resume_clause(body,$old$state='source_unavailable' AND o.kind='resume'$old$,
      $new$state IN ('source_unavailable','reconciliation_required') AND o.kind='resume'$new$);
    EXECUTE pg_temp.replace_resume_clause(body,$old$o.kind='resume' AND state='source_unavailable'$old$,
      $new$o.kind='resume' AND state IN ('source_unavailable','reconciliation_required')$new$);

    body:=pg_get_functiondef('polygon_live_activity.stream_update_guard()'::regprocedure);
    EXECUTE pg_temp.replace_resume_clause(body,$old$OLD.status='source_unavailable' AND NEW.status='observing'$old$,
      $new$OLD.status IN ('source_unavailable','reconciliation_required') AND NEW.status='observing'$new$);
END
$guards$;

SELECT a.writer_role AS writer_role,
       jsonb_build_object('session_id',i.session_id,'request',jsonb_build_object(
         'sessionId',i.session_id,'runId',i.run_id,'operationId',i.resume_id,
         'expectedLastOperationId',i.stop_id,'expectedCheckpoint',i.checkpoint,
         'expectedHighWatermark',i.watermark::text,'evidenceSha256',p.evidence_sha256)) AS command
FROM recovery_input i JOIN polygon_live_activity.assignments a USING(session_id)
JOIN polygon_live_activity.reconciled_resume_proofs p ON (p.session_id,p.stop_id)=(i.session_id,i.stop_id)
\gset

RESET ROLE;
SET LOCAL SESSION AUTHORIZATION :"writer_role";
\if :rehearsal
SELECT (polygon.live_activity_resume(jsonb_set(:'command'::jsonb,'{request,evidenceSha256}',
  to_jsonb(repeat('0',64))))->>'http'='409') AS rejected
\gset
\if :rejected
\else
\quit 3
\endif
\endif
SELECT polygon.live_activity_resume(:'command'::jsonb) AS receipt
\gset
SELECT (:'receipt'::jsonb->>'http'='200'
    AND :'receipt'::jsonb=polygon.live_activity_resume(:'command'::jsonb)) AS resumed
\gset
\if :resumed
\else
\echo Resume refused: :receipt
\quit 3
\endif
RESET SESSION AUTHORIZATION;
SET LOCAL ROLE polygon_owner;

DO $after$
DECLARE i pg_temp.recovery_input;b pg_temp.before_recovery;st polygon_live_activity.stream;
BEGIN
    SELECT * INTO STRICT i FROM pg_temp.recovery_input;
    SELECT * INTO STRICT b FROM pg_temp.before_recovery;
    SELECT * INTO STRICT st FROM polygon_live_activity.stream WHERE session_id=i.session_id;
    IF st.status<>'observing' OR st.last_operation_id<>i.resume_id
       OR (to_jsonb(st)-ARRAY['status','last_operation_id'])<>(b.stream_row-ARRAY['status','last_operation_id'])
       OR (SELECT to_jsonb(s) FROM polygon.paper_sessions s WHERE id=i.session_id) IS DISTINCT FROM b.session_row
       OR live_buy_core.read_state(i.session_id) IS DISTINCT FROM b.snapshot
       OR (SELECT count(*) FROM polygon_live_activity.operations WHERE session_id=i.session_id)<>b.operations+1
       OR (SELECT count(*) FROM polygon_live_activity.calls WHERE session_id=i.session_id)<>b.calls+1
       OR polygon_live_activity.bound_state_valid(i.session_id) IS DISTINCT FROM true
       OR polygon_live_activity.calls_valid(i.session_id) IS DISTINCT FROM true
       OR polygon.session_valid(i.session_id) IS DISTINCT FROM true
    THEN RAISE EXCEPTION 'Resume failed to preserve session or financial history'; END IF;
END
$after$;

SET CONSTRAINTS ALL IMMEDIATE;
COMMIT;
SELECT :'receipt'::jsonb;
