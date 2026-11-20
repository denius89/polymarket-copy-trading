CREATE TABLE polygon_live_activity.installation(
 singleton boolean PRIMARY KEY CHECK(singleton),database_name text NOT NULL,run_id uuid NOT NULL,
 profile text NOT NULL CHECK(profile='per-session-bound-skip-v1'),created_at timestamptz NOT NULL
);
INSERT INTO polygon_live_activity.installation SELECT true,db,run_id,'per-session-bound-skip-v1',date_trunc('milliseconds',clock_timestamp()) FROM live_activity_input;
CREATE TABLE polygon_live_activity.assignments(
 session_id uuid PRIMARY KEY,stream_id uuid NOT NULL UNIQUE,binding_revision bigint NOT NULL CHECK(binding_revision=1),
 database_name text NOT NULL,run_id uuid NOT NULL,writer_role name NOT NULL UNIQUE,writer_oid oid NOT NULL UNIQUE,
 user_id uuid NOT NULL,source_id uuid NOT NULL,venue_id uuid NOT NULL,trader_id uuid NOT NULL,revision_id uuid NOT NULL,
 owner_address text NOT NULL CHECK(owner_address='0x1111111111111111111111111111111111111111'),
 namespace text NOT NULL CHECK(namespace='polygon-137-ctfv2-orderfilled-owner-v1'),created_at timestamptz NOT NULL,
 FOREIGN KEY(session_id,user_id) REFERENCES polygon.paper_sessions(id,user_id),
 FOREIGN KEY(revision_id,trader_id,source_id,venue_id) REFERENCES polygon.trader_revisions(id,trader_id,source_id,venue_id),
 CHECK(writer_role::text ~ '^polygon_live_writer_[0-9a-f]{32}$')
);
CREATE TRIGGER immutable_installation BEFORE UPDATE OR DELETE ON polygon_live_activity.installation FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_assignment BEFORE UPDATE OR DELETE ON polygon_live_activity.assignments FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE FUNCTION polygon_live_activity.has_binding(sid uuid) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM polygon_live_activity.assignments WHERE session_id=sid)
$$;
CREATE FUNCTION polygon_live_activity.role_valid(who oid) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM pg_roles r WHERE r.oid=who AND r.rolname::text ~ '^polygon_live_writer_[0-9a-f]{32}$'
 AND to_regprocedure('polygon.live_activity_arm(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_ingest(jsonb)') IS NOT NULL
 AND to_regprocedure('polygon.live_activity_stop(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_lookup(jsonb)') IS NOT NULL
 AND r.rolcanlogin AND NOT(r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls)
 AND NOT EXISTS(SELECT FROM pg_auth_members WHERE member=r.oid)
 AND NOT EXISTS(SELECT FROM pg_namespace n WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','v00_session','v00_upstream') AND has_schema_privilege(r.oid,n.oid,'CREATE'))
 AND NOT EXISTS(SELECT FROM pg_namespace n WHERE n.nspname IN('polygon_live','polygon_live_activity','v00_session','v00_upstream') AND has_schema_privilege(r.oid,n.oid,'USAGE'))
 AND NOT EXISTS(SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity') AND has_function_privilege(r.oid,p.oid,'EXECUTE')
 AND (p.oid NOT IN(to_regprocedure('polygon.live_activity_arm(jsonb)'),to_regprocedure('polygon.live_activity_ingest(jsonb)'),
 to_regprocedure('polygon.live_activity_stop(jsonb)'),to_regprocedure('polygon.live_activity_lookup(jsonb)'))
 OR has_function_privilege(r.oid,p.oid,'EXECUTE WITH GRANT OPTION')))
 AND NOT EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','v00_session','v00_upstream') AND c.relkind IN('r','p','v','m','S')
 AND CASE WHEN c.relkind='S' THEN has_sequence_privilege(r.oid,c.oid,'USAGE,SELECT,UPDATE')
 ELSE has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') END))
$$;
