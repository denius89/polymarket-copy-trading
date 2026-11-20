-- Preserve every existing CHECK as the old branch; add a strictly validated new
-- branch. Existing rows/initial C06/funding journals are not rewritten.
DO $$DECLARE tab text;c record;old_shape text;extra text;BEGIN
 FOREACH tab IN ARRAY ARRAY['paper_sessions','session_snapshots'] LOOP
  old_shape:='';
  FOR c IN SELECT conname,pg_get_expr(conbin,conrelid) expr FROM pg_constraint WHERE conrelid=('polygon.'||tab)::regclass AND contype='c' ORDER BY conname LOOP
   old_shape:=old_shape||CASE WHEN old_shape='' THEN '' ELSE ' AND ' END||'('||c.expr||')';
   EXECUTE format('ALTER TABLE polygon.%I DROP CONSTRAINT %I',tab,c.conname);
  END LOOP;
  IF tab='paper_sessions' THEN
   extra:=$x$version>1 AND current_snapshot_version=version AND current_ledger_sequence=version AND lifecycle='active' AND control_state='paper_copying'
   AND created_at=started_at AND updated_at>=started_at AND evaluation_deadline_at>started_at
   AND deadline_calculation_version='paper-evaluation-deadline-v1'$x$;
  ELSE
   old_shape:=old_shape||' AND equity_n IS NOT NULL AND equity_d IS NOT NULL AND position_value_n IS NOT NULL AND position_value_d IS NOT NULL AND trading_result_n IS NOT NULL AND trading_result_d IS NOT NULL';
   extra:=$x$version>1 AND session_version=version AND ledger_sequence=version AND calculation_version='paper-buy-financial-v1'
   AND lifecycle='active' AND control_state='paper_copying' AND content_state='HAS_ACTIVITY' AND coverage_state='trade_data_unvalued'
   AND data_origin IN('synthetic','public_api') AND unit='virtual_USD' AND record_schema_version='v1'
   AND free_n>=0 AND free_d>0 AND reserved_n>=0 AND reserved_d>0 AND position_cost_n>=0 AND position_cost_d>0
   AND initial_funding_n>0 AND initial_funding_d>0 AND trade_count>=0 AND position_count>=0 AND order_count>0
   AND equity_n IS NULL AND equity_d IS NULL AND position_value_n IS NULL AND position_value_d IS NULL AND trading_result_n IS NULL AND trading_result_d IS NULL$x$;
  END IF;
  EXECUTE format('ALTER TABLE polygon.%I ADD CONSTRAINT buy_closed_shape CHECK((%s) OR (%s))',tab,old_shape,extra);
 END LOOP;
END $$;
ALTER TABLE polygon.session_snapshots ALTER COLUMN equity_n DROP NOT NULL,ALTER COLUMN equity_d DROP NOT NULL,
 ALTER COLUMN position_value_n DROP NOT NULL,ALTER COLUMN position_value_d DROP NOT NULL,ALTER COLUMN trading_result_n DROP NOT NULL,ALTER COLUMN trading_result_d DROP NOT NULL;
DO $$DECLARE c record;n int:=0;BEGIN
 FOR c IN SELECT conname FROM pg_constraint WHERE conrelid='polygon.session_snapshots'::regclass AND contype='f' AND confrelid='polygon.journals'::regclass LOOP
  n:=n+1;EXECUTE format('ALTER TABLE polygon.session_snapshots DROP CONSTRAINT %I',c.conname);
 END LOOP;
 IF n<>1 THEN RAISE EXCEPTION 'unexpected original snapshot ledger binding';END IF;
END $$;
ALTER TABLE polygon.session_snapshots ADD FOREIGN KEY(session_id,ledger_sequence) REFERENCES polygon_buy.ledger_index(session_id,sequence) DEFERRABLE INITIALLY DEFERRED;
CREATE OR REPLACE FUNCTION polygon_live.session_write_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'session history cannot be deleted' USING ERRCODE='23514';END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.version<>1 OR NEW.lifecycle<>'active' THEN RAISE EXCEPTION 'new session must start at version1' USING ERRCODE='23514';END IF;
 ELSIF EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=OLD.id) THEN
  IF NEW.version<>OLD.version+1 OR NEW.lifecycle<>'active' OR NEW.control_state<>'paper_copying' OR NEW.current_snapshot_version<>NEW.version OR NEW.current_ledger_sequence<>NEW.version
  OR (to_jsonb(NEW)-ARRAY['version','current_snapshot_version','current_ledger_sequence','control_state','updated_at']) IS DISTINCT FROM
   (to_jsonb(OLD)-ARRAY['version','current_snapshot_version','current_ledger_sequence','control_state','updated_at'])
  THEN RAISE EXCEPTION 'invalid bound financial transition' USING ERRCODE='23514';END IF;
 ELSE
  IF OLD.version<>1 OR NEW.version<>2 OR NEW.lifecycle<>'completed'
   OR (to_jsonb(NEW)-ARRAY['version','lifecycle','current_snapshot_version','updated_at']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['version','lifecycle','current_snapshot_version','updated_at'])
  THEN RAISE EXCEPTION 'only immutable-identity empty completion allowed' USING ERRCODE='23514';END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION polygon_buy.expected_snapshot(sid uuid,v bigint) RETURNS polygon.session_snapshots LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE sn polygon.session_snapshots;core live_buy_core.snapshots;st jsonb;cost jsonb;
BEGIN
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=sid AND version=1;
 IF v=1 THEN RETURN sn;END IF;
 SELECT * INTO STRICT core FROM live_buy_core.snapshots WHERE session_id=sid AND version=v;st:=core.data;
 SELECT live_buy_core.sumq(value->'cost') INTO cost FROM jsonb_array_elements(st->'positions');
 sn.id:=core.id;sn.version:=v;sn.session_version:=v;sn.ledger_sequence:=v;sn.calculation_version:='paper-buy-financial-v1';
 sn.control_state:='paper_copying';sn.content_state:='HAS_ACTIVITY';sn.coverage_state:='trade_data_unvalued';
 sn.free_n:=(st#>>'{freeCash,n}')::numeric;sn.free_d:=(st#>>'{freeCash,d}')::numeric;
 sn.reserved_n:=(st#>>'{reservedCash,n}')::numeric;sn.reserved_d:=(st#>>'{reservedCash,d}')::numeric;
 sn.position_cost_n:=(cost->>'n')::numeric;sn.position_cost_d:=(cost->>'d')::numeric;
 sn.equity_n:=NULL;sn.equity_d:=NULL;sn.position_value_n:=NULL;sn.position_value_d:=NULL;sn.trading_result_n:=NULL;sn.trading_result_d:=NULL;
 SELECT count(*) INTO sn.order_count FROM live_buy_core.intents WHERE session_id=sid AND version<=v;
 SELECT count(*) INTO sn.trade_count FROM live_buy_core.fills f JOIN live_buy_core.executions e USING(session_id,intent_id) WHERE f.session_id=sid AND e.version<=v;
 SELECT count(*) INTO sn.position_count FROM jsonb_array_elements(st->'positions') WHERE live_buy_core.positive(value->'quantity');
 sn.as_of:=live_buy_core.event_time(sid,v);sn.created_at:=sn.as_of;
 RETURN sn;
END $$;
CREATE FUNCTION polygon_buy.publish(sid uuid,cid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE r live_buy_core.receipts;sn polygon.session_snapshots;
BEGIN
 SELECT * INTO STRICT r FROM live_buy_core.receipts WHERE session_id=sid AND command_id=cid;
 sn:=polygon_buy.expected_snapshot(sid,r.version);
 INSERT INTO polygon_buy.ledger_index VALUES(sid,r.version,NULL,cid);
 INSERT INTO polygon.session_snapshots SELECT sn.*;
 INSERT INTO polygon_buy.snapshot_links VALUES(sid,r.version,cid,sn.id);
 UPDATE polygon.paper_sessions SET version=r.version,current_snapshot_version=r.version,current_ledger_sequence=r.version,control_state='paper_copying',updated_at=sn.as_of
 WHERE id=sid AND version=r.version-1;
 IF NOT FOUND THEN RAISE EXCEPTION 'public financial version conflict' USING ERRCODE='40001';END IF;
END $$;
CREATE FUNCTION polygon_buy.session_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions;scope live_buy_core.scopes;h bigint;sn polygon.session_snapshots;l polygon_buy.snapshot_links;r live_buy_core.receipts;st polygon.settings_revisions;b polygon_buy.bindings;release polygon_live_activity.release_record;
BEGIN
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 SELECT * INTO scope FROM live_buy_core.scopes WHERE session_id=sid;
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=sid;
 SELECT * INTO release FROM polygon_live_activity.release_record WHERE singleton;
 SELECT version INTO h FROM live_buy_core.heads WHERE session_id=sid;
 SELECT * INTO st FROM polygon.settings_revisions WHERE session_id=sid AND id=s.current_settings_revision_id;
 IF s.id IS NULL OR scope.session_id IS NULL OR b.session_id IS NULL OR h IS NULL OR st.id IS NULL
 OR release.run_id IS DISTINCT FROM b.run_id OR release.database_name IS DISTINCT FROM current_database() OR release.database_oid IS DISTINCT FROM polygon_buy.database_oid()
 OR polygon_live.initial_valid(sid) IS DISTINCT FROM true OR polygon_live.slot_valid(s.user_id) IS DISTINCT FROM true
 OR polygon_live.source_admitted(s.user_id,s.source_id,s.trader_id,s.trader_revision_id,s.venue_id) IS DISTINCT FROM true
 OR live_buy_core.valid(sid) IS DISTINCT FROM true OR s.version<>h OR s.current_snapshot_version<>h OR s.current_ledger_sequence<>h OR s.lifecycle<>'active'
 OR ROW(scope.owner_id,scope.release_id,scope.timezone_name) IS DISTINCT FROM ROW(s.user_id,b.run_id,s.iana_timezone)
 OR scope.budget<>live_buy_core.q(st.budget_n,st.budget_d) OR scope.position_limit<>live_buy_core.q(st.market_n,st.market_d) OR scope.daily_limit<>live_buy_core.q(st.daily_n,st.daily_d)
 OR EXISTS(SELECT FROM polygon_live.completions WHERE session_id=sid)
 OR (SELECT count(*) FROM polygon.session_snapshots WHERE session_id=sid)<>h
 OR (SELECT count(*) FROM polygon_buy.snapshot_links WHERE session_id=sid)<>h-1
 OR (SELECT count(*) FROM polygon_buy.ledger_index WHERE session_id=sid)<>h
 THEN RETURN false;END IF;
 IF h=1 THEN RETURN s.control_state='copying_not_connected' AND s.updated_at=s.started_at;END IF;
 IF s.control_state<>'paper_copying' OR s.updated_at<>live_buy_core.event_time(sid,h) THEN RETURN false;END IF;
 FOR sn IN SELECT * FROM polygon.session_snapshots WHERE session_id=sid AND version>1 LOOP
  SELECT * INTO l FROM polygon_buy.snapshot_links WHERE session_id=sid AND version=sn.version;
  SELECT * INTO r FROM live_buy_core.receipts WHERE session_id=sid AND version=sn.version;
  IF to_jsonb(sn) IS DISTINCT FROM to_jsonb(polygon_buy.expected_snapshot(sid,sn.version)) OR l.command_id IS DISTINCT FROM r.command_id OR l.snapshot_id IS DISTINCT FROM sn.id
   OR NOT EXISTS(SELECT FROM polygon_buy.ledger_index WHERE session_id=sid AND sequence=sn.version AND command_id=r.command_id) THEN RETURN false;END IF;
 END LOOP;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION polygon.session_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; sn polygon.session_snapshots; origin text;
BEGIN
 IF EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=sid) THEN RETURN polygon_buy.session_valid(sid);END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF s.id IS NULL OR polygon_live.initial_valid(sid) IS DISTINCT FROM true OR polygon_live.slot_valid(s.user_id) IS DISTINCT FROM true
 OR polygon_live.source_admitted(s.user_id,s.source_id,s.trader_id,s.trader_revision_id,s.venue_id) IS DISTINCT FROM true THEN RETURN false; END IF;
 SELECT * INTO sn FROM polygon.session_snapshots WHERE session_id=sid AND version=1;
 SELECT data_origin INTO origin FROM polygon.catalog_sources WHERE id=s.source_id;
 IF sn.data_origin IS DISTINCT FROM origin THEN RETURN false; END IF;
 IF s.lifecycle='completed' THEN RETURN polygon_live.terminal_valid(sid); END IF;
 RETURN s.version=1 AND s.current_snapshot_version=1 AND s.updated_at=s.started_at
 AND NOT EXISTS(SELECT FROM polygon_live.completions WHERE session_id=sid)
 AND (SELECT count(*) FROM polygon.session_snapshots WHERE session_id=sid)=1;
END $$;

CREATE OR REPLACE FUNCTION polygon_live.empty_admitted(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE present boolean; s polygon.paper_sessions;
BEGIN
 IF EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=sid) THEN RETURN false;END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF s.id IS NULL OR s.lifecycle<>'active' OR s.version<>1 OR s.control_state<>'copying_not_connected'
 OR polygon.session_valid(sid) IS DISTINCT FROM true THEN RETURN false; END IF;
 -- Only this frozen no-execution profile is supported. No unknown sidecar is treated as zero.
 IF (SELECT array_agg(c.relname::text ORDER BY c.relname::text) FROM pg_class c WHERE c.relnamespace='polygon'::regnamespace AND c.relkind IN('r','p'))
 IS DISTINCT FROM ARRAY['audit_events','catalog_sources','command_keys','command_receipt_details','command_receipts','draft_ownerships','drafts','funding_flows','journal_entries','journals','outbox_events','paper_controls','paper_policy_versions','paper_sessions','profile','read_scopes','scope_sources','session_snapshots','settings_revisions','setup_reviews','start_plans','trader_revisions','traders','user_session_slots','users','venues']::text[] THEN RAISE EXCEPTION 'unknown polygon storage profile' USING ERRCODE='55000'; END IF;
 IF to_regnamespace('polygon_activity') IS NOT NULL OR to_regnamespace('polygon_bound') IS NOT NULL
 OR to_regnamespace('polygon_execution') IS NOT NULL
 THEN RAISE EXCEPTION 'unsupported execution/activity profile' USING ERRCODE='55000'; END IF;
 IF to_regnamespace('polygon_live_activity') IS NOT NULL THEN
  IF to_regprocedure('polygon_live_activity.has_binding(uuid)') IS NULL THEN RAISE EXCEPTION 'missing activity boundary' USING ERRCODE='55000'; END IF;
  EXECUTE 'SELECT polygon_live_activity.has_binding($1)' INTO present USING sid;
  IF present IS DISTINCT FROM false THEN RETURN false; END IF;
 END IF;
 RETURN true;
END $$;
