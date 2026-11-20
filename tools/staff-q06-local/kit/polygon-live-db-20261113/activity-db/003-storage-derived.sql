-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE TABLE polygon_live_activity.operations(
 id uuid NOT NULL,session_id uuid NOT NULL REFERENCES polygon_live_activity.assignments(session_id),ordinal bigint NOT NULL CHECK(ordinal>0),
 PRIMARY KEY(session_id,id),UNIQUE(session_id,ordinal),
 kind text NOT NULL CHECK(kind IN('arm','ingest','stop')), request jsonb NOT NULL,
 request_digest text NOT NULL CHECK(request_digest~'^[0-9a-f]{64}$'),result jsonb NOT NULL,
 created_at timestamptz NOT NULL,
 UNIQUE(id,session_id),
 CHECK(polygon_live_activity.request_shape(request,kind)),
 CHECK(request_digest=polygon_live_activity.digest(kind||chr(10)||request::text)),
 CHECK(request->>'operationId'=id::text AND request->>'sessionId'=session_id::text),
 CHECK(result->>'operationId'=id::text AND result->>'sessionId'=session_id::text),
 CHECK(jsonb_typeof(result)='object' AND result ?& ARRAY['operationId','kind','sessionId']),
 CHECK((kind='ingest' AND result->>'kind' IN('ingest','ingest_blocked')) OR result->>'kind'=kind)
);
CREATE TABLE polygon_live_activity.stream(
 session_id uuid PRIMARY KEY REFERENCES polygon_live_activity.assignments(session_id),
 baseline jsonb NOT NULL CHECK(polygon_live_activity.header(baseline)),armed_at timestamptz NOT NULL,
 arm_operation_id uuid NOT NULL,last_operation_id uuid NOT NULL,
 last_range_operation_id uuid,checkpoint jsonb NOT NULL CHECK(polygon_live_activity.checkpoint(checkpoint)),
 high_watermark bigint NOT NULL DEFAULT 0 CHECK(high_watermark>=0),
 status text NOT NULL CHECK(status IN('observing','source_unavailable','reconciliation_required','stopped')),
 last_observed_at timestamptz,
 FOREIGN KEY(arm_operation_id,session_id) REFERENCES polygon_live_activity.operations(id,session_id) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(last_operation_id,session_id) REFERENCES polygon_live_activity.operations(id,session_id) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(last_range_operation_id,session_id) REFERENCES polygon_live_activity.operations(id,session_id) DEFERRABLE INITIALLY DEFERRED,
 CHECK(last_observed_at IS NULL OR last_observed_at>=armed_at),
 CHECK((last_range_operation_id IS NULL)=(last_observed_at IS NULL))
);
CREATE TABLE polygon_live_activity.observations(
 id uuid PRIMARY KEY,session_id uuid NOT NULL REFERENCES polygon_live_activity.stream(session_id),
 operation_id uuid NOT NULL,transaction_hash text NOT NULL CHECK(transaction_hash~'^0x[0-9a-f]{64}$'),
 log_index numeric(78,0) NOT NULL CHECK(log_index>=0),raw_log jsonb NOT NULL CHECK(polygon_live_activity.log_shape(raw_log)),
 header jsonb NOT NULL CHECK(polygon_live_activity.header(header)),semantic_preimage text NOT NULL,record_hash text NOT NULL,
 received_at timestamptz NOT NULL,sequence bigint CHECK(sequence>0),classification text NOT NULL CHECK(classification IN('accepted','excluded')),
 FOREIGN KEY(operation_id,session_id) REFERENCES polygon_live_activity.operations(id,session_id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(session_id,transaction_hash,log_index),UNIQUE(session_id,sequence),UNIQUE(id,session_id,sequence),
 CHECK((classification='accepted')=(sequence IS NOT NULL)),
 CHECK(raw_log->>'transactionHash'=transaction_hash AND (raw_log->>'logIndex')::numeric=log_index),
 CHECK(raw_log->'blockNumber'=header->'number' AND raw_log->'blockHash'=header->'hash'),
 CHECK(semantic_preimage=polygon_live_activity.semantic(raw_log,header)),
 CHECK(record_hash=polygon_live_activity.digest(semantic_preimage))
);
CREATE TABLE polygon_live_activity.decisions(
 id uuid PRIMARY KEY,observation_id uuid NOT NULL UNIQUE,session_id uuid NOT NULL,sequence bigint NOT NULL,
 decided_at timestamptz NOT NULL,settings_revision_id uuid NOT NULL REFERENCES polygon.settings_revisions(id),
 status text NOT NULL CHECK(status='skipped'),reason_code text NOT NULL CHECK(reason_code='context_invalid'),
 detail_code text NOT NULL CHECK(detail_code='market_binding_unavailable'),
 policy_version text NOT NULL CHECK(policy_version='paper-chain-observation-skip-v1'),checks jsonb NOT NULL,
 FOREIGN KEY(observation_id,session_id,sequence) REFERENCES polygon_live_activity.observations(id,session_id,sequence) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(session_id,sequence),
 CHECK(checks='[{"check":"market_binding","status":"unavailable","reasonCode":"context_invalid","detailCode":"market_binding_unavailable"},{"check":"execution_admission","status":"not_evaluated","dependency":"market_binding"}]'::jsonb)
);
CREATE TABLE polygon_live_activity.conflicts(
 id uuid PRIMARY KEY,operation_id uuid NOT NULL,session_id uuid NOT NULL,UNIQUE(session_id,operation_id),
 code text NOT NULL CHECK(code IN('baseline_hash_mismatch','canonical_chain_mismatch','future_source_timestamp','log_identity_conflict')),
 details jsonb NOT NULL CHECK(jsonb_typeof(details)='array' AND jsonb_array_length(details)>0),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256~'^[0-9a-f]{64}$'),created_at timestamptz NOT NULL,
 FOREIGN KEY(operation_id,session_id) REFERENCES polygon_live_activity.operations(id,session_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TRIGGER immutable_operation BEFORE UPDATE OR DELETE ON polygon_live_activity.operations FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_observation BEFORE UPDATE OR DELETE ON polygon_live_activity.observations FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_decision BEFORE UPDATE OR DELETE ON polygon_live_activity.decisions FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_conflict BEFORE UPDATE OR DELETE ON polygon_live_activity.conflicts FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
