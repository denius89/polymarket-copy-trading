CREATE FUNCTION live_buy_core.compute_state_at(sid uuid,v bigint,snapshot_id uuid,at_time timestamptz) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 WITH i AS (SELECT * FROM live_buy_core.intents WHERE session_id=sid AND version<=v),
 e AS (SELECT * FROM live_buy_core.executions WHERE session_id=sid AND version<=v),
 f AS (SELECT f.* FROM live_buy_core.fills f JOIN e USING(session_id,intent_id)),
 pending AS (SELECT i.* FROM i LEFT JOIN e ON e.intent_id=i.id WHERE e.id IS NULL),
 p AS (SELECT k.condition_id,k.token_id,
 (SELECT live_buy_core.sumq(f.notional) FROM f JOIN i ON f.intent_id=i.id WHERE i.condition_id=k.condition_id AND i.token_id=k.token_id) AS cost,
 (SELECT live_buy_core.sumq(f.net) FROM f JOIN i ON f.intent_id=i.id WHERE i.condition_id=k.condition_id AND i.token_id=k.token_id) AS quantity,
 (SELECT live_buy_core.sumq(x.notional) FROM pending x WHERE x.condition_id=k.condition_id AND x.token_id=k.token_id) AS reserved
 FROM (SELECT DISTINCT condition_id,token_id FROM i) k),
 d AS (SELECT k.day,
 (SELECT live_buy_core.sumq(f.notional) FROM f,live_buy_core.scopes scope WHERE scope.session_id=sid AND (f.executed_at AT TIME ZONE scope.timezone_name)::date=k.day) AS used,
 CASE WHEN k.day=(at_time AT TIME ZONE scope.timezone_name)::date THEN (SELECT live_buy_core.sumq(x.notional) FROM pending x) ELSE live_buy_core.q(0,1) END AS reserved
 FROM (SELECT quota_day AS day FROM i UNION SELECT (f.executed_at AT TIME ZONE scope.timezone_name)::date FROM f,live_buy_core.scopes scope WHERE scope.session_id=sid
 UNION SELECT (at_time AT TIME ZONE scope.timezone_name)::date FROM live_buy_core.scopes scope WHERE scope.session_id=sid) k,
 live_buy_core.scopes scope WHERE scope.session_id=sid),
 money AS (SELECT live_buy_core.subq(s.budget,(SELECT live_buy_core.sumq(live_buy_core.addq(f.notional,f.cash_fee)) FROM f)) AS cash,
 (SELECT live_buy_core.sumq(reserved_cash) FROM pending) AS reserved,
 (SELECT live_buy_core.sumq(cash_fee) FROM f) AS expenses FROM live_buy_core.scopes s WHERE session_id=sid)
 SELECT jsonb_build_object('schemaVersion','paper-buy-core-state-v1','sessionId',sid,'version',v::text,'snapshotId',snapshot_id,
 'cash',cash,'reservedCash',reserved,'freeCash',live_buy_core.subq(cash,reserved),'cashExpenses',expenses,
 'positions',COALESCE((SELECT jsonb_agg(jsonb_build_object('conditionId',condition_id,'tokenId',token_id,'cost',cost,'quantity',quantity,'reserved',reserved) ORDER BY condition_id COLLATE "C",token_id COLLATE "C") FROM p),'[]'::jsonb),
 'daily',COALESCE((SELECT jsonb_agg(jsonb_build_object('day',day::text,'used',used,'reserved',reserved) ORDER BY day) FROM d),'[]'::jsonb)) FROM money
$$;
CREATE FUNCTION live_buy_core.event_time(sid uuid,v bigint) RETURNS timestamptz LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE((SELECT admitted_at FROM live_buy_core.intents WHERE session_id=sid AND version=v),
 (SELECT settled_at FROM live_buy_core.executions WHERE session_id=sid AND version=v),
 (SELECT opened_at FROM live_buy_core.scopes WHERE session_id=sid AND v=1))
$$;
CREATE FUNCTION live_buy_core.compute_state(sid uuid,v bigint,snapshot_id uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT live_buy_core.compute_state_at(sid,v,snapshot_id,live_buy_core.event_time(sid,v))
$$;
CREATE FUNCTION live_buy_core.read_state(sid uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT s.data FROM live_buy_core.heads h JOIN live_buy_core.snapshots s USING(session_id,version) WHERE h.session_id=sid
$$;
CREATE FUNCTION live_buy_core.lookup(sid uuid,cid uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT result FROM live_buy_core.receipts WHERE session_id=sid AND command_id=cid
$$;
-- Owner-only local fixture/bootstrap boundary. Not granted to application identities.
CREATE FUNCTION live_buy_core.bootstrap(sid uuid,uid uuid,rid uuid,initial_ref uuid,budget jsonb,plimit jsonb,dlimit jsonb,zone_name text) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE sn uuid:=gen_random_uuid();t timestamptz:=live_buy_core.decision_time();
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001';END IF;
 INSERT INTO live_buy_core.scopes VALUES(sid,uid,rid,'polymarket',initial_ref,zone_name,(t AT TIME ZONE zone_name)::date,t,budget,plimit,dlimit);
 INSERT INTO live_buy_core.snapshots VALUES(sid,1,sn,live_buy_core.compute_state(sid,1,sn));
 INSERT INTO live_buy_core.heads VALUES(sid,1);
END $$;
CREATE FUNCTION live_buy_core.snapshot(sid uuid,v bigint) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE sn uuid:=gen_random_uuid();st jsonb;p jsonb;
BEGIN
 st:=live_buy_core.compute_state(sid,v,sn);
 INSERT INTO live_buy_core.snapshots VALUES(sid,v,sn,st);
 UPDATE live_buy_core.heads SET version=v WHERE session_id=sid AND version=v-1;
 IF NOT FOUND THEN RAISE EXCEPTION 'financial version conflict' USING ERRCODE='40001';END IF;
 FOR p IN SELECT value FROM jsonb_array_elements(st->'positions') LOOP
  INSERT INTO live_buy_core.positions VALUES(sid,p->>'conditionId',p->>'tokenId',p->'cost',p->'quantity',p->'reserved')
  ON CONFLICT(session_id,condition_id,token_id) DO UPDATE SET cost=EXCLUDED.cost,quantity=EXCLUDED.quantity,reserved=EXCLUDED.reserved;
 END LOOP;
 RETURN st;
END $$;
CREATE FUNCTION live_buy_core.record_result(sid uuid,cid uuid,iid uuid,k text,req jsonb,v bigint,execution uuid DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE st jsonb;r jsonb;
BEGIN
 st:=live_buy_core.snapshot(sid,v);
 r:=jsonb_build_object('schemaVersion','paper-buy-core-result-v1','sessionId',sid,'commandId',cid,'kind',k,'intentId',iid,'version',v::text,'state',st);
 IF execution IS NOT NULL THEN r:=r||jsonb_build_object('executionId',execution);END IF;
 INSERT INTO live_buy_core.receipts VALUES(sid,cid,iid,k,req,r,v);
 INSERT INTO live_buy_core.audit VALUES(sid,cid,k);
 INSERT INTO live_buy_core.outbox VALUES(sid,cid,r);
 RETURN r;
END $$;
CREATE FUNCTION live_buy_core.shape(req jsonb,k text) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE n text;f jsonb;
BEGIN
 IF req IS NULL OR octet_length(req::text)>1048576 THEN RETURN false; END IF;
 IF k='reserve' THEN
  IF live_buy_core.keys(req,ARRAY['commandId','intentId','observationId','expectedVersion','conditionId','tokenId','sizingRevisionId','admissionRevisionId','evidenceRef','desiredNotional','fullQuantity','quantityStep','priceCap','feeCashBound','delayMs']) IS DISTINCT FROM true THEN RETURN false;END IF;
  FOREACH n IN ARRAY ARRAY['observationId','sizingRevisionId','admissionRevisionId'] LOOP
   IF jsonb_typeof(req->n) IS DISTINCT FROM 'string' OR (req->>n~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') IS DISTINCT FROM true THEN RETURN false;END IF;
  END LOOP;
  FOREACH n IN ARRAY ARRAY['conditionId','tokenId'] LOOP
   IF jsonb_typeof(req->n) IS DISTINCT FROM 'string' OR length(req->>n) NOT BETWEEN 1 AND 256 OR (req->>n~'^[A-Za-z0-9:_-]+$') IS DISTINCT FROM true THEN RETURN false;END IF;
  END LOOP;
  FOREACH n IN ARRAY ARRAY['desiredNotional','fullQuantity','quantityStep','priceCap'] LOOP
   IF live_buy_core.positive(req->n) IS DISTINCT FROM true THEN RETURN false; END IF;
  END LOOP;
  IF live_buy_core.nonnegative(req->'feeCashBound') IS DISTINCT FROM true OR live_buy_core.cmp(req->'priceCap',live_buy_core.q(1,1))>0
   OR jsonb_typeof(req->'delayMs') IS DISTINCT FROM 'string' OR (req->>'delayMs'~'^(0|[1-9][0-9]{0,8})$') IS DISTINCT FROM true THEN RETURN false;END IF;
 ELSIF k='settle' THEN
  IF live_buy_core.keys(req,ARRAY['commandId','intentId','expectedVersion','evidenceRef','confirmationId','fills']) IS DISTINCT FROM true
   OR jsonb_typeof(req->'fills') IS DISTINCT FROM 'array' THEN RETURN false;END IF;
  IF jsonb_array_length(req->'fills') NOT BETWEEN 1 AND 128 OR jsonb_typeof(req->'confirmationId') IS DISTINCT FROM 'string'
   OR (req->>'confirmationId'~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') IS DISTINCT FROM true THEN RETURN false;END IF;
  FOR f IN SELECT value FROM jsonb_array_elements(req->'fills') LOOP
   IF live_buy_core.keys(f,ARRAY['fillId','price','quantityGross','quantityFee','cashFee','executedAt']) IS DISTINCT FROM true
    OR jsonb_typeof(f->'fillId') IS DISTINCT FROM 'string' OR (f->>'fillId'~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') IS DISTINCT FROM true
    OR jsonb_typeof(f->'executedAt') IS DISTINCT FROM 'string' OR (f->>'executedAt'~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$') IS DISTINCT FROM true
    OR live_buy_core.positive(f->'price') IS DISTINCT FROM true OR live_buy_core.positive(f->'quantityGross') IS DISTINCT FROM true
    OR live_buy_core.nonnegative(f->'quantityFee') IS DISTINCT FROM true OR live_buy_core.nonnegative(f->'cashFee') IS DISTINCT FROM true
   THEN RETURN false;END IF;
  END LOOP;
 ELSE RETURN false;
 END IF;
 FOREACH n IN ARRAY ARRAY['commandId','intentId'] LOOP
  IF jsonb_typeof(req->n) IS DISTINCT FROM 'string' OR (req->>n~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') IS DISTINCT FROM true THEN RETURN false;END IF;
 END LOOP;
 RETURN jsonb_typeof(req->'expectedVersion')='string' AND req->>'expectedVersion'~'^[1-9][0-9]{0,17}$'
 AND jsonb_typeof(req->'evidenceRef')='string' AND length(req->>'evidenceRef') BETWEEN 1 AND 256;
END $$;
