BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout='3s';
SET LOCAL ROLE polygon_owner;
SET LOCAL search_path=pg_catalog;

-- Both writers contend on the same unique key even across overlapping snapshots.
CREATE TABLE polygon_buy.personal_log_dispositions(
 session_id uuid NOT NULL REFERENCES polygon_buy.segment_starts,
 transaction_hash text NOT NULL, log_index numeric NOT NULL,
 disposition text NOT NULL CHECK(disposition IN ('admission','skip')),
 PRIMARY KEY(session_id,transaction_hash,log_index)
);
CREATE TRIGGER immutable_disposition BEFORE UPDATE OR DELETE ON polygon_buy.personal_log_dispositions
 FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();

-- The unique, immutable enrollment wallet selects the personal session.
-- Pin the currently deployed segment once; a later session cannot inherit it.
CREATE VIEW polygon_buy.current_breakthebank_segment AS
 SELECT sg.session_id,sg.operation_id
 FROM polygon_buy.segment_starts sg
 JOIN polygon_live_activity.operations op ON op.session_id=sg.session_id AND op.id=sg.operation_id AND op.kind='start_segment'
 JOIN polygon_buy.enrolled e ON e.session_id=sg.session_id
 JOIN polygon_buy.issuer_scopes sc ON sc.session_id=e.session_id AND sc.wallet=e.wallet
 JOIN polygon_live_activity.assignments a ON (a.session_id,a.run_id,a.user_id,a.revision_id,a.owner_address)
   =(e.session_id,e.run_id,e.user_id,e.revision_id,e.wallet)
 JOIN polygon_buy.bindings b ON (b.session_id,b.run_id)=(a.session_id,a.run_id)
 JOIN polygon.paper_sessions s ON (s.id,s.user_id,s.trader_id,s.trader_revision_id,s.current_settings_revision_id)
   =(a.session_id,a.user_id,a.trader_id,a.revision_id,sc.settings_id)
 JOIN polygon.user_session_slots sl ON (sl.user_id,sl.current_session_id)=(s.user_id,s.id)
 JOIN polygon.traders t ON (t.id,t.source_id,t.venue_id,t.external_trader_id)=(s.trader_id,s.source_id,s.venue_id,e.wallet)
 JOIN polygon.catalog_sources c ON c.id=s.source_id AND c.data_origin='public_api'
 JOIN polygon.venues v ON v.id=s.venue_id AND v.code='polymarket'
 WHERE s.lifecycle='active' AND e.wallet='0xf0318c32136c2db7fec88b84869aee6a1106c80c';
DO $pin$ DECLARE target polygon_buy.current_breakthebank_segment; BEGIN
 SELECT * INTO STRICT target FROM polygon_buy.current_breakthebank_segment;
 EXECUTE format($fn$CREATE FUNCTION polygon_buy.decision_gap_scope(sid uuid) RETURNS boolean
 LANGUAGE sql STABLE SET search_path=pg_catalog AS
 $body$SELECT EXISTS(SELECT FROM polygon_buy.current_breakthebank_segment
 WHERE session_id=sid AND (session_id,operation_id)=(%L::uuid,%L::uuid))$body$$fn$,
 target.session_id,target.operation_id);
END $pin$;
CREATE FUNCTION polygon_buy.guard_personal_admission() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NOT polygon_buy.decision_gap_scope(NEW.session_id) THEN RETURN NEW; END IF;
  INSERT INTO polygon_buy.personal_log_dispositions VALUES(NEW.session_id,NEW.transaction_hash,NEW.log_index,'admission')
  ON CONFLICT DO NOTHING;
  IF NOT EXISTS(SELECT FROM polygon_buy.personal_log_dispositions WHERE session_id=NEW.session_id
    AND transaction_hash=NEW.transaction_hash AND log_index=NEW.log_index AND disposition='admission') THEN
   RAISE EXCEPTION 'final BUY skip already recorded';
  END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER personal_admission_disposition BEFORE INSERT ON polygon_buy.admissions
 FOR EACH ROW EXECUTE FUNCTION polygon_buy.guard_personal_admission();

DO $$ DECLARE d text; needle text:='ARRAY[''before_personal_activation'',''not_buy'','; BEGIN
 d:=pg_get_functiondef('polygon_live_activity.reason(text)'::regprocedure);
 IF cardinality(string_to_array(d,needle))<>2 THEN RAISE EXCEPTION 'unexpected reason registry'; END IF;
 EXECUTE replace(d,needle,'ARRAY[''copy_decision_unavailable'',''before_personal_activation'',''not_buy'',');
END $$;

CREATE OR REPLACE FUNCTION polygon_live_activity.evidence_shape(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT polygon_buy.pending_shape(v) OR coalesce(v->>'schemaVersion'='paper-buy-evidence-v1' AND v->>'kind'='skip'
 AND polygon_live_activity.reason(v->>'reason') AND polygon_live_activity.sha_value(v->'evidenceSha256')
 AND CASE WHEN v->>'reason'='copy_decision_unavailable' THEN
   polygon.exact_keys(v,ARRAY['schemaVersion','kind','reason','evidenceSha256','binding','decisionFence'])
   AND v->'binding'='null'::jsonb
   AND polygon.exact_keys(v->'decisionFence',ARRAY['firstFinalizedObservedAt','closedAt'])
   AND v#>>'{decisionFence,firstFinalizedObservedAt}' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}Z$'
   AND v#>>'{decisionFence,closedAt}' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}Z$'
 ELSE polygon.exact_keys(v,ARRAY['schemaVersion','kind','reason','evidenceSha256','binding'])
   AND polygon_live_activity.binding_shape(v->'binding') END,false)
$$;
CREATE FUNCTION polygon_buy.guard_decision_gap() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ob polygon_live_activity.observations; e jsonb:=NEW.checks->'evidence';
 first_at timestamptz; closed_at timestamptz;
BEGIN
 IF NOT polygon_buy.decision_gap_scope(NEW.session_id) THEN
  IF NEW.detail_code='copy_decision_unavailable' THEN RAISE EXCEPTION 'outside approved BreakTheBank segment'; END IF;
  RETURN NEW;
 END IF;
 SELECT * INTO STRICT ob FROM polygon_live_activity.observations WHERE id=NEW.observation_id AND session_id=NEW.session_id;
 IF NEW.detail_code<>'copy_decision_unavailable' AND ob.raw_log->>'side'<>'BUY' THEN RETURN NEW; END IF;
 IF NEW.detail_code='copy_decision_unavailable' THEN
 first_at:=(e#>>'{decisionFence,firstFinalizedObservedAt}')::timestamptz;
 closed_at:=(e#>>'{decisionFence,closedAt}')::timestamptz;
 IF (ob.classification='accepted' AND ob.raw_log->>'side'='BUY'
 AND EXISTS(SELECT FROM polygon_buy.issuer_scopes sc JOIN polygon_buy.segment_starts sg USING(session_id)
 WHERE sc.session_id=ob.session_id AND sc.wallet=ob.raw_log->>'owner')
 AND polygon_live_activity.evidence_shape(e) AND e->>'evidenceSha256'=ob.raw_log->>'receiptSha256'
 AND first_at>=to_timestamp((ob.header->>'timestampSeconds')::bigint)
 AND closed_at>=first_at+interval '30 seconds' AND closed_at<=ob.received_at AND closed_at<=clock_timestamp()) IS DISTINCT FROM true THEN
  RAISE EXCEPTION 'missing authenticated BUY decision closure';
 END IF;
 END IF;
 -- The normal entry point already holds the session lock and validated the
 -- complete stream. Mid-ingest its operation is still being assembled.
 IF (current_setting('transaction_isolation')='serializable'
 AND EXISTS(SELECT FROM polygon_live_activity.assignments a JOIN pg_roles r ON r.oid=a.writer_oid
 JOIN polygon_buy.issuer_scopes sc ON sc.session_id=a.session_id
 WHERE a.session_id=ob.session_id AND r.rolname=session_user AND a.writer_role=session_user
 AND a.owner_address=sc.wallet AND sc.wallet=ob.raw_log->>'owner')
 AND NOT EXISTS(SELECT FROM polygon_buy.admissions WHERE session_id=ob.session_id
 AND transaction_hash=ob.transaction_hash AND log_index=ob.log_index)) IS DISTINCT FROM true THEN
  RAISE EXCEPTION 'missing authenticated BUY decision closure or existing admission';
 END IF;
 INSERT INTO polygon_buy.personal_log_dispositions VALUES(ob.session_id,ob.transaction_hash,ob.log_index,'skip');
 RETURN NEW;
END $$;
CREATE TRIGGER personal_decision_gap BEFORE INSERT ON polygon_live_activity.decisions
 FOR EACH ROW WHEN (NEW.status='skipped' AND NEW.detail_code<>'before_personal_activation') EXECUTE FUNCTION polygon_buy.guard_decision_gap();
REVOKE ALL ON polygon_buy.current_breakthebank_segment,polygon_buy.personal_log_dispositions FROM PUBLIC,polygon_executor;
REVOKE ALL ON FUNCTION polygon_buy.decision_gap_scope(uuid),polygon_buy.guard_personal_admission(),polygon_buy.guard_decision_gap() FROM PUBLIC,polygon_executor;
COMMIT;
