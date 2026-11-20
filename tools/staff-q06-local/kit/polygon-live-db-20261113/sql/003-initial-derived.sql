-- Derived from pinned e4224c6: snapshot1 and historical slot owner; all other initial checks retained.
CREATE FUNCTION polygon_live.initial_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; r polygon.setup_reviews; st polygon.settings_revisions; sn polygon.session_snapshots;
 f polygon.funding_flows; j polygon.journals; d polygon.drafts; sl polygon.user_session_slots; cr polygon.command_receipts;
 au polygon.audit_events; ob polygon.outbox_events; je polygon.journal_entries;
 k polygon.command_keys; plan polygon.start_plans; original_request jsonb;
BEGIN
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 SELECT * INTO r FROM polygon.setup_reviews WHERE id=s.review_id;
 SELECT * INTO st FROM polygon.settings_revisions WHERE id=s.current_settings_revision_id;
 SELECT * INTO sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=1;
 SELECT * INTO f FROM polygon.funding_flows WHERE id=s.initial_funding_flow_id;
 SELECT * INTO j FROM polygon.journals WHERE id=f.journal_id;
 SELECT * INTO d FROM polygon.drafts WHERE id=s.draft_id;
 SELECT * INTO sl FROM polygon.user_session_slots WHERE id=s.slot_id;
 SELECT * INTO cr FROM polygon.command_receipts WHERE id=s.start_receipt_id;
 SELECT * INTO au FROM polygon.audit_events WHERE session_id=s.id;
 SELECT * INTO ob FROM polygon.outbox_events WHERE session_id=s.id;
 SELECT * INTO k FROM polygon.command_keys WHERE id=cr.key_id;
 SELECT * INTO plan FROM polygon.start_plans WHERE key_id=k.id;
 IF s.id IS NULL OR r.id IS NULL OR st.id IS NULL OR sn.id IS NULL OR f.id IS NULL OR j.id IS NULL OR d.id IS NULL
  OR sl.id IS NULL OR cr.id IS NULL OR au.id IS NULL OR ob.id IS NULL OR k.id IS NULL OR plan.id IS NULL THEN RETURN false; END IF;
 original_request:=jsonb_build_object('requestSchemaVersion','v1','clientCommandId',k.client_command_id,'reviewId',r.id,
 'expectedDraftVersion',k.expected_draft_version::text,'expectedSlot',CASE WHEN r.slot_observation='absent' THEN
 jsonb_build_object('state','absent') ELSE jsonb_build_object('state','present','generation',r.expected_slot_generation::text) END);
 IF ROW(k.target_draft_id,k.target_ownership_id,k.target_review_id,k.expected_draft_version,k.operation)
 IS DISTINCT FROM ROW(s.draft_id,s.ownership_id,s.review_id,r.draft_version,'start'::text)
 OR k.request_hash IS DISTINCT FROM polygon.command_hash(s.user_id,'C06','start',s.draft_id,original_request,polygon.review_body(r))
 OR ROW(plan.receipt_id,plan.user_id,plan.login_id,plan.review_id,plan.started_at)
 IS DISTINCT FROM ROW(cr.id,s.user_id,au.login_id,r.id,s.started_at) THEN RETURN false; END IF;
 IF r.record_schema_version<>'v1' OR st.record_schema_version<>'v1' OR sn.record_schema_version<>'v1'
  OR r.allowed_to_start IS DISTINCT FROM true OR r.normalization_valid IS DISTINCT FROM true
  OR r.reason_details IS DISTINCT FROM '{"reasons":[],"fieldErrors":[]}'::jsonb
  OR ROW(s.user_id,s.ownership_id,s.venue_id,s.source_id,s.trader_id,s.trader_revision_id,s.iana_timezone)
    IS DISTINCT FROM ROW(r.user_id,r.ownership_id,r.venue_id,r.source_id,r.trader_id,r.trader_revision_id,r.proposed_timezone)
  OR ROW(d.user_id,d.version,d.ownership_id,d.used_at,d.used_by_session_id)
    IS DISTINCT FROM ROW(s.user_id,r.draft_version,r.ownership_id,s.started_at,s.id)
  OR sl.user_id IS DISTINCT FROM s.user_id
  OR ROW(d.venue_id,d.trader_id,d.selected_mode,d.raw_budget,d.raw_fixed_amount,d.raw_copy_percent,d.raw_market_limit_percent,d.raw_daily_buy_limit_percent,d.proposed_timezone)
    IS DISTINCT FROM ROW(r.venue_id,r.trader_id,r.selected_mode,r.raw_budget,r.raw_fixed_amount,r.raw_copy_percent,r.raw_market_limit_percent,r.raw_daily_buy_limit_percent,r.proposed_timezone)
  OR ROW(cr.user_id,cr.command_type,cr.outcome,cr.result_session_id,cr.result_settings_revision_id)
    IS DISTINCT FROM ROW(s.user_id,'C06'::text,'succeeded'::text,s.id,st.id) THEN RETURN false; END IF;
 IF ROW(st.session_id,st.command_receipt_id,st.budget_n,st.budget_d,st.sizing_mode,st.fixed_n,st.fixed_d,st.copy_percent,
 st.market_percent,st.daily_percent,st.market_n,st.market_d,st.daily_n,st.daily_d,st.policy_id,st.created_at)
 IS DISTINCT FROM ROW(s.id,cr.id,r.budget_n,r.budget_d,r.selected_mode,r.fixed_n,r.fixed_d,r.copy_percent,
 r.market_percent,r.daily_percent,r.market_n,r.market_d,r.daily_n,r.daily_d,r.policy_id,s.started_at) THEN RETURN false; END IF;
 IF ROW(f.session_id,f.command_receipt_id,f.amount_n,f.amount_d,f.created_at,j.session_id,j.command_receipt_id,j.funding_flow_id,j.created_at)
  IS DISTINCT FROM ROW(s.id,cr.id,r.budget_n,r.budget_d,s.started_at,s.id,cr.id,f.id,s.started_at) THEN RETURN false; END IF;
 IF (SELECT count(*) FROM polygon.journal_entries WHERE journal_id=j.id)<>2 THEN RETURN false; END IF;
 FOR je IN SELECT * FROM polygon.journal_entries WHERE journal_id=j.id LOOP
  IF ROW(je.session_id,je.amount_n,je.amount_d,je.unit) IS DISTINCT FROM
    ROW(s.id,CASE WHEN je.account='paper_cash' THEN r.budget_n ELSE -r.budget_n END,r.budget_d,'virtual_USD'::text) THEN RETURN false; END IF;
 END LOOP;
 IF ROW(sn.session_id,sn.settings_revision_id,sn.initial_funding_n,sn.initial_funding_d,sn.free_n,sn.free_d,sn.equity_n,sn.equity_d,sn.as_of,sn.created_at)
 IS DISTINCT FROM ROW(s.id,st.id,r.budget_n,r.budget_d,r.budget_n,r.budget_d,r.budget_n,r.budget_d,s.started_at,s.started_at) THEN RETURN false; END IF;
 IF ROW(au.receipt_id,au.actor_user_id,au.snapshot_id,au.created_at,ob.receipt_id,ob.created_at)
 IS DISTINCT FROM ROW(cr.id,s.user_id,sn.id,s.started_at,cr.id,s.started_at) THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT 1 FROM polygon.users u JOIN v00_session.logins l ON l.actor_id=u.auth_actor_id WHERE u.id=s.user_id AND l.id=au.login_id)
 THEN RETURN false; END IF;
 IF polygon.receipt_reply(cr.id)->>'http'<>'201' THEN RETURN false; END IF;
 RETURN true;
END $$;
