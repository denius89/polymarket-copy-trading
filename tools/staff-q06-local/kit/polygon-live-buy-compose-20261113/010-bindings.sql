-- Run as polygon_owner, only after the pinned live/resume baseline and core sources.
CREATE SCHEMA polygon_buy AUTHORIZATION polygon_owner;
REVOKE ALL ON SCHEMA polygon_buy FROM PUBLIC,polygon_executor;
ALTER DEFAULT PRIVILEGES FOR ROLE polygon_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER TABLE polygon_live_activity.release_record ADD UNIQUE(run_id);
ALTER TABLE polygon_live_activity.observations ADD UNIQUE(session_id,id);
ALTER TABLE live_buy_core.scopes ADD FOREIGN KEY(session_id,owner_id) REFERENCES polygon.paper_sessions(id,user_id);
ALTER TABLE live_buy_core.scopes ADD FOREIGN KEY(release_id) REFERENCES polygon_live_activity.release_record(run_id);
ALTER TABLE live_buy_core.scopes ADD FOREIGN KEY(session_id,initial_snapshot_ref) REFERENCES polygon.session_snapshots(session_id,id);
ALTER TABLE live_buy_core.intents ADD FOREIGN KEY(session_id,observation_id) REFERENCES polygon_live_activity.observations(session_id,id);
ALTER TABLE live_buy_core.intents ADD COLUMN sizing_revision_id uuid GENERATED ALWAYS AS ((request->>'sizingRevisionId')::uuid) STORED;
ALTER TABLE live_buy_core.intents ADD COLUMN admission_revision_id uuid GENERATED ALWAYS AS ((request->>'admissionRevisionId')::uuid) STORED;
ALTER TABLE live_buy_core.intents ADD FOREIGN KEY(session_id,sizing_revision_id) REFERENCES polygon.settings_revisions(session_id,id);
ALTER TABLE live_buy_core.intents ADD FOREIGN KEY(session_id,admission_revision_id) REFERENCES polygon.settings_revisions(session_id,id);
CREATE TABLE polygon_buy.bindings(
 session_id uuid PRIMARY KEY REFERENCES live_buy_core.scopes,run_id uuid NOT NULL REFERENCES polygon_live_activity.release_record(run_id),
 first_sequence bigint NOT NULL CHECK(first_sequence>0),bound_at timestamptz NOT NULL,
 FOREIGN KEY(session_id) REFERENCES polygon_live_activity.assignments(session_id)
);
-- Only a separately verified/installed evaluator can populate this store. No grant
-- or installer here makes a market eligible. An empty store admits no write.
CREATE TABLE polygon_buy.admissions(
 id uuid PRIMARY KEY,session_id uuid NOT NULL REFERENCES polygon_buy.bindings,
 run_id uuid NOT NULL REFERENCES polygon_live_activity.release_record(run_id),
 kind text NOT NULL CHECK(kind IN('reserve','settle')),request jsonb NOT NULL,
 transaction_hash text NOT NULL CHECK(transaction_hash~'^0x[0-9a-f]{64}$'),log_index numeric(78,0) NOT NULL CHECK(log_index>=0),
 token_id text NOT NULL,condition_id text NOT NULL,profile_ref text NOT NULL,clock_ref text NOT NULL,fee_ref text NOT NULL,book_ref text NOT NULL,
 issued_at timestamptz NOT NULL,expires_at timestamptz NOT NULL CHECK(expires_at>issued_at),
 CHECK(live_buy_core.shape(request,kind)),UNIQUE(session_id,id),
 UNIQUE(session_id,kind,transaction_hash,log_index)
);
CREATE TABLE polygon_buy.commands(
 session_id uuid NOT NULL,command_id uuid NOT NULL,admission_id uuid NOT NULL,
 request jsonb NOT NULL,kind text NOT NULL CHECK(kind IN('reserve','settle')),
 PRIMARY KEY(session_id,command_id),
 FOREIGN KEY(session_id,command_id) REFERENCES live_buy_core.receipts DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(session_id,admission_id) REFERENCES polygon_buy.admissions(session_id,id)
);
ALTER TABLE live_buy_core.receipts ADD FOREIGN KEY(session_id,command_id) REFERENCES polygon_buy.commands DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE polygon_buy.ledger_index(
 session_id uuid NOT NULL REFERENCES polygon.paper_sessions,sequence bigint NOT NULL CHECK(sequence>0),
 initial_journal_id uuid,command_id uuid,
 PRIMARY KEY(session_id,sequence),UNIQUE(session_id,command_id),
 CHECK((sequence=1 AND initial_journal_id IS NOT NULL AND command_id IS NULL) OR (sequence>1 AND initial_journal_id IS NULL AND command_id IS NOT NULL)),
 FOREIGN KEY(initial_journal_id,session_id) REFERENCES polygon.journals(id,session_id),
 FOREIGN KEY(session_id,command_id) REFERENCES polygon_buy.commands DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO polygon_buy.ledger_index SELECT session_id,sequence,id,NULL FROM polygon.journals;
CREATE FUNCTION polygon_buy.initial_ledger() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN INSERT INTO polygon_buy.ledger_index VALUES(NEW.session_id,NEW.sequence,NEW.id,NULL);RETURN NULL;END $$;
CREATE TRIGGER buy_initial_ledger AFTER INSERT ON polygon.journals FOR EACH ROW EXECUTE FUNCTION polygon_buy.initial_ledger();
CREATE TABLE polygon_buy.snapshot_links(
 session_id uuid NOT NULL,version bigint NOT NULL,command_id uuid NOT NULL,snapshot_id uuid NOT NULL,
 PRIMARY KEY(session_id,version),UNIQUE(session_id,command_id),UNIQUE(session_id,snapshot_id),
 FOREIGN KEY(session_id,version) REFERENCES live_buy_core.snapshots DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(session_id,snapshot_id) REFERENCES polygon.session_snapshots(session_id,id) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(session_id,command_id) REFERENCES polygon_buy.commands DEFERRABLE INITIALLY DEFERRED
);
DO $$DECLARE n text;BEGIN
 FOREACH n IN ARRAY ARRAY['bindings','admissions','commands','ledger_index','snapshot_links'] LOOP
 EXECUTE format('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON polygon_buy.%I FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row()',n);
 END LOOP;
END $$;
CREATE FUNCTION polygon_buy.bind_session(sid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions;st polygon.settings_revisions;sn polygon.session_snapshots;a polygon_live_activity.assignments;r polygon_live_activity.release_record;stream polygon_live_activity.stream;t timestamptz:=live_buy_core.decision_time();
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required';END IF;
 PERFORM 1 FROM v00_upstream.gate WHERE singleton FOR SHARE;
 PERFORM 1 FROM polygon.profile WHERE singleton FOR SHARE;
 SELECT * INTO STRICT s FROM polygon.paper_sessions WHERE id=sid FOR UPDATE;
 SELECT * INTO STRICT a FROM polygon_live_activity.assignments WHERE session_id=sid;
 SELECT * INTO STRICT stream FROM polygon_live_activity.stream WHERE session_id=sid FOR UPDATE;
 SELECT * INTO STRICT r FROM polygon_live_activity.release_record WHERE singleton;
 SELECT * INTO STRICT st FROM polygon.settings_revisions WHERE session_id=sid AND id=s.current_settings_revision_id;
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=sid AND version=1;
 IF s.version<>1 OR s.lifecycle<>'active' OR stream.status<>'stopped' OR polygon.session_valid(sid) IS DISTINCT FROM true
 OR polygon_live_activity.bound_state_valid(sid) IS DISTINCT FROM true OR polygon_live_activity.calls_valid(sid) IS DISTINCT FROM true
 OR r.run_id<>a.run_id OR r.database_name<>current_database() OR r.database_oid<>polygon_buy.database_oid()
 THEN RAISE EXCEPTION 'intact stopped live/resume target required' USING ERRCODE='55000';END IF;
 INSERT INTO live_buy_core.scopes VALUES(sid,s.user_id,r.run_id,'polymarket',sn.id,s.iana_timezone,(t AT TIME ZONE s.iana_timezone)::date,t,
 live_buy_core.q(st.budget_n,st.budget_d),live_buy_core.q(st.market_n,st.market_d),live_buy_core.q(st.daily_n,st.daily_d));
 INSERT INTO live_buy_core.snapshots VALUES(sid,1,sn.id,live_buy_core.compute_state(sid,1,sn.id));
 INSERT INTO live_buy_core.heads VALUES(sid,1);
 INSERT INTO polygon_buy.bindings VALUES(sid,r.run_id,stream.high_watermark+1,t);
END $$;
