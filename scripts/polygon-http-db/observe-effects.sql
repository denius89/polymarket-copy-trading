\set ON_ERROR_STOP on
-- Trusted operator reads actual committed HTTP effects in the disposable clone.
BEGIN READ ONLY;
SET LOCAL search_path=pg_catalog,pg_temp;
SET LOCAL polygon.http_runtime_role TO :'runtime_role';
DO $$
DECLARE u record; n integer:=0; expected_budget numeric; s polygon.paper_sessions;
 st polygon.settings_revisions; sn polygon.session_snapshots; f polygon.funding_flows;
 j polygon.journals; sl polygon.user_session_slots;
BEGIN
 IF current_setting('polygon.disposable_test',true) IS DISTINCT FROM 'offline-http-clone' THEN
  RAISE EXCEPTION 'explicit offline HTTP clone marker required'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND application_name='shadow-polygon-paper-api')
 OR EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND application_name='shadow-polygon-paper-api'
 AND usename IS DISTINCT FROM current_setting('polygon.http_runtime_role'))
 THEN RAISE EXCEPTION 'actual API connections must use the dedicated runtime LOGIN'; END IF;
 IF (SELECT count(*) FROM polygon.paper_sessions)<>2 OR (SELECT count(*) FROM polygon.settings_revisions)<>2
 OR (SELECT count(*) FROM polygon.funding_flows)<>2 OR (SELECT count(*) FROM polygon.journals)<>2
 OR (SELECT count(*) FROM polygon.journal_entries)<>4 OR (SELECT count(*) FROM polygon.session_snapshots)<>2
 OR (SELECT count(*) FROM polygon.audit_events)<>2 OR (SELECT count(*) FROM polygon.outbox_events)<>2
 OR (SELECT count(*) FROM polygon.users)<>2 OR (SELECT count(*) FROM polygon.user_session_slots)<>2
 THEN RAISE EXCEPTION 'unexpected HTTP financial bundle cardinality'; END IF;
 IF (SELECT count(*) FROM polygon.drafts)<>2 OR (SELECT count(*) FROM polygon.command_keys)<>8
 OR (SELECT count(*) FROM polygon.command_receipts)<>8 OR (SELECT count(*) FROM polygon.command_receipt_details)<>8
 OR (SELECT count(*) FROM polygon.setup_reviews)<>3
 OR (SELECT count(*) FROM polygon.command_receipts WHERE command_type='C04' AND outcome='succeeded')<>4
 OR (SELECT count(*) FROM polygon.command_receipts WHERE command_type='C04' AND outcome='rejected' AND reason_code='VERSION_CONFLICT')<>1
 OR (SELECT count(*) FROM polygon.command_receipts WHERE command_type='C06' AND outcome='succeeded')<>2
 OR (SELECT count(*) FROM polygon.command_receipts WHERE command_type='C06' AND outcome='rejected' AND reason_code='DRAFT_USED')<>1
 OR (SELECT count(*) FROM polygon.setup_reviews WHERE allowed_to_start AND normalization_valid)<>2
 OR (SELECT count(*) FROM polygon.setup_reviews WHERE NOT allowed_to_start AND NOT normalization_valid
 AND primary_reason_code='NUMERIC_SETTINGS_INVALID' AND raw_budget=decode('32303000','hex'))<>1
 THEN RAISE EXCEPTION 'HTTP command/review history cardinality mismatch'; END IF;
 FOR u IN SELECT * FROM polygon.users ORDER BY id LOOP
  n:=n+1; expected_budget:=CASE n WHEN 1 THEN 300 ELSE 100 END;
  SELECT * INTO s FROM polygon.paper_sessions WHERE user_id=u.id;
  SELECT * INTO st FROM polygon.settings_revisions WHERE id=s.current_settings_revision_id;
  SELECT * INTO sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=s.current_snapshot_version;
  SELECT * INTO f FROM polygon.funding_flows WHERE id=s.initial_funding_flow_id;
  SELECT * INTO j FROM polygon.journals WHERE id=f.journal_id;
  SELECT * INTO sl FROM polygon.user_session_slots WHERE id=s.slot_id;
  IF s.id IS NULL OR st.id IS NULL OR sn.id IS NULL OR f.id IS NULL OR j.id IS NULL OR sl.id IS NULL
  OR ROW(st.session_id,st.budget_n,st.budget_d) IS DISTINCT FROM ROW(s.id,expected_budget,1::numeric)
  OR ROW(sn.initial_funding_n,sn.initial_funding_d,sn.free_n,sn.free_d,sn.equity_n,sn.equity_d)
   IS DISTINCT FROM ROW(expected_budget,1::numeric,expected_budget,1::numeric,expected_budget,1::numeric)
  OR ROW(f.session_id,f.amount_n,f.amount_d,j.session_id) IS DISTINCT FROM ROW(s.id,expected_budget,1::numeric,s.id)
  OR ROW(sl.user_id,sl.current_session_id) IS DISTINCT FROM ROW(u.id,s.id)
  OR (SELECT count(*) FROM polygon.journal_entries WHERE journal_id=j.id)<>2
  OR (SELECT sum(amount_n/amount_d) FROM polygon.journal_entries WHERE journal_id=j.id) IS DISTINCT FROM 0::numeric
  OR NOT EXISTS(SELECT 1 FROM polygon.journal_entries WHERE journal_id=j.id AND account='paper_cash' AND amount_n=expected_budget AND amount_d=1)
  OR NOT EXISTS(SELECT 1 FROM polygon.journal_entries WHERE journal_id=j.id AND account<>'paper_cash' AND amount_n=-expected_budget AND amount_d=1)
  OR NOT EXISTS(SELECT 1 FROM polygon.audit_events WHERE session_id=s.id AND receipt_id=s.start_receipt_id AND snapshot_id=sn.id AND actor_user_id=u.id)
  OR NOT EXISTS(SELECT 1 FROM polygon.outbox_events WHERE session_id=s.id AND receipt_id=s.start_receipt_id)
  OR polygon.session_valid(s.id) IS DISTINCT FROM true
  THEN RAISE EXCEPTION 'HTTP financial tuple mismatch'; END IF;
 END LOOP;
END $$;
SELECT jsonb_build_object('format','polygon-http-effects-v1','financialTupleCheck','passed','runtimeConnectionCheck','passed',
 'sessions',(SELECT count(*) FROM polygon.paper_sessions),'settings',(SELECT count(*) FROM polygon.settings_revisions),
 'fundings',(SELECT count(*) FROM polygon.funding_flows),'journals',(SELECT count(*) FROM polygon.journals),
 'entries',(SELECT count(*) FROM polygon.journal_entries),'snapshots',(SELECT count(*) FROM polygon.session_snapshots),
 'audit',(SELECT count(*) FROM polygon.audit_events),'outbox',(SELECT count(*) FROM polygon.outbox_events),
 'receipts',(SELECT count(*) FROM polygon.command_receipts),'receiptDetails',(SELECT count(*) FROM polygon.command_receipt_details),
 'keys',(SELECT count(*) FROM polygon.command_keys),'reviews',(SELECT count(*) FROM polygon.setup_reviews),
 'drafts',(SELECT count(*) FROM polygon.drafts),
 'fundingTotal',(SELECT sum(amount_n/amount_d)::text FROM polygon.funding_flows),
 'freeTotal',(SELECT sum(free_n/free_d)::text FROM polygon.session_snapshots),
 'equityTotal',(SELECT sum(equity_n/equity_d)::text FROM polygon.session_snapshots),
 'ledgerNet',(SELECT sum(amount_n/amount_d)::text FROM polygon.journal_entries));
ROLLBACK;
