BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout='3s';
SET LOCAL ROLE polygon_owner;
SET LOCAL search_path=pg_catalog;
CREATE VIEW polygon_buy.current_tradecraft_gap AS
 SELECT e.session_id,a.stream_id,a.run_id,st.arm_operation_id,st.baseline,st.armed_at,b.bound_at
 FROM polygon_buy.enrolled e JOIN polygon_buy.issuer_scopes sc USING(session_id)
 JOIN polygon_live_activity.assignments a USING(session_id)
 JOIN polygon_buy.bindings b ON b.session_id=e.session_id AND b.run_id=a.run_id
 JOIN polygon_live_activity.stream st ON st.session_id=e.session_id
 JOIN polygon_live_activity.operations op ON (op.session_id,op.id,op.kind)=(e.session_id,st.arm_operation_id,'arm')
 JOIN polygon.paper_sessions s ON (s.id,s.user_id,s.trader_revision_id)=(e.session_id,e.user_id,e.revision_id)
 JOIN polygon.user_session_slots sl ON (sl.user_id,sl.current_session_id)=(s.user_id,s.id)
 JOIN polygon.settings_revisions r ON (r.session_id,r.id)=(s.id,s.current_settings_revision_id)
 JOIN polygon_live_activity.release_record rel ON rel.run_id=e.run_id AND rel.database_name=current_database()
 WHERE polygon_buy.pinned_tradecraft(e.session_id) AND s.lifecycle='active'
 AND e.wallet='0xde9f7f4e77a1595623ceb58e469f776257ccd43c' AND a.owner_address=e.wallet AND sc.wallet=e.wallet
 AND a.run_id=e.run_id AND a.user_id=e.user_id AND sc.settings_id=r.id AND a.database_name=current_database()
 AND rel.database_oid=polygon_buy.database_oid() AND op.request->'baseline'=st.baseline AND op.created_at=st.armed_at
 AND op.request->>'runId'=a.run_id::text AND op.ordinal=1 AND st.armed_at<=b.bound_at
 AND r.sizing_mode='fixed' AND r.budget_n=200*r.budget_d AND r.fixed_n=20*r.fixed_d
 AND r.market_percent=10 AND r.daily_percent=15 AND r.market_n=20*r.market_d AND r.daily_n=30*r.daily_d;
DO $pin$ DECLARE x polygon_buy.current_tradecraft_gap; first_id uuid; BEGIN
 SELECT * INTO STRICT x FROM polygon_buy.current_tradecraft_gap;
 SELECT session_id INTO STRICT first_id FROM polygon_buy.current_breakthebank_segment WHERE polygon_buy.decision_gap_scope(session_id);
 EXECUTE format($f$CREATE FUNCTION polygon_buy.tradecraft_gap_scope(sid uuid) RETURNS boolean
 LANGUAGE sql STABLE SET search_path=pg_catalog AS $b$ SELECT EXISTS(SELECT FROM polygon_buy.current_tradecraft_gap t
 WHERE t.session_id=sid AND (t.session_id,t.stream_id,t.run_id,t.arm_operation_id)=(%L::uuid,%L::uuid,%L::uuid,%L::uuid)) $b$$f$,
 x.session_id,x.stream_id,x.run_id,x.arm_operation_id);
 ALTER TABLE polygon_buy.personal_log_dispositions DROP CONSTRAINT personal_log_dispositions_session_id_fkey,
 ADD FOREIGN KEY(session_id) REFERENCES polygon_buy.issuer_scopes;
 EXECUTE format('ALTER TABLE polygon_buy.personal_log_dispositions ADD CHECK(session_id IN (%L::uuid,%L::uuid))',first_id,x.session_id);
END $pin$;
DO $patch$ DECLARE d text;n text;f regprocedure; BEGIN
 FOREACH f IN ARRAY ARRAY['polygon_buy.guard_personal_admission()'::regprocedure,'polygon_buy.guard_decision_gap()'::regprocedure] LOOP
  d:=pg_get_functiondef(f); n:='IF NOT polygon_buy.decision_gap_scope(NEW.session_id) THEN';
  IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'unexpected decision-gap gate'; END IF;
  d:=replace(d,n,'IF NOT polygon_buy.decision_gap_scope(NEW.session_id) AND NOT polygon_buy.tradecraft_gap_scope(NEW.session_id) THEN');
  IF f='polygon_buy.guard_decision_gap()'::regprocedure THEN
   n:='AND EXISTS(SELECT FROM polygon_buy.issuer_scopes sc JOIN polygon_buy.segment_starts sg USING(session_id)
 WHERE sc.session_id=ob.session_id AND sc.wallet=ob.raw_log->>''owner'')';
   IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'unexpected BUY activation gate'; END IF;
   d:=replace(d,n,'AND ('||substr(n,5)||$b$ OR EXISTS(SELECT FROM polygon_buy.current_tradecraft_gap t
   WHERE t.session_id=ob.session_id AND polygon_buy.tradecraft_gap_scope(t.session_id)
   AND ob.raw_log->>'owner'='0xde9f7f4e77a1595623ceb58e469f776257ccd43c'
   AND (ob.header->>'number')::bigint>(t.baseline->>'number')::bigint
   AND to_timestamp((ob.header->>'timestampSeconds')::bigint)>t.armed_at))$b$);
  END IF;
  EXECUTE d;
 END LOOP;
 d:=pg_get_functiondef('polygon.personal_quote_issue_v1(jsonb)'::regprocedure);
 n:='AND NOT EXISTS(SELECT FROM polygon_buy.personal_start_blocks ab WHERE ab.session_id=sid';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'unexpected quote activation gate'; END IF;
 EXECUTE replace(d,n,$b$AND (NOT polygon_buy.tradecraft_gap_scope(sid) OR EXISTS(SELECT FROM polygon_buy.current_tradecraft_gap tg
 WHERE tg.session_id=sid AND (fin->>'blockNumber')::bigint>(tg.baseline->>'number')::bigint))
 $b$||n);
END $patch$;
REVOKE ALL ON polygon_buy.current_tradecraft_gap FROM PUBLIC,polygon_executor;
REVOKE ALL ON FUNCTION polygon_buy.tradecraft_gap_scope(uuid) FROM PUBLIC,polygon_executor;
COMMIT;
