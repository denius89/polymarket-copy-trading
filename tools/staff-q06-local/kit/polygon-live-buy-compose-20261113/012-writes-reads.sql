-- Sizing comes from the persisted revision and the already normalized source BUY.
-- Same source USD-six-decimal interpretation as the reviewed earlier BUY calculator;
-- it is not supplied by a browser or inferred from a current display string.
CREATE FUNCTION polygon_buy.sized_notional(sid uuid,oid uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN st.sizing_mode='fixed' THEN live_buy_core.q(st.fixed_n,st.fixed_d)
 ELSE live_buy_core.mulq(live_buy_core.q((ob.raw_log->>'makerAmountFilledRaw')::numeric,1000000),live_buy_core.q(st.copy_percent*100,10000)) END
 FROM polygon_live_activity.observations ob JOIN polygon_live_activity.decisions d ON d.observation_id=ob.id AND d.session_id=ob.session_id
 JOIN polygon.settings_revisions st ON st.session_id=ob.session_id AND st.id=d.settings_revision_id
 WHERE ob.session_id=sid AND ob.id=oid AND ob.raw_log->>'side'='BUY'
$$;
CREATE FUNCTION polygon_buy.writer(sid uuid) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE b polygon_buy.bindings;r polygon_live_activity.release_record;a jsonb;
BEGIN
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=sid;
 SELECT * INTO r FROM polygon_live_activity.release_record WHERE singleton;
 IF b.session_id IS NULL OR r.run_id IS DISTINCT FROM b.run_id OR r.database_name<>current_database()
 OR r.database_oid<>polygon_buy.database_oid() THEN RETURN polygon.err('ACCESS_DENIED',403);END IF;
 a:=polygon_live_activity.writer_guard(jsonb_build_object('sessionId',sid,'runId',b.run_id));
 RETURN a;
END $$;
CREATE FUNCTION polygon_buy.dispatch(p jsonb,k text) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE sid uuid;cid uuid;auth jsonb;old polygon_buy.commands;ad polygon_buy.admissions;ob polygon_live_activity.observations;
 de polygon_live_activity.decisions;i live_buy_core.intents;r jsonb;b polygon_buy.bindings;s polygon.paper_sessions;t timestamptz;
BEGIN
 IF k='lookup' THEN
  IF polygon.exact_keys(p,ARRAY['session_id','command_id']) IS DISTINCT FROM true OR NOT polygon.uuid_text(p->>'command_id') THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
  cid:=(p->>'command_id')::uuid;
 ELSE
  IF polygon.exact_keys(p,ARRAY['session_id','request','admission_id']) IS DISTINCT FROM true OR NOT polygon.uuid_text(p->>'admission_id')
   OR live_buy_core.shape(p->'request',k) IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
  cid:=(p#>>'{request,commandId}')::uuid;
 END IF;
 IF NOT polygon.uuid_text(p->>'session_id') THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 sid:=(p->>'session_id')::uuid;auth:=polygon_buy.writer(sid);IF auth->>'http'<>'200' THEN RETURN auth;END IF;
 SELECT * INTO old FROM polygon_buy.commands WHERE session_id=sid AND command_id=cid;
 IF FOUND THEN
  IF k<>'lookup' AND (old.kind<>k OR old.request IS DISTINCT FROM p) THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409);END IF;
  RETURN jsonb_build_object('http',200,'result',live_buy_core.lookup(sid,cid));
 ELSIF k='lookup' THEN RETURN jsonb_build_object('http',202,'status','pending','commandId',cid);END IF;
 SELECT * INTO STRICT b FROM polygon_buy.bindings WHERE session_id=sid;
 SELECT * INTO STRICT s FROM polygon.paper_sessions WHERE id=sid;
 IF polygon_live_activity.new_admission(sid) IS DISTINCT FROM true OR NOT EXISTS(SELECT FROM polygon_live_activity.stream WHERE session_id=sid AND status='observing') THEN RETURN polygon.err('SERVICE_UNAVAILABLE');END IF;
 SELECT * INTO ad FROM polygon_buy.admissions WHERE id=(p->>'admission_id')::uuid AND session_id=sid;
 t:=live_buy_core.decision_time();
 IF ad.id IS NULL OR ad.run_id<>b.run_id OR ad.kind<>k OR ad.request IS DISTINCT FROM p->'request' OR t<ad.issued_at OR t>=ad.expires_at
 THEN RETURN polygon.err('ADMISSION_UNAVAILABLE',409);END IF;
 IF k='reserve' THEN
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE session_id=sid AND id=(p#>>'{request,observationId}')::uuid;
 ELSE
  SELECT * INTO i FROM live_buy_core.intents WHERE session_id=sid AND id=(p#>>'{request,intentId}')::uuid;
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE session_id=sid AND id=i.observation_id;
 END IF;
 SELECT * INTO de FROM polygon_live_activity.decisions WHERE session_id=sid AND observation_id=ob.id;
 IF ob.id IS NULL OR ob.classification<>'accepted' OR ob.sequence<b.first_sequence OR ob.raw_log->>'side'<>'BUY'
 OR ob.transaction_hash<>ad.transaction_hash OR ob.log_index<>ad.log_index OR ob.raw_log->>'tokenId'<>ad.token_id
 OR de.policy_version IS DISTINCT FROM 'paper-buy-queued-v1' OR de.status IS DISTINCT FROM 'pending'
 THEN RETURN polygon.err('ADMISSION_UNAVAILABLE',409);END IF;
 IF k='reserve' THEN
  IF p#>'{request,desiredNotional}' IS DISTINCT FROM polygon_buy.sized_notional(sid,ob.id)
  OR p#>>'{request,tokenId}'<>ad.token_id OR p#>>'{request,conditionId}'<>ad.condition_id
  OR p#>>'{request,sizingRevisionId}'<>de.settings_revision_id::text OR p#>>'{request,admissionRevisionId}'<>s.current_settings_revision_id::text
  OR EXISTS(SELECT FROM polygon_live_activity.decisions d WHERE d.session_id=sid AND d.sequence>=b.first_sequence AND d.sequence<ob.sequence AND d.policy_version='paper-buy-queued-v1'
    AND NOT EXISTS(SELECT FROM live_buy_core.intents x WHERE x.session_id=sid AND x.observation_id=d.observation_id))
  THEN RETURN polygon.err('ADMISSION_UNAVAILABLE',409);END IF;
  r:=live_buy_core.reserve(sid,p->'request');
 ELSE
  IF i.token_id<>ad.token_id OR i.condition_id<>ad.condition_id THEN RETURN polygon.err('ADMISSION_UNAVAILABLE',409);END IF;
  r:=live_buy_core.settle(sid,p->'request');
 END IF;
 INSERT INTO polygon_buy.commands VALUES(sid,cid,ad.id,p,k);
 PERFORM polygon_buy.publish(sid,cid);
 RETURN jsonb_build_object('http',200,'result',r);
END $$;
CREATE FUNCTION polygon.live_buy_reserve_v1(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_buy.dispatch(p,'reserve') $$;
CREATE FUNCTION polygon.live_buy_settle_v1(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_buy.dispatch(p,'settle') $$;
CREATE FUNCTION polygon.live_buy_lookup_v1(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_buy.dispatch(p,'lookup') $$;
CREATE FUNCTION polygon_buy.daily_context(sid uuid,t timestamptz) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE h bigint;sn uuid;scope live_buy_core.scopes;st jsonb;day date;d jsonb;
BEGIN
 SELECT * INTO STRICT scope FROM live_buy_core.scopes WHERE session_id=sid;
 SELECT version INTO STRICT h FROM live_buy_core.heads WHERE session_id=sid;
 SELECT id INTO STRICT sn FROM live_buy_core.snapshots WHERE session_id=sid AND version=h;
 day:=(t AT TIME ZONE scope.timezone_name)::date;st:=live_buy_core.compute_state_at(sid,h,sn,t);
 SELECT value INTO STRICT d FROM jsonb_array_elements(st->'daily') WHERE value->>'day'=day::text;
 RETURN jsonb_build_object('day',day::text,'timezone',scope.timezone_name,'used',d->'used','reserved',d->'reserved','limit',scope.daily_limit,
 'nextResetAt',v00_session.utc((day+1)::timestamp AT TIME ZONE scope.timezone_name),'asOf',v00_session.utc(t));
END $$;
CREATE FUNCTION polygon_buy.context(s polygon.paper_sessions) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE st polygon.settings_revisions; sn polygon.session_snapshots; tr polygon.trader_revisions; summary jsonb; settings jsonb; snapshot jsonb;
BEGIN
 SELECT * INTO st FROM polygon.settings_revisions WHERE session_id=s.id AND id=s.current_settings_revision_id;
 SELECT * INTO sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=s.current_snapshot_version;
 SELECT * INTO tr FROM polygon.trader_revisions WHERE id=s.trader_revision_id;
 summary:=jsonb_build_object('sessionId',s.id,'mode','paper','venueId',s.venue_id,'catalogSourceId',s.source_id,
 'traderId',s.trader_id,'traderRevisionId',s.trader_revision_id,'traderDisplayName',tr.display_name,
 'dataOrigin',sn.data_origin,'lifecycle',s.lifecycle,'controlState',s.control_state,'contentState',sn.content_state,
 'coverageState',sn.coverage_state,'sessionVersion',s.version::text,'snapshotVersion',sn.version::text,'settingsRevisionId',st.id,
 'asOf',v00_session.utc(sn.as_of),'startedAt',v00_session.utc(s.started_at),'evaluationDeadlineAt',v00_session.utc(s.evaluation_deadline_at),
 'ianaTimezone',s.iana_timezone,'deadlineCalculationVersion',s.deadline_calculation_version,'timezoneDatabaseVersion',s.timezone_database_version,
 'createdAt',v00_session.utc(s.created_at),'updatedAt',v00_session.utc(s.updated_at));
 settings:=jsonb_build_object('settingsRevisionId',st.id,'sessionId',s.id,'recordSchemaVersion',st.record_schema_version,'sequence',st.sequence::text,
 'previousRevisionId',st.previous_revision_id,'budget',polygon.money(st.budget_n,st.budget_d),'sizingMode',st.sizing_mode,
 'fixedAmount',polygon.money(st.fixed_n,st.fixed_d),'copyPercent',polygon.percent(st.copy_percent),
 'marketLimitPercent',polygon.percent(st.market_percent),'dailyBuyLimitPercent',polygon.percent(st.daily_percent),
 'effectiveMarketLimit',polygon.money(st.market_n,st.market_d),'effectiveDailyBuyLimit',polygon.money(st.daily_n,st.daily_d),
 'policyVersionId',st.policy_id,'calculationVersion',st.calculation_version,'signalMaxAgeSeconds',st.signal_max_age_seconds,
 'commandReceiptId',st.command_receipt_id,'createdAt',v00_session.utc(st.created_at));
 RETURN jsonb_build_object('summary',summary,'settings',settings);
END $$;
CREATE FUNCTION polygon_buy.body(sid uuid) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions;sn polygon.session_snapshots;body jsonb;
BEGIN
 SELECT * INTO STRICT s FROM polygon.paper_sessions WHERE id=sid;
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=sid AND version=s.current_snapshot_version;
 body:=polygon_buy.context(s);
 RETURN jsonb_build_object('schemaVersion','live-buy-session-v1','sessionId',sid,'sessionVersion',s.version::text,'snapshotId',sn.id,
 'snapshotVersion',sn.version::text,'ledgerSequence',sn.ledger_sequence::text,'asOf',v00_session.utc(sn.as_of),'ianaTimezone',s.iana_timezone,
 'financial',live_buy_core.read_state(sid),'valuation',jsonb_build_object('status','unavailable'),
 'context',jsonb_build_object('summary',body->'summary','settings',body->'settings'),
 'dailyContext',polygon_buy.daily_context(sid,clock_timestamp()));
END $$;
CREATE FUNCTION polygon.buy_session_read_v1(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;sid uuid;s polygon.paper_sessions;r polygon_live_activity.release_record;b polygon_buy.bindings;
BEGIN
 IF polygon.exact_keys(p,ARRAY['auth','session_id']) IS DISTINCT FROM true OR (p->'session_id'<>'null' AND NOT polygon.uuid_text(p->>'session_id')) THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 a:=polygon.guard(p->'auth');IF a->>'http'<>'200' THEN RETURN a;END IF;
 IF p->'session_id'='null' THEN SELECT current_session_id INTO sid FROM polygon.user_session_slots WHERE user_id=(a->>'user_id')::uuid;
 ELSE sid:=(p->>'session_id')::uuid;END IF;
 IF sid IS NULL THEN RETURN jsonb_build_object('http',200,'schemaVersion','live-buy-session-v1','sessionId',NULL,'buyState',NULL);END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid AND user_id=(a->>'user_id')::uuid;
 IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404);END IF;
 IF polygon.session_valid(sid) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=sid;
 IF b.session_id IS NULL OR s.version=1 THEN RETURN jsonb_build_object('http',200,'schemaVersion','live-buy-session-v1','sessionId',sid,'buyState',NULL);END IF;
 SELECT * INTO r FROM polygon_live_activity.release_record WHERE singleton;
 IF r.run_id IS DISTINCT FROM b.run_id OR r.database_name<>current_database() OR r.database_oid<>polygon_buy.database_oid() THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 RETURN jsonb_build_object('http',200)||polygon_buy.body(sid);
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA polygon_buy FROM PUBLIC,polygon_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon_buy FROM PUBLIC,polygon_executor;
REVOKE ALL ON FUNCTION polygon.live_buy_reserve_v1(jsonb),polygon.live_buy_settle_v1(jsonb),polygon.live_buy_lookup_v1(jsonb),polygon.buy_session_read_v1(jsonb) FROM PUBLIC,polygon_executor;
GRANT EXECUTE ON FUNCTION polygon.buy_session_read_v1(jsonb) TO polygon_executor;

CREATE OR REPLACE FUNCTION polygon.q04_session(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; s polygon.paper_sessions; sl polygon.user_session_slots;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','session_id']) OR (p->'session_id'<>'null' AND NOT polygon.uuid_text(p->>'session_id'))
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 IF p->'session_id'='null' THEN
  SELECT * INTO sl FROM polygon.user_session_slots WHERE user_id=(a->>'user_id')::uuid;
  IF sl.id IS NULL OR sl.current_session_id IS NULL THEN RETURN jsonb_build_object('http',200,'session',NULL); END IF;
  SELECT * INTO s FROM polygon.paper_sessions WHERE id=sl.current_session_id AND user_id=(a->>'user_id')::uuid;
  IF s.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 ELSE
  SELECT * INTO s FROM polygon.paper_sessions WHERE id=(p->>'session_id')::uuid AND user_id=(a->>'user_id')::uuid;
  IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 END IF;
 IF polygon.session_valid(s.id) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 IF s.version>1 AND EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=s.id) THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 RETURN jsonb_build_object('http',200,'session',polygon.session_body(s));
END $$;
