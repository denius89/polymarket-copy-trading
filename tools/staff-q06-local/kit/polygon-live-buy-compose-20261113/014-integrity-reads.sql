CREATE FUNCTION polygon_buy.command_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE c polygon_buy.commands;r live_buy_core.receipts;a polygon_buy.admissions;i live_buy_core.intents;ob polygon_live_activity.observations;de polygon_live_activity.decisions;b polygon_buy.bindings;t timestamptz;
BEGIN
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=sid;
 FOR c IN SELECT * FROM polygon_buy.commands WHERE session_id=sid LOOP
  SELECT * INTO r FROM live_buy_core.receipts WHERE session_id=sid AND command_id=c.command_id;
  SELECT * INTO a FROM polygon_buy.admissions WHERE session_id=sid AND id=c.admission_id;
  SELECT * INTO i FROM live_buy_core.intents WHERE session_id=sid AND id=r.intent_id;
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE session_id=sid AND id=i.observation_id;
  SELECT * INTO de FROM polygon_live_activity.decisions WHERE session_id=sid AND observation_id=ob.id;
  t:=live_buy_core.event_time(sid,r.version);
  IF r.command_id IS NULL OR a.id IS NULL OR i.id IS NULL OR ob.id IS NULL OR b.session_id IS NULL
   OR c.kind<>r.kind OR c.kind<>a.kind OR c.request IS DISTINCT FROM jsonb_build_object('session_id',sid,'request',r.request,'admission_id',a.id)
   OR (c.kind='reserve' AND r.request->'desiredNotional' IS DISTINCT FROM polygon_buy.sized_notional(sid,ob.id))
   OR a.request IS DISTINCT FROM r.request OR a.run_id<>b.run_id OR a.token_id<>i.token_id OR a.condition_id<>i.condition_id
   OR a.transaction_hash<>ob.transaction_hash OR a.log_index<>ob.log_index OR ob.sequence<b.first_sequence OR ob.raw_log->>'side'<>'BUY'
   OR de.policy_version IS DISTINCT FROM 'paper-buy-queued-v1' OR de.status IS DISTINCT FROM 'pending'
   OR t<a.issued_at OR t>=a.expires_at THEN RETURN false;END IF;
 END LOOP;
 RETURN (SELECT count(*) FROM polygon_buy.commands WHERE session_id=sid)=(SELECT count(*) FROM live_buy_core.receipts WHERE session_id=sid);
END $$;
CREATE FUNCTION polygon_buy.enforce() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE sid uuid:=COALESCE(NEW.session_id,OLD.session_id);
BEGIN
 IF polygon_buy.session_valid(sid) IS DISTINCT FROM true OR polygon_buy.command_valid(sid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete composed financial state' USING ERRCODE='23514';END IF;
 RETURN NULL;
END $$;
DO $$DECLARE n text;BEGIN
 FOREACH n IN ARRAY ARRAY['bindings','commands','snapshot_links'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER complete_composed AFTER INSERT OR UPDATE OR DELETE ON polygon_buy.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_buy.enforce()',n);
 END LOOP;
 FOREACH n IN ARRAY ARRAY['scopes','heads','snapshots','positions','intents','executions','fills','lots','reservation_events','journal_entries','receipts','audit','outbox'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER complete_composed AFTER INSERT OR UPDATE OR DELETE ON live_buy_core.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_buy.enforce()',n);
 END LOOP;
END $$;
CREATE FUNCTION polygon_buy.item(ob polygon_live_activity.observations,d polygon_live_activity.decisions) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE body jsonb;i live_buy_core.intents;e live_buy_core.executions;sn live_buy_core.snapshots;copy jsonb;fills jsonb;cost jsonb;gross jsonb;net jsonb;qfee jsonb;cfee jsonb;
BEGIN
 body:=polygon_live_activity.item(ob,d);
 IF d.policy_version='paper-bound-skip-v1' THEN RETURN body;END IF;
 SELECT * INTO i FROM live_buy_core.intents WHERE session_id=ob.session_id AND observation_id=ob.id;
 SELECT * INTO e FROM live_buy_core.executions WHERE session_id=ob.session_id AND intent_id=i.id;
 IF e.id IS NULL THEN
  copy:=jsonb_build_object('kind','pending','intentId',i.id,'reservedCash',i.reserved_cash,'reservedNotional',i.notional,'admittedAt',v00_session.utc(i.admitted_at));
 ELSE
  SELECT * INTO STRICT sn FROM live_buy_core.snapshots WHERE session_id=ob.session_id AND version=e.version;
  SELECT live_buy_core.sumq(notional),live_buy_core.sumq(f.gross),live_buy_core.sumq(f.net),live_buy_core.sumq(quantity_fee),live_buy_core.sumq(cash_fee),
   jsonb_agg(jsonb_build_object('fillId',id,'executedAt',v00_session.utc(executed_at),'price',price,'quantityGross',f.gross,'quantityNet',f.net,'quantityFee',quantity_fee,'cashFee',cash_fee,'notional',notional) ORDER BY ordinal)
  INTO cost,gross,net,qfee,cfee,fills FROM live_buy_core.fills f WHERE session_id=ob.session_id AND intent_id=i.id;
  copy:=jsonb_build_object('kind','filled','intentId',i.id,'executionId',e.id,'settledAt',v00_session.utc(e.settled_at),'notional',cost,
   'quantityGross',gross,'quantityNet',net,'quantityFee',qfee,'cashFee',cfee,'snapshotId',sn.id,'snapshotVersion',sn.version::text,'fills',fills);
 END IF;
 RETURN body||jsonb_build_object('decision',jsonb_build_object('status',CASE WHEN e.id IS NULL THEN 'pending' ELSE 'filled' END,
 'reasonCode',NULL,'detailCode',NULL,'decidedAt',v00_session.utc(d.decided_at),'policyVersion','paper-buy-queued-v1','copy',copy));
END $$;

CREATE FUNCTION polygon.buy_activity_read_v1(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;s polygon.paper_sessions;st polygon_live_activity.stream;i polygon_live_activity.assignments;
 items jsonb;binding jsonb;after_seq bigint;lim integer;water bigint:=0;next_seq bigint;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 IF polygon.exact_keys(p,ARRAY['auth','session_id','after_sequence','limit']) IS DISTINCT FROM true
 OR NOT polygon_live_activity.uuid_value(p->'session_id') OR NOT polygon_live_activity.uint(p->'after_sequence')
 OR jsonb_typeof(p->'limit') IS DISTINCT FROM 'number' OR (p->>'limit' ~ '^[0-9]{1,3}$') IS DISTINCT FROM true
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 IF (p->>'after_sequence')::numeric>9223372036854775807 OR (p->>'limit')::integer NOT BETWEEN 1 AND 100 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 after_seq:=(p->>'after_sequence')::bigint;lim:=(p->>'limit')::integer;
 a:=polygon.guard(p->'auth');IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=(p->>'session_id')::uuid AND user_id=(a->>'user_id')::uuid;
 IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 IF polygon.session_valid(s.id) IS DISTINCT FROM true OR NOT EXISTS(
 SELECT FROM polygon_live_activity.installation x JOIN polygon_live.installation l ON l.database_name=x.database_name AND l.operator_run_id=x.run_id WHERE x.database_name=current_database())
 THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 SELECT * INTO i FROM polygon_live_activity.assignments WHERE session_id=s.id;
 SELECT * INTO st FROM polygon_live_activity.stream WHERE session_id=s.id;
 IF i.session_id IS NULL THEN
  IF st.session_id IS NOT NULL OR EXISTS(SELECT FROM polygon_live_activity.operations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.observations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.decisions WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.calls WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.bound_requests WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.evaluations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.conflicts WHERE session_id=s.id)
  THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 ELSE
  IF polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true
  OR polygon_live_activity.calls_valid(s.id) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  binding:=jsonb_build_object('streamId',i.stream_id,'venueCode','polymarket','catalogSourceId',i.source_id,'traderId',i.trader_id,
  'traderRevisionId',i.revision_id,'externalTraderId',i.owner_address,'bindingRevision',i.binding_revision::text);
 END IF;
 water:=COALESCE(st.high_watermark,0);
 IF after_seq>water THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT COALESCE(jsonb_agg(x.body ORDER BY x.sequence),'[]'),COALESCE(max(x.sequence),after_seq) INTO items,next_seq FROM (
 SELECT ob.sequence,polygon_buy.item(ob,d) AS body FROM polygon_live_activity.observations ob
 JOIN polygon_live_activity.decisions d ON d.observation_id=ob.id AND d.session_id=ob.session_id AND d.sequence=ob.sequence
 WHERE ob.session_id=s.id AND ob.sequence>after_seq AND ob.sequence<=water ORDER BY ob.sequence LIMIT lim) x;
 RETURN jsonb_build_object('http',200,'schemaVersion','live-buy-activity-v1','binding',binding,'observation',jsonb_build_object('status',COALESCE(st.status,'not_armed'),
 'armedAt',CASE WHEN st.armed_at IS NULL THEN NULL ELSE v00_session.utc(st.armed_at) END,
 'lastObservedAt',CASE WHEN st.last_observed_at IS NULL THEN NULL ELSE v00_session.utc(st.last_observed_at) END,'completeness','unproven'),
 'items',items,'page',jsonb_build_object('afterSequence',after_seq::text,'nextAfterSequence',next_seq::text,'highWatermark',water::text,'hasMore',next_seq<water),
 'session',CASE WHEN s.version>1 AND EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=s.id) THEN polygon_buy.body(s.id) ELSE polygon.session_body(s) END);
END $$;

-- Existing staff target scopes and audit evidence retained. Initial audit is linked to snapshot1.
CREATE OR REPLACE FUNCTION polygon.pilot_staff_snapshot(sid uuid) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; sn polygon.session_snapshots; au polygon.audit_events; body jsonb; pc polygon.profile;
BEGIN
 SELECT * INTO STRICT pc FROM polygon.profile WHERE singleton FOR SHARE;
 IF NOT pc.enabled OR pc.environment<>'shadow-polygon-synthetic-v1' THEN RAISE EXCEPTION 'paper unavailable' USING ERRCODE='55000'; END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF polygon.session_valid(sid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete paper source' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=s.current_snapshot_version;
 SELECT * INTO STRICT au FROM polygon.audit_events WHERE session_id=s.id;
 IF s.current_settings_revision_id<>sn.settings_revision_id OR au.snapshot_id IS DISTINCT FROM (SELECT id FROM polygon.session_snapshots WHERE session_id=s.id AND version=1) OR au.receipt_id<>s.start_receipt_id
 OR au.actor_user_id<>s.user_id OR au.kind<>'paper_session.started' OR au.outcome<>'succeeded' OR au.created_at<>s.started_at
 OR sn.data_origin NOT IN('synthetic','public_api') OR NOT ((sn.content_state='EMPTY' AND sn.coverage_state='no_trade_data') OR (sn.content_state='HAS_ACTIVITY' AND sn.coverage_state='trade_data_unvalued' AND EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=sid)))
 THEN RAISE EXCEPTION 'inconsistent paper projection' USING ERRCODE='23514'; END IF;
 body:=CASE WHEN s.version>1 AND EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=sid) THEN polygon_buy.body(sid) ELSE polygon.session_body(s) END;
 RETURN jsonb_build_object('user_id',s.user_id,'session_id',s.id,'snapshot_id',sn.id,'snapshot_version',sn.version,
  'settings_revision_id',sn.settings_revision_id,'session',body,
  'event',jsonb_build_object('eventId',au.id,'sessionId',s.id,'kind',au.kind,'occurredAt',v00_session.utc(au.created_at)));
END $$;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon_buy FROM PUBLIC,polygon_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA live_buy_core FROM PUBLIC,polygon_executor;
REVOKE ALL ON FUNCTION polygon.buy_activity_read_v1(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION polygon.buy_activity_read_v1(jsonb) TO polygon_executor;

-- Deferred core checks execute after the definer RPC returns to the scoped worker.
ALTER FUNCTION live_buy_core.enforce() SECURITY DEFINER;
