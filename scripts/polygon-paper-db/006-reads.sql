\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE polygon_owner;
CREATE FUNCTION polygon.catalog_read(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; venue polygon.venues; ctl polygon.paper_controls; src polygon.catalog_sources; tr polygon.traders; rev polygon.trader_revisions;
 sources jsonb:='[]'; traders jsonb; items jsonb:='[]'; cap text; n integer; descriptor jsonb;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','venue_code']) OR (p->>'venue_code' IN ('polymarket','limitless')) IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO venue FROM polygon.venues WHERE code=p->>'venue_code';
 SELECT * INTO ctl FROM polygon.paper_controls WHERE singleton;
 IF venue.id IS NULL OR ctl.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 SELECT count(*) INTO n FROM polygon.catalog_sources s JOIN polygon.scope_sources ss ON ss.source_id=s.id
 WHERE ss.scope_id=(a->>'scope_id')::uuid AND s.venue_id=venue.id;
 IF n>100 THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 SELECT count(*) INTO n FROM polygon.traders t JOIN polygon.scope_sources ss ON ss.source_id=t.source_id
 WHERE ss.scope_id=(a->>'scope_id')::uuid AND t.venue_id=venue.id;
 IF n>1000 THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 FOR src IN SELECT s.* FROM polygon.catalog_sources s JOIN polygon.scope_sources ss ON ss.source_id=s.id
 WHERE ss.scope_id=(a->>'scope_id')::uuid AND s.venue_id=venue.id ORDER BY s.id LOOP
  traders:='[]';
  FOR tr IN SELECT * FROM polygon.traders WHERE source_id=src.id ORDER BY id LOOP
   SELECT * INTO rev FROM polygon.trader_revisions WHERE id=tr.current_revision_id AND trader_id=tr.id AND source_id=src.id AND venue_id=venue.id;
   IF rev.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
   traders:=traders||jsonb_build_array(jsonb_build_object('traderId',tr.id,'version',tr.control_version::text,
    'currentRevisionId',rev.id,'currentRevision',rev.revision::text,'readVisible',tr.is_catalog_visible,'startAllowed',tr.paper_start_enabled));
   IF tr.is_catalog_visible AND src.is_catalog_visible THEN
    cap:=polygon.capability(tr.id,ctl);
    items:=items||jsonb_build_array(jsonb_build_object('traderId',tr.id,'venueId',venue.id,'catalogSourceId',src.id,
    'venueCode',venue.code,'externalTraderId',tr.external_trader_id,'displayName',rev.display_name,'traderRevisionId',rev.id,
    'traderRevision',rev.revision::text,'dataOrigin',src.data_origin,'sourceRef',rev.source_ref,'observedAt',v00_session.utc(rev.observed_at),
    'revisionCreatedAt',v00_session.utc(rev.created_at),'catalogVersionAtCreation',rev.catalog_version_at_creation::text,
    'catalogVersion',src.version::text,'traderControlVersion',tr.control_version::text,'paperControlVersion',ctl.version::text,
    'startAvailability',jsonb_build_object('available',cap IS NULL,'capabilityReasonCode',cap)));
   END IF;
  END LOOP;
  sources:=sources||jsonb_build_array(jsonb_build_object('sourceId',src.id,'venueId',src.venue_id,'version',src.version::text,
   'readVisible',src.is_catalog_visible,'startEnabled',src.paper_start_enabled,'traders',traders));
 END LOOP;
 SELECT COALESCE(jsonb_agg(value ORDER BY value->>'traderId'),'[]'::jsonb) INTO items FROM jsonb_array_elements(items);
 descriptor:=jsonb_build_object('venueId',venue.id,'venueCode',venue.code,'paperControl',
  jsonb_build_object('id',ctl.id,'version',ctl.version::text,'startEnabled',ctl.enabled),'sources',sources);
 RETURN jsonb_build_object('http',200,'read_binding',jsonb_build_object('environment',a->>'environment','realm','user',
 'read_context_id',a->>'read_context_id','scope_id',a->>'scope_id','scope_revision',a->>'scope_revision'),
 'descriptor',descriptor,'items',items);
END $$;

CREATE FUNCTION polygon.q03_draft(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; d polygon.drafts; r polygon.command_receipts; dt polygon.command_receipt_details; body jsonb;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','draft_id']) OR NOT polygon.uuid_text(p->>'draft_id') THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO d FROM polygon.drafts WHERE id=(p->>'draft_id')::uuid AND user_id=(a->>'user_id')::uuid;
 IF d.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 SELECT * INTO r FROM polygon.command_receipts WHERE id=d.last_input_receipt_id;
 SELECT * INTO dt FROM polygon.command_receipt_details WHERE receipt_id=r.id;
 IF r.id IS NULL OR ROW(r.result_draft_id,r.result_draft_version,r.result_last_saved_at,r.result_expires_at)
 IS DISTINCT FROM ROW(d.id,d.version,d.last_saved_at,d.expires_at) OR r.change_kind NOT IN ('created','updated')
 OR polygon.receipt_reply(r.id)->>'http' NOT IN ('200','201') OR dt.receipt_id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 body:=polygon.draft_form(d)||jsonb_build_object('draftId',d.id,'currentOwnershipId',d.ownership_id,'draftVersion',d.version::text,'ownerKind','user',
 'state',CASE WHEN d.used_at IS NOT NULL THEN 'used' WHEN clock_timestamp()>=d.expires_at THEN 'expired' ELSE 'editable' END,
 'lastSavedAt',v00_session.utc(d.last_saved_at),'expiresAt',v00_session.utc(d.expires_at),'createdAt',v00_session.utc(d.created_at),
 'updatedAt',v00_session.utc(d.updated_at),'usedAt',v00_session.utc(d.used_at),'usedBySessionId',d.used_by_session_id);
 RETURN jsonb_build_object('http',200,'raw_encoding','utf8-base64-v1','draft',body,'field_errors',dt.response_data->'fieldErrors',
 'field_errors_source',jsonb_build_object('receiptId',r.id,'draftVersion',d.version::text));
END $$;
CREATE FUNCTION polygon.q05_command(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; k polygon.command_keys;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','command_type','client_command_id','actor_id','actor_realm'])
 OR (p->>'command_type' IN ('C04','C06')) IS DISTINCT FROM true OR p->>'actor_realm' IS DISTINCT FROM 'user'
 OR NOT polygon.uuid_text(p->>'actor_id') OR NOT polygon.uuid_text(p->>'client_command_id') THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 IF p->>'actor_id'<>a->>'user_id' THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 SELECT * INTO k FROM polygon.command_keys WHERE user_id=(a->>'user_id')::uuid AND command_type=p->>'command_type' AND client_command_id=(p->>'client_command_id')::uuid;
 IF k.id IS NOT NULL THEN RETURN polygon.receipt_reply(k.receipt_id,true); END IF;
 RETURN jsonb_build_object('http',202,'command_ref',jsonb_build_object('actorRealm','user','actorId',a->>'user_id',
 'commandType',p->>'command_type','clientCommandId',p->>'client_command_id'),'status','pending','receipt',NULL);
END $$;

CREATE FUNCTION polygon.session_body(s polygon.paper_sessions) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
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
 snapshot:=jsonb_build_object('snapshotId',sn.id,'sessionId',sn.session_id,'settingsRevisionId',sn.settings_revision_id,'recordSchemaVersion',sn.record_schema_version,
 'snapshotVersion',sn.version::text,'sessionVersion',sn.session_version::text,'ledgerSequence',sn.ledger_sequence::text,
 'projectionCalculationVersion',sn.calculation_version,'lifecycle',sn.lifecycle,'controlState',sn.control_state,'contentState',sn.content_state,
 'dataOrigin',sn.data_origin,'coverageState',sn.coverage_state,'unit',sn.unit,
 'initialFunding',polygon.money(sn.initial_funding_n,sn.initial_funding_d),'free',polygon.money(sn.free_n,sn.free_d),'equity',polygon.money(sn.equity_n,sn.equity_d),
 'reserved',polygon.money(sn.reserved_n,sn.reserved_d),'positionCost',polygon.money(sn.position_cost_n,sn.position_cost_d),
 'positionValue',polygon.money(sn.position_value_n,sn.position_value_d),'tradingResult',polygon.money(sn.trading_result_n,sn.trading_result_d),
 'tradeCount',sn.trade_count::text,'positionCount',sn.position_count::text,'orderCount',sn.order_count::text,
 'asOf',v00_session.utc(sn.as_of),'createdAt',v00_session.utc(sn.created_at));
 RETURN jsonb_build_object('summary',summary,'settings',settings,'financialSnapshot',snapshot);
END $$;
CREATE FUNCTION polygon.q04_session(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
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
 RETURN jsonb_build_object('http',200,'session',polygon.session_body(s));
END $$;
-- Close every existing function before granting the exact public RPC surface.
-- Default privileges protect future owner-created helpers; this covers this set.
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon FROM PUBLIC, polygon_executor;
GRANT USAGE ON SCHEMA polygon TO polygon_executor;
GRANT EXECUTE ON FUNCTION polygon.current_identity(jsonb),polygon.catalog_read(jsonb),polygon.c04_save(jsonb),
 polygon.c05_validate(jsonb),polygon.c06_prepare(jsonb),polygon.c06_finish(jsonb),polygon.q03_draft(jsonb),
 polygon.q04_session(jsonb),polygon.q05_command(jsonb) TO polygon_executor;
COMMIT;
