\set ON_ERROR_STOP on
-- Explicit operator-only step on the stopped, isolated release candidate.
-- Independent host/container/mount/transport receipt and exact manifest required.
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL search_path=pg_catalog,pg_temp;
\ir 010-input.sql
DO $$ BEGIN
 IF to_regclass('polygon_live_activity.release_record') IS NOT NULL
 OR EXISTS(SELECT FROM polygon_live_activity.assignments)
 OR EXISTS(SELECT FROM polygon_live_activity.stream)
 OR EXISTS(SELECT FROM polygon_live_activity.operations)
 OR EXISTS(SELECT FROM polygon_live_activity.calls)
 OR EXISTS(SELECT FROM polygon.paper_sessions sess WHERE polygon.session_valid(sess.id) IS DISTINCT FROM true)
 THEN RAISE EXCEPTION 'unmarked intact release candidate without activity required'; END IF;
END $$;
SET LOCAL ROLE polygon_owner;
CREATE TABLE polygon_live_activity.release_record(
 singleton boolean PRIMARY KEY CHECK(singleton),
 database_name text NOT NULL,run_id uuid NOT NULL,database_oid oid NOT NULL,
 system_identifier text NOT NULL CHECK(system_identifier ~ '^[1-9][0-9]{0,19}$'),
 manifest_sha256 text NOT NULL CHECK(manifest_sha256 ~ '^[0-9a-f]{64}$'),
 profile text NOT NULL CHECK(profile='operator-bounded-public-skip-v1'),
 created_at timestamptz NOT NULL
);
REVOKE ALL ON polygon_live_activity.release_record FROM PUBLIC,polygon_executor;
CREATE TRIGGER immutable_release BEFORE UPDATE OR DELETE
 ON polygon_live_activity.release_record FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_release_truncate BEFORE TRUNCATE
 ON polygon_live_activity.release_record FOR EACH STATEMENT EXECUTE FUNCTION polygon.immutable_row();
INSERT INTO polygon_live_activity.release_record
 SELECT true,database_name,run_id,database_oid,system_identifier,manifest_sha256,
 'operator-bounded-public-skip-v1',date_trunc('milliseconds',clock_timestamp())
 FROM release_operator_input;
SET CONSTRAINTS ALL IMMEDIATE;
COMMIT;
