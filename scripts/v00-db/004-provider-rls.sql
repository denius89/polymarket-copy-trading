\set ON_ERROR_STOP on
-- Integrated isolated stand only. Keep provider RLS enabled; no BYPASSRLS role.
BEGIN;
SET LOCAL ROLE v00_db_owner;
CREATE TABLE v00_db.provider_allowlist (
  user_id uuid PRIMARY KEY,
  registered_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
REVOKE ALL ON v00_db.provider_allowlist FROM PUBLIC,v00_db_executor,v00_db_observer;
GRANT SELECT ON v00_db.provider_allowlist TO v00_db_observer;
-- Only the trusted operator/owner may populate this list, after checking fixture IDs.
RESET ROLE;
CREATE POLICY v00_probe_user_read ON auth.users FOR SELECT TO v00_db_owner
  USING (id IN (SELECT user_id FROM v00_db.provider_allowlist)
    AND lower(email) LIKE '%.invalid');
CREATE POLICY v00_probe_user_lock ON auth.users FOR UPDATE TO v00_db_owner
  USING (id IN (SELECT user_id FROM v00_db.provider_allowlist)
    AND lower(email) LIKE '%.invalid')
  WITH CHECK (false);
CREATE POLICY v00_probe_session_read ON auth.sessions FOR SELECT TO v00_db_owner
  USING (user_id IN (SELECT user_id FROM v00_db.provider_allowlist));
COMMIT;
