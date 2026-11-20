-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE FUNCTION polygon_live_activity.bound_state_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE rq polygon_live_activity.bound_requests;op polygon_live_activity.operations;ev polygon_live_activity.evaluations;ob polygon_live_activity.observations;de polygon_live_activity.decisions;
BEGIN
 IF polygon_live_activity.state_valid(sid) IS DISTINCT FROM true THEN RETURN false;END IF;
 IF EXISTS(SELECT FROM polygon_live_activity.operations o WHERE o.session_id=sid AND o.kind='ingest' AND NOT EXISTS(SELECT FROM polygon_live_activity.bound_requests r WHERE r.session_id=sid AND r.operation_id=o.id)) THEN RETURN false;END IF;
 FOR rq IN SELECT * FROM polygon_live_activity.bound_requests WHERE session_id=sid LOOP
  SELECT * INTO op FROM polygon_live_activity.operations WHERE session_id=sid AND id=rq.operation_id;
  IF op.id IS NULL OR op.kind<>'ingest' OR op.request IS DISTINCT FROM rq.request->'ingest' OR op.created_at<>rq.created_at OR op.session_id<>rq.session_id THEN RETURN false;END IF;
  IF op.result->>'kind'='ingest' AND jsonb_array_length(rq.request->'evaluations')<>(SELECT count(*) FROM polygon_live_activity.evaluations WHERE session_id=sid AND operation_id=op.id) THEN RETURN false;END IF;
 END LOOP;
 IF (SELECT count(*) FROM polygon_live_activity.evaluations WHERE session_id=sid)<>(SELECT count(*) FROM polygon_live_activity.observations WHERE session_id=sid AND classification='accepted') THEN RETURN false;END IF;
 FOR ev IN SELECT * FROM polygon_live_activity.evaluations WHERE session_id=sid LOOP
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE id=ev.observation_id;
  SELECT * INTO de FROM polygon_live_activity.decisions WHERE id=ev.decision_id;
  SELECT * INTO op FROM polygon_live_activity.operations WHERE session_id=sid AND id=ev.operation_id;
  SELECT * INTO rq FROM polygon_live_activity.bound_requests WHERE session_id=sid AND operation_id=ev.operation_id;
  IF de.id IS NULL OR op.id IS NULL OR rq.operation_id IS NULL OR ob.classification<>'accepted'
   OR ROW(ev.sequence,ev.session_id,ev.created_at,ev.operation_id) IS DISTINCT FROM ROW(ob.sequence,ob.session_id,op.created_at,ob.operation_id)
   OR ROW(de.observation_id,de.session_id,de.sequence,de.decided_at,de.policy_version,de.status,de.reason_code)
    IS DISTINCT FROM ROW(ob.id,ob.session_id,ob.sequence,ev.created_at,'paper-bound-skip-v1'::text,'skipped'::text,'context_invalid'::text)
   OR de.detail_code IS DISTINCT FROM ev.evidence->>'reason'
   OR de.checks IS DISTINCT FROM jsonb_build_object('evidence',ev.evidence,'executionAdmission','blocked')
   OR (ev.evidence->'binding'<>'null'::jsonb AND ev.evidence#>>'{binding,tokenId}' IS DISTINCT FROM ob.raw_log->>'tokenId')
   OR (SELECT count(*) FROM jsonb_array_elements(rq.request->'evaluations') x WHERE x.value->>'transactionHash'=ob.transaction_hash
    AND x.value->>'logIndex'=ob.log_index::text AND x.value->'evidence'=ev.evidence)<>1 THEN RETURN false;END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION polygon_live_activity.assert_bound_valid() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF polygon_live_activity.bound_state_valid(COALESCE(NEW.session_id,OLD.session_id)) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete bound skip bundle' USING ERRCODE='23514';END IF;
 RETURN NULL;
END $$;
DO $$ DECLARE n text;BEGIN
 FOREACH n IN ARRAY ARRAY['bound_requests','evaluations'] LOOP
  EXECUTE format('CREATE CONSTRAINT TRIGGER complete_bound_skip AFTER INSERT OR UPDATE OR DELETE ON polygon_live_activity.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_live_activity.assert_bound_valid()',n);
 END LOOP;
 FOREACH n IN ARRAY ARRAY['stream','operations','observations','decisions','conflicts'] LOOP
  EXECUTE format('CREATE CONSTRAINT TRIGGER complete_bound_extension AFTER INSERT OR UPDATE OR DELETE ON polygon_live_activity.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_live_activity.assert_bound_valid()',n);
 END LOOP;
END $$;
