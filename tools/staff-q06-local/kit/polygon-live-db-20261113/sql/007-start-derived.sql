-- Derived from pinned C06: only scoped source admission and snapshot origin changed.
CREATE OR REPLACE FUNCTION polygon.c06_finish(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; plan polygon.start_plans; r polygon.setup_reviews; k polygon.command_keys; slot polygon.user_session_slots;
 pr polygon.profile; sid uuid:=gen_random_uuid(); settings_id uuid:=gen_random_uuid(); snapshot_id uuid:=gen_random_uuid();
 flow_id uuid:=gen_random_uuid(); journal_id uuid:=gen_random_uuid(); ddl timestamptz; t timestamptz;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','ticket_id','evaluation_deadline_at','deadline_calculation_version','timezone_database_version'])
  OR NOT polygon.uuid_text(p->>'ticket_id') OR p->>'deadline_calculation_version' IS DISTINCT FROM 'paper-evaluation-deadline-v1'
  OR COALESCE(p->>'evaluation_deadline_at','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$'
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO plan FROM polygon.start_plans WHERE id=(p->>'ticket_id')::uuid;
 IF plan.id IS NULL OR plan.transaction_id<>txid_current() OR plan.user_id<>(a->>'user_id')::uuid
  OR plan.login_id<>(a->>'login_id')::uuid OR plan.upstream_epoch<>(a->>'epoch')::bigint
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT * INTO pr FROM polygon.profile WHERE singleton;
 IF p->>'timezone_database_version' IS DISTINCT FROM pr.timezone_database_version THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 t:=date_trunc('milliseconds',clock_timestamp());
 IF t>=plan.deadline_at THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 BEGIN ddl:=(p->>'evaluation_deadline_at')::timestamptz;
 EXCEPTION WHEN datetime_field_overflow OR invalid_datetime_format THEN RETURN polygon.err('INVALID_REQUEST',400); END;
 IF v00_session.utc(ddl) IS DISTINCT FROM p->>'evaluation_deadline_at' OR ddl<=plan.started_at THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT * INTO r FROM polygon.setup_reviews WHERE id=plan.review_id;
 SELECT * INTO k FROM polygon.command_keys WHERE id=plan.key_id;
 -- Locks and guards from prepare remain held in this exact transaction. Time can advance.
 IF t>=r.expires_at OR EXISTS(SELECT 1 FROM polygon.drafts WHERE id=r.draft_id AND t>=expires_at)
 THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 SELECT * INTO slot FROM polygon.user_session_slots WHERE user_id=r.user_id FOR UPDATE;
 IF slot.id IS NULL THEN
  INSERT INTO polygon.user_session_slots VALUES(gen_random_uuid(),r.user_id,1,NULL) RETURNING * INTO slot;
 ELSE
  IF slot.current_session_id IS NOT NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  UPDATE polygon.user_session_slots SET generation=generation+1 WHERE id=slot.id RETURNING * INTO slot;
 END IF;
 IF NOT polygon_live.source_admitted(r.user_id,r.source_id,r.trader_id,r.trader_revision_id,r.venue_id) THEN RAISE EXCEPTION 'unadmitted source' USING ERRCODE='23514'; END IF;
 INSERT INTO polygon.paper_sessions VALUES(sid,r.user_id,slot.id,r.draft_id,r.id,r.ownership_id,r.venue_id,r.source_id,r.trader_id,r.trader_revision_id,
 k.receipt_id,settings_id,1,1,flow_id,1,'active','copying_not_connected',plan.started_at,r.proposed_timezone,ddl,
 'paper-evaluation-deadline-v1',pr.timezone_database_version,plan.started_at,plan.started_at);
 INSERT INTO polygon.settings_revisions VALUES(settings_id,sid,k.receipt_id,1,NULL,r.budget_n,r.budget_d,r.selected_mode,
 r.fixed_n,r.fixed_d,r.copy_percent,r.market_percent,r.daily_percent,r.market_n,r.market_d,r.daily_n,r.daily_d,
 r.policy_id,'paper-settings-calculation-v1',30,plan.started_at,'v1');
 INSERT INTO polygon.funding_flows VALUES(flow_id,sid,k.receipt_id,journal_id,'initial',r.budget_n,r.budget_d,'virtual_USD',plan.started_at);
 INSERT INTO polygon.journals VALUES(journal_id,sid,k.receipt_id,flow_id,1,plan.started_at);
 INSERT INTO polygon.journal_entries VALUES
 (gen_random_uuid(),journal_id,sid,'paper_cash',r.budget_n,r.budget_d,'virtual_USD'),
 (gen_random_uuid(),journal_id,sid,'virtual_funding_source',-r.budget_n,r.budget_d,'virtual_USD');
 INSERT INTO polygon.session_snapshots VALUES(snapshot_id,sid,settings_id,1,1,1,'paper-empty-snapshot-v1',
 'active','copying_not_connected','EMPTY',(SELECT data_origin FROM polygon.catalog_sources WHERE id=r.source_id),'no_trade_data','virtual_USD',
 r.budget_n,r.budget_d,r.budget_n,r.budget_d,r.budget_n,r.budget_d,0,1,0,1,0,1,0,1,0,0,0,plan.started_at,plan.started_at,'v1');
 INSERT INTO polygon.command_receipts(id,key_id,user_id,command_type,outcome,http_status,created_at,result_session_id,result_settings_revision_id)
 VALUES(k.receipt_id,k.id,k.user_id,'C06','succeeded',201,plan.started_at,sid,settings_id);
 INSERT INTO polygon.command_receipt_details VALUES(k.receipt_id,'{}','{}');
 UPDATE polygon.user_session_slots SET current_session_id=sid WHERE id=slot.id;
 UPDATE polygon.drafts SET used_at=plan.started_at,used_by_session_id=sid,updated_at=plan.started_at WHERE id=r.draft_id;
 INSERT INTO polygon.audit_events VALUES(gen_random_uuid(),sid,k.receipt_id,r.user_id,plan.login_id,snapshot_id,'paper_session.started','succeeded',plan.started_at);
 INSERT INTO polygon.outbox_events VALUES(gen_random_uuid(),sid,k.receipt_id,'paper_session.started','v1','paper_start_observer',1,'pending','{}',plan.started_at);
 RETURN polygon.receipt_reply(k.receipt_id);
END $$;
