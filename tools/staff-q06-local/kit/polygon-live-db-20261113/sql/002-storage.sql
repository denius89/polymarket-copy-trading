-- Included by the single atomic installer as polygon_owner.
CREATE TABLE polygon_live.installation(
 singleton boolean PRIMARY KEY CHECK(singleton),database_name text NOT NULL,
 operator_run_id uuid NOT NULL,installed_at timestamptz NOT NULL,
 profile text NOT NULL CHECK(profile='empty-completion-public-skip-v1')
);
INSERT INTO polygon_live.installation SELECT true,current_database(),run_id,
 date_trunc('milliseconds',clock_timestamp()),'empty-completion-public-skip-v1' FROM live_install_input;
CREATE TABLE polygon_live.results(
 id uuid PRIMARY KEY,user_id uuid NOT NULL REFERENCES polygon.users,
 client_command_id uuid NOT NULL,session_id uuid NOT NULL,login_id uuid NOT NULL REFERENCES v00_session.logins,
 request jsonb NOT NULL,request_digest text NOT NULL,
 outcome text NOT NULL CHECK(outcome IN('committed','rejected')),
 reason_code text CHECK(reason_code IN('VERSION_CONFLICT','SESSION_NOT_SETTLED')),
 created_at timestamptz NOT NULL,
 UNIQUE(user_id,client_command_id),UNIQUE(id,session_id,user_id),
 FOREIGN KEY(session_id,user_id) REFERENCES polygon.paper_sessions(id,user_id),
 CHECK(polygon.exact_keys(request,ARRAY['requestSchemaVersion','clientCommandId','expectedSessionVersion'])),
 CHECK((request->>'requestSchemaVersion'='v1' AND request->>'clientCommandId'=client_command_id::text
  AND jsonb_typeof(request->'expectedSessionVersion')='string' AND polygon.version_text(request->>'expectedSessionVersion')) IS TRUE),
 CHECK(request_digest=encode(sha256(convert_to('complete-empty-v1'||chr(10)||user_id::text||chr(10)||session_id::text||chr(10)||request::text,'UTF8')),'hex')),
 CHECK((outcome='committed' AND reason_code IS NULL) OR (outcome='rejected' AND reason_code IS NOT NULL))
);
CREATE TABLE polygon_live.completions(
 id uuid PRIMARY KEY,session_id uuid NOT NULL UNIQUE,user_id uuid NOT NULL,
 result_id uuid NOT NULL UNIQUE,slot_id uuid NOT NULL,
 before_generation bigint NOT NULL CHECK(before_generation>0),after_generation bigint NOT NULL,
 initial_snapshot_id uuid NOT NULL,terminal_snapshot_id uuid NOT NULL UNIQUE,
 completed_at timestamptz NOT NULL,
 CHECK(after_generation=before_generation+1),CHECK(initial_snapshot_id<>terminal_snapshot_id),
 UNIQUE(id,result_id),
 FOREIGN KEY(result_id,session_id,user_id) REFERENCES polygon_live.results(id,session_id,user_id) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(session_id,slot_id,user_id) REFERENCES polygon.paper_sessions(id,slot_id,user_id),
 FOREIGN KEY(session_id,initial_snapshot_id) REFERENCES polygon.session_snapshots(session_id,id),
 FOREIGN KEY(session_id,terminal_snapshot_id) REFERENCES polygon.session_snapshots(session_id,id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE polygon_live.audit(
 result_id uuid PRIMARY KEY REFERENCES polygon_live.results DEFERRABLE INITIALLY DEFERRED,
 user_id uuid NOT NULL,session_id uuid NOT NULL,login_id uuid NOT NULL REFERENCES v00_session.logins,
 kind text NOT NULL CHECK(kind='paper_session.complete_empty'),created_at timestamptz NOT NULL,
 FOREIGN KEY(result_id,session_id,user_id) REFERENCES polygon_live.results(id,session_id,user_id)
);
ALTER TABLE polygon_live.results ADD FOREIGN KEY(id) REFERENCES polygon_live.audit(result_id) DEFERRABLE INITIALLY DEFERRED;
DO $$ DECLARE n text; BEGIN
 FOREACH n IN ARRAY ARRAY['installation','results','completions','audit'] LOOP
 EXECUTE format('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON polygon_live.%I FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row()',n);
 END LOOP;
END $$;

ALTER TABLE polygon.paper_sessions DROP CONSTRAINT paper_sessions_current_snapshot_version_check;
ALTER TABLE polygon.paper_sessions DROP CONSTRAINT paper_sessions_version_check;
ALTER TABLE polygon.paper_sessions DROP CONSTRAINT paper_sessions_lifecycle_check;
DO $$ DECLARE n text; num integer; BEGIN
 SELECT count(*),min(conname::text) INTO num,n FROM pg_constraint WHERE conrelid='polygon.paper_sessions'::regclass
  AND contype='c' AND pg_get_constraintdef(oid) LIKE '%(updated_at = started_at)%';
 IF num<>1 THEN RAISE EXCEPTION 'unexpected original session timestamp constraint'; END IF;
 EXECUTE format('ALTER TABLE polygon.paper_sessions DROP CONSTRAINT %I',n);
END $$;
ALTER TABLE polygon.paper_sessions ADD CONSTRAINT live_session_shape CHECK(
 created_at=started_at AND (
 (version=1 AND lifecycle='active' AND current_snapshot_version=1 AND updated_at=started_at) OR
 (version=2 AND lifecycle='completed' AND current_snapshot_version=2 AND updated_at>=started_at)));
ALTER TABLE polygon.session_snapshots DROP CONSTRAINT session_snapshots_version_check;
ALTER TABLE polygon.session_snapshots DROP CONSTRAINT session_snapshots_session_version_check;
ALTER TABLE polygon.session_snapshots DROP CONSTRAINT session_snapshots_calculation_version_check;
ALTER TABLE polygon.session_snapshots DROP CONSTRAINT session_snapshots_lifecycle_check;
ALTER TABLE polygon.session_snapshots DROP CONSTRAINT session_snapshots_data_origin_check;
ALTER TABLE polygon.session_snapshots ADD CONSTRAINT live_snapshot_shape CHECK(
 ((version=1 AND session_version=1 AND lifecycle='active' AND calculation_version='paper-empty-snapshot-v1') OR
 (version=2 AND session_version=2 AND lifecycle='completed' AND calculation_version='paper-empty-completion-v1'))
 AND data_origin IN('synthetic','public_api'));

CREATE FUNCTION polygon_live.session_write_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'session history cannot be deleted' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.version<>1 OR NEW.lifecycle<>'active' THEN RAISE EXCEPTION 'new session must start at version1' USING ERRCODE='23514'; END IF;
 ELSE
  IF OLD.version<>1 OR NEW.version<>2 OR NEW.lifecycle<>'completed'
   OR (to_jsonb(NEW)-ARRAY['version','lifecycle','current_snapshot_version','updated_at'])
    IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['version','lifecycle','current_snapshot_version','updated_at'])
  THEN RAISE EXCEPTION 'only immutable-identity empty completion allowed' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER immutable_history ON polygon.paper_sessions;
CREATE TRIGGER live_session_write BEFORE INSERT OR UPDATE OR DELETE ON polygon.paper_sessions
 FOR EACH ROW EXECUTE FUNCTION polygon_live.session_write_guard();
