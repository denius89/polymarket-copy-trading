\set ON_ERROR_STOP on
\set resume_action install
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL search_path=pg_catalog,pg_temp;
\ir 000-target.sql
CREATE TEMP TABLE resume_function_pins(signature text PRIMARY KEY,before_sha text NOT NULL) ON COMMIT DROP;
INSERT INTO resume_function_pins VALUES
 ('polygon_live_activity.request_shape(jsonb,text)','c17c5acbeadd00740af8381f36cb91dda50d2732e1eb75108fb3e821b495f7ab'),
 ('polygon_live_activity.role_valid(oid)','281a1793a48b70fb63b5732c8a65827dfb72de630da99a6e952cdcbde560377c'),
 ('polygon_live_activity.dispatch(jsonb,text)','04697746db022faaf21e9b7e7900390c17058c1547ec186327818982c6f4fb68'),
 ('polygon_live_activity.stream_update_guard()','046601b63e83d9888258dee4d935b3be01e4200661c77be4e4716c7247197c4e'),
 ('polygon_live_activity.state_valid(uuid)','a4a19ed104bbdc8bbb6b5e345e1ca8cbd505ee9a90cc5445b8089aa86f18f6f4');
GRANT SELECT ON resume_function_pins TO polygon_owner;
DO $$ DECLARE pin record;tab text;constraint_name text;BEGIN
 IF to_regclass('polygon_live_activity.resume_patch') IS NOT NULL
 OR to_regprocedure('polygon.live_activity_resume(jsonb)') IS NOT NULL
 OR to_regprocedure('polygon_live_activity.inner_resume(jsonb)') IS NOT NULL
 THEN RAISE EXCEPTION 'resume patch already exists'; END IF;
 FOR pin IN SELECT * FROM resume_function_pins LOOP
  IF to_regprocedure(pin.signature) IS NULL OR encode(sha256(convert_to(pg_get_functiondef(to_regprocedure(pin.signature)),'UTF8')),'hex')<>pin.before_sha
  THEN RAISE EXCEPTION 'resume source pin mismatch: %',pin.signature; END IF;
 END LOOP;
 FOREACH tab IN ARRAY ARRAY['operations','calls'] LOOP
  constraint_name:=tab||'_kind_check';
  IF NOT EXISTS(SELECT FROM pg_constraint c WHERE c.conrelid=to_regclass('polygon_live_activity.'||tab)
    AND c.conname=constraint_name AND c.contype='c' AND c.convalidated
    AND pg_get_constraintdef(c.oid)='CHECK ((kind = ANY (ARRAY[''arm''::text, ''ingest''::text, ''stop''::text])))')
  THEN RAISE EXCEPTION 'original operation kind constraint mismatch'; END IF;
 END LOOP;
END $$;
SET LOCAL ROLE polygon_owner;
CREATE TABLE polygon_live_activity.resume_patch(
 singleton boolean PRIMARY KEY CHECK(singleton),session_id uuid NOT NULL REFERENCES polygon.paper_sessions(id),
 run_id uuid NOT NULL,writer_role name NOT NULL,writer_oid oid NOT NULL,
 manifest_sha256 text NOT NULL CHECK(manifest_sha256~'^[0-9a-f]{64}$'),
 profile text NOT NULL CHECK(profile='explicit-clean-stop-resume-v1'),
 installed_at timestamptz NOT NULL,function_hashes jsonb NOT NULL
);
REVOKE ALL ON polygon_live_activity.resume_patch FROM PUBLIC,polygon_executor;
CREATE TRIGGER immutable_resume_patch BEFORE UPDATE OR DELETE ON polygon_live_activity.resume_patch
 FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_resume_patch_truncate BEFORE TRUNCATE ON polygon_live_activity.resume_patch
 FOR EACH STATEMENT EXECUTE FUNCTION polygon.immutable_row();
ALTER TABLE polygon_live_activity.operations DROP CONSTRAINT operations_kind_check;
ALTER TABLE polygon_live_activity.operations ADD CONSTRAINT operations_kind_check CHECK(kind IN('arm','ingest','stop','resume'));
ALTER TABLE polygon_live_activity.calls DROP CONSTRAINT calls_kind_check;
ALTER TABLE polygon_live_activity.calls ADD CONSTRAINT calls_kind_check CHECK(kind IN('arm','ingest','stop','resume'));
\ir 003-resume.sql
\ir 005-functions.sql
INSERT INTO polygon_live_activity.resume_patch
 SELECT true,x.sid,x.run_id,a.writer_role,a.writer_oid,x.patch_sha,'explicit-clean-stop-resume-v1',
 date_trunc('milliseconds',clock_timestamp()),
 (SELECT jsonb_object_agg(signature,encode(sha256(convert_to(pg_get_functiondef(to_regprocedure(signature)),'UTF8')),'hex'))
 FROM (SELECT signature FROM resume_function_pins UNION ALL SELECT 'polygon.live_activity_resume(jsonb)'
       UNION ALL SELECT 'polygon_live_activity.inner_resume(jsonb)') funcs)
 FROM resume_input x JOIN polygon_live_activity.assignments a ON a.session_id=x.sid;
DO $$ DECLARE arg record;w name;BEGIN
 SELECT * INTO STRICT arg FROM resume_input;
 SELECT writer_role INTO STRICT w FROM polygon_live_activity.assignments WHERE session_id=arg.sid;
 EXECUTE format('GRANT EXECUTE ON FUNCTION polygon.live_activity_resume(jsonb) TO %I',w);
 IF polygon_live_activity.role_valid((SELECT writer_oid FROM polygon_live_activity.assignments WHERE session_id=arg.sid)) IS DISTINCT FROM true
 OR EXISTS(SELECT FROM polygon_live_activity.assignments a WHERE polygon_live_activity.state_valid(a.session_id) IS DISTINCT FROM true
   OR polygon_live_activity.bound_state_valid(a.session_id) IS DISTINCT FROM true OR polygon_live_activity.calls_valid(a.session_id) IS DISTINCT FROM true)
 THEN RAISE EXCEPTION 'post-patch role/history invalid'; END IF;
END $$;
\ir 007-preserved.sql
SET CONSTRAINTS ALL IMMEDIATE;
COMMIT;
