\set ON_ERROR_STOP on
-- Forward-only correction of installed candidate 43bb6f5; no data changes.
BEGIN;
SET LOCAL ROLE v00_upstream_owner;
CREATE OR REPLACE FUNCTION v00_upstream.capture(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE started timestamptz:=clock_timestamp(); initial_epoch bigint; g v00_upstream.gate;
  a v00_upstream.admissions; cmp v00_upstream.comparisons; prior_result v00_upstream.results; e jsonb; expiry timestamptz;
BEGIN
  -- This role is called before the trusted ingress queues/dispatches the handler.
  SELECT epoch INTO STRICT initial_epoch FROM v00_upstream.gate WHERE singleton;
  PERFORM v00_upstream.keys(p,ARRAY['context_id','proof_digest','operation_id','action','fingerprint','comparison_hmac','comparison_key_id','executor_id','executor_proof_digest']);
  IF p->>'comparison_hmac' !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'invalid comparison'; END IF;
  e:=v00_upstream.lock_scope(p); IF e IS NOT NULL THEN RETURN e; END IF;
  SELECT * INTO a FROM v00_upstream.admissions WHERE context_id=(p->>'context_id')::uuid AND operation_id=(p->>'operation_id')::uuid;
  IF FOUND THEN
    SELECT * INTO prior_result FROM v00_upstream.results WHERE context_id=a.context_id AND operation_id=a.operation_id;
    IF FOUND AND v00_upstream.valid_result(prior_result) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
    SELECT * INTO STRICT cmp FROM v00_upstream.comparisons WHERE admission_id=a.id;
    IF a.action<>p->>'action' OR a.fingerprint<>p->>'fingerprint' OR cmp.hmac<>p->>'comparison_hmac' OR cmp.key_id<>p->>'comparison_key_id' THEN
      RETURN v00_session.error(409,'KEY_REUSE_CONFLICT');
    END IF;
    RETURN jsonb_build_object('http',200,'admission_id',a.id,'created',false);
  END IF;
  SELECT * INTO STRICT g FROM v00_upstream.gate WHERE singleton;
  IF initial_epoch<>g.epoch OR clock_timestamp()>=started+interval '10 seconds' THEN RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); END IF;
  -- An unresolved earlier attempt on this actor cannot be bypassed with a new scope.
  IF EXISTS(SELECT 1 FROM v00_upstream.admissions x JOIN v00_upstream.contexts xc ON xc.id=x.context_id
     JOIN v00_upstream.contexts own ON own.id=(p->>'context_id')::uuid
     WHERE xc.actor_id=own.actor_id AND NOT EXISTS(SELECT 1 FROM v00_upstream.results r WHERE r.context_id=x.context_id AND r.operation_id=x.operation_id)) THEN
    RETURN v00_session.error(503,'SERVICE_UNAVAILABLE');
  END IF;
  SELECT expires_at INTO STRICT expiry FROM v00_session.contexts WHERE id=(p->>'context_id')::uuid;
  INSERT INTO v00_upstream.admissions(context_id,operation_id,action,fingerprint,executor_id,executor_proof_digest,epoch,captured_at,deadline_at)
    VALUES((p->>'context_id')::uuid,(p->>'operation_id')::uuid,p->>'action',p->>'fingerprint',(p->>'executor_id')::uuid,p->>'executor_proof_digest',
      initial_epoch,started,started+interval '10 seconds') RETURNING * INTO a;
  INSERT INTO v00_upstream.comparisons VALUES(a.id,p->>'comparison_hmac',p->>'comparison_key_id',expiry);
  RETURN jsonb_build_object('http',201,'admission_id',a.id,'created',true);
END $$;
COMMIT;
