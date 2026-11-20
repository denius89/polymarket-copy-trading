CREATE FUNCTION live_buy_core.reserve(sid uuid,req jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE h bigint;c live_buy_core.receipts;s live_buy_core.scopes;st jsonb;p jsonb;d jsonb;
 desired jsonb;qty jsonb;steps jsonb;notional jsonb;cash jsonb;t timestamptz;day date;z jsonb:=live_buy_core.q(0,1);
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001';END IF;
 IF live_buy_core.shape(req,'reserve') IS DISTINCT FROM true THEN RAISE EXCEPTION 'invalid reserve request' USING ERRCODE='22023';END IF;
 SELECT version INTO STRICT h FROM live_buy_core.heads WHERE session_id=sid FOR UPDATE;
 SELECT * INTO c FROM live_buy_core.receipts WHERE session_id=sid AND command_id=(req->>'commandId')::uuid;
 IF FOUND THEN
  IF c.kind<>'reserve' OR c.request IS DISTINCT FROM req THEN RAISE EXCEPTION 'key reuse conflict' USING ERRCODE='23505';END IF;
  RETURN c.result;
 END IF;
 IF h::text<>req->>'expectedVersion' THEN RAISE EXCEPTION 'financial version conflict' USING ERRCODE='40001';END IF;
 SELECT * INTO STRICT s FROM live_buy_core.scopes WHERE session_id=sid;
 t:=live_buy_core.decision_time();day:=(t AT TIME ZONE s.timezone_name)::date;
 st:=live_buy_core.compute_state_at(sid,h,(live_buy_core.read_state(sid)->>'snapshotId')::uuid,t);
 SELECT jsonb_build_object('cost',live_buy_core.sumq(value->'cost'),'reserved',live_buy_core.sumq(value->'reserved')) INTO p FROM jsonb_array_elements(st->'positions') WHERE value->>'conditionId'=req->>'conditionId';
 SELECT value INTO d FROM jsonb_array_elements(st->'daily') WHERE value->>'day'=day::text;
 desired:=req->'desiredNotional';
 IF desired<>live_buy_core.mulq(req->'fullQuantity',req->'priceCap') THEN RAISE EXCEPTION 'inconsistent capacity plan' USING ERRCODE='22023';END IF;
 IF live_buy_core.cmp(live_buy_core.addq(desired,req->'feeCashBound'),st->'freeCash')>0
 OR live_buy_core.cmp(live_buy_core.addq(desired,live_buy_core.addq(COALESCE(p->'cost',z),COALESCE(p->'reserved',z))),s.position_limit)>0
 OR live_buy_core.cmp(live_buy_core.addq(desired,live_buy_core.addq(COALESCE(d->'used',z),COALESCE(d->'reserved',z))),s.daily_limit)>0
 THEN RAISE EXCEPTION 'full desired capacity unavailable' USING ERRCODE='23514';END IF;
 steps:=live_buy_core.divq(req->'fullQuantity',req->'quantityStep');
 qty:=live_buy_core.mulq(live_buy_core.q(div((steps->>'n')::numeric,(steps->>'d')::numeric),1),req->'quantityStep');
 IF live_buy_core.positive(qty) IS DISTINCT FROM true THEN RAISE EXCEPTION 'normalized quantity empty' USING ERRCODE='22023';END IF;
 notional:=live_buy_core.mulq(qty,req->'priceCap');cash:=live_buy_core.addq(notional,req->'feeCashBound');
 INSERT INTO live_buy_core.intents VALUES(sid,(req->>'intentId')::uuid,(req->>'observationId')::uuid,(req->>'commandId')::uuid,h+1,
 req->>'conditionId',req->>'tokenId',req,qty,notional,cash,t,t+(req->>'delayMs')::integer*interval '1 millisecond',day);
 INSERT INTO live_buy_core.reservation_events VALUES(sid,(req->>'intentId')::uuid,'grant',notional,cash,z);
 RETURN live_buy_core.record_result(sid,(req->>'commandId')::uuid,(req->>'intentId')::uuid,'reserve',req,h+1);
END $$;
CREATE FUNCTION live_buy_core.expected_journal(sid uuid,iid uuid) RETURNS TABLE(asset text,account text,amount jsonb) LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 WITH total AS (SELECT live_buy_core.sumq(notional) n,live_buy_core.sumq(cash_fee) cf,live_buy_core.sumq(gross) g,live_buy_core.sumq(net) net,live_buy_core.sumq(quantity_fee) qf
 FROM live_buy_core.fills WHERE session_id=sid AND intent_id=iid), t AS (SELECT token_id FROM live_buy_core.intents WHERE session_id=sid AND id=iid),
 a AS (SELECT 'virtual_USD'::text asset,'paper_cash'::text account,live_buy_core.negq(live_buy_core.addq(n,cf)) amount FROM total
 UNION ALL SELECT 'virtual_USD','copied_position_cost',n FROM total
 UNION ALL SELECT 'virtual_USD','cash_fee',cf FROM total
 UNION ALL SELECT 'token:'||token_id,'acquired_quantity',live_buy_core.negq(g) FROM total,t
 UNION ALL SELECT 'token:'||token_id,'copied_position_quantity',net FROM total,t
 UNION ALL SELECT 'token:'||token_id,'quantity_fee',qf FROM total,t)
 SELECT * FROM a WHERE live_buy_core.cmp(amount,live_buy_core.q(0,1))<>0
$$;
CREATE FUNCTION live_buy_core.settle(sid uuid,req jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE h bigint;c live_buy_core.receipts;i live_buy_core.intents;s live_buy_core.scopes;f jsonb;j int:=0;eid uuid:=gen_random_uuid();t timestamptz;
 gross jsonb:=live_buy_core.q(0,1);fee jsonb:=live_buy_core.q(0,1);cost jsonb:=live_buy_core.q(0,1);n jsonb;net jsonb;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001';END IF;
 IF live_buy_core.shape(req,'settle') IS DISTINCT FROM true THEN RAISE EXCEPTION 'invalid settle request' USING ERRCODE='22023';END IF;
 SELECT version INTO STRICT h FROM live_buy_core.heads WHERE session_id=sid FOR UPDATE;
 SELECT * INTO c FROM live_buy_core.receipts WHERE session_id=sid AND command_id=(req->>'commandId')::uuid;
 IF FOUND THEN
  IF c.kind<>'settle' OR c.request IS DISTINCT FROM req THEN RAISE EXCEPTION 'key reuse conflict' USING ERRCODE='23505';END IF;
  RETURN c.result;
 END IF;
 IF h::text<>req->>'expectedVersion' THEN RAISE EXCEPTION 'financial version conflict' USING ERRCODE='40001';END IF;
 SELECT * INTO STRICT i FROM live_buy_core.intents WHERE session_id=sid AND id=(req->>'intentId')::uuid;
 IF EXISTS(SELECT FROM live_buy_core.executions WHERE session_id=sid AND intent_id=i.id) THEN RAISE EXCEPTION 'intent already settled' USING ERRCODE='23505';END IF;
 SELECT * INTO STRICT s FROM live_buy_core.scopes WHERE session_id=sid;
 t:=live_buy_core.decision_time();
 IF t<i.not_before THEN RAISE EXCEPTION 'delay not elapsed' USING ERRCODE='55000';END IF;
 FOR f IN SELECT value FROM jsonb_array_elements(req->'fills') LOOP
  IF (f->>'executedAt')::timestamptz<i.not_before OR (f->>'executedAt')::timestamptz>t OR live_buy_core.cmp(f->'price',i.request->'priceCap')>0 OR live_buy_core.cmp(f->'quantityFee',f->'quantityGross')>=0
  THEN RAISE EXCEPTION 'fill outside retained limits' USING ERRCODE='23514';END IF;
  gross:=live_buy_core.addq(gross,f->'quantityGross');fee:=live_buy_core.addq(fee,f->'cashFee');
  cost:=live_buy_core.addq(cost,live_buy_core.mulq(f->'price',f->'quantityGross'));
 END LOOP;
 IF gross<>i.quantity OR live_buy_core.cmp(fee,i.request->'feeCashBound')>0 OR live_buy_core.cmp(cost,i.notional)>0
 THEN RAISE EXCEPTION 'incomplete or over-bound settlement; reserve retained' USING ERRCODE='23514';END IF;
 INSERT INTO live_buy_core.executions VALUES(sid,i.id,eid,(req->>'commandId')::uuid,(req->>'confirmationId')::uuid,h+1,t);
 FOR f IN SELECT value FROM jsonb_array_elements(req->'fills') LOOP
  j:=j+1;n:=live_buy_core.mulq(f->'price',f->'quantityGross');net:=live_buy_core.subq(f->'quantityGross',f->'quantityFee');
  INSERT INTO live_buy_core.fills VALUES(sid,(f->>'fillId')::uuid,i.id,j,f->'price',f->'quantityGross',f->'quantityFee',f->'cashFee',(f->>'executedAt')::timestamptz,net,n);
  INSERT INTO live_buy_core.lots VALUES(sid,(f->>'fillId')::uuid,i.id,net,n,f->'cashFee',f->'quantityFee');
 END LOOP;
 INSERT INTO live_buy_core.reservation_events VALUES(sid,i.id,'settle',cost,live_buy_core.addq(cost,fee),live_buy_core.subq(i.reserved_cash,live_buy_core.addq(cost,fee)));
 INSERT INTO live_buy_core.journal_entries SELECT sid,i.id,asset,account,amount FROM live_buy_core.expected_journal(sid,i.id);
 RETURN live_buy_core.record_result(sid,(req->>'commandId')::uuid,i.id,'settle',req,h+1,eid);
END $$;
