-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
-- Closed metadata/skip union. No money, fill, order or lot path exists in this package.
CREATE FUNCTION polygon_live_activity.reason(v text) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(v=ANY(ARRAY['not_buy','signal_expired','market_binding_unavailable','market_unavailable','book_unavailable',
 'book_stale','clock_unproven','profile_unavailable','fee_profile_unavailable','invalid_book','insufficient_liquidity',
 'below_minimum','precision_unavailable','insufficient_funds','position_limit_exceeded','daily_limit_exceeded',
 'source_unavailable','one_buy_scope_complete']),false)
$$;
CREATE FUNCTION polygon_live_activity.binding_shape(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE k text;
BEGIN
 IF v='null'::jsonb THEN RETURN true;END IF;
 IF polygon.exact_keys(v,ARRAY['tokenId','conditionId','outcome','marketTitle','protocol','marketSha256']) IS DISTINCT FROM true
  OR NOT polygon_live_activity.uint(v->'tokenId') OR NOT polygon_live_activity.hash_value(v->'conditionId')
  OR NOT polygon_live_activity.sha_value(v->'marketSha256') OR COALESCE(v->>'protocol' IN('v1','v2'),false)=false THEN RETURN false;END IF;
 FOREACH k IN ARRAY ARRAY['outcome','marketTitle'] LOOP
  IF jsonb_typeof(v->k) IS DISTINCT FROM 'string' OR length(v->>k) NOT BETWEEN 1 AND (CASE WHEN k='marketTitle' THEN 2048 ELSE 256 END) OR v->>k ~ '[[:cntrl:]]' THEN RETURN false;END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION polygon_live_activity.evidence_shape(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(polygon.exact_keys(v,ARRAY['schemaVersion','kind','reason','evidenceSha256','binding'])
  AND v->>'schemaVersion'='paper-buy-evidence-v1' AND v->>'kind'='skip'
  AND polygon_live_activity.reason(v->>'reason') AND polygon_live_activity.sha_value(v->'evidenceSha256')
  AND polygon_live_activity.binding_shape(v->'binding'),false)
$$;
CREATE TABLE polygon_live_activity.bound_requests(
 operation_id uuid NOT NULL,session_id uuid NOT NULL,request jsonb NOT NULL,
 PRIMARY KEY(session_id,operation_id),request_digest text NOT NULL,created_at timestamptz NOT NULL,
 FOREIGN KEY(operation_id,session_id) REFERENCES polygon_live_activity.operations(id,session_id) DEFERRABLE INITIALLY DEFERRED,
 CHECK(request_digest=polygon_live_activity.digest('paper-bound-skip-envelope-v1'||chr(10)||request::text)),
 CHECK(request#>>'{ingest,operationId}'=operation_id::text AND request#>>'{ingest,sessionId}'=session_id::text),
 CHECK(request->'expectedSnapshotVersion'='"1"'::jsonb),UNIQUE(operation_id,session_id)
);
CREATE TABLE polygon_live_activity.evaluations(
 observation_id uuid PRIMARY KEY,session_id uuid NOT NULL,operation_id uuid NOT NULL,sequence bigint NOT NULL,
 decision_id uuid NOT NULL UNIQUE REFERENCES polygon_live_activity.decisions(id) DEFERRABLE INITIALLY DEFERRED,
 evidence jsonb NOT NULL CHECK(polygon_live_activity.evidence_shape(evidence)),created_at timestamptz NOT NULL,
 FOREIGN KEY(operation_id,session_id) REFERENCES polygon_live_activity.bound_requests(operation_id,session_id) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(observation_id,session_id,sequence) REFERENCES polygon_live_activity.observations(id,session_id,sequence),
 UNIQUE(session_id,sequence)
);
CREATE TRIGGER immutable_bound_request BEFORE UPDATE OR DELETE ON polygon_live_activity.bound_requests FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_bound_evaluation BEFORE UPDATE OR DELETE ON polygon_live_activity.evaluations FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
-- Install only before C06/arm on a fresh clone: no historical decision is modified.
ALTER TABLE polygon_live_activity.decisions DROP CONSTRAINT decisions_detail_code_check;
ALTER TABLE polygon_live_activity.decisions DROP CONSTRAINT decisions_policy_version_check;
ALTER TABLE polygon_live_activity.decisions DROP CONSTRAINT decisions_checks_check;
ALTER TABLE polygon_live_activity.decisions ADD CONSTRAINT bound_skip_detail CHECK(polygon_live_activity.reason(detail_code));
ALTER TABLE polygon_live_activity.decisions ADD CONSTRAINT bound_skip_policy CHECK(policy_version='paper-bound-skip-v1');
ALTER TABLE polygon_live_activity.decisions ADD CONSTRAINT bound_skip_checks CHECK(jsonb_typeof(checks)='object');
-- status='skipped' and reason_code='context_invalid' constraints deliberately remain.
CREATE FUNCTION polygon_live_activity.write_decision(oid uuid,es jsonb,t timestamptz) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ob polygon_live_activity.observations;e jsonb;did uuid:=gen_random_uuid();
BEGIN
 SELECT * INTO STRICT ob FROM polygon_live_activity.observations WHERE id=oid;
 SELECT value->'evidence' INTO STRICT e FROM jsonb_array_elements(es) WHERE value->>'transactionHash'=ob.transaction_hash AND (value->>'logIndex')::numeric=ob.log_index;
 IF polygon_live_activity.evidence_shape(e) IS DISTINCT FROM true OR (e->'binding'<>'null'::jsonb AND e#>>'{binding,tokenId}'<>ob.raw_log->>'tokenId')
 THEN RAISE EXCEPTION 'invalid binding for source observation' USING ERRCODE='22023';END IF;
 INSERT INTO polygon_live_activity.decisions SELECT did,ob.id,ob.session_id,ob.sequence,t,current_settings_revision_id,'skipped','context_invalid',
  e->>'reason','paper-bound-skip-v1',jsonb_build_object('evidence',e,'executionAdmission','blocked') FROM polygon.paper_sessions WHERE id=ob.session_id;
 INSERT INTO polygon_live_activity.evaluations VALUES(ob.id,ob.session_id,ob.operation_id,ob.sequence,did,e,t);
END $$;
