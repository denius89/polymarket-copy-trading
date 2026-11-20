CREATE TABLE polygon_live.public_source(
 singleton boolean PRIMARY KEY CHECK(singleton),database_name text NOT NULL,operator_run_id uuid NOT NULL,
 purpose text NOT NULL CHECK(purpose='empty_session_only'),venue_id uuid NOT NULL REFERENCES polygon.venues,
 source_id uuid NOT NULL CHECK(source_id='1ae54ea1-7149-48f1-8189-41be4fa064ce'),
 trader_id uuid NOT NULL CHECK(trader_id='6e91ae7c-a813-4b98-9bbc-022c0e04c2ff'),
 revision_id uuid NOT NULL CHECK(revision_id='faf7d35a-f4a4-4b8c-a1d4-74ed2bbe1ebd'),
 admission_id uuid NOT NULL CHECK(admission_id='77517c4e-6e3e-4bd3-9007-557f44a1a56d'),
 source_binding_version bigint NOT NULL CHECK(source_binding_version=1),
 adapter_version text NOT NULL CHECK(adapter_version='polymarket-empty-session-v1'),
 policy_version text NOT NULL CHECK(policy_version='real-trader-empty-session-v1'),
 snapshot_sha256 text NOT NULL CHECK(snapshot_sha256~'^[0-9a-f]{64}$'),created_at timestamptz NOT NULL,
 FOREIGN KEY(revision_id,trader_id,source_id,venue_id) REFERENCES polygon.trader_revisions(id,trader_id,source_id,venue_id)
);
CREATE TABLE polygon_live.admissions(
 user_id uuid NOT NULL REFERENCES polygon.users,source_id uuid NOT NULL REFERENCES polygon.catalog_sources,
 PRIMARY KEY(user_id,source_id)
);
CREATE TRIGGER immutable_source BEFORE UPDATE OR DELETE ON polygon_live.public_source FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_admission BEFORE UPDATE OR DELETE ON polygon_live.admissions FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
ALTER TABLE polygon.catalog_sources DROP CONSTRAINT catalog_sources_data_origin_check;
ALTER TABLE polygon.catalog_sources ADD CONSTRAINT live_source_origin CHECK(
 (id='1ae54ea1-7149-48f1-8189-41be4fa064ce' AND data_origin='public_api') OR
 (id<>'1ae54ea1-7149-48f1-8189-41be4fa064ce' AND data_origin='synthetic'));
ALTER TABLE polygon.traders ADD CONSTRAINT live_pinned_identity CHECK(
 (source_id<>'1ae54ea1-7149-48f1-8189-41be4fa064ce' AND id<>'6e91ae7c-a813-4b98-9bbc-022c0e04c2ff') OR
 (source_id='1ae54ea1-7149-48f1-8189-41be4fa064ce' AND id='6e91ae7c-a813-4b98-9bbc-022c0e04c2ff'
 AND external_trader_id='0x1111111111111111111111111111111111111111' AND current_revision_id='faf7d35a-f4a4-4b8c-a1d4-74ed2bbe1ebd'));
DO $$ DECLARE i record; v uuid; t timestamptz:=date_trunc('milliseconds',clock_timestamp()); BEGIN
 SELECT * INTO STRICT i FROM live_install_input;
 SELECT id INTO STRICT v FROM polygon.venues WHERE code='polymarket';
 INSERT INTO polygon.catalog_sources VALUES('1ae54ea1-7149-48f1-8189-41be4fa064ce',v,1,true,true,'public_api');
 INSERT INTO polygon.traders VALUES('6e91ae7c-a813-4b98-9bbc-022c0e04c2ff','1ae54ea1-7149-48f1-8189-41be4fa064ce',v,
 1,true,true,'faf7d35a-f4a4-4b8c-a1d4-74ed2bbe1ebd','0x1111111111111111111111111111111111111111');
 INSERT INTO polygon.trader_revisions VALUES('faf7d35a-f4a4-4b8c-a1d4-74ed2bbe1ebd','6e91ae7c-a813-4b98-9bbc-022c0e04c2ff',
 '1ae54ea1-7149-48f1-8189-41be4fa064ce',v,i.provenance->>'displayName',i.provenance->>'sourceRef',
 (i.provenance->>'observedAt')::timestamptz,1,t,1);
 INSERT INTO polygon_live.public_source VALUES(true,current_database(),i.run_id,'empty_session_only',v,
 '1ae54ea1-7149-48f1-8189-41be4fa064ce','6e91ae7c-a813-4b98-9bbc-022c0e04c2ff','faf7d35a-f4a4-4b8c-a1d4-74ed2bbe1ebd',
 '77517c4e-6e3e-4bd3-9007-557f44a1a56d',1,'polymarket-empty-session-v1','real-trader-empty-session-v1',i.provenance->>'snapshotSha256',t);
 INSERT INTO polygon_live.admissions SELECT id,'1ae54ea1-7149-48f1-8189-41be4fa064ce' FROM polygon.users;
 INSERT INTO polygon.scope_sources SELECT id,'1ae54ea1-7149-48f1-8189-41be4fa064ce' FROM polygon.read_scopes;
 UPDATE polygon.read_scopes SET revision=revision+1;
END $$;
CREATE FUNCTION polygon_live.source_admitted(uid uuid,src uuid,tr uuid,rev uuid,v uuid) RETURNS boolean
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM polygon.catalog_sources c JOIN polygon.trader_revisions r ON r.source_id=c.id AND r.venue_id=c.venue_id
 WHERE c.id=src AND c.venue_id=v AND r.id=rev AND r.trader_id=tr AND (c.data_origin='synthetic' OR
 EXISTS(SELECT FROM polygon_live.public_source p JOIN polygon_live.admissions a ON a.source_id=p.source_id
 JOIN polygon.traders t ON t.id=p.trader_id WHERE p.database_name=current_database() AND a.user_id=uid
 AND ROW(p.source_id,p.trader_id,p.revision_id,p.venue_id)=ROW(src,tr,rev,v)
 AND t.external_trader_id='0x1111111111111111111111111111111111111111')))
$$;
CREATE FUNCTION polygon_live.public_valid(sid uuid) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM polygon.paper_sessions s JOIN polygon_live.public_source p
 ON ROW(s.source_id,s.trader_id,s.trader_revision_id,s.venue_id)=ROW(p.source_id,p.trader_id,p.revision_id,p.venue_id)
 JOIN polygon.session_snapshots sn ON sn.session_id=s.id AND sn.version=1
 WHERE s.id=sid AND sn.data_origin='public_api' AND polygon_live.source_admitted(s.user_id,s.source_id,s.trader_id,s.trader_revision_id,s.venue_id))
$$;
