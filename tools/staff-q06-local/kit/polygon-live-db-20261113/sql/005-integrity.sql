CREATE FUNCTION polygon_live.result_valid(rid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE r polygon_live.results; a polygon_live.audit; c polygon_live.completions;
BEGIN
 SELECT * INTO r FROM polygon_live.results WHERE id=rid;
 SELECT * INTO a FROM polygon_live.audit WHERE result_id=rid;
 IF r.id IS NULL OR a.result_id IS NULL OR ROW(a.user_id,a.session_id,a.login_id,a.created_at)
 IS DISTINCT FROM ROW(r.user_id,r.session_id,r.login_id,r.created_at)
 OR NOT EXISTS(SELECT FROM polygon.users u JOIN v00_session.logins l ON l.actor_id=u.auth_actor_id WHERE u.id=r.user_id AND l.id=r.login_id)
 THEN RETURN false; END IF;
 SELECT * INTO c FROM polygon_live.completions WHERE result_id=rid;
 IF r.outcome='rejected' THEN RETURN c.id IS NULL; END IF;
 RETURN c.id IS NOT NULL AND ROW(c.user_id,c.session_id,c.completed_at) IS NOT DISTINCT FROM ROW(r.user_id,r.session_id,r.created_at)
  AND r.request->>'expectedSessionVersion'='1';
END $$;
CREATE FUNCTION polygon_live.terminal_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; a polygon.session_snapshots; b polygon.session_snapshots; c polygon_live.completions;
BEGIN
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 SELECT * INTO c FROM polygon_live.completions WHERE session_id=sid;
 SELECT * INTO a FROM polygon.session_snapshots WHERE session_id=sid AND version=1;
 SELECT * INTO b FROM polygon.session_snapshots WHERE session_id=sid AND version=2;
 IF s.id IS NULL OR c.id IS NULL OR a.id IS NULL OR b.id IS NULL OR NOT polygon_live.result_valid(c.result_id)
 OR ROW(c.user_id,c.slot_id,c.initial_snapshot_id,c.terminal_snapshot_id,c.completed_at)
 IS DISTINCT FROM ROW(s.user_id,s.slot_id,a.id,b.id,s.updated_at)
 OR ROW(s.version,s.current_snapshot_version,s.lifecycle) IS DISTINCT FROM ROW(2::bigint,2::bigint,'completed'::text)
 OR ROW(b.version,b.session_version,b.lifecycle,b.calculation_version,b.as_of,b.created_at)
 IS DISTINCT FROM ROW(2::bigint,2::bigint,'completed'::text,'paper-empty-completion-v1'::text,c.completed_at,c.completed_at)
 OR c.completed_at<s.started_at
 OR (to_jsonb(a)-ARRAY['id','version','session_version','lifecycle','calculation_version','as_of','created_at'])
 IS DISTINCT FROM (to_jsonb(b)-ARRAY['id','version','session_version','lifecycle','calculation_version','as_of','created_at'])
 THEN RETURN false; END IF;
 RETURN (SELECT count(*) FROM polygon.session_snapshots WHERE session_id=sid)=2;
END $$;
CREATE FUNCTION polygon_live.slot_valid(uid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE sl polygon.user_session_slots; s record; c polygon_live.completions; gen bigint:=0; current_id uuid; n integer:=0;
BEGIN
 SELECT * INTO sl FROM polygon.user_session_slots WHERE user_id=uid;
 IF sl.id IS NULL THEN RETURN NOT EXISTS(SELECT FROM polygon.paper_sessions WHERE user_id=uid); END IF;
 FOR s IN SELECT p.*,CASE WHEN r.slot_observation='absent' THEN 1 ELSE r.expected_slot_generation+1 END AS start_generation
 FROM polygon.paper_sessions p JOIN polygon.setup_reviews r ON r.id=p.review_id WHERE p.user_id=uid
 ORDER BY CASE WHEN r.slot_observation='absent' THEN 1 ELSE r.expected_slot_generation+1 END,p.id LOOP
  n:=n+1;
  IF current_id IS NOT NULL OR s.slot_id<>sl.id OR s.start_generation<>gen+1 THEN RETURN false; END IF;
  gen:=s.start_generation;
  SELECT * INTO c FROM polygon_live.completions WHERE session_id=s.id;
  IF s.lifecycle='active' THEN
   IF c.id IS NOT NULL THEN RETURN false; END IF;
   current_id:=s.id;
  ELSE
   IF c.id IS NULL OR c.before_generation<>gen OR c.after_generation<>gen+1 OR NOT polygon_live.terminal_valid(s.id) THEN RETURN false; END IF;
   gen:=gen+1;
  END IF;
 END LOOP;
 RETURN n>0 AND sl.generation=gen AND sl.current_session_id IS NOT DISTINCT FROM current_id;
END $$;
CREATE OR REPLACE FUNCTION polygon.session_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; sn polygon.session_snapshots; origin text;
BEGIN
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF s.id IS NULL OR polygon_live.initial_valid(sid) IS DISTINCT FROM true OR polygon_live.slot_valid(s.user_id) IS DISTINCT FROM true
 OR polygon_live.source_admitted(s.user_id,s.source_id,s.trader_id,s.trader_revision_id,s.venue_id) IS DISTINCT FROM true THEN RETURN false; END IF;
 SELECT * INTO sn FROM polygon.session_snapshots WHERE session_id=sid AND version=1;
 SELECT data_origin INTO origin FROM polygon.catalog_sources WHERE id=s.source_id;
 IF sn.data_origin IS DISTINCT FROM origin THEN RETURN false; END IF;
 IF s.lifecycle='completed' THEN RETURN polygon_live.terminal_valid(sid); END IF;
 RETURN s.version=1 AND s.current_snapshot_version=1 AND s.updated_at=s.started_at
 AND NOT EXISTS(SELECT FROM polygon_live.completions WHERE session_id=sid)
 AND (SELECT count(*) FROM polygon.session_snapshots WHERE session_id=sid)=1;
END $$;
CREATE FUNCTION polygon_live.enforce() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE uid uuid; s record; r record;
BEGIN
 IF TG_TABLE_SCHEMA='polygon_live' AND TG_TABLE_NAME='audit' THEN uid:=NEW.user_id;
 ELSIF TG_TABLE_NAME='paper_sessions' OR TG_TABLE_NAME='user_session_slots' OR TG_TABLE_NAME IN('results','completions') THEN uid:=NEW.user_id;
 ELSE SELECT user_id INTO uid FROM polygon.paper_sessions WHERE id=NEW.session_id; END IF;
 IF uid IS NULL OR polygon_live.slot_valid(uid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'invalid session slot history' USING ERRCODE='23514'; END IF;
 FOR s IN SELECT id FROM polygon.paper_sessions WHERE user_id=uid LOOP
  IF polygon.session_valid(s.id) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete lifecycle bundle' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR r IN SELECT id FROM polygon_live.results WHERE user_id=uid LOOP
  IF polygon_live.result_valid(r.id) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete completion result' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN NULL;
END $$;
DO $$ DECLARE n text; BEGIN
 FOREACH n IN ARRAY ARRAY['results','completions','audit'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER complete_lifecycle AFTER INSERT OR UPDATE ON polygon_live.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_live.enforce()',n);
 END LOOP;
 FOREACH n IN ARRAY ARRAY['paper_sessions','user_session_slots','session_snapshots'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER complete_lifecycle AFTER INSERT OR UPDATE ON polygon.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_live.enforce()',n);
 END LOOP;
END $$;
CREATE FUNCTION polygon_live.slot_write_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' OR NEW.id<>OLD.id OR NEW.user_id<>OLD.user_id OR NEW.generation<OLD.generation
 OR NEW.generation>OLD.generation+1 THEN RAISE EXCEPTION 'invalid slot transition' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER live_slot_write BEFORE UPDATE OR DELETE ON polygon.user_session_slots FOR EACH ROW EXECUTE FUNCTION polygon_live.slot_write_guard();
