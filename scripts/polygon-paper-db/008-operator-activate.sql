\set ON_ERROR_STOP on
-- Execute only after server/backend/DB package review and disposable assertions.
-- Separate existing/new runtime LOGIN is provisioned by server; no secrets here.
-- Required variables polygon_runtime_role and polygon_tzdb_version.
BEGIN;
SELECT set_config('polygon.activate_role',:'polygon_runtime_role',true);
SELECT set_config('polygon.activate_tzdb',:'polygon_tzdb_version',true);
DO $$
DECLARE r pg_roles; pr polygon.profile;
BEGIN
 SELECT * INTO pr FROM polygon.profile WHERE singleton FOR UPDATE;
 IF pr.singleton IS NULL OR pr.enabled OR pr.timezone_database_version<>current_setting('polygon.activate_tzdb')
 THEN RAISE EXCEPTION 'unexpected profile state or timezone data'; END IF;
 SELECT * INTO r FROM pg_roles WHERE rolname=current_setting('polygon.activate_role');
 IF r.oid IS NULL OR NOT r.rolcanlogin OR r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls
 THEN RAISE EXCEPTION 'unsafe runtime role'; END IF;
 IF EXISTS(SELECT 1 FROM pg_auth_members WHERE member=r.oid) THEN RAISE EXCEPTION 'runtime role must initially have no memberships'; END IF;
 EXECUTE format('GRANT polygon_executor TO %I',r.rolname);
 UPDATE polygon.paper_controls SET enabled=true,version=version+1 WHERE singleton;
 UPDATE polygon.profile SET enabled=true WHERE singleton;
END $$;
COMMIT;
