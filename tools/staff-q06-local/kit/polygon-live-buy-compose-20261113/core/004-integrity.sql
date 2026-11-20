CREATE FUNCTION live_buy_core.valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s live_buy_core.scopes;h bigint;r live_buy_core.receipts;i live_buy_core.intents;e live_buy_core.executions;
 sn live_buy_core.snapshots;g live_buy_core.reservation_events;settled live_buy_core.reservation_events;
 n bigint;st jsonb;p jsonb;d jsonb;prior jsonb;qty jsonb;cost jsonb;fee jsonb;steps jsonb;want jsonb;actual jsonb;
 z jsonb:=live_buy_core.q(0,1);
BEGIN
 SELECT * INTO s FROM live_buy_core.scopes WHERE session_id=sid;
 SELECT version INTO h FROM live_buy_core.heads WHERE session_id=sid;
 IF s.session_id IS NULL OR h IS NULL THEN RETURN false;END IF;
 SELECT count(*) INTO n FROM live_buy_core.snapshots WHERE session_id=sid;
 IF n<>h OR (SELECT min(version) FROM live_buy_core.snapshots WHERE session_id=sid)<>1
 OR (SELECT max(version) FROM live_buy_core.snapshots WHERE session_id=sid)<>h
 OR (SELECT count(*) FROM live_buy_core.receipts WHERE session_id=sid)<>h-1 THEN RETURN false;END IF;
 FOR sn IN SELECT * FROM live_buy_core.snapshots WHERE session_id=sid ORDER BY version LOOP
  st:=live_buy_core.compute_state(sid,sn.version,sn.id);
  IF sn.data IS DISTINCT FROM st OR live_buy_core.nonnegative(st->'freeCash') IS DISTINCT FROM true THEN RETURN false;END IF;
  FOR p IN SELECT jsonb_build_object('cost',live_buy_core.sumq(value->'cost'),'reserved',live_buy_core.sumq(value->'reserved')) FROM jsonb_array_elements(st->'positions') GROUP BY value->>'conditionId' LOOP
   IF live_buy_core.cmp(live_buy_core.addq(p->'cost',p->'reserved'),s.position_limit)>0 THEN RETURN false;END IF;
  END LOOP;
  FOR d IN SELECT value FROM jsonb_array_elements(st->'daily') LOOP
   IF live_buy_core.cmp(live_buy_core.addq(d->'used',d->'reserved'),s.daily_limit)>0 THEN RETURN false;END IF;
  END LOOP;
 END LOOP;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('conditionId',pos.condition_id,'tokenId',pos.token_id,'cost',pos.cost,'quantity',pos.quantity,'reserved',pos.reserved) ORDER BY pos.condition_id COLLATE "C",pos.token_id COLLATE "C"),'[]'::jsonb)
 INTO actual FROM live_buy_core.positions pos WHERE pos.session_id=sid;
 IF actual IS DISTINCT FROM live_buy_core.read_state(sid)->'positions' THEN RETURN false;END IF;
 FOR r IN SELECT * FROM live_buy_core.receipts WHERE session_id=sid LOOP
  SELECT * INTO sn FROM live_buy_core.snapshots WHERE session_id=sid AND version=r.version;
  IF sn.id IS NULL OR live_buy_core.shape(r.request,r.kind) IS DISTINCT FROM true
   OR r.request->>'commandId' IS DISTINCT FROM r.command_id::text OR r.request->>'intentId' IS DISTINCT FROM r.intent_id::text
   OR r.request->>'expectedVersion' IS DISTINCT FROM (r.version-1)::text THEN RETURN false;END IF;
  want:=jsonb_build_object('schemaVersion','paper-buy-core-result-v1','sessionId',sid,'commandId',r.command_id,'kind',r.kind,'intentId',r.intent_id,'version',r.version::text,'state',sn.data);
  IF r.kind='settle' THEN
   SELECT * INTO e FROM live_buy_core.executions WHERE session_id=sid AND intent_id=r.intent_id;
   IF e.id IS NULL OR e.command_id<>r.command_id OR e.version<>r.version THEN RETURN false;END IF;
   want:=want||jsonb_build_object('executionId',e.id);
  ELSE
   IF NOT EXISTS(SELECT FROM live_buy_core.intents WHERE session_id=sid AND id=r.intent_id AND command_id=r.command_id AND version=r.version) THEN RETURN false;END IF;
  END IF;
  IF r.result IS DISTINCT FROM want OR NOT EXISTS(SELECT FROM live_buy_core.audit WHERE session_id=sid AND command_id=r.command_id AND kind=r.kind)
   OR NOT EXISTS(SELECT FROM live_buy_core.outbox WHERE session_id=sid AND command_id=r.command_id AND payload=r.result) THEN RETURN false;END IF;
 END LOOP;
 FOR i IN SELECT * FROM live_buy_core.intents WHERE session_id=sid LOOP
  SELECT * INTO r FROM live_buy_core.receipts WHERE session_id=sid AND command_id=i.command_id;
  IF r.kind IS DISTINCT FROM 'reserve' OR r.request IS DISTINCT FROM i.request OR r.intent_id IS DISTINCT FROM i.id OR r.version IS DISTINCT FROM i.version
   OR i.request->>'observationId' IS DISTINCT FROM i.observation_id::text OR i.request->>'conditionId' IS DISTINCT FROM i.condition_id
   OR i.request->>'tokenId' IS DISTINCT FROM i.token_id OR i.quota_day<>(i.admitted_at AT TIME ZONE s.timezone_name)::date
   OR i.not_before<>i.admitted_at+(i.request->>'delayMs')::integer*interval '1 millisecond'
   OR i.request->'desiredNotional'<>live_buy_core.mulq(i.request->'fullQuantity',i.request->'priceCap') THEN RETURN false;END IF;
  steps:=live_buy_core.divq(i.request->'fullQuantity',i.request->'quantityStep');
  qty:=live_buy_core.mulq(live_buy_core.q(div((steps->>'n')::numeric,(steps->>'d')::numeric),1),i.request->'quantityStep');
  IF qty<>i.quantity OR i.notional<>live_buy_core.mulq(qty,i.request->'priceCap') OR i.reserved_cash<>live_buy_core.addq(i.notional,i.request->'feeCashBound') THEN RETURN false;END IF;
  SELECT live_buy_core.compute_state_at(sid,version,id,i.admitted_at) INTO prior FROM live_buy_core.snapshots WHERE session_id=sid AND version=i.version-1;
  SELECT jsonb_build_object('cost',live_buy_core.sumq(value->'cost'),'reserved',live_buy_core.sumq(value->'reserved')) INTO p FROM jsonb_array_elements(prior->'positions') WHERE value->>'conditionId'=i.condition_id;
  SELECT value INTO d FROM jsonb_array_elements(prior->'daily') WHERE value->>'day'=i.quota_day::text;
  IF prior IS NULL OR live_buy_core.cmp(live_buy_core.addq(i.request->'desiredNotional',i.request->'feeCashBound'),prior->'freeCash')>0
   OR live_buy_core.cmp(live_buy_core.addq(i.request->'desiredNotional',live_buy_core.addq(COALESCE(p->'cost',z),COALESCE(p->'reserved',z))),s.position_limit)>0
   OR live_buy_core.cmp(live_buy_core.addq(i.request->'desiredNotional',live_buy_core.addq(COALESCE(d->'used',z),COALESCE(d->'reserved',z))),s.daily_limit)>0 THEN RETURN false;END IF;
  SELECT * INTO g FROM live_buy_core.reservation_events WHERE session_id=sid AND intent_id=i.id AND kind='grant';
  IF g.intent_id IS NULL OR g.notional<>i.notional OR g.cash<>i.reserved_cash OR g.released_cash<>z THEN RETURN false;END IF;
  SELECT * INTO e FROM live_buy_core.executions WHERE session_id=sid AND intent_id=i.id;
  SELECT * INTO settled FROM live_buy_core.reservation_events WHERE session_id=sid AND intent_id=i.id AND kind='settle';
  IF e.id IS NULL THEN
   IF settled.intent_id IS NOT NULL THEN RETURN false;END IF;
   CONTINUE;
  END IF;
  SELECT * INTO r FROM live_buy_core.receipts WHERE session_id=sid AND command_id=e.command_id;
  IF r.kind IS DISTINCT FROM 'settle' OR r.intent_id IS DISTINCT FROM i.id OR r.version IS DISTINCT FROM e.version OR e.version<=i.version
   OR e.settled_at<i.not_before OR e.confirmation_id::text IS DISTINCT FROM r.request->>'confirmationId' THEN RETURN false;END IF;
  SELECT live_buy_core.sumq(gross),live_buy_core.sumq(notional),live_buy_core.sumq(cash_fee),count(*) INTO qty,cost,fee,n FROM live_buy_core.fills WHERE session_id=sid AND intent_id=i.id;
  IF n<1 OR n<>jsonb_array_length(r.request->'fills') OR qty<>i.quantity OR live_buy_core.cmp(cost,i.notional)>0
   OR live_buy_core.cmp(fee,i.request->'feeCashBound')>0 OR EXISTS(SELECT FROM live_buy_core.fills WHERE session_id=sid AND intent_id=i.id AND (live_buy_core.cmp(price,i.request->'priceCap')>0 OR executed_at<i.not_before OR executed_at>e.settled_at)) THEN RETURN false;END IF;
  SELECT jsonb_agg(jsonb_build_object('fillId',id,'price',price,'quantityGross',gross,'quantityFee',quantity_fee,'cashFee',cash_fee,'executedAt',to_char(executed_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')) ORDER BY ordinal)
  INTO actual FROM live_buy_core.fills WHERE session_id=sid AND intent_id=i.id;
  IF actual IS DISTINCT FROM r.request->'fills' OR (SELECT max(ordinal) FROM live_buy_core.fills WHERE session_id=sid AND intent_id=i.id)<>n THEN RETURN false;END IF;
  IF settled.intent_id IS NULL OR settled.notional<>cost OR settled.cash<>live_buy_core.addq(cost,fee)
   OR settled.released_cash<>live_buy_core.subq(i.reserved_cash,settled.cash) THEN RETURN false;END IF;
  IF EXISTS(SELECT FROM live_buy_core.fills f LEFT JOIN live_buy_core.lots l ON l.session_id=f.session_id AND l.fill_id=f.id
    WHERE f.session_id=sid AND f.intent_id=i.id AND (l.fill_id IS NULL OR l.intent_id<>i.id OR l.original_quantity<>f.net OR l.original_cost<>f.notional OR l.attributed_cash_fee<>f.cash_fee OR l.attributed_quantity_fee<>f.quantity_fee)) THEN RETURN false;END IF;
  SELECT jsonb_agg(jsonb_build_array(asset,account,amount) ORDER BY asset,account) INTO want FROM live_buy_core.expected_journal(sid,i.id);
  SELECT jsonb_agg(jsonb_build_array(asset,account,amount) ORDER BY asset,account) INTO actual FROM live_buy_core.journal_entries WHERE session_id=sid AND intent_id=i.id;
  IF actual IS DISTINCT FROM want THEN RETURN false;END IF;
  IF EXISTS(SELECT asset FROM live_buy_core.journal_entries WHERE session_id=sid AND intent_id=i.id GROUP BY asset HAVING live_buy_core.sumq(amount)<>z) THEN RETURN false;END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION live_buy_core.enforce() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF live_buy_core.valid(COALESCE(NEW.session_id,OLD.session_id)) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete financial graph' USING ERRCODE='23514';END IF;
 RETURN NULL;
END $$;
DO $$ DECLARE n text;BEGIN
 FOREACH n IN ARRAY ARRAY['scopes','intents','executions','fills','lots','reservation_events','journal_entries','receipts','audit','outbox','snapshots','heads','positions'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER complete_graph AFTER INSERT OR UPDATE OR DELETE ON live_buy_core.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION live_buy_core.enforce()',n);
 END LOOP;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA live_buy_core FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA live_buy_core FROM PUBLIC;

CREATE FUNCTION live_buy_core.scope_key_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.session_id IS DISTINCT FROM OLD.session_id THEN RAISE EXCEPTION 'financial scope key is immutable' USING ERRCODE='23514';END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER immutable_scope_key BEFORE UPDATE ON live_buy_core.positions FOR EACH ROW EXECUTE FUNCTION live_buy_core.scope_key_guard();
CREATE TRIGGER immutable_scope_key BEFORE UPDATE ON live_buy_core.heads FOR EACH ROW EXECUTE FUNCTION live_buy_core.scope_key_guard();
REVOKE ALL ON FUNCTION live_buy_core.scope_key_guard() FROM PUBLIC;
