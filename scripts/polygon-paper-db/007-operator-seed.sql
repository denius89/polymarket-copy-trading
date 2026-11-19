\set ON_ERROR_STOP on
-- Once only; operator, never runtime startup. Requires two existing verified
-- synthetic directory identities. No emails or credentials in this artifact/output.
-- Required psql variable polygon_tzdb_version: verified backend pinned data version.
BEGIN;
SELECT set_config('polygon.seed_tzdb',:'polygon_tzdb_version',true);
DO $$
DECLARE actor uuid; uid uuid; scope uuid; venue uuid; source uuid; trader uuid; rev uuid;
 code text; ordinal integer; t timestamptz:=date_trunc('milliseconds',clock_timestamp()); policy uuid:=gen_random_uuid();
BEGIN
 IF EXISTS(SELECT 1 FROM polygon.profile) OR EXISTS(SELECT 1 FROM polygon.users) OR EXISTS(SELECT 1 FROM polygon.venues)
 THEN RAISE EXCEPTION 'polygon already provisioned; no startup reseed'; END IF;
 IF (SELECT count(*) FROM v00_email.directory)<>2 OR
 (SELECT count(*) FROM v00_email.directory d JOIN v00_upstream.subjects s ON s.actor_id=d.actor_id
 JOIN v00_session.actors a ON a.id=s.actor_id JOIN auth.users u ON u.id=s.provider_user_id
 WHERE d.enabled AND NOT a.blocked AND a.fixed_time IS NULL AND u.email_confirmed_at IS NOT NULL
 AND (u.banned_until IS NULL OR u.banned_until<=clock_timestamp()))<>2
 THEN RAISE EXCEPTION 'expected two actual verified synthetic directory subjects'; END IF;
 INSERT INTO polygon.profile VALUES(true,'shadow-polygon-synthetic-v1',false,current_setting('polygon.seed_tzdb'),'24076847cf48c911eaa5fb21ca34b5969f89f109');
 INSERT INTO polygon.paper_policy_versions VALUES(policy,1,100,1000,10,5,200,1,1,20,0.5,5,20,1,10,30,1,30,'paper-settings-calculation-v1');
 INSERT INTO polygon.paper_controls VALUES(gen_random_uuid(),true,1,false,policy);
 FOREACH code IN ARRAY ARRAY['polymarket','limitless'] LOOP
  venue:=gen_random_uuid(); source:=gen_random_uuid();
  INSERT INTO polygon.venues VALUES(venue,code);
  INSERT INTO polygon.catalog_sources VALUES(source,venue,1,true,true,'synthetic');
  FOR ordinal IN 1..2 LOOP
   trader:=gen_random_uuid(); rev:=gen_random_uuid();
   INSERT INTO polygon.traders VALUES(trader,source,venue,1,true,true,rev,'synthetic-'||code||'-'||ordinal);
   INSERT INTO polygon.trader_revisions VALUES(rev,trader,source,venue,code||' demo '||ordinal,
    'synthetic:'||code||':'||ordinal,t,1,t,1);
  END LOOP;
 END LOOP;
 FOR actor IN SELECT actor_id FROM v00_email.directory ORDER BY actor_id LOOP
  uid:=gen_random_uuid(); scope:=gen_random_uuid();
  INSERT INTO polygon.users VALUES(uid,actor,t);
  INSERT INTO polygon.read_scopes VALUES(scope,uid,1);
  INSERT INTO polygon.scope_sources SELECT scope,id FROM polygon.catalog_sources;
 END LOOP;
END $$;
COMMIT;
-- Disabled until the operator binds the reviewed runtime/calendar package.
SELECT jsonb_build_object('profile','shadow-polygon-synthetic-v1','enabled',enabled,
 'users',(SELECT count(*) FROM polygon.users),'venues',(SELECT count(*) FROM polygon.venues),
 'sources',(SELECT count(*) FROM polygon.catalog_sources),'traders',(SELECT count(*) FROM polygon.traders)) FROM polygon.profile;
