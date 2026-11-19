BEGIN ISOLATION LEVEL SERIALIZABLE; SET LOCAL lock_timeout='3s'; SET LOCAL search_path=pg_catalog;

DO $$BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.binding_shape(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '5888287a80cf91a6aa5f3ac25e44c3bbbc27a6ff7d3aeb33ba933a1f101a1dc3' THEN RAISE EXCEPTION 'unexpected preimage of polygon_live_activity.binding_shape(jsonb)'; END IF; END $$;

DO $$BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.bound_ingest(jsonb,jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '6f246be1017721a8a10e003d54c41f65362234df1c57963619b65bc932722c35' THEN RAISE EXCEPTION 'unexpected preimage of polygon_live_activity.bound_ingest(jsonb,jsonb)'; END IF; END $$;

DO $$BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.inner_resume(jsonb)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '4a44ffe83aea2e46d49e32a7f8c7883f9f054ff54e584273a4f9fad4cc51ee81' THEN RAISE EXCEPTION 'unexpected preimage of polygon_live_activity.inner_resume(jsonb)'; END IF; END $$;

DO $$BEGIN IF encode(sha256(convert_to(pg_get_functiondef('polygon_live_activity.role_valid(oid)'::regprocedure),'UTF8')),'hex') IS DISTINCT FROM '406b1f1aea8a66db73f07bdac12038bc771b8e4789c5fd933d4abf2c7e76ca72' THEN RAISE EXCEPTION 'unexpected preimage of polygon_live_activity.role_valid(oid)'; END IF; END $$;

CREATE SCHEMA live_buy_core AUTHORIZATION polygon_owner; CREATE SCHEMA polygon_buy AUTHORIZATION polygon_owner; SET LOCAL ROLE polygon_owner;

-- Local private component, not an installer for the live application.
REVOKE ALL ON SCHEMA live_buy_core FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA live_buy_core REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
CREATE FUNCTION live_buy_core.keys(v jsonb, k text[]) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_typeof(v)='object' AND (SELECT array_agg(x ORDER BY x) FROM jsonb_object_keys(v) x)=(SELECT array_agg(x ORDER BY x) FROM unnest(k) x)
$$;
CREATE FUNCTION live_buy_core.q(n numeric,d numeric) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE a numeric; b numeric; r numeric;
BEGIN
 IF n IS NULL OR d IS NULL OR n::text IN('NaN','Infinity','-Infinity') OR d::text IN('NaN','Infinity','-Infinity')
 OR n<>trunc(n) OR d<>trunc(d) OR d=0 THEN RAISE EXCEPTION 'invalid rational' USING ERRCODE='22003'; END IF;
 IF d<0 THEN n:=-n; d:=-d; END IF;
 a:=abs(n);b:=d; WHILE b<>0 LOOP r:=mod(a,b);a:=b;b:=r;END LOOP;
 n:=div(n,a);d:=div(d,a);
 IF length(n::text)>257 OR length(d::text)>256 THEN RAISE EXCEPTION 'rational resource bound' USING ERRCODE='54000';END IF;
 RETURN jsonb_build_object('n',n::text,'d',d::text);
END $$;
CREATE FUNCTION live_buy_core.valid_q(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 IF live_buy_core.keys(v,ARRAY['n','d']) IS DISTINCT FROM true OR jsonb_typeof(v->'n') IS DISTINCT FROM 'string'
 OR jsonb_typeof(v->'d') IS DISTINCT FROM 'string' OR (v->>'n'~'^(0|-?[1-9][0-9]{0,255})$') IS DISTINCT FROM true
 OR (v->>'d'~'^[1-9][0-9]{0,255}$') IS DISTINCT FROM true THEN RETURN false; END IF;
 RETURN v=live_buy_core.q((v->>'n')::numeric,(v->>'d')::numeric);
END $$;
CREATE FUNCTION live_buy_core.addq(a jsonb,b jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT live_buy_core.q((a->>'n')::numeric*(b->>'d')::numeric+(b->>'n')::numeric*(a->>'d')::numeric,(a->>'d')::numeric*(b->>'d')::numeric)
$$;
CREATE FUNCTION live_buy_core.negq(a jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT live_buy_core.q(-(a->>'n')::numeric,(a->>'d')::numeric) $$;
CREATE FUNCTION live_buy_core.subq(a jsonb,b jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT live_buy_core.addq(a,live_buy_core.negq(b)) $$;
CREATE FUNCTION live_buy_core.mulq(a jsonb,b jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT live_buy_core.q((a->>'n')::numeric*(b->>'n')::numeric,(a->>'d')::numeric*(b->>'d')::numeric) $$;
CREATE FUNCTION live_buy_core.divq(a jsonb,b jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT live_buy_core.q((a->>'n')::numeric*(b->>'d')::numeric,(a->>'d')::numeric*(b->>'n')::numeric) $$;
CREATE FUNCTION live_buy_core.cmp(a jsonb,b jsonb) RETURNS int LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT sign((a->>'n')::numeric*(b->>'d')::numeric-(b->>'n')::numeric*(a->>'d')::numeric)::int $$;
CREATE AGGREGATE live_buy_core.sumq(jsonb)(SFUNC=live_buy_core.addq,STYPE=jsonb,INITCOND='{"n":"0","d":"1"}');
CREATE FUNCTION live_buy_core.nonnegative(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT live_buy_core.valid_q(v) AND live_buy_core.cmp(v,'{"n":"0","d":"1"}')>=0 $$;
CREATE FUNCTION live_buy_core.positive(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$ SELECT live_buy_core.valid_q(v) AND live_buy_core.cmp(v,'{"n":"0","d":"1"}')>0 $$;
CREATE FUNCTION live_buy_core.immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN RAISE EXCEPTION 'immutable financial history' USING ERRCODE='23514';END $$;

CREATE FUNCTION live_buy_core.iana_zone(z text) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT z IS NOT NULL AND (z='UTC' OR z~'^[A-Za-z_]+(/[A-Za-z0-9_+-]+)+$') AND EXISTS(SELECT FROM pg_timezone_names WHERE name=z)
$$;
CREATE FUNCTION live_buy_core.decision_time() RETURNS timestamptz LANGUAGE sql VOLATILE SET search_path=pg_catalog AS $$ SELECT clock_timestamp() $$;
CREATE TABLE live_buy_core.scopes(
 session_id uuid PRIMARY KEY, owner_id uuid NOT NULL, release_id uuid NOT NULL,
 venue text NOT NULL CHECK(venue='polymarket'),initial_snapshot_ref uuid NOT NULL,
 timezone_name text NOT NULL CHECK(live_buy_core.iana_zone(timezone_name)),operating_day date NOT NULL,opened_at timestamptz NOT NULL,
 budget jsonb NOT NULL CHECK(live_buy_core.positive(budget)),
 position_limit jsonb NOT NULL CHECK(live_buy_core.positive(position_limit)),
 daily_limit jsonb NOT NULL CHECK(live_buy_core.positive(daily_limit))
);
CREATE TABLE live_buy_core.intents(
 session_id uuid NOT NULL REFERENCES live_buy_core.scopes, id uuid NOT NULL, observation_id uuid NOT NULL,
 command_id uuid NOT NULL, version bigint NOT NULL CHECK(version>1), condition_id text NOT NULL CHECK(length(condition_id) BETWEEN 1 AND 256 AND condition_id~'^[A-Za-z0-9:_-]+$'),
 token_id text NOT NULL CHECK(length(token_id) BETWEEN 1 AND 256 AND token_id~'^[A-Za-z0-9:_-]+$'),request jsonb NOT NULL,
 quantity jsonb NOT NULL CHECK(live_buy_core.positive(quantity)),notional jsonb NOT NULL CHECK(live_buy_core.positive(notional)),
 reserved_cash jsonb NOT NULL CHECK(live_buy_core.positive(reserved_cash)), admitted_at timestamptz NOT NULL,
 not_before timestamptz NOT NULL CHECK(not_before>=admitted_at), quota_day date NOT NULL,
 PRIMARY KEY(session_id,id),UNIQUE(session_id,observation_id),UNIQUE(session_id,command_id)
);
CREATE TABLE live_buy_core.executions(
 session_id uuid NOT NULL,intent_id uuid NOT NULL,id uuid NOT NULL,command_id uuid NOT NULL,
 confirmation_id uuid NOT NULL,version bigint NOT NULL CHECK(version>1),settled_at timestamptz NOT NULL,
 PRIMARY KEY(session_id,intent_id),UNIQUE(session_id,id),UNIQUE(session_id,confirmation_id),UNIQUE(session_id,command_id),
 FOREIGN KEY(session_id,intent_id) REFERENCES live_buy_core.intents DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE live_buy_core.fills(
 session_id uuid NOT NULL,id uuid NOT NULL,intent_id uuid NOT NULL,ordinal int NOT NULL CHECK(ordinal BETWEEN 1 AND 128),
 price jsonb NOT NULL CHECK(live_buy_core.positive(price)),gross jsonb NOT NULL CHECK(live_buy_core.positive(gross)),
 quantity_fee jsonb NOT NULL CHECK(live_buy_core.nonnegative(quantity_fee)),cash_fee jsonb NOT NULL CHECK(live_buy_core.nonnegative(cash_fee)),
 executed_at timestamptz NOT NULL,net jsonb NOT NULL CHECK(live_buy_core.positive(net)),notional jsonb NOT NULL CHECK(live_buy_core.positive(notional)),
 PRIMARY KEY(session_id,id),UNIQUE(session_id,intent_id,ordinal),UNIQUE(session_id,intent_id,id),
 FOREIGN KEY(session_id,intent_id) REFERENCES live_buy_core.executions DEFERRABLE INITIALLY DEFERRED,
 CHECK(net=live_buy_core.subq(gross,quantity_fee)),CHECK(notional=live_buy_core.mulq(price,gross))
);
CREATE TABLE live_buy_core.lots(
 session_id uuid NOT NULL,fill_id uuid NOT NULL,intent_id uuid NOT NULL,
 original_quantity jsonb NOT NULL CHECK(live_buy_core.positive(original_quantity)),
 original_cost jsonb NOT NULL CHECK(live_buy_core.positive(original_cost)),
 attributed_cash_fee jsonb NOT NULL CHECK(live_buy_core.nonnegative(attributed_cash_fee)),
 attributed_quantity_fee jsonb NOT NULL CHECK(live_buy_core.nonnegative(attributed_quantity_fee)),
 PRIMARY KEY(session_id,fill_id), FOREIGN KEY(session_id,intent_id,fill_id) REFERENCES live_buy_core.fills(session_id,intent_id,id) DEFERRABLE INITIALLY DEFERRED
);
ALTER TABLE live_buy_core.fills ADD FOREIGN KEY(session_id,id) REFERENCES live_buy_core.lots(session_id,fill_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE live_buy_core.reservation_events(
 session_id uuid NOT NULL,intent_id uuid NOT NULL,kind text NOT NULL CHECK(kind IN('grant','settle')),
 notional jsonb NOT NULL CHECK(live_buy_core.positive(notional)),cash jsonb NOT NULL CHECK(live_buy_core.positive(cash)),
 released_cash jsonb NOT NULL CHECK(live_buy_core.nonnegative(released_cash)),
 PRIMARY KEY(session_id,intent_id,kind),FOREIGN KEY(session_id,intent_id) REFERENCES live_buy_core.intents DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE live_buy_core.journal_entries(
 session_id uuid NOT NULL,intent_id uuid NOT NULL,asset text NOT NULL,account text NOT NULL,
 amount jsonb NOT NULL CHECK(live_buy_core.valid_q(amount) AND live_buy_core.cmp(amount,'{"n":"0","d":"1"}')<>0),
 PRIMARY KEY(session_id,intent_id,asset,account),FOREIGN KEY(session_id,intent_id) REFERENCES live_buy_core.executions DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE live_buy_core.receipts(
 session_id uuid NOT NULL REFERENCES live_buy_core.scopes,command_id uuid NOT NULL,intent_id uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN('reserve','settle')),request jsonb NOT NULL,result jsonb NOT NULL,
 version bigint NOT NULL CHECK(version>1),PRIMARY KEY(session_id,command_id),UNIQUE(session_id,version),
 FOREIGN KEY(session_id,intent_id) REFERENCES live_buy_core.intents DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE live_buy_core.audit(
 session_id uuid NOT NULL,command_id uuid NOT NULL,kind text NOT NULL CHECK(kind IN('reserve','settle')),
 PRIMARY KEY(session_id,command_id),FOREIGN KEY(session_id,command_id) REFERENCES live_buy_core.receipts DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE live_buy_core.outbox(
 session_id uuid NOT NULL,command_id uuid NOT NULL,payload jsonb NOT NULL,
 PRIMARY KEY(session_id,command_id),FOREIGN KEY(session_id,command_id) REFERENCES live_buy_core.receipts DEFERRABLE INITIALLY DEFERRED
);
ALTER TABLE live_buy_core.receipts ADD FOREIGN KEY(session_id,command_id) REFERENCES live_buy_core.audit DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE live_buy_core.receipts ADD FOREIGN KEY(session_id,command_id) REFERENCES live_buy_core.outbox DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE live_buy_core.intents ADD FOREIGN KEY(session_id,command_id) REFERENCES live_buy_core.receipts DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE live_buy_core.executions ADD FOREIGN KEY(session_id,command_id) REFERENCES live_buy_core.receipts DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE live_buy_core.snapshots(
 session_id uuid NOT NULL REFERENCES live_buy_core.scopes,version bigint NOT NULL CHECK(version>0),id uuid NOT NULL,
 data jsonb NOT NULL,PRIMARY KEY(session_id,version),UNIQUE(session_id,id)
);
CREATE TABLE live_buy_core.heads(
 session_id uuid PRIMARY KEY REFERENCES live_buy_core.scopes,version bigint NOT NULL,
 FOREIGN KEY(session_id,version) REFERENCES live_buy_core.snapshots DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE live_buy_core.positions(
 session_id uuid NOT NULL REFERENCES live_buy_core.scopes,condition_id text NOT NULL,token_id text NOT NULL,
 cost jsonb NOT NULL CHECK(live_buy_core.nonnegative(cost)),quantity jsonb NOT NULL CHECK(live_buy_core.nonnegative(quantity)),
 reserved jsonb NOT NULL CHECK(live_buy_core.nonnegative(reserved)),
 PRIMARY KEY(session_id,condition_id,token_id)
);
DO $$ DECLARE n text;BEGIN
 FOREACH n IN ARRAY ARRAY['scopes','intents','executions','fills','lots','reservation_events','journal_entries','receipts','audit','outbox','snapshots'] LOOP
 EXECUTE format('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON live_buy_core.%I FOR EACH ROW EXECUTE FUNCTION live_buy_core.immutable()',n);
 END LOOP;
END $$;

CREATE FUNCTION live_buy_core.compute_state_at(sid uuid,v bigint,snapshot_id uuid,at_time timestamptz) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 WITH i AS (SELECT * FROM live_buy_core.intents WHERE session_id=sid AND version<=v),
 e AS (SELECT * FROM live_buy_core.executions WHERE session_id=sid AND version<=v),
 f AS (SELECT f.* FROM live_buy_core.fills f JOIN e USING(session_id,intent_id)),
 pending AS (SELECT i.* FROM i LEFT JOIN e ON e.intent_id=i.id WHERE e.id IS NULL),
 p AS (SELECT k.condition_id,k.token_id,
 (SELECT live_buy_core.sumq(f.notional) FROM f JOIN i ON f.intent_id=i.id WHERE i.condition_id=k.condition_id AND i.token_id=k.token_id) AS cost,
 (SELECT live_buy_core.sumq(f.net) FROM f JOIN i ON f.intent_id=i.id WHERE i.condition_id=k.condition_id AND i.token_id=k.token_id) AS quantity,
 (SELECT live_buy_core.sumq(x.notional) FROM pending x WHERE x.condition_id=k.condition_id AND x.token_id=k.token_id) AS reserved
 FROM (SELECT DISTINCT condition_id,token_id FROM i) k),
 d AS (SELECT k.day,
 (SELECT live_buy_core.sumq(f.notional) FROM f,live_buy_core.scopes scope WHERE scope.session_id=sid AND (f.executed_at AT TIME ZONE scope.timezone_name)::date=k.day) AS used,
 CASE WHEN k.day=(at_time AT TIME ZONE scope.timezone_name)::date THEN (SELECT live_buy_core.sumq(x.notional) FROM pending x) ELSE live_buy_core.q(0,1) END AS reserved
 FROM (SELECT quota_day AS day FROM i UNION SELECT (f.executed_at AT TIME ZONE scope.timezone_name)::date FROM f,live_buy_core.scopes scope WHERE scope.session_id=sid
 UNION SELECT (at_time AT TIME ZONE scope.timezone_name)::date FROM live_buy_core.scopes scope WHERE scope.session_id=sid) k,
 live_buy_core.scopes scope WHERE scope.session_id=sid),
 money AS (SELECT live_buy_core.subq(s.budget,(SELECT live_buy_core.sumq(live_buy_core.addq(f.notional,f.cash_fee)) FROM f)) AS cash,
 (SELECT live_buy_core.sumq(reserved_cash) FROM pending) AS reserved,
 (SELECT live_buy_core.sumq(cash_fee) FROM f) AS expenses FROM live_buy_core.scopes s WHERE session_id=sid)
 SELECT jsonb_build_object('schemaVersion','paper-buy-core-state-v1','sessionId',sid,'version',v::text,'snapshotId',snapshot_id,
 'cash',cash,'reservedCash',reserved,'freeCash',live_buy_core.subq(cash,reserved),'cashExpenses',expenses,
 'positions',COALESCE((SELECT jsonb_agg(jsonb_build_object('conditionId',condition_id,'tokenId',token_id,'cost',cost,'quantity',quantity,'reserved',reserved) ORDER BY condition_id COLLATE "C",token_id COLLATE "C") FROM p),'[]'::jsonb),
 'daily',COALESCE((SELECT jsonb_agg(jsonb_build_object('day',day::text,'used',used,'reserved',reserved) ORDER BY day) FROM d),'[]'::jsonb)) FROM money
$$;
CREATE FUNCTION live_buy_core.event_time(sid uuid,v bigint) RETURNS timestamptz LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE((SELECT admitted_at FROM live_buy_core.intents WHERE session_id=sid AND version=v),
 (SELECT settled_at FROM live_buy_core.executions WHERE session_id=sid AND version=v),
 (SELECT opened_at FROM live_buy_core.scopes WHERE session_id=sid AND v=1))
$$;
CREATE FUNCTION live_buy_core.compute_state(sid uuid,v bigint,snapshot_id uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT live_buy_core.compute_state_at(sid,v,snapshot_id,live_buy_core.event_time(sid,v))
$$;
CREATE FUNCTION live_buy_core.read_state(sid uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT s.data FROM live_buy_core.heads h JOIN live_buy_core.snapshots s USING(session_id,version) WHERE h.session_id=sid
$$;
CREATE FUNCTION live_buy_core.lookup(sid uuid,cid uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT result FROM live_buy_core.receipts WHERE session_id=sid AND command_id=cid
$$;
-- Owner-only local fixture/bootstrap boundary. Not granted to application identities.
CREATE FUNCTION live_buy_core.bootstrap(sid uuid,uid uuid,rid uuid,initial_ref uuid,budget jsonb,plimit jsonb,dlimit jsonb,zone_name text) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE sn uuid:=gen_random_uuid();t timestamptz:=live_buy_core.decision_time();
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001';END IF;
 INSERT INTO live_buy_core.scopes VALUES(sid,uid,rid,'polymarket',initial_ref,zone_name,(t AT TIME ZONE zone_name)::date,t,budget,plimit,dlimit);
 INSERT INTO live_buy_core.snapshots VALUES(sid,1,sn,live_buy_core.compute_state(sid,1,sn));
 INSERT INTO live_buy_core.heads VALUES(sid,1);
END $$;
CREATE FUNCTION live_buy_core.snapshot(sid uuid,v bigint) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE sn uuid:=gen_random_uuid();st jsonb;p jsonb;
BEGIN
 st:=live_buy_core.compute_state(sid,v,sn);
 INSERT INTO live_buy_core.snapshots VALUES(sid,v,sn,st);
 UPDATE live_buy_core.heads SET version=v WHERE session_id=sid AND version=v-1;
 IF NOT FOUND THEN RAISE EXCEPTION 'financial version conflict' USING ERRCODE='40001';END IF;
 FOR p IN SELECT value FROM jsonb_array_elements(st->'positions') LOOP
  INSERT INTO live_buy_core.positions VALUES(sid,p->>'conditionId',p->>'tokenId',p->'cost',p->'quantity',p->'reserved')
  ON CONFLICT(session_id,condition_id,token_id) DO UPDATE SET cost=EXCLUDED.cost,quantity=EXCLUDED.quantity,reserved=EXCLUDED.reserved;
 END LOOP;
 RETURN st;
END $$;
CREATE FUNCTION live_buy_core.record_result(sid uuid,cid uuid,iid uuid,k text,req jsonb,v bigint,execution uuid DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE st jsonb;r jsonb;
BEGIN
 st:=live_buy_core.snapshot(sid,v);
 r:=jsonb_build_object('schemaVersion','paper-buy-core-result-v1','sessionId',sid,'commandId',cid,'kind',k,'intentId',iid,'version',v::text,'state',st);
 IF execution IS NOT NULL THEN r:=r||jsonb_build_object('executionId',execution);END IF;
 INSERT INTO live_buy_core.receipts VALUES(sid,cid,iid,k,req,r,v);
 INSERT INTO live_buy_core.audit VALUES(sid,cid,k);
 INSERT INTO live_buy_core.outbox VALUES(sid,cid,r);
 RETURN r;
END $$;
CREATE FUNCTION live_buy_core.shape(req jsonb,k text) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE n text;f jsonb;
BEGIN
 IF req IS NULL OR octet_length(req::text)>1048576 THEN RETURN false; END IF;
 IF k='reserve' THEN
  IF live_buy_core.keys(req,ARRAY['commandId','intentId','observationId','expectedVersion','conditionId','tokenId','sizingRevisionId','admissionRevisionId','evidenceRef','desiredNotional','fullQuantity','quantityStep','priceCap','feeCashBound','delayMs']) IS DISTINCT FROM true THEN RETURN false;END IF;
  FOREACH n IN ARRAY ARRAY['observationId','sizingRevisionId','admissionRevisionId'] LOOP
   IF jsonb_typeof(req->n) IS DISTINCT FROM 'string' OR (req->>n~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') IS DISTINCT FROM true THEN RETURN false;END IF;
  END LOOP;
  FOREACH n IN ARRAY ARRAY['conditionId','tokenId'] LOOP
   IF jsonb_typeof(req->n) IS DISTINCT FROM 'string' OR length(req->>n) NOT BETWEEN 1 AND 256 OR (req->>n~'^[A-Za-z0-9:_-]+$') IS DISTINCT FROM true THEN RETURN false;END IF;
  END LOOP;
  FOREACH n IN ARRAY ARRAY['desiredNotional','fullQuantity','quantityStep','priceCap'] LOOP
   IF live_buy_core.positive(req->n) IS DISTINCT FROM true THEN RETURN false; END IF;
  END LOOP;
  IF live_buy_core.nonnegative(req->'feeCashBound') IS DISTINCT FROM true OR live_buy_core.cmp(req->'priceCap',live_buy_core.q(1,1))>0
   OR jsonb_typeof(req->'delayMs') IS DISTINCT FROM 'string' OR (req->>'delayMs'~'^(0|[1-9][0-9]{0,8})$') IS DISTINCT FROM true THEN RETURN false;END IF;
 ELSIF k='settle' THEN
  IF live_buy_core.keys(req,ARRAY['commandId','intentId','expectedVersion','evidenceRef','confirmationId','fills']) IS DISTINCT FROM true
   OR jsonb_typeof(req->'fills') IS DISTINCT FROM 'array' THEN RETURN false;END IF;
  IF jsonb_array_length(req->'fills') NOT BETWEEN 1 AND 128 OR jsonb_typeof(req->'confirmationId') IS DISTINCT FROM 'string'
   OR (req->>'confirmationId'~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') IS DISTINCT FROM true THEN RETURN false;END IF;
  FOR f IN SELECT value FROM jsonb_array_elements(req->'fills') LOOP
   IF live_buy_core.keys(f,ARRAY['fillId','price','quantityGross','quantityFee','cashFee','executedAt']) IS DISTINCT FROM true
    OR jsonb_typeof(f->'fillId') IS DISTINCT FROM 'string' OR (f->>'fillId'~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') IS DISTINCT FROM true
    OR jsonb_typeof(f->'executedAt') IS DISTINCT FROM 'string' OR (f->>'executedAt'~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$') IS DISTINCT FROM true
    OR live_buy_core.positive(f->'price') IS DISTINCT FROM true OR live_buy_core.positive(f->'quantityGross') IS DISTINCT FROM true
    OR live_buy_core.nonnegative(f->'quantityFee') IS DISTINCT FROM true OR live_buy_core.nonnegative(f->'cashFee') IS DISTINCT FROM true
   THEN RETURN false;END IF;
  END LOOP;
 ELSE RETURN false;
 END IF;
 FOREACH n IN ARRAY ARRAY['commandId','intentId'] LOOP
  IF jsonb_typeof(req->n) IS DISTINCT FROM 'string' OR (req->>n~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') IS DISTINCT FROM true THEN RETURN false;END IF;
 END LOOP;
 RETURN jsonb_typeof(req->'expectedVersion')='string' AND req->>'expectedVersion'~'^[1-9][0-9]{0,17}$'
 AND jsonb_typeof(req->'evidenceRef')='string' AND length(req->>'evidenceRef') BETWEEN 1 AND 256;
END $$;

CREATE FUNCTION live_buy_core.reserve(sid uuid,req jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE h bigint;c live_buy_core.receipts;s live_buy_core.scopes;st jsonb;p jsonb;d jsonb;
 desired jsonb;qty jsonb;steps jsonb;notional jsonb;cash jsonb;t timestamptz;day date;z jsonb:=live_buy_core.q(0,1);
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001';END IF;
 IF live_buy_core.shape(req,'reserve') IS DISTINCT FROM true THEN RAISE EXCEPTION 'invalid reserve request' USING ERRCODE='22023';END IF;
 SELECT version INTO STRICT h FROM live_buy_core.heads WHERE session_id=sid FOR UPDATE;
 SELECT * INTO c FROM live_buy_core.receipts WHERE session_id=sid AND command_id=(req->>'commandId')::uuid;
 IF FOUND THEN
  IF c.kind<>'reserve' OR c.request IS DISTINCT FROM req THEN RAISE EXCEPTION 'key reuse conflict' USING ERRCODE='23505';END IF;
  RETURN c.result;
 END IF;
 IF h::text<>req->>'expectedVersion' THEN RAISE EXCEPTION 'financial version conflict' USING ERRCODE='40001';END IF;
 SELECT * INTO STRICT s FROM live_buy_core.scopes WHERE session_id=sid;
 t:=live_buy_core.decision_time();day:=(t AT TIME ZONE s.timezone_name)::date;
 st:=live_buy_core.compute_state_at(sid,h,(live_buy_core.read_state(sid)->>'snapshotId')::uuid,t);
 SELECT jsonb_build_object('cost',live_buy_core.sumq(value->'cost'),'reserved',live_buy_core.sumq(value->'reserved')) INTO p FROM jsonb_array_elements(st->'positions') WHERE value->>'conditionId'=req->>'conditionId';
 SELECT value INTO d FROM jsonb_array_elements(st->'daily') WHERE value->>'day'=day::text;
 desired:=req->'desiredNotional';
 IF desired<>live_buy_core.mulq(req->'fullQuantity',req->'priceCap') THEN RAISE EXCEPTION 'inconsistent capacity plan' USING ERRCODE='22023';END IF;
 IF live_buy_core.cmp(live_buy_core.addq(desired,req->'feeCashBound'),st->'freeCash')>0
 OR live_buy_core.cmp(live_buy_core.addq(desired,live_buy_core.addq(COALESCE(p->'cost',z),COALESCE(p->'reserved',z))),s.position_limit)>0
 OR live_buy_core.cmp(live_buy_core.addq(desired,live_buy_core.addq(COALESCE(d->'used',z),COALESCE(d->'reserved',z))),s.daily_limit)>0
 THEN RAISE EXCEPTION 'full desired capacity unavailable' USING ERRCODE='23514';END IF;
 steps:=live_buy_core.divq(req->'fullQuantity',req->'quantityStep');
 qty:=live_buy_core.mulq(live_buy_core.q(div((steps->>'n')::numeric,(steps->>'d')::numeric),1),req->'quantityStep');
 IF live_buy_core.positive(qty) IS DISTINCT FROM true THEN RAISE EXCEPTION 'normalized quantity empty' USING ERRCODE='22023';END IF;
 notional:=live_buy_core.mulq(qty,req->'priceCap');cash:=live_buy_core.addq(notional,req->'feeCashBound');
 INSERT INTO live_buy_core.intents VALUES(sid,(req->>'intentId')::uuid,(req->>'observationId')::uuid,(req->>'commandId')::uuid,h+1,
 req->>'conditionId',req->>'tokenId',req,qty,notional,cash,t,t+(req->>'delayMs')::integer*interval '1 millisecond',day);
 INSERT INTO live_buy_core.reservation_events VALUES(sid,(req->>'intentId')::uuid,'grant',notional,cash,z);
 RETURN live_buy_core.record_result(sid,(req->>'commandId')::uuid,(req->>'intentId')::uuid,'reserve',req,h+1);
END $$;
CREATE FUNCTION live_buy_core.expected_journal(sid uuid,iid uuid) RETURNS TABLE(asset text,account text,amount jsonb) LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 WITH total AS (SELECT live_buy_core.sumq(notional) n,live_buy_core.sumq(cash_fee) cf,live_buy_core.sumq(gross) g,live_buy_core.sumq(net) net,live_buy_core.sumq(quantity_fee) qf
 FROM live_buy_core.fills WHERE session_id=sid AND intent_id=iid), t AS (SELECT token_id FROM live_buy_core.intents WHERE session_id=sid AND id=iid),
 a AS (SELECT 'virtual_USD'::text asset,'paper_cash'::text account,live_buy_core.negq(live_buy_core.addq(n,cf)) amount FROM total
 UNION ALL SELECT 'virtual_USD','copied_position_cost',n FROM total
 UNION ALL SELECT 'virtual_USD','cash_fee',cf FROM total
 UNION ALL SELECT 'token:'||token_id,'acquired_quantity',live_buy_core.negq(g) FROM total,t
 UNION ALL SELECT 'token:'||token_id,'copied_position_quantity',net FROM total,t
 UNION ALL SELECT 'token:'||token_id,'quantity_fee',qf FROM total,t)
 SELECT * FROM a WHERE live_buy_core.cmp(amount,live_buy_core.q(0,1))<>0
$$;
CREATE FUNCTION live_buy_core.settle(sid uuid,req jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE h bigint;c live_buy_core.receipts;i live_buy_core.intents;s live_buy_core.scopes;f jsonb;j int:=0;eid uuid:=gen_random_uuid();t timestamptz;
 gross jsonb:=live_buy_core.q(0,1);fee jsonb:=live_buy_core.q(0,1);cost jsonb:=live_buy_core.q(0,1);n jsonb;net jsonb;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001';END IF;
 IF live_buy_core.shape(req,'settle') IS DISTINCT FROM true THEN RAISE EXCEPTION 'invalid settle request' USING ERRCODE='22023';END IF;
 SELECT version INTO STRICT h FROM live_buy_core.heads WHERE session_id=sid FOR UPDATE;
 SELECT * INTO c FROM live_buy_core.receipts WHERE session_id=sid AND command_id=(req->>'commandId')::uuid;
 IF FOUND THEN
  IF c.kind<>'settle' OR c.request IS DISTINCT FROM req THEN RAISE EXCEPTION 'key reuse conflict' USING ERRCODE='23505';END IF;
  RETURN c.result;
 END IF;
 IF h::text<>req->>'expectedVersion' THEN RAISE EXCEPTION 'financial version conflict' USING ERRCODE='40001';END IF;
 SELECT * INTO STRICT i FROM live_buy_core.intents WHERE session_id=sid AND id=(req->>'intentId')::uuid;
 IF EXISTS(SELECT FROM live_buy_core.executions WHERE session_id=sid AND intent_id=i.id) THEN RAISE EXCEPTION 'intent already settled' USING ERRCODE='23505';END IF;
 SELECT * INTO STRICT s FROM live_buy_core.scopes WHERE session_id=sid;
 t:=live_buy_core.decision_time();
 IF t<i.not_before THEN RAISE EXCEPTION 'delay not elapsed' USING ERRCODE='55000';END IF;
 FOR f IN SELECT value FROM jsonb_array_elements(req->'fills') LOOP
  IF (f->>'executedAt')::timestamptz<i.not_before OR (f->>'executedAt')::timestamptz>t OR live_buy_core.cmp(f->'price',i.request->'priceCap')>0 OR live_buy_core.cmp(f->'quantityFee',f->'quantityGross')>=0
  THEN RAISE EXCEPTION 'fill outside retained limits' USING ERRCODE='23514';END IF;
  gross:=live_buy_core.addq(gross,f->'quantityGross');fee:=live_buy_core.addq(fee,f->'cashFee');
  cost:=live_buy_core.addq(cost,live_buy_core.mulq(f->'price',f->'quantityGross'));
 END LOOP;
 IF gross<>i.quantity OR live_buy_core.cmp(fee,i.request->'feeCashBound')>0 OR live_buy_core.cmp(cost,i.notional)>0
 THEN RAISE EXCEPTION 'incomplete or over-bound settlement; reserve retained' USING ERRCODE='23514';END IF;
 INSERT INTO live_buy_core.executions VALUES(sid,i.id,eid,(req->>'commandId')::uuid,(req->>'confirmationId')::uuid,h+1,t);
 FOR f IN SELECT value FROM jsonb_array_elements(req->'fills') LOOP
  j:=j+1;n:=live_buy_core.mulq(f->'price',f->'quantityGross');net:=live_buy_core.subq(f->'quantityGross',f->'quantityFee');
  INSERT INTO live_buy_core.fills VALUES(sid,(f->>'fillId')::uuid,i.id,j,f->'price',f->'quantityGross',f->'quantityFee',f->'cashFee',(f->>'executedAt')::timestamptz,net,n);
  INSERT INTO live_buy_core.lots VALUES(sid,(f->>'fillId')::uuid,i.id,net,n,f->'cashFee',f->'quantityFee');
 END LOOP;
 INSERT INTO live_buy_core.reservation_events VALUES(sid,i.id,'settle',cost,live_buy_core.addq(cost,fee),live_buy_core.subq(i.reserved_cash,live_buy_core.addq(cost,fee)));
 INSERT INTO live_buy_core.journal_entries SELECT sid,i.id,asset,account,amount FROM live_buy_core.expected_journal(sid,i.id);
 RETURN live_buy_core.record_result(sid,(req->>'commandId')::uuid,i.id,'settle',req,h+1,eid);
END $$;

CREATE FUNCTION live_buy_core.valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s live_buy_core.scopes;h bigint;r live_buy_core.receipts;i live_buy_core.intents;e live_buy_core.executions;
 sn live_buy_core.snapshots;g live_buy_core.reservation_events;settled live_buy_core.reservation_events;
 n bigint;st jsonb;p jsonb;d jsonb;prior jsonb;qty jsonb;cost jsonb;fee jsonb;steps jsonb;want jsonb;actual jsonb;
 z jsonb:=live_buy_core.q(0,1);
BEGIN
 SELECT * INTO s FROM live_buy_core.scopes WHERE session_id=sid;
 SELECT version INTO h FROM live_buy_core.heads WHERE session_id=sid;
 IF s.session_id IS NULL OR h IS NULL THEN RETURN false;END IF;
 SELECT count(*) INTO n FROM live_buy_core.snapshots WHERE session_id=sid;
 IF n<>h OR (SELECT min(version) FROM live_buy_core.snapshots WHERE session_id=sid)<>1
 OR (SELECT max(version) FROM live_buy_core.snapshots WHERE session_id=sid)<>h
 OR (SELECT count(*) FROM live_buy_core.receipts WHERE session_id=sid)<>h-1 THEN RETURN false;END IF;
 FOR sn IN SELECT * FROM live_buy_core.snapshots WHERE session_id=sid ORDER BY version LOOP
  st:=live_buy_core.compute_state(sid,sn.version,sn.id);
  IF sn.data IS DISTINCT FROM st OR live_buy_core.nonnegative(st->'freeCash') IS DISTINCT FROM true THEN RETURN false;END IF;
  FOR p IN SELECT jsonb_build_object('cost',live_buy_core.sumq(value->'cost'),'reserved',live_buy_core.sumq(value->'reserved')) FROM jsonb_array_elements(st->'positions') GROUP BY value->>'conditionId' LOOP
   IF live_buy_core.cmp(live_buy_core.addq(p->'cost',p->'reserved'),s.position_limit)>0 THEN RETURN false;END IF;
  END LOOP;
  FOR d IN SELECT value FROM jsonb_array_elements(st->'daily') LOOP
   IF live_buy_core.cmp(live_buy_core.addq(d->'used',d->'reserved'),s.daily_limit)>0 THEN RETURN false;END IF;
  END LOOP;
 END LOOP;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('conditionId',pos.condition_id,'tokenId',pos.token_id,'cost',pos.cost,'quantity',pos.quantity,'reserved',pos.reserved) ORDER BY pos.condition_id COLLATE "C",pos.token_id COLLATE "C"),'[]'::jsonb)
 INTO actual FROM live_buy_core.positions pos WHERE pos.session_id=sid;
 IF actual IS DISTINCT FROM live_buy_core.read_state(sid)->'positions' THEN RETURN false;END IF;
 FOR r IN SELECT * FROM live_buy_core.receipts WHERE session_id=sid LOOP
  SELECT * INTO sn FROM live_buy_core.snapshots WHERE session_id=sid AND version=r.version;
  IF sn.id IS NULL OR live_buy_core.shape(r.request,r.kind) IS DISTINCT FROM true
   OR r.request->>'commandId' IS DISTINCT FROM r.command_id::text OR r.request->>'intentId' IS DISTINCT FROM r.intent_id::text
   OR r.request->>'expectedVersion' IS DISTINCT FROM (r.version-1)::text THEN RETURN false;END IF;
  want:=jsonb_build_object('schemaVersion','paper-buy-core-result-v1','sessionId',sid,'commandId',r.command_id,'kind',r.kind,'intentId',r.intent_id,'version',r.version::text,'state',sn.data);
  IF r.kind='settle' THEN
   SELECT * INTO e FROM live_buy_core.executions WHERE session_id=sid AND intent_id=r.intent_id;
   IF e.id IS NULL OR e.command_id<>r.command_id OR e.version<>r.version THEN RETURN false;END IF;
   want:=want||jsonb_build_object('executionId',e.id);
  ELSE
   IF NOT EXISTS(SELECT FROM live_buy_core.intents WHERE session_id=sid AND id=r.intent_id AND command_id=r.command_id AND version=r.version) THEN RETURN false;END IF;
  END IF;
  IF r.result IS DISTINCT FROM want OR NOT EXISTS(SELECT FROM live_buy_core.audit WHERE session_id=sid AND command_id=r.command_id AND kind=r.kind)
   OR NOT EXISTS(SELECT FROM live_buy_core.outbox WHERE session_id=sid AND command_id=r.command_id AND payload=r.result) THEN RETURN false;END IF;
 END LOOP;
 FOR i IN SELECT * FROM live_buy_core.intents WHERE session_id=sid LOOP
  SELECT * INTO r FROM live_buy_core.receipts WHERE session_id=sid AND command_id=i.command_id;
  IF r.kind IS DISTINCT FROM 'reserve' OR r.request IS DISTINCT FROM i.request OR r.intent_id IS DISTINCT FROM i.id OR r.version IS DISTINCT FROM i.version
   OR i.request->>'observationId' IS DISTINCT FROM i.observation_id::text OR i.request->>'conditionId' IS DISTINCT FROM i.condition_id
   OR i.request->>'tokenId' IS DISTINCT FROM i.token_id OR i.quota_day<>(i.admitted_at AT TIME ZONE s.timezone_name)::date
   OR i.not_before<>i.admitted_at+(i.request->>'delayMs')::integer*interval '1 millisecond'
   OR i.request->'desiredNotional'<>live_buy_core.mulq(i.request->'fullQuantity',i.request->'priceCap') THEN RETURN false;END IF;
  steps:=live_buy_core.divq(i.request->'fullQuantity',i.request->'quantityStep');
  qty:=live_buy_core.mulq(live_buy_core.q(div((steps->>'n')::numeric,(steps->>'d')::numeric),1),i.request->'quantityStep');
  IF qty<>i.quantity OR i.notional<>live_buy_core.mulq(qty,i.request->'priceCap') OR i.reserved_cash<>live_buy_core.addq(i.notional,i.request->'feeCashBound') THEN RETURN false;END IF;
  SELECT live_buy_core.compute_state_at(sid,version,id,i.admitted_at) INTO prior FROM live_buy_core.snapshots WHERE session_id=sid AND version=i.version-1;
  SELECT jsonb_build_object('cost',live_buy_core.sumq(value->'cost'),'reserved',live_buy_core.sumq(value->'reserved')) INTO p FROM jsonb_array_elements(prior->'positions') WHERE value->>'conditionId'=i.condition_id;
  SELECT value INTO d FROM jsonb_array_elements(prior->'daily') WHERE value->>'day'=i.quota_day::text;
  IF prior IS NULL OR live_buy_core.cmp(live_buy_core.addq(i.request->'desiredNotional',i.request->'feeCashBound'),prior->'freeCash')>0
   OR live_buy_core.cmp(live_buy_core.addq(i.request->'desiredNotional',live_buy_core.addq(COALESCE(p->'cost',z),COALESCE(p->'reserved',z))),s.position_limit)>0
   OR live_buy_core.cmp(live_buy_core.addq(i.request->'desiredNotional',live_buy_core.addq(COALESCE(d->'used',z),COALESCE(d->'reserved',z))),s.daily_limit)>0 THEN RETURN false;END IF;
  SELECT * INTO g FROM live_buy_core.reservation_events WHERE session_id=sid AND intent_id=i.id AND kind='grant';
  IF g.intent_id IS NULL OR g.notional<>i.notional OR g.cash<>i.reserved_cash OR g.released_cash<>z THEN RETURN false;END IF;
  SELECT * INTO e FROM live_buy_core.executions WHERE session_id=sid AND intent_id=i.id;
  SELECT * INTO settled FROM live_buy_core.reservation_events WHERE session_id=sid AND intent_id=i.id AND kind='settle';
  IF e.id IS NULL THEN
   IF settled.intent_id IS NOT NULL THEN RETURN false;END IF;
   CONTINUE;
  END IF;
  SELECT * INTO r FROM live_buy_core.receipts WHERE session_id=sid AND command_id=e.command_id;
  IF r.kind IS DISTINCT FROM 'settle' OR r.intent_id IS DISTINCT FROM i.id OR r.version IS DISTINCT FROM e.version OR e.version<=i.version
   OR e.settled_at<i.not_before OR e.confirmation_id::text IS DISTINCT FROM r.request->>'confirmationId' THEN RETURN false;END IF;
  SELECT live_buy_core.sumq(gross),live_buy_core.sumq(notional),live_buy_core.sumq(cash_fee),count(*) INTO qty,cost,fee,n FROM live_buy_core.fills WHERE session_id=sid AND intent_id=i.id;
  IF n<1 OR n<>jsonb_array_length(r.request->'fills') OR qty<>i.quantity OR live_buy_core.cmp(cost,i.notional)>0
   OR live_buy_core.cmp(fee,i.request->'feeCashBound')>0 OR EXISTS(SELECT FROM live_buy_core.fills WHERE session_id=sid AND intent_id=i.id AND (live_buy_core.cmp(price,i.request->'priceCap')>0 OR executed_at<i.not_before OR executed_at>e.settled_at)) THEN RETURN false;END IF;
  SELECT jsonb_agg(jsonb_build_object('fillId',id,'price',price,'quantityGross',gross,'quantityFee',quantity_fee,'cashFee',cash_fee,'executedAt',to_char(executed_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')) ORDER BY ordinal)
  INTO actual FROM live_buy_core.fills WHERE session_id=sid AND intent_id=i.id;
  IF actual IS DISTINCT FROM r.request->'fills' OR (SELECT max(ordinal) FROM live_buy_core.fills WHERE session_id=sid AND intent_id=i.id)<>n THEN RETURN false;END IF;
  IF settled.intent_id IS NULL OR settled.notional<>cost OR settled.cash<>live_buy_core.addq(cost,fee)
   OR settled.released_cash<>live_buy_core.subq(i.reserved_cash,settled.cash) THEN RETURN false;END IF;
  IF EXISTS(SELECT FROM live_buy_core.fills f LEFT JOIN live_buy_core.lots l ON l.session_id=f.session_id AND l.fill_id=f.id
    WHERE f.session_id=sid AND f.intent_id=i.id AND (l.fill_id IS NULL OR l.intent_id<>i.id OR l.original_quantity<>f.net OR l.original_cost<>f.notional OR l.attributed_cash_fee<>f.cash_fee OR l.attributed_quantity_fee<>f.quantity_fee)) THEN RETURN false;END IF;
  SELECT jsonb_agg(jsonb_build_array(asset,account,amount) ORDER BY asset,account) INTO want FROM live_buy_core.expected_journal(sid,i.id);
  SELECT jsonb_agg(jsonb_build_array(asset,account,amount) ORDER BY asset,account) INTO actual FROM live_buy_core.journal_entries WHERE session_id=sid AND intent_id=i.id;
  IF actual IS DISTINCT FROM want THEN RETURN false;END IF;
  IF EXISTS(SELECT asset FROM live_buy_core.journal_entries WHERE session_id=sid AND intent_id=i.id GROUP BY asset HAVING live_buy_core.sumq(amount)<>z) THEN RETURN false;END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION live_buy_core.enforce() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF live_buy_core.valid(COALESCE(NEW.session_id,OLD.session_id)) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete financial graph' USING ERRCODE='23514';END IF;
 RETURN NULL;
END $$;
DO $$ DECLARE n text;BEGIN
 FOREACH n IN ARRAY ARRAY['scopes','intents','executions','fills','lots','reservation_events','journal_entries','receipts','audit','outbox','snapshots','heads','positions'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER complete_graph AFTER INSERT OR UPDATE OR DELETE ON live_buy_core.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION live_buy_core.enforce()',n);
 END LOOP;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA live_buy_core FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA live_buy_core FROM PUBLIC;

CREATE FUNCTION live_buy_core.scope_key_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.session_id IS DISTINCT FROM OLD.session_id THEN RAISE EXCEPTION 'financial scope key is immutable' USING ERRCODE='23514';END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER immutable_scope_key BEFORE UPDATE ON live_buy_core.positions FOR EACH ROW EXECUTE FUNCTION live_buy_core.scope_key_guard();
CREATE TRIGGER immutable_scope_key BEFORE UPDATE ON live_buy_core.heads FOR EACH ROW EXECUTE FUNCTION live_buy_core.scope_key_guard();
REVOKE ALL ON FUNCTION live_buy_core.scope_key_guard() FROM PUBLIC;

-- Run as polygon_owner, only after the pinned live/resume baseline and core sources.
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

RESET ROLE;

-- Execute as the trusted database operator AFTER 010 creates the private schema.
-- PGlite/native catalog ACL differences must not remove the database identity check.
-- The owner receives only this fixed, argument-free read, not catalog mutation.
CREATE FUNCTION polygon_buy.database_oid() RETURNS oid LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()
$$;
REVOKE ALL ON FUNCTION polygon_buy.database_oid() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION polygon_buy.database_oid() TO polygon_owner;


SET LOCAL ROLE polygon_owner;

-- Preserve every existing CHECK as the old branch; add a strictly validated new
-- branch. Existing rows/initial C06/funding journals are not rewritten.
DO $$DECLARE tab text;c record;old_shape text;extra text;BEGIN
 FOREACH tab IN ARRAY ARRAY['paper_sessions','session_snapshots'] LOOP
  old_shape:='';
  FOR c IN SELECT conname,pg_get_expr(conbin,conrelid) expr FROM pg_constraint WHERE conrelid=('polygon.'||tab)::regclass AND contype='c' ORDER BY conname LOOP
   old_shape:=old_shape||CASE WHEN old_shape='' THEN '' ELSE ' AND ' END||'('||c.expr||')';
   EXECUTE format('ALTER TABLE polygon.%I DROP CONSTRAINT %I',tab,c.conname);
  END LOOP;
  IF tab='paper_sessions' THEN
   extra:=$x$version>1 AND current_snapshot_version=version AND current_ledger_sequence=version AND lifecycle='active' AND control_state='paper_copying'
   AND created_at=started_at AND updated_at>=started_at AND evaluation_deadline_at>started_at
   AND deadline_calculation_version='paper-evaluation-deadline-v1'$x$;
  ELSE
   old_shape:=old_shape||' AND equity_n IS NOT NULL AND equity_d IS NOT NULL AND position_value_n IS NOT NULL AND position_value_d IS NOT NULL AND trading_result_n IS NOT NULL AND trading_result_d IS NOT NULL';
   extra:=$x$version>1 AND session_version=version AND ledger_sequence=version AND calculation_version='paper-buy-financial-v1'
   AND lifecycle='active' AND control_state='paper_copying' AND content_state='HAS_ACTIVITY' AND coverage_state='trade_data_unvalued'
   AND data_origin IN('synthetic','public_api') AND unit='virtual_USD' AND record_schema_version='v1'
   AND free_n>=0 AND free_d>0 AND reserved_n>=0 AND reserved_d>0 AND position_cost_n>=0 AND position_cost_d>0
   AND initial_funding_n>0 AND initial_funding_d>0 AND trade_count>=0 AND position_count>=0 AND order_count>0
   AND equity_n IS NULL AND equity_d IS NULL AND position_value_n IS NULL AND position_value_d IS NULL AND trading_result_n IS NULL AND trading_result_d IS NULL$x$;
  END IF;
  EXECUTE format('ALTER TABLE polygon.%I ADD CONSTRAINT buy_closed_shape CHECK((%s) OR (%s))',tab,old_shape,extra);
 END LOOP;
END $$;
ALTER TABLE polygon.session_snapshots ALTER COLUMN equity_n DROP NOT NULL,ALTER COLUMN equity_d DROP NOT NULL,
 ALTER COLUMN position_value_n DROP NOT NULL,ALTER COLUMN position_value_d DROP NOT NULL,ALTER COLUMN trading_result_n DROP NOT NULL,ALTER COLUMN trading_result_d DROP NOT NULL;
DO $$DECLARE c record;n int:=0;BEGIN
 FOR c IN SELECT conname FROM pg_constraint WHERE conrelid='polygon.session_snapshots'::regclass AND contype='f' AND confrelid='polygon.journals'::regclass LOOP
  n:=n+1;EXECUTE format('ALTER TABLE polygon.session_snapshots DROP CONSTRAINT %I',c.conname);
 END LOOP;
 IF n<>1 THEN RAISE EXCEPTION 'unexpected original snapshot ledger binding';END IF;
END $$;
ALTER TABLE polygon.session_snapshots ADD FOREIGN KEY(session_id,ledger_sequence) REFERENCES polygon_buy.ledger_index(session_id,sequence) DEFERRABLE INITIALLY DEFERRED;
CREATE OR REPLACE FUNCTION polygon_live.session_write_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'session history cannot be deleted' USING ERRCODE='23514';END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.version<>1 OR NEW.lifecycle<>'active' THEN RAISE EXCEPTION 'new session must start at version1' USING ERRCODE='23514';END IF;
 ELSIF EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=OLD.id) THEN
  IF NEW.version<>OLD.version+1 OR NEW.lifecycle<>'active' OR NEW.control_state<>'paper_copying' OR NEW.current_snapshot_version<>NEW.version OR NEW.current_ledger_sequence<>NEW.version
  OR (to_jsonb(NEW)-ARRAY['version','current_snapshot_version','current_ledger_sequence','control_state','updated_at']) IS DISTINCT FROM
   (to_jsonb(OLD)-ARRAY['version','current_snapshot_version','current_ledger_sequence','control_state','updated_at'])
  THEN RAISE EXCEPTION 'invalid bound financial transition' USING ERRCODE='23514';END IF;
 ELSE
  IF OLD.version<>1 OR NEW.version<>2 OR NEW.lifecycle<>'completed'
   OR (to_jsonb(NEW)-ARRAY['version','lifecycle','current_snapshot_version','updated_at']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['version','lifecycle','current_snapshot_version','updated_at'])
  THEN RAISE EXCEPTION 'only immutable-identity empty completion allowed' USING ERRCODE='23514';END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION polygon_buy.expected_snapshot(sid uuid,v bigint) RETURNS polygon.session_snapshots LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE sn polygon.session_snapshots;core live_buy_core.snapshots;st jsonb;cost jsonb;
BEGIN
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=sid AND version=1;
 IF v=1 THEN RETURN sn;END IF;
 SELECT * INTO STRICT core FROM live_buy_core.snapshots WHERE session_id=sid AND version=v;st:=core.data;
 SELECT live_buy_core.sumq(value->'cost') INTO cost FROM jsonb_array_elements(st->'positions');
 sn.id:=core.id;sn.version:=v;sn.session_version:=v;sn.ledger_sequence:=v;sn.calculation_version:='paper-buy-financial-v1';
 sn.control_state:='paper_copying';sn.content_state:='HAS_ACTIVITY';sn.coverage_state:='trade_data_unvalued';
 sn.free_n:=(st#>>'{freeCash,n}')::numeric;sn.free_d:=(st#>>'{freeCash,d}')::numeric;
 sn.reserved_n:=(st#>>'{reservedCash,n}')::numeric;sn.reserved_d:=(st#>>'{reservedCash,d}')::numeric;
 sn.position_cost_n:=(cost->>'n')::numeric;sn.position_cost_d:=(cost->>'d')::numeric;
 sn.equity_n:=NULL;sn.equity_d:=NULL;sn.position_value_n:=NULL;sn.position_value_d:=NULL;sn.trading_result_n:=NULL;sn.trading_result_d:=NULL;
 SELECT count(*) INTO sn.order_count FROM live_buy_core.intents WHERE session_id=sid AND version<=v;
 SELECT count(*) INTO sn.trade_count FROM live_buy_core.fills f JOIN live_buy_core.executions e USING(session_id,intent_id) WHERE f.session_id=sid AND e.version<=v;
 SELECT count(*) INTO sn.position_count FROM jsonb_array_elements(st->'positions') WHERE live_buy_core.positive(value->'quantity');
 sn.as_of:=live_buy_core.event_time(sid,v);sn.created_at:=sn.as_of;
 RETURN sn;
END $$;
CREATE FUNCTION polygon_buy.publish(sid uuid,cid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE r live_buy_core.receipts;sn polygon.session_snapshots;
BEGIN
 SELECT * INTO STRICT r FROM live_buy_core.receipts WHERE session_id=sid AND command_id=cid;
 sn:=polygon_buy.expected_snapshot(sid,r.version);
 INSERT INTO polygon_buy.ledger_index VALUES(sid,r.version,NULL,cid);
 INSERT INTO polygon.session_snapshots SELECT sn.*;
 INSERT INTO polygon_buy.snapshot_links VALUES(sid,r.version,cid,sn.id);
 UPDATE polygon.paper_sessions SET version=r.version,current_snapshot_version=r.version,current_ledger_sequence=r.version,control_state='paper_copying',updated_at=sn.as_of
 WHERE id=sid AND version=r.version-1;
 IF NOT FOUND THEN RAISE EXCEPTION 'public financial version conflict' USING ERRCODE='40001';END IF;
END $$;
CREATE FUNCTION polygon_buy.session_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions;scope live_buy_core.scopes;h bigint;sn polygon.session_snapshots;l polygon_buy.snapshot_links;r live_buy_core.receipts;st polygon.settings_revisions;b polygon_buy.bindings;release polygon_live_activity.release_record;
BEGIN
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 SELECT * INTO scope FROM live_buy_core.scopes WHERE session_id=sid;
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=sid;
 SELECT * INTO release FROM polygon_live_activity.release_record WHERE singleton;
 SELECT version INTO h FROM live_buy_core.heads WHERE session_id=sid;
 SELECT * INTO st FROM polygon.settings_revisions WHERE session_id=sid AND id=s.current_settings_revision_id;
 IF s.id IS NULL OR scope.session_id IS NULL OR b.session_id IS NULL OR h IS NULL OR st.id IS NULL
 OR release.run_id IS DISTINCT FROM b.run_id OR release.database_name IS DISTINCT FROM current_database() OR release.database_oid IS DISTINCT FROM polygon_buy.database_oid()
 OR polygon_live.initial_valid(sid) IS DISTINCT FROM true OR polygon_live.slot_valid(s.user_id) IS DISTINCT FROM true
 OR polygon_live.source_admitted(s.user_id,s.source_id,s.trader_id,s.trader_revision_id,s.venue_id) IS DISTINCT FROM true
 OR live_buy_core.valid(sid) IS DISTINCT FROM true OR s.version<>h OR s.current_snapshot_version<>h OR s.current_ledger_sequence<>h OR s.lifecycle<>'active'
 OR ROW(scope.owner_id,scope.release_id,scope.timezone_name) IS DISTINCT FROM ROW(s.user_id,b.run_id,s.iana_timezone)
 OR scope.budget<>live_buy_core.q(st.budget_n,st.budget_d) OR scope.position_limit<>live_buy_core.q(st.market_n,st.market_d) OR scope.daily_limit<>live_buy_core.q(st.daily_n,st.daily_d)
 OR EXISTS(SELECT FROM polygon_live.completions WHERE session_id=sid)
 OR (SELECT count(*) FROM polygon.session_snapshots WHERE session_id=sid)<>h
 OR (SELECT count(*) FROM polygon_buy.snapshot_links WHERE session_id=sid)<>h-1
 OR (SELECT count(*) FROM polygon_buy.ledger_index WHERE session_id=sid)<>h
 THEN RETURN false;END IF;
 IF h=1 THEN RETURN s.control_state='copying_not_connected' AND s.updated_at=s.started_at;END IF;
 IF s.control_state<>'paper_copying' OR s.updated_at<>live_buy_core.event_time(sid,h) THEN RETURN false;END IF;
 FOR sn IN SELECT * FROM polygon.session_snapshots WHERE session_id=sid AND version>1 LOOP
  SELECT * INTO l FROM polygon_buy.snapshot_links WHERE session_id=sid AND version=sn.version;
  SELECT * INTO r FROM live_buy_core.receipts WHERE session_id=sid AND version=sn.version;
  IF to_jsonb(sn) IS DISTINCT FROM to_jsonb(polygon_buy.expected_snapshot(sid,sn.version)) OR l.command_id IS DISTINCT FROM r.command_id OR l.snapshot_id IS DISTINCT FROM sn.id
   OR NOT EXISTS(SELECT FROM polygon_buy.ledger_index WHERE session_id=sid AND sequence=sn.version AND command_id=r.command_id) THEN RETURN false;END IF;
 END LOOP;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION polygon.session_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; sn polygon.session_snapshots; origin text;
BEGIN
 IF EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=sid) THEN RETURN polygon_buy.session_valid(sid);END IF;
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

CREATE OR REPLACE FUNCTION polygon_live.empty_admitted(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE present boolean; s polygon.paper_sessions;
BEGIN
 IF EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=sid) THEN RETURN false;END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF s.id IS NULL OR s.lifecycle<>'active' OR s.version<>1 OR s.control_state<>'copying_not_connected'
 OR polygon.session_valid(sid) IS DISTINCT FROM true THEN RETURN false; END IF;
 -- Only this frozen no-execution profile is supported. No unknown sidecar is treated as zero.
 IF (SELECT array_agg(c.relname::text ORDER BY c.relname::text) FROM pg_class c WHERE c.relnamespace='polygon'::regnamespace AND c.relkind IN('r','p'))
 IS DISTINCT FROM ARRAY['audit_events','catalog_sources','command_keys','command_receipt_details','command_receipts','draft_ownerships','drafts','funding_flows','journal_entries','journals','outbox_events','paper_controls','paper_policy_versions','paper_sessions','profile','read_scopes','scope_sources','session_snapshots','settings_revisions','setup_reviews','start_plans','trader_revisions','traders','user_session_slots','users','venues']::text[] THEN RAISE EXCEPTION 'unknown polygon storage profile' USING ERRCODE='55000'; END IF;
 IF to_regnamespace('polygon_activity') IS NOT NULL OR to_regnamespace('polygon_bound') IS NOT NULL
 OR to_regnamespace('polygon_execution') IS NOT NULL
 THEN RAISE EXCEPTION 'unsupported execution/activity profile' USING ERRCODE='55000'; END IF;
 IF to_regnamespace('polygon_live_activity') IS NOT NULL THEN
  IF to_regprocedure('polygon_live_activity.has_binding(uuid)') IS NULL THEN RAISE EXCEPTION 'missing activity boundary' USING ERRCODE='55000'; END IF;
  EXECUTE 'SELECT polygon_live_activity.has_binding($1)' INTO present USING sid;
  IF present IS DISTINCT FROM false THEN RETURN false; END IF;
 END IF;
 RETURN true;
END $$;


-- Sizing comes from the persisted revision and the already normalized source BUY.
-- Same source USD-six-decimal interpretation as the reviewed earlier BUY calculator;
-- it is not supplied by a browser or inferred from a current display string.
CREATE FUNCTION polygon_buy.sized_notional(sid uuid,oid uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN st.sizing_mode='fixed' THEN live_buy_core.q(st.fixed_n,st.fixed_d)
 ELSE live_buy_core.mulq(live_buy_core.q((ob.raw_log->>'makerAmountFilledRaw')::numeric,1000000),live_buy_core.q(st.copy_percent*100,10000)) END
 FROM polygon_live_activity.observations ob JOIN polygon_live_activity.decisions d ON d.observation_id=ob.id AND d.session_id=ob.session_id
 JOIN polygon.settings_revisions st ON st.session_id=ob.session_id AND st.id=d.settings_revision_id
 WHERE ob.session_id=sid AND ob.id=oid AND ob.raw_log->>'side'='BUY'
$$;
CREATE FUNCTION polygon_buy.writer(sid uuid) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE b polygon_buy.bindings;r polygon_live_activity.release_record;a jsonb;
BEGIN
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=sid;
 SELECT * INTO r FROM polygon_live_activity.release_record WHERE singleton;
 IF b.session_id IS NULL OR r.run_id IS DISTINCT FROM b.run_id OR r.database_name<>current_database()
 OR r.database_oid<>polygon_buy.database_oid() THEN RETURN polygon.err('ACCESS_DENIED',403);END IF;
 a:=polygon_live_activity.writer_guard(jsonb_build_object('sessionId',sid,'runId',b.run_id));
 RETURN a;
END $$;
CREATE FUNCTION polygon_buy.dispatch(p jsonb,k text) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE sid uuid;cid uuid;auth jsonb;old polygon_buy.commands;ad polygon_buy.admissions;ob polygon_live_activity.observations;
 de polygon_live_activity.decisions;i live_buy_core.intents;r jsonb;b polygon_buy.bindings;s polygon.paper_sessions;t timestamptz;
BEGIN
 IF k='lookup' THEN
  IF polygon.exact_keys(p,ARRAY['session_id','command_id']) IS DISTINCT FROM true OR NOT polygon.uuid_text(p->>'command_id') THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
  cid:=(p->>'command_id')::uuid;
 ELSE
  IF polygon.exact_keys(p,ARRAY['session_id','request','admission_id']) IS DISTINCT FROM true OR NOT polygon.uuid_text(p->>'admission_id')
   OR live_buy_core.shape(p->'request',k) IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
  cid:=(p#>>'{request,commandId}')::uuid;
 END IF;
 IF NOT polygon.uuid_text(p->>'session_id') THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 sid:=(p->>'session_id')::uuid;auth:=polygon_buy.writer(sid);IF auth->>'http'<>'200' THEN RETURN auth;END IF;
 SELECT * INTO old FROM polygon_buy.commands WHERE session_id=sid AND command_id=cid;
 IF FOUND THEN
  IF k<>'lookup' AND (old.kind<>k OR old.request IS DISTINCT FROM p) THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409);END IF;
  RETURN jsonb_build_object('http',200,'result',live_buy_core.lookup(sid,cid));
 ELSIF k='lookup' THEN RETURN jsonb_build_object('http',202,'status','pending','commandId',cid);END IF;
 SELECT * INTO STRICT b FROM polygon_buy.bindings WHERE session_id=sid;
 SELECT * INTO STRICT s FROM polygon.paper_sessions WHERE id=sid;
 IF polygon_live_activity.new_admission(sid) IS DISTINCT FROM true OR NOT EXISTS(SELECT FROM polygon_live_activity.stream WHERE session_id=sid AND status='observing') THEN RETURN polygon.err('SERVICE_UNAVAILABLE');END IF;
 SELECT * INTO ad FROM polygon_buy.admissions WHERE id=(p->>'admission_id')::uuid AND session_id=sid;
 t:=live_buy_core.decision_time();
 IF ad.id IS NULL OR ad.run_id<>b.run_id OR ad.kind<>k OR ad.request IS DISTINCT FROM p->'request' OR t<ad.issued_at OR t>=ad.expires_at
 THEN RETURN polygon.err('ADMISSION_UNAVAILABLE',409);END IF;
 IF k='reserve' THEN
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE session_id=sid AND id=(p#>>'{request,observationId}')::uuid;
 ELSE
  SELECT * INTO i FROM live_buy_core.intents WHERE session_id=sid AND id=(p#>>'{request,intentId}')::uuid;
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE session_id=sid AND id=i.observation_id;
 END IF;
 SELECT * INTO de FROM polygon_live_activity.decisions WHERE session_id=sid AND observation_id=ob.id;
 IF ob.id IS NULL OR ob.classification<>'accepted' OR ob.sequence<b.first_sequence OR ob.raw_log->>'side'<>'BUY'
 OR ob.transaction_hash<>ad.transaction_hash OR ob.log_index<>ad.log_index OR ob.raw_log->>'tokenId'<>ad.token_id
 OR de.policy_version IS DISTINCT FROM 'paper-buy-queued-v1' OR de.status IS DISTINCT FROM 'pending'
 THEN RETURN polygon.err('ADMISSION_UNAVAILABLE',409);END IF;
 IF k='reserve' THEN
  IF p#>'{request,desiredNotional}' IS DISTINCT FROM polygon_buy.sized_notional(sid,ob.id)
  OR p#>>'{request,tokenId}'<>ad.token_id OR p#>>'{request,conditionId}'<>ad.condition_id
  OR p#>>'{request,sizingRevisionId}'<>de.settings_revision_id::text OR p#>>'{request,admissionRevisionId}'<>s.current_settings_revision_id::text
  OR EXISTS(SELECT FROM polygon_live_activity.decisions d WHERE d.session_id=sid AND d.sequence>=b.first_sequence AND d.sequence<ob.sequence AND d.policy_version='paper-buy-queued-v1'
    AND NOT EXISTS(SELECT FROM live_buy_core.intents x WHERE x.session_id=sid AND x.observation_id=d.observation_id))
  THEN RETURN polygon.err('ADMISSION_UNAVAILABLE',409);END IF;
  r:=live_buy_core.reserve(sid,p->'request');
 ELSE
  IF i.token_id<>ad.token_id OR i.condition_id<>ad.condition_id THEN RETURN polygon.err('ADMISSION_UNAVAILABLE',409);END IF;
  r:=live_buy_core.settle(sid,p->'request');
 END IF;
 INSERT INTO polygon_buy.commands VALUES(sid,cid,ad.id,p,k);
 PERFORM polygon_buy.publish(sid,cid);
 RETURN jsonb_build_object('http',200,'result',r);
END $$;
CREATE FUNCTION polygon.live_buy_reserve_v1(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_buy.dispatch(p,'reserve') $$;
CREATE FUNCTION polygon.live_buy_settle_v1(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_buy.dispatch(p,'settle') $$;
CREATE FUNCTION polygon.live_buy_lookup_v1(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_buy.dispatch(p,'lookup') $$;
CREATE FUNCTION polygon_buy.daily_context(sid uuid,t timestamptz) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE h bigint;sn uuid;scope live_buy_core.scopes;st jsonb;day date;d jsonb;
BEGIN
 SELECT * INTO STRICT scope FROM live_buy_core.scopes WHERE session_id=sid;
 SELECT version INTO STRICT h FROM live_buy_core.heads WHERE session_id=sid;
 SELECT id INTO STRICT sn FROM live_buy_core.snapshots WHERE session_id=sid AND version=h;
 day:=(t AT TIME ZONE scope.timezone_name)::date;st:=live_buy_core.compute_state_at(sid,h,sn,t);
 SELECT value INTO STRICT d FROM jsonb_array_elements(st->'daily') WHERE value->>'day'=day::text;
 RETURN jsonb_build_object('day',day::text,'timezone',scope.timezone_name,'used',d->'used','reserved',d->'reserved','limit',scope.daily_limit,
 'nextResetAt',v00_session.utc((day+1)::timestamp AT TIME ZONE scope.timezone_name),'asOf',v00_session.utc(t));
END $$;
CREATE FUNCTION polygon_buy.context(s polygon.paper_sessions) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE st polygon.settings_revisions; sn polygon.session_snapshots; tr polygon.trader_revisions; summary jsonb; settings jsonb; snapshot jsonb;
BEGIN
 SELECT * INTO st FROM polygon.settings_revisions WHERE session_id=s.id AND id=s.current_settings_revision_id;
 SELECT * INTO sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=s.current_snapshot_version;
 SELECT * INTO tr FROM polygon.trader_revisions WHERE id=s.trader_revision_id;
 summary:=jsonb_build_object('sessionId',s.id,'mode','paper','venueId',s.venue_id,'catalogSourceId',s.source_id,
 'traderId',s.trader_id,'traderRevisionId',s.trader_revision_id,'traderDisplayName',tr.display_name,
 'dataOrigin',sn.data_origin,'lifecycle',s.lifecycle,'controlState',s.control_state,'contentState',sn.content_state,
 'coverageState',sn.coverage_state,'sessionVersion',s.version::text,'snapshotVersion',sn.version::text,'settingsRevisionId',st.id,
 'asOf',v00_session.utc(sn.as_of),'startedAt',v00_session.utc(s.started_at),'evaluationDeadlineAt',v00_session.utc(s.evaluation_deadline_at),
 'ianaTimezone',s.iana_timezone,'deadlineCalculationVersion',s.deadline_calculation_version,'timezoneDatabaseVersion',s.timezone_database_version,
 'createdAt',v00_session.utc(s.created_at),'updatedAt',v00_session.utc(s.updated_at));
 settings:=jsonb_build_object('settingsRevisionId',st.id,'sessionId',s.id,'recordSchemaVersion',st.record_schema_version,'sequence',st.sequence::text,
 'previousRevisionId',st.previous_revision_id,'budget',polygon.money(st.budget_n,st.budget_d),'sizingMode',st.sizing_mode,
 'fixedAmount',polygon.money(st.fixed_n,st.fixed_d),'copyPercent',polygon.percent(st.copy_percent),
 'marketLimitPercent',polygon.percent(st.market_percent),'dailyBuyLimitPercent',polygon.percent(st.daily_percent),
 'effectiveMarketLimit',polygon.money(st.market_n,st.market_d),'effectiveDailyBuyLimit',polygon.money(st.daily_n,st.daily_d),
 'policyVersionId',st.policy_id,'calculationVersion',st.calculation_version,'signalMaxAgeSeconds',st.signal_max_age_seconds,
 'commandReceiptId',st.command_receipt_id,'createdAt',v00_session.utc(st.created_at));
 RETURN jsonb_build_object('summary',summary,'settings',settings);
END $$;
CREATE FUNCTION polygon_buy.body(sid uuid) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions;sn polygon.session_snapshots;body jsonb;
BEGIN
 SELECT * INTO STRICT s FROM polygon.paper_sessions WHERE id=sid;
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=sid AND version=s.current_snapshot_version;
 body:=polygon_buy.context(s);
 RETURN jsonb_build_object('schemaVersion','live-buy-session-v1','sessionId',sid,'sessionVersion',s.version::text,'snapshotId',sn.id,
 'snapshotVersion',sn.version::text,'ledgerSequence',sn.ledger_sequence::text,'asOf',v00_session.utc(sn.as_of),'ianaTimezone',s.iana_timezone,
 'financial',live_buy_core.read_state(sid),'valuation',jsonb_build_object('status','unavailable'),
 'context',jsonb_build_object('summary',body->'summary','settings',body->'settings'),
 'dailyContext',polygon_buy.daily_context(sid,clock_timestamp()));
END $$;
CREATE FUNCTION polygon.buy_session_read_v1(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;sid uuid;s polygon.paper_sessions;r polygon_live_activity.release_record;b polygon_buy.bindings;
BEGIN
 IF polygon.exact_keys(p,ARRAY['auth','session_id']) IS DISTINCT FROM true OR (p->'session_id'<>'null' AND NOT polygon.uuid_text(p->>'session_id')) THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 a:=polygon.guard(p->'auth');IF a->>'http'<>'200' THEN RETURN a;END IF;
 IF p->'session_id'='null' THEN SELECT current_session_id INTO sid FROM polygon.user_session_slots WHERE user_id=(a->>'user_id')::uuid;
 ELSE sid:=(p->>'session_id')::uuid;END IF;
 IF sid IS NULL THEN RETURN jsonb_build_object('http',200,'schemaVersion','live-buy-session-v1','sessionId',NULL,'buyState',NULL);END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid AND user_id=(a->>'user_id')::uuid;
 IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404);END IF;
 IF polygon.session_valid(sid) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=sid;
 IF b.session_id IS NULL OR s.version=1 THEN RETURN jsonb_build_object('http',200,'schemaVersion','live-buy-session-v1','sessionId',sid,'buyState',NULL);END IF;
 SELECT * INTO r FROM polygon_live_activity.release_record WHERE singleton;
 IF r.run_id IS DISTINCT FROM b.run_id OR r.database_name<>current_database() OR r.database_oid<>polygon_buy.database_oid() THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 RETURN jsonb_build_object('http',200)||polygon_buy.body(sid);
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA polygon_buy FROM PUBLIC,polygon_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon_buy FROM PUBLIC,polygon_executor;
REVOKE ALL ON FUNCTION polygon.live_buy_reserve_v1(jsonb),polygon.live_buy_settle_v1(jsonb),polygon.live_buy_lookup_v1(jsonb),polygon.buy_session_read_v1(jsonb) FROM PUBLIC,polygon_executor;
GRANT EXECUTE ON FUNCTION polygon.buy_session_read_v1(jsonb) TO polygon_executor;

CREATE OR REPLACE FUNCTION polygon.q04_session(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; s polygon.paper_sessions; sl polygon.user_session_slots;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','session_id']) OR (p->'session_id'<>'null' AND NOT polygon.uuid_text(p->>'session_id'))
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 IF p->'session_id'='null' THEN
  SELECT * INTO sl FROM polygon.user_session_slots WHERE user_id=(a->>'user_id')::uuid;
  IF sl.id IS NULL OR sl.current_session_id IS NULL THEN RETURN jsonb_build_object('http',200,'session',NULL); END IF;
  SELECT * INTO s FROM polygon.paper_sessions WHERE id=sl.current_session_id AND user_id=(a->>'user_id')::uuid;
  IF s.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 ELSE
  SELECT * INTO s FROM polygon.paper_sessions WHERE id=(p->>'session_id')::uuid AND user_id=(a->>'user_id')::uuid;
  IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 END IF;
 IF polygon.session_valid(s.id) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 IF s.version>1 AND EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=s.id) THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 RETURN jsonb_build_object('http',200,'session',polygon.session_body(s));
END $$;


CREATE FUNCTION polygon_buy.pending_shape(e jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(polygon.exact_keys(e,ARRAY['schemaVersion','kind','admissionId','binding','evidenceSha256']) AND e->>'schemaVersion'='paper-buy-pending-v1'
 AND e->>'kind'='candidate' AND polygon.uuid_text(e->>'admissionId') AND polygon_live_activity.binding_shape(e->'binding') AND e->'binding'<>'null'::jsonb
 AND polygon_live_activity.sha_value(e->'evidenceSha256'),false)
$$;
CREATE OR REPLACE FUNCTION polygon_live_activity.evidence_shape(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(polygon.exact_keys(v,ARRAY['schemaVersion','kind','reason','evidenceSha256','binding'])
 AND v->>'schemaVersion'='paper-buy-evidence-v1' AND v->>'kind'='skip' AND polygon_live_activity.reason(v->>'reason')
 AND polygon_live_activity.sha_value(v->'evidenceSha256') AND polygon_live_activity.binding_shape(v->'binding'),false) OR polygon_buy.pending_shape(v)
$$;
ALTER TABLE polygon_live_activity.decisions DROP CONSTRAINT decisions_status_check,DROP CONSTRAINT decisions_reason_code_check,
 DROP CONSTRAINT bound_skip_detail,DROP CONSTRAINT bound_skip_policy;
ALTER TABLE polygon_live_activity.decisions ALTER COLUMN reason_code DROP NOT NULL,ALTER COLUMN detail_code DROP NOT NULL;
ALTER TABLE polygon_live_activity.decisions ADD CONSTRAINT closed_buy_decision CHECK(
 (status='skipped' AND reason_code='context_invalid' AND polygon_live_activity.reason(detail_code) AND policy_version='paper-bound-skip-v1') OR
 (status='pending' AND reason_code IS NULL AND detail_code IS NULL AND policy_version='paper-buy-queued-v1'));
CREATE FUNCTION polygon_buy.pending_valid(oid uuid,e jsonb,t timestamptz) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE ob polygon_live_activity.observations;a polygon_buy.admissions;b polygon_buy.bindings;
BEGIN
 IF polygon_buy.pending_shape(e) IS DISTINCT FROM true THEN RETURN false;END IF;
 SELECT * INTO ob FROM polygon_live_activity.observations WHERE id=oid;
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=ob.session_id;
 SELECT * INTO a FROM polygon_buy.admissions WHERE id=(e->>'admissionId')::uuid AND session_id=ob.session_id;
 RETURN ob.id IS NOT NULL AND b.session_id IS NOT NULL AND a.id IS NOT NULL AND ob.sequence>=b.first_sequence
 AND a.run_id=b.run_id AND a.kind='reserve' AND ob.classification='accepted' AND ob.raw_log->>'side'='BUY'
 AND a.request->>'observationId'=oid::text AND a.transaction_hash=ob.transaction_hash AND a.log_index=ob.log_index
 AND a.token_id=ob.raw_log->>'tokenId' AND a.token_id=e#>>'{binding,tokenId}' AND a.condition_id=e#>>'{binding,conditionId}'
 AND t>=a.issued_at AND t<a.expires_at;
END $$;
CREATE OR REPLACE FUNCTION polygon_live_activity.write_decision(oid uuid,es jsonb,t timestamptz) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE ob polygon_live_activity.observations;e jsonb;did uuid:=gen_random_uuid();pending boolean;
BEGIN
 SELECT * INTO STRICT ob FROM polygon_live_activity.observations WHERE id=oid;
 SELECT value->'evidence' INTO STRICT e FROM jsonb_array_elements(es) WHERE value->>'transactionHash'=ob.transaction_hash AND (value->>'logIndex')::numeric=ob.log_index;
 pending:=polygon_buy.pending_shape(e);
 IF polygon_live_activity.evidence_shape(e) IS DISTINCT FROM true OR (e->'binding'<>'null'::jsonb AND e#>>'{binding,tokenId}'<>ob.raw_log->>'tokenId')
 OR (pending AND polygon_buy.pending_valid(oid,e,t) IS DISTINCT FROM true) THEN RAISE EXCEPTION 'invalid admitted observation' USING ERRCODE='22023';END IF;
 INSERT INTO polygon_live_activity.decisions SELECT did,ob.id,ob.session_id,ob.sequence,t,current_settings_revision_id,
 CASE WHEN pending THEN 'pending' ELSE 'skipped' END,CASE WHEN pending THEN NULL ELSE 'context_invalid' END,CASE WHEN pending THEN NULL ELSE e->>'reason' END,
 CASE WHEN pending THEN 'paper-buy-queued-v1' ELSE 'paper-bound-skip-v1' END,
 jsonb_build_object('evidence',e,'executionAdmission',CASE WHEN pending THEN 'queued' ELSE 'blocked' END) FROM polygon.paper_sessions WHERE id=ob.session_id;
 INSERT INTO polygon_live_activity.evaluations VALUES(ob.id,ob.session_id,ob.operation_id,ob.sequence,did,e,t);
END $$;
-- Old immutable envelopes remain valid; new envelopes pin the actual initial
-- financial version once for the entire ingest command, not once per event.
DO $$DECLARE c record;n int:=0;BEGIN
 FOR c IN SELECT conname FROM pg_constraint WHERE conrelid='polygon_live_activity.bound_requests'::regclass AND contype='c' AND pg_get_constraintdef(oid) LIKE '%expectedSnapshotVersion%' LOOP
 n:=n+1;EXECUTE format('ALTER TABLE polygon_live_activity.bound_requests DROP CONSTRAINT %I',c.conname);END LOOP;
 IF n<>1 THEN RAISE EXCEPTION 'unexpected bound version constraint';END IF;
END $$;
ALTER TABLE polygon_live_activity.bound_requests ADD CONSTRAINT bound_version CHECK(jsonb_typeof(request->'expectedSnapshotVersion')='string' AND polygon.version_text(request->>'expectedSnapshotVersion'));

-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
-- Derived v2 range logic; only name/signature and final skip writer differ.
CREATE OR REPLACE FUNCTION polygon_live_activity.bound_ingest(p jsonb,es jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;st polygon_live_activity.stream;i polygon_live_activity.assignments;sid uuid;op uuid;t timestamptz;ot timestamptz;
 h jsonb;v jsonb;prev jsonb;hs jsonb:='{}';seen jsonb:='{}';first_v jsonb;sem text;key text;row_n numeric;row_i numeric;
 errs jsonb:='[]';sorted_errs jsonb;code text;cid uuid;oid uuid;old polygon_live_activity.observations;r jsonb;
 accepted bigint:=0;excluded bigint:=0;duplicates bigint:=0;seq bigint;class text;ns bigint;
BEGIN
 IF polygon_live_activity.request_shape(p,'ingest') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon_live_activity.writer_guard(p); IF a->>'http'<>'200' THEN RETURN a; END IF;
 a:=polygon_live_activity.old_result(p,'ingest'); IF a IS NOT NULL THEN RETURN a; END IF;
 sid:=(p->>'sessionId')::uuid;op:=(p->>'operationId')::uuid;
 SELECT * INTO st FROM polygon_live_activity.stream WHERE session_id=sid;
 IF st.session_id IS NULL OR st.status<>'observing' OR st.checkpoint IS DISTINCT FROM p->'previous'
 THEN RETURN polygon.err('VERSION_CONFLICT',409); END IF;
 IF NOT polygon_live_activity.new_admission(sid) THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 t:=date_trunc('milliseconds',clock_timestamp());ot:=(p->>'observedAt')::timestamptz;
 IF ot<st.armed_at OR ot>t OR ot<st.last_observed_at THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT * INTO STRICT i FROM polygon_live_activity.assignments WHERE session_id=sid;
 IF p->'baselineCanonicalHash' IS DISTINCT FROM st.baseline->'hash' THEN
  errs:=errs||jsonb_build_array(jsonb_build_object('code','baseline_hash_mismatch','expected',st.baseline->'hash','actual',p->'baselineCanonicalHash'));
 END IF;
 prev:=p->'previous';
 FOR h IN SELECT value FROM jsonb_array_elements(p->'headers') LOOP
  IF (h->>'number')::numeric<>(prev->>'number')::numeric+1 OR h->'parentHash' IS DISTINCT FROM prev->'hash' THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','canonical_chain_mismatch','blockNumber',h->'number','logIndex',NULL,'expectedPrevious',prev,'actualHeader',h));
  END IF;
  IF (h->>'timestampSeconds')::numeric>extract(epoch FROM ot) THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','future_source_timestamp','blockNumber',h->'number','logIndex',NULL,'timestampSeconds',h->'timestampSeconds','observedAt',p->'observedAt'));
  END IF;
  IF hs ? (h->>'number') THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','canonical_chain_mismatch','blockNumber',h->'number','logIndex',NULL,'duplicateHeader',h));
  END IF;
  hs:=hs||jsonb_build_object(h->>'number',h); prev:=polygon_live_activity.cp(h);
 END LOOP;
 IF h IS DISTINCT FROM p->'finalized' THEN
  errs:=errs||jsonb_build_array(jsonb_build_object('code','canonical_chain_mismatch','expectedFinalized',p->'finalized','actualLastHeader',h));
 END IF;
 -- Validate every log and detect all bounded conflicts BEFORE inserting any observation.
 FOR v IN SELECT value FROM jsonb_array_elements(p->'logs') ORDER BY (value->>'blockNumber')::numeric,(value->>'logIndex')::numeric LOOP
  IF v->>'owner'<>i.owner_address THEN RETURN polygon.err('ACCESS_DENIED',403); END IF;
  h:=hs->(v->>'blockNumber'); key:=(v->>'transactionHash')||':'||(v->>'logIndex');
  IF h IS NULL OR h->'hash' IS DISTINCT FROM v->'blockHash' THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','canonical_chain_mismatch','blockNumber',v->'blockNumber','logIndex',v->'logIndex',
    'expectedHeader',h,'actualLog',v)); CONTINUE;
  END IF;
  sem:=polygon_live_activity.semantic(v,h);
  first_v:=seen->key;
  IF first_v IS NOT NULL AND first_v->>'semantic'<>sem THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','log_identity_conflict','blockNumber',v->'blockNumber','logIndex',v->'logIndex',
    'identity',key,'existingObservationId',NULL,'expectedPreimage',first_v->'semantic','actualPreimage',sem));
  END IF;
  IF first_v IS NULL THEN seen:=seen||jsonb_build_object(key,jsonb_build_object('semantic',sem)); END IF;
  SELECT * INTO old FROM polygon_live_activity.observations WHERE session_id=sid AND transaction_hash=v->>'transactionHash' AND log_index=(v->>'logIndex')::numeric;
  IF FOUND AND old.semantic_preimage<>sem THEN
   errs:=errs||jsonb_build_array(jsonb_build_object('code','log_identity_conflict','blockNumber',v->'blockNumber','logIndex',v->'logIndex',
    'identity',key,'existingObservationId',old.id,'expectedPreimage',old.semantic_preimage,'actualPreimage',sem));
  END IF;
 END LOOP;
 IF jsonb_array_length(errs)>0 THEN
  SELECT jsonb_agg(value ORDER BY CASE value->>'code' WHEN 'baseline_hash_mismatch' THEN 1 WHEN 'canonical_chain_mismatch' THEN 2
   WHEN 'future_source_timestamp' THEN 3 ELSE 4 END,(value->>'blockNumber')::numeric NULLS FIRST,(value->>'logIndex')::numeric NULLS FIRST,value::text)
   INTO sorted_errs FROM jsonb_array_elements(errs);
  code:=sorted_errs#>>'{0,code}';cid:=gen_random_uuid();
  INSERT INTO polygon_live_activity.conflicts VALUES(cid,op,sid,code,sorted_errs,p->>'evidenceSha256',t);
  UPDATE polygon_live_activity.stream SET status='reconciliation_required',last_operation_id=op WHERE session_id=sid;
  r:=jsonb_build_object('operationId',op,'kind','ingest_blocked','sessionId',sid,'status','reconciliation_required','conflictId',cid,
   'conflictCode',code,'checkpoint',st.checkpoint,'highWatermark',st.high_watermark::text,'evidenceSha256',p->'evidenceSha256');
  RETURN polygon_live_activity.save_result(p,'ingest',r,t);
 END IF;
 -- Valid range. No previous accepted range can overlap this one. Duplicate rows within this batch share one observation.
 seen:='{}';seq:=st.high_watermark;
 FOR v IN SELECT value FROM jsonb_array_elements(p->'logs') ORDER BY (value->>'blockNumber')::numeric,(value->>'logIndex')::numeric LOOP
  key:=(v->>'transactionHash')||':'||(v->>'logIndex');
  IF seen ? key THEN duplicates:=duplicates+1;CONTINUE; END IF;
  seen:=seen||jsonb_build_object(key,true);h:=hs->(v->>'blockNumber');sem:=polygon_live_activity.semantic(v,h);oid:=gen_random_uuid();
  IF EXISTS(SELECT FROM polygon_live_activity.observations WHERE session_id=sid AND transaction_hash=v->>'transactionHash' AND log_index=(v->>'logIndex')::numeric)
  THEN RAISE EXCEPTION 'nonoverlapping range unexpectedly repeats a stored log' USING ERRCODE='23514'; END IF;
  IF (h->>'timestampSeconds')::numeric<=extract(epoch FROM st.armed_at) THEN
   class:='excluded';ns:=NULL;excluded:=excluded+1;
  ELSE class:='accepted';seq:=seq+1;ns:=seq;accepted:=accepted+1; END IF;
  IF class='accepted' THEN
   SELECT COALESCE((ad.request->>'observationId')::uuid,oid) INTO oid FROM (SELECT 1) one_row
   LEFT JOIN LATERAL (SELECT value->'evidence' evidence FROM jsonb_array_elements(es) WHERE value->>'transactionHash'=v->>'transactionHash' AND value->>'logIndex'=v->>'logIndex') ev ON true
   LEFT JOIN polygon_buy.admissions ad ON polygon_buy.pending_shape(ev.evidence) AND ad.id=(CASE WHEN polygon_buy.pending_shape(ev.evidence) THEN ev.evidence->>'admissionId' END)::uuid AND ad.session_id=sid;
  END IF;
  INSERT INTO polygon_live_activity.observations VALUES(oid,sid,op,v->>'transactionHash',(v->>'logIndex')::numeric,v,h,sem,polygon_live_activity.digest(sem),ot,ns,class);
  IF class='accepted' THEN
   PERFORM polygon_live_activity.write_decision(oid,es,t);
  END IF;
 END LOOP;
 UPDATE polygon_live_activity.stream SET checkpoint=polygon_live_activity.cp(p->'finalized'),high_watermark=seq,last_observed_at=ot,last_operation_id=op,last_range_operation_id=op WHERE session_id=sid;
 r:=jsonb_build_object('operationId',op,'kind','ingest','sessionId',sid,'checkpoint',polygon_live_activity.cp(p->'finalized'),
  'accepted',accepted::text,'duplicates',duplicates::text,'excluded',excluded::text,'highWatermark',seq::text);
 RETURN polygon_live_activity.save_result(p,'ingest',r,t);
END $$;

-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE OR REPLACE FUNCTION polygon_live_activity.inner_bound(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE b jsonb;a jsonb;e jsonb;old polygon_live_activity.bound_requests;o polygon_live_activity.operations;st polygon_live_activity.stream;version text;
BEGIN
 IF polygon.exact_keys(p,ARRAY['ingest','expectedSnapshotVersion','evaluations']) IS DISTINCT FROM true OR octet_length(p::text)>4194304
  OR polygon_live_activity.request_shape(p->'ingest','ingest') IS DISTINCT FROM true
  OR polygon.version_text(p->>'expectedSnapshotVersion') IS DISTINCT FROM true
  OR jsonb_typeof(p->'expectedSnapshotVersion') IS DISTINCT FROM 'string' OR jsonb_typeof(p->'evaluations') IS DISTINCT FROM 'array'
 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 IF jsonb_array_length(p->'evaluations')>128 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 FOR e IN SELECT value FROM jsonb_array_elements(p->'evaluations') LOOP
  IF polygon.exact_keys(e,ARRAY['transactionHash','logIndex','evidence']) IS DISTINCT FROM true
   OR NOT polygon_live_activity.hash_value(e->'transactionHash') OR NOT polygon_live_activity.uint(e->'logIndex')
   OR polygon_live_activity.evidence_shape(e->'evidence') IS DISTINCT FROM true THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(p->'evaluations') x GROUP BY x.value->>'transactionHash',x.value->>'logIndex' HAVING count(*)>1)
 THEN RETURN polygon.err('INVALID_REQUEST',400);END IF;
 b:=p->'ingest';a:=polygon_live_activity.writer_guard(b);IF a->>'http'<>'200' THEN RETURN a;END IF;
 IF polygon_live_activity.bound_state_valid((b->>'sessionId')::uuid) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE');END IF;
 SELECT * INTO old FROM polygon_live_activity.bound_requests WHERE session_id=(b->>'sessionId')::uuid AND operation_id=(b->>'operationId')::uuid;
 IF FOUND THEN
  IF old.request IS DISTINCT FROM p THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409);END IF;
  SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=old.session_id AND id=old.operation_id;
  RETURN jsonb_build_object('http',200,'result',o.result);
 END IF;
 IF EXISTS(SELECT FROM polygon_live_activity.operations WHERE session_id=(b->>'sessionId')::uuid AND id=(b->>'operationId')::uuid) THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409);END IF;
 SELECT current_snapshot_version::text INTO STRICT version FROM polygon.paper_sessions WHERE id=(b->>'sessionId')::uuid;
 IF version<>p->>'expectedSnapshotVersion' THEN RETURN polygon.err('VERSION_CONFLICT',409);END IF;
 a:=polygon_live_activity.bound_ingest(b,p->'evaluations');IF a->>'http'<>'200' THEN RETURN a;END IF;
 SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=(b->>'sessionId')::uuid AND id=(b->>'operationId')::uuid;
 IF a#>>'{result,kind}'='ingest' THEN
  IF jsonb_array_length(p->'evaluations')<>(SELECT count(*) FROM polygon_live_activity.observations WHERE session_id=o.session_id AND operation_id=o.id AND classification='accepted')
   OR EXISTS(SELECT FROM jsonb_array_elements(p->'evaluations') x WHERE NOT EXISTS(
    SELECT FROM polygon_live_activity.observations ob WHERE ob.session_id=o.session_id AND ob.operation_id=o.id AND ob.classification='accepted'
     AND ob.transaction_hash=x.value->>'transactionHash' AND ob.log_index=(x.value->>'logIndex')::numeric))
  THEN RAISE EXCEPTION 'BUY evaluation set differs from accepted logs' USING ERRCODE='22023';END IF;
 END IF;
 INSERT INTO polygon_live_activity.bound_requests VALUES(o.id,o.session_id,p,polygon_live_activity.digest('paper-bound-skip-envelope-v1'||chr(10)||p::text),o.created_at);
 RETURN a;
END $$;

-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE OR REPLACE FUNCTION polygon_live_activity.bound_state_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE rq polygon_live_activity.bound_requests;op polygon_live_activity.operations;ev polygon_live_activity.evaluations;ob polygon_live_activity.observations;de polygon_live_activity.decisions;
BEGIN
 IF polygon_live_activity.state_valid(sid) IS DISTINCT FROM true THEN RETURN false;END IF;
 IF EXISTS(SELECT FROM polygon_live_activity.operations o WHERE o.session_id=sid AND o.kind='ingest' AND NOT EXISTS(SELECT FROM polygon_live_activity.bound_requests r WHERE r.session_id=sid AND r.operation_id=o.id)) THEN RETURN false;END IF;
 FOR rq IN SELECT * FROM polygon_live_activity.bound_requests WHERE session_id=sid LOOP
  SELECT * INTO op FROM polygon_live_activity.operations WHERE session_id=sid AND id=rq.operation_id;
  IF op.id IS NULL OR op.kind<>'ingest' OR op.request IS DISTINCT FROM rq.request->'ingest' OR op.created_at<>rq.created_at OR op.session_id<>rq.session_id THEN RETURN false;END IF;
  IF op.result->>'kind'='ingest' AND jsonb_array_length(rq.request->'evaluations')<>(SELECT count(*) FROM polygon_live_activity.evaluations WHERE session_id=sid AND operation_id=op.id) THEN RETURN false;END IF;
 END LOOP;
 IF (SELECT count(*) FROM polygon_live_activity.evaluations WHERE session_id=sid)<>(SELECT count(*) FROM polygon_live_activity.observations WHERE session_id=sid AND classification='accepted') THEN RETURN false;END IF;
 FOR ev IN SELECT * FROM polygon_live_activity.evaluations WHERE session_id=sid LOOP
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE id=ev.observation_id;
  SELECT * INTO de FROM polygon_live_activity.decisions WHERE id=ev.decision_id;
  SELECT * INTO op FROM polygon_live_activity.operations WHERE session_id=sid AND id=ev.operation_id;
  SELECT * INTO rq FROM polygon_live_activity.bound_requests WHERE session_id=sid AND operation_id=ev.operation_id;
  IF de.id IS NULL OR op.id IS NULL OR rq.operation_id IS NULL OR ob.classification<>'accepted'
   OR ROW(ev.sequence,ev.session_id,ev.created_at,ev.operation_id) IS DISTINCT FROM ROW(ob.sequence,ob.session_id,op.created_at,ob.operation_id)
   OR ROW(de.observation_id,de.session_id,de.sequence,de.decided_at) IS DISTINCT FROM ROW(ob.id,ob.session_id,ob.sequence,ev.created_at)
   OR NOT ((de.policy_version='paper-bound-skip-v1' AND de.status='skipped' AND de.reason_code='context_invalid'
     AND de.detail_code=ev.evidence->>'reason' AND de.checks=jsonb_build_object('evidence',ev.evidence,'executionAdmission','blocked'))
    OR (de.policy_version='paper-buy-queued-v1' AND de.status='pending' AND de.reason_code IS NULL AND de.detail_code IS NULL
     AND de.checks=jsonb_build_object('evidence',ev.evidence,'executionAdmission','queued') AND polygon_buy.pending_valid(ob.id,ev.evidence,ev.created_at)))
   OR (ev.evidence->'binding'<>'null'::jsonb AND ev.evidence#>>'{binding,tokenId}' IS DISTINCT FROM ob.raw_log->>'tokenId')
   OR (SELECT count(*) FROM jsonb_array_elements(rq.request->'evaluations') x WHERE x.value->>'transactionHash'=ob.transaction_hash
    AND x.value->>'logIndex'=ob.log_index::text AND x.value->'evidence'=ev.evidence)<>1 THEN RETURN false;END IF;
 END LOOP;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION polygon_live_activity.role_valid(who oid) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM pg_roles r WHERE r.oid=who AND r.rolname::text ~ '^polygon_live_writer_[0-9a-f]{32}$'
 AND to_regprocedure('polygon.live_activity_arm(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_ingest(jsonb)') IS NOT NULL
 AND to_regprocedure('polygon.live_activity_resume(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_stop(jsonb)') IS NOT NULL AND to_regprocedure('polygon.live_activity_lookup(jsonb)') IS NOT NULL
 AND r.rolcanlogin AND NOT(r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls)
 AND NOT EXISTS(SELECT FROM pg_auth_members WHERE member=r.oid)
 AND NOT EXISTS(SELECT FROM pg_namespace n WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','polygon_buy','live_buy_core','v00_session','v00_upstream') AND has_schema_privilege(r.oid,n.oid,'CREATE'))
 AND NOT EXISTS(SELECT FROM pg_namespace n WHERE n.nspname IN('polygon_live','polygon_live_activity','polygon_buy','live_buy_core','v00_session','v00_upstream') AND has_schema_privilege(r.oid,n.oid,'USAGE'))
 AND NOT EXISTS(SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','polygon_buy','live_buy_core') AND has_function_privilege(r.oid,p.oid,'EXECUTE')
 AND (p.oid NOT IN(to_regprocedure('polygon.live_activity_arm(jsonb)'),to_regprocedure('polygon.live_activity_ingest(jsonb)'),
 to_regprocedure('polygon.live_activity_stop(jsonb)'),to_regprocedure('polygon.live_activity_lookup(jsonb)'),to_regprocedure('polygon.live_activity_resume(jsonb)'),to_regprocedure('polygon.live_buy_reserve_v1(jsonb)'),to_regprocedure('polygon.live_buy_settle_v1(jsonb)'),to_regprocedure('polygon.live_buy_lookup_v1(jsonb)'))
 OR has_function_privilege(r.oid,p.oid,'EXECUTE WITH GRANT OPTION')))
 AND NOT EXISTS(SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN('polygon','polygon_live','polygon_live_activity','polygon_buy','live_buy_core','v00_session','v00_upstream') AND c.relkind IN('r','p','v','m','S')
 AND CASE WHEN c.relkind='S' THEN has_sequence_privilege(r.oid,c.oid,'USAGE,SELECT,UPDATE')
 ELSE has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') END))
$$;



CREATE FUNCTION polygon_buy.command_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE c polygon_buy.commands;r live_buy_core.receipts;a polygon_buy.admissions;i live_buy_core.intents;ob polygon_live_activity.observations;de polygon_live_activity.decisions;b polygon_buy.bindings;t timestamptz;
BEGIN
 SELECT * INTO b FROM polygon_buy.bindings WHERE session_id=sid;
 FOR c IN SELECT * FROM polygon_buy.commands WHERE session_id=sid LOOP
  SELECT * INTO r FROM live_buy_core.receipts WHERE session_id=sid AND command_id=c.command_id;
  SELECT * INTO a FROM polygon_buy.admissions WHERE session_id=sid AND id=c.admission_id;
  SELECT * INTO i FROM live_buy_core.intents WHERE session_id=sid AND id=r.intent_id;
  SELECT * INTO ob FROM polygon_live_activity.observations WHERE session_id=sid AND id=i.observation_id;
  SELECT * INTO de FROM polygon_live_activity.decisions WHERE session_id=sid AND observation_id=ob.id;
  t:=live_buy_core.event_time(sid,r.version);
  IF r.command_id IS NULL OR a.id IS NULL OR i.id IS NULL OR ob.id IS NULL OR b.session_id IS NULL
   OR c.kind<>r.kind OR c.kind<>a.kind OR c.request IS DISTINCT FROM jsonb_build_object('session_id',sid,'request',r.request,'admission_id',a.id)
   OR (c.kind='reserve' AND r.request->'desiredNotional' IS DISTINCT FROM polygon_buy.sized_notional(sid,ob.id))
   OR a.request IS DISTINCT FROM r.request OR a.run_id<>b.run_id OR a.token_id<>i.token_id OR a.condition_id<>i.condition_id
   OR a.transaction_hash<>ob.transaction_hash OR a.log_index<>ob.log_index OR ob.sequence<b.first_sequence OR ob.raw_log->>'side'<>'BUY'
   OR de.policy_version IS DISTINCT FROM 'paper-buy-queued-v1' OR de.status IS DISTINCT FROM 'pending'
   OR t<a.issued_at OR t>=a.expires_at THEN RETURN false;END IF;
 END LOOP;
 RETURN (SELECT count(*) FROM polygon_buy.commands WHERE session_id=sid)=(SELECT count(*) FROM live_buy_core.receipts WHERE session_id=sid);
END $$;
CREATE FUNCTION polygon_buy.enforce() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE sid uuid:=COALESCE(NEW.session_id,OLD.session_id);
BEGIN
 IF polygon_buy.session_valid(sid) IS DISTINCT FROM true OR polygon_buy.command_valid(sid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete composed financial state' USING ERRCODE='23514';END IF;
 RETURN NULL;
END $$;
DO $$DECLARE n text;BEGIN
 FOREACH n IN ARRAY ARRAY['bindings','commands','snapshot_links'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER complete_composed AFTER INSERT OR UPDATE OR DELETE ON polygon_buy.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_buy.enforce()',n);
 END LOOP;
 FOREACH n IN ARRAY ARRAY['scopes','heads','snapshots','positions','intents','executions','fills','lots','reservation_events','journal_entries','receipts','audit','outbox'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER complete_composed AFTER INSERT OR UPDATE OR DELETE ON live_buy_core.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_buy.enforce()',n);
 END LOOP;
END $$;
CREATE FUNCTION polygon_buy.item(ob polygon_live_activity.observations,d polygon_live_activity.decisions) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE body jsonb;i live_buy_core.intents;e live_buy_core.executions;sn live_buy_core.snapshots;copy jsonb;fills jsonb;cost jsonb;gross jsonb;net jsonb;qfee jsonb;cfee jsonb;
BEGIN
 body:=polygon_live_activity.item(ob,d);
 IF d.policy_version='paper-bound-skip-v1' THEN RETURN body;END IF;
 SELECT * INTO i FROM live_buy_core.intents WHERE session_id=ob.session_id AND observation_id=ob.id;
 SELECT * INTO e FROM live_buy_core.executions WHERE session_id=ob.session_id AND intent_id=i.id;
 IF e.id IS NULL THEN
  copy:=jsonb_build_object('kind','pending','intentId',i.id,'reservedCash',i.reserved_cash,'reservedNotional',i.notional,'admittedAt',v00_session.utc(i.admitted_at));
 ELSE
  SELECT * INTO STRICT sn FROM live_buy_core.snapshots WHERE session_id=ob.session_id AND version=e.version;
  SELECT live_buy_core.sumq(notional),live_buy_core.sumq(f.gross),live_buy_core.sumq(f.net),live_buy_core.sumq(quantity_fee),live_buy_core.sumq(cash_fee),
   jsonb_agg(jsonb_build_object('fillId',id,'executedAt',v00_session.utc(executed_at),'price',price,'quantityGross',f.gross,'quantityNet',f.net,'quantityFee',quantity_fee,'cashFee',cash_fee,'notional',notional) ORDER BY ordinal)
  INTO cost,gross,net,qfee,cfee,fills FROM live_buy_core.fills f WHERE session_id=ob.session_id AND intent_id=i.id;
  copy:=jsonb_build_object('kind','filled','intentId',i.id,'executionId',e.id,'settledAt',v00_session.utc(e.settled_at),'notional',cost,
   'quantityGross',gross,'quantityNet',net,'quantityFee',qfee,'cashFee',cfee,'snapshotId',sn.id,'snapshotVersion',sn.version::text,'fills',fills);
 END IF;
 RETURN body||jsonb_build_object('decision',jsonb_build_object('status',CASE WHEN e.id IS NULL THEN 'pending' ELSE 'filled' END,
 'reasonCode',NULL,'detailCode',NULL,'decidedAt',v00_session.utc(d.decided_at),'policyVersion','paper-buy-queued-v1','copy',copy));
END $$;

CREATE FUNCTION polygon.buy_activity_read_v1(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;s polygon.paper_sessions;st polygon_live_activity.stream;i polygon_live_activity.assignments;
 items jsonb;binding jsonb;after_seq bigint;lim integer;water bigint:=0;next_seq bigint;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 IF polygon.exact_keys(p,ARRAY['auth','session_id','after_sequence','limit']) IS DISTINCT FROM true
 OR NOT polygon_live_activity.uuid_value(p->'session_id') OR NOT polygon_live_activity.uint(p->'after_sequence')
 OR jsonb_typeof(p->'limit') IS DISTINCT FROM 'number' OR (p->>'limit' ~ '^[0-9]{1,3}$') IS DISTINCT FROM true
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 IF (p->>'after_sequence')::numeric>9223372036854775807 OR (p->>'limit')::integer NOT BETWEEN 1 AND 100 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 after_seq:=(p->>'after_sequence')::bigint;lim:=(p->>'limit')::integer;
 a:=polygon.guard(p->'auth');IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=(p->>'session_id')::uuid AND user_id=(a->>'user_id')::uuid;
 IF s.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 IF polygon.session_valid(s.id) IS DISTINCT FROM true OR NOT EXISTS(
 SELECT FROM polygon_live_activity.installation x JOIN polygon_live.installation l ON l.database_name=x.database_name AND l.operator_run_id=x.run_id WHERE x.database_name=current_database())
 THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 SELECT * INTO i FROM polygon_live_activity.assignments WHERE session_id=s.id;
 SELECT * INTO st FROM polygon_live_activity.stream WHERE session_id=s.id;
 IF i.session_id IS NULL THEN
  IF st.session_id IS NOT NULL OR EXISTS(SELECT FROM polygon_live_activity.operations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.observations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.decisions WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.calls WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.bound_requests WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.evaluations WHERE session_id=s.id)
  OR EXISTS(SELECT FROM polygon_live_activity.conflicts WHERE session_id=s.id)
  THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 ELSE
  IF polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true
  OR polygon_live_activity.calls_valid(s.id) IS DISTINCT FROM true THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  binding:=jsonb_build_object('streamId',i.stream_id,'venueCode','polymarket','catalogSourceId',i.source_id,'traderId',i.trader_id,
  'traderRevisionId',i.revision_id,'externalTraderId',i.owner_address,'bindingRevision',i.binding_revision::text);
 END IF;
 water:=COALESCE(st.high_watermark,0);
 IF after_seq>water THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT COALESCE(jsonb_agg(x.body ORDER BY x.sequence),'[]'),COALESCE(max(x.sequence),after_seq) INTO items,next_seq FROM (
 SELECT ob.sequence,polygon_buy.item(ob,d) AS body FROM polygon_live_activity.observations ob
 JOIN polygon_live_activity.decisions d ON d.observation_id=ob.id AND d.session_id=ob.session_id AND d.sequence=ob.sequence
 WHERE ob.session_id=s.id AND ob.sequence>after_seq AND ob.sequence<=water ORDER BY ob.sequence LIMIT lim) x;
 RETURN jsonb_build_object('http',200,'schemaVersion','live-buy-activity-v1','binding',binding,'observation',jsonb_build_object('status',COALESCE(st.status,'not_armed'),
 'armedAt',CASE WHEN st.armed_at IS NULL THEN NULL ELSE v00_session.utc(st.armed_at) END,
 'lastObservedAt',CASE WHEN st.last_observed_at IS NULL THEN NULL ELSE v00_session.utc(st.last_observed_at) END,'completeness','unproven'),
 'items',items,'page',jsonb_build_object('afterSequence',after_seq::text,'nextAfterSequence',next_seq::text,'highWatermark',water::text,'hasMore',next_seq<water),
 'session',CASE WHEN s.version>1 AND EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=s.id) THEN polygon_buy.body(s.id) ELSE polygon.session_body(s) END);
END $$;

-- Existing staff target scopes and audit evidence retained. Initial audit is linked to snapshot1.
CREATE OR REPLACE FUNCTION polygon.pilot_staff_snapshot(sid uuid) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s polygon.paper_sessions; sn polygon.session_snapshots; au polygon.audit_events; body jsonb; pc polygon.profile;
BEGIN
 SELECT * INTO STRICT pc FROM polygon.profile WHERE singleton FOR SHARE;
 IF NOT pc.enabled OR pc.environment<>'shadow-polygon-synthetic-v1' THEN RAISE EXCEPTION 'paper unavailable' USING ERRCODE='55000'; END IF;
 SELECT * INTO s FROM polygon.paper_sessions WHERE id=sid;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF polygon.session_valid(sid) IS DISTINCT FROM true THEN RAISE EXCEPTION 'incomplete paper source' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT sn FROM polygon.session_snapshots WHERE session_id=s.id AND version=s.current_snapshot_version;
 SELECT * INTO STRICT au FROM polygon.audit_events WHERE session_id=s.id;
 IF s.current_settings_revision_id<>sn.settings_revision_id OR au.snapshot_id IS DISTINCT FROM (SELECT id FROM polygon.session_snapshots WHERE session_id=s.id AND version=1) OR au.receipt_id<>s.start_receipt_id
 OR au.actor_user_id<>s.user_id OR au.kind<>'paper_session.started' OR au.outcome<>'succeeded' OR au.created_at<>s.started_at
 OR sn.data_origin NOT IN('synthetic','public_api') OR NOT ((sn.content_state='EMPTY' AND sn.coverage_state='no_trade_data') OR (sn.content_state='HAS_ACTIVITY' AND sn.coverage_state='trade_data_unvalued' AND EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=sid)))
 THEN RAISE EXCEPTION 'inconsistent paper projection' USING ERRCODE='23514'; END IF;
 body:=CASE WHEN s.version>1 AND EXISTS(SELECT FROM polygon_buy.bindings WHERE session_id=sid) THEN polygon_buy.body(sid) ELSE polygon.session_body(s) END;
 RETURN jsonb_build_object('user_id',s.user_id,'session_id',s.id,'snapshot_id',sn.id,'snapshot_version',sn.version,
  'settings_revision_id',sn.settings_revision_id,'session',body,
  'event',jsonb_build_object('eventId',au.id,'sessionId',s.id,'kind',au.kind,'occurredAt',v00_session.utc(au.created_at)));
END $$;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon_buy FROM PUBLIC,polygon_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA live_buy_core FROM PUBLIC,polygon_executor;
REVOKE ALL ON FUNCTION polygon.buy_activity_read_v1(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION polygon.buy_activity_read_v1(jsonb) TO polygon_executor;

-- Deferred core checks execute after the definer RPC returns to the scoped worker.
ALTER FUNCTION live_buy_core.enforce() SECURITY DEFINER;


-- Executed as polygon_owner after the November composition, inside its transaction.
-- Only the two approved public wallets are admitted. Catalog and C06 own their IDs.
DO $scope$
DECLARE constraint_name name;
BEGIN
 SELECT conname INTO STRICT constraint_name FROM pg_constraint
 WHERE conrelid='polygon_live_activity.assignments'::regclass AND contype='c'
 AND pg_get_constraintdef(oid) LIKE '%owner_address%0xf0318c32136c2db7fec88b84869aee6a1106c80c%';
 EXECUTE format('ALTER TABLE polygon_live_activity.assignments DROP CONSTRAINT %I',constraint_name);
END $scope$;
ALTER TABLE polygon_live_activity.assignments ADD CONSTRAINT personal_pilot_address
 CHECK(owner_address IN ('0xf0318c32136c2db7fec88b84869aee6a1106c80c','0xde9f7f4e77a1595623ceb58e469f776257ccd43c'));
CREATE TABLE polygon_buy.issuer_scopes(
 session_id uuid PRIMARY KEY REFERENCES polygon_buy.bindings,
 issuer_oid oid NOT NULL UNIQUE,issuer_role name NOT NULL UNIQUE,
 wallet text NOT NULL,settings_id uuid NOT NULL,
 FOREIGN KEY(session_id,settings_id) REFERENCES polygon.settings_revisions(session_id,id)
);
CREATE TRIGGER immutable_scope BEFORE UPDATE OR DELETE ON polygon_buy.issuer_scopes
 FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TABLE polygon_buy.verified_quotes(
 session_id uuid NOT NULL REFERENCES polygon_buy.issuer_scopes,
 execution_id text NOT NULL CHECK(execution_id ~ '^[a-f0-9]{64}$'),
 quote jsonb NOT NULL, reserve_id uuid NOT NULL UNIQUE REFERENCES polygon_buy.admissions(id),
 settle_id uuid NOT NULL UNIQUE, issuetime timestamptz NOT NULL,
 PRIMARY KEY(session_id,execution_id)
);
CREATE TRIGGER immutable_quote BEFORE UPDATE OR DELETE ON polygon_buy.verified_quotes
 FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
REVOKE ALL ON polygon_buy.issuer_scopes,polygon_buy.verified_quotes FROM PUBLIC,polygon_executor;


-- Individual enrollment is an operator action. One row per approved wallet.
CREATE TABLE polygon_buy.enrolled(
 session_id uuid PRIMARY KEY,user_id uuid NOT NULL,wallet text NOT NULL UNIQUE,
 revision_id uuid NOT NULL,run_id uuid NOT NULL REFERENCES polygon_live_activity.release_record(run_id),
 FOREIGN KEY(session_id,user_id) REFERENCES polygon.paper_sessions(id,user_id),
 CHECK(wallet IN ('0xf0318c32136c2db7fec88b84869aee6a1106c80c','0xde9f7f4e77a1595623ceb58e469f776257ccd43c'))
);
CREATE TRIGGER immutable_enrollment BEFORE UPDATE OR DELETE ON polygon_buy.enrolled FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE FUNCTION polygon_buy.pinned_tradecraft(sid uuid) RETURNS boolean
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM polygon_buy.enrolled p
 JOIN polygon.paper_sessions s ON (s.id,s.user_id,s.trader_revision_id)=(p.session_id,p.user_id,p.revision_id)
 JOIN polygon_live_activity.assignments a ON (a.session_id,a.user_id,a.owner_address,a.run_id,a.revision_id)
  =(p.session_id,p.user_id,p.wallet,p.run_id,p.revision_id)
 JOIN polygon.traders t ON (t.id,t.external_trader_id,t.source_id,t.venue_id)=(s.trader_id,p.wallet,s.source_id,s.venue_id)
 JOIN polygon.catalog_sources c ON c.id=s.source_id AND c.data_origin='public_api'
 JOIN polygon.venues v ON v.id=s.venue_id AND v.code='polymarket'
 JOIN polygon.session_snapshots sn ON sn.session_id=s.id AND sn.version=1 AND sn.data_origin='public_api'
 WHERE p.session_id=sid AND a.database_name=current_database()
 AND p.wallet='0xde9f7f4e77a1595623ceb58e469f776257ccd43c'
 AND s.source_id='ae86e8a7-1d5f-44a0-95d8-4770a981e57d'
 AND s.trader_id='5ba3155e-b23e-40b8-a968-85b94b1b9e03'
 AND p.revision_id='0bfa3009-cbae-4aeb-87c9-b636631b565d'
 AND polygon_live.source_admitted(s.user_id,s.source_id,s.trader_id,s.trader_revision_id,s.venue_id))
$$;
-- Keep original checks for every other session, including historic assignments.
DO $narrow$ DECLARE d text;old text; BEGIN
 d:=pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure);
 old:='OR NOT EXISTS(SELECT FROM polygon_live.public_source p WHERE p.database_name=i.database_name AND p.operator_run_id=i.run_id';
 IF cardinality(string_to_array(d,old))<>2 OR cardinality(string_to_array(d,'polygon_live.public_valid(sid) IS DISTINCT FROM true'))<>2
 THEN RAISE EXCEPTION 'state_valid preimage mismatch'; END IF;
 d:=replace(d,'polygon_live.public_valid(sid) IS DISTINCT FROM true','(polygon_live.public_valid(sid) OR polygon_buy.pinned_tradecraft(sid)) IS DISTINCT FROM true');
 EXECUTE replace(d,old,'OR NOT polygon_buy.pinned_tradecraft(sid) AND NOT EXISTS(SELECT FROM polygon_live.public_source p WHERE p.database_name=i.database_name AND p.operator_run_id=i.run_id');
 d:=pg_get_functiondef('polygon_live_activity.writer_guard(jsonb)'::regprocedure);
 old:='polygon_live.public_valid(s.id) IS DISTINCT FROM true';
 IF cardinality(string_to_array(d,old))<>2 THEN RAISE EXCEPTION 'writer guard preimage mismatch'; END IF;
 EXECUTE replace(d,old,'(polygon_live.public_valid(s.id) OR polygon_buy.pinned_tradecraft(s.id)) IS DISTINCT FROM true');
 d:=pg_get_functiondef('polygon_live_activity.inner_resume(jsonb)'::regprocedure);
 old:='AND patch.writer_role=bind.writer_role)';
 IF cardinality(string_to_array(d,old))<>2 THEN RAISE EXCEPTION 'resume preimage mismatch'; END IF;
 EXECUTE replace(d,old,old||' AND NOT polygon_buy.pinned_tradecraft(sid)');
END $narrow$;
-- Legacy hashes are frozen. Only Exchange 2 uses an explicit exchange field.
DO $copy$ BEGIN
 EXECUTE replace(pg_get_functiondef('polygon_live_activity.log_shape(jsonb)'::regprocedure),'FUNCTION polygon_live_activity.log_shape(', 'FUNCTION polygon_live_activity.log_shape_original(');
END $copy$;
CREATE OR REPLACE FUNCTION polygon_live_activity.log_shape(v jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT polygon_live_activity.log_shape_original(v) OR
 coalesce(v->>'exchange'='0xe2222d279d744050d28e00520010520000310f59'
 AND polygon_live_activity.log_shape_original(v-'exchange'),false)
$$;
DO $copy$ BEGIN
 EXECUTE replace(pg_get_functiondef('polygon_live_activity.semantic(jsonb,jsonb)'::regprocedure),'FUNCTION polygon_live_activity.semantic(', 'FUNCTION polygon_live_activity.semantic_original(');
END $copy$;
CREATE OR REPLACE FUNCTION polygon_live_activity.semantic(v jsonb,h jsonb) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE parts text[];
BEGIN
 IF NOT (v ? 'exchange') THEN RETURN polygon_live_activity.semantic_original(v,h); END IF;
 IF v->>'exchange' IS DISTINCT FROM '0xe2222d279d744050d28e00520010520000310f59' THEN RAISE EXCEPTION 'unsupported exchange'; END IF;
 parts:=string_to_array(polygon_live_activity.semantic_original(v-'exchange',h),chr(10));
 IF parts[3] IS DISTINCT FROM '0xe111180000d2663c0091e4f400237545b87b996b' THEN RAISE EXCEPTION 'unexpected semantic template'; END IF;
 parts[1]:='shadow-personal-chain-log-semantic-v2'; parts[3]:=v->>'exchange';
 RETURN array_to_string(parts,chr(10));
END $$;


CREATE TABLE polygon_buy.personal_start_blocks(
 session_id uuid PRIMARY KEY REFERENCES polygon_buy.issuer_scopes,
 previous_checkpoint jsonb NOT NULL, previous_watermark bigint NOT NULL,
 previous_operation uuid NOT NULL, chain_id integer NOT NULL CHECK(chain_id=137),
 block_number bigint NOT NULL CHECK(block_number>=0),block_hash text NOT NULL CHECK(block_hash~'^0x[0-9a-f]{64}$'),
 attached_at timestamptz NOT NULL,proof_bytes bytea NOT NULL,
 evidence_sha256 text GENERATED ALWAYS AS (encode(sha256(proof_bytes),'hex')) STORED
);
CREATE TRIGGER immutable_anchor BEFORE UPDATE OR DELETE ON polygon_buy.personal_start_blocks
 FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE FUNCTION polygon_buy.record_start_block(sid uuid,raw bytea) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE proof jsonb:=convert_from(raw,'UTF8')::jsonb; h jsonb:=proof->'finalized'; n bigint; st polygon_live_activity.stream; b polygon_buy.bindings;
BEGIN
 IF octet_length(raw)>65536 OR polygon.exact_keys(proof,ARRAY['chainId','method','tag','observedAt','finalized','canonicalHash','evidenceRef']) IS DISTINCT FROM true
 OR (proof->'chainId'='137'::jsonb AND proof->>'method'='eth_getBlockByNumber' AND proof->>'tag'='finalized'
 AND polygon_live_activity.checkpoint(h) AND proof->>'canonicalHash'=h->>'hash'
 AND polygon_live_activity.time_value(proof->'observedAt') AND length(proof->>'evidenceRef')>0) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'invalid operator finalized block evidence'; END IF;
 n:=(h->>'number')::bigint;
 SELECT * INTO STRICT b FROM polygon_buy.bindings WHERE session_id=sid;
 SELECT * INTO STRICT st FROM polygon_live_activity.stream WHERE session_id=sid AND status='stopped' FOR UPDATE;
 IF (proof->>'observedAt')::timestamptz NOT BETWEEN b.bound_at-interval '30 seconds' AND clock_timestamp()
 OR NOT EXISTS(SELECT FROM polygon_buy.issuer_scopes WHERE session_id=sid AND wallet='0xf0318c32136c2db7fec88b84869aee6a1106c80c')
 OR n<(st.checkpoint->>'number')::bigint OR (n=(st.checkpoint->>'number')::bigint AND h->>'hash'<>st.checkpoint->>'hash')
 THEN RAISE EXCEPTION 'incompatible personal start block'; END IF;
 INSERT INTO polygon_buy.personal_start_blocks(session_id,previous_checkpoint,previous_watermark,previous_operation,chain_id,block_number,block_hash,attached_at,proof_bytes)
 VALUES(sid,st.checkpoint,st.high_watermark,st.last_operation_id,137,n,h->>'hash',b.bound_at,raw);
END $$;
CREATE FUNCTION polygon_buy.start_receipt(sid uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('chainId',chain_id,'number',block_number::text,'hash',block_hash,'evidenceSha256',evidence_sha256)
 FROM polygon_buy.personal_start_blocks WHERE session_id=sid
$$;
DO $patch$ DECLARE d text; needle text; BEGIN
 d:=pg_get_functiondef('polygon_live_activity.reason(text)'::regprocedure);
 needle:='ARRAY[''not_buy'',';
 IF cardinality(string_to_array(d,needle))<>2 THEN RAISE EXCEPTION 'reason preimage mismatch'; END IF;
 EXECUTE replace(d,needle,'ARRAY[''before_personal_activation'',''not_buy'',');
END $patch$;
CREATE FUNCTION polygon_buy.check_start_decision() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE anchor polygon_buy.personal_start_blocks;ob polygon_live_activity.observations;early boolean:=false;
BEGIN
 SELECT * INTO anchor FROM polygon_buy.personal_start_blocks WHERE session_id=NEW.session_id;
 IF FOUND THEN
 SELECT * INTO STRICT ob FROM polygon_live_activity.observations WHERE session_id=NEW.session_id AND id=NEW.observation_id;
 early:=(ob.raw_log->>'blockNumber')::bigint<=anchor.block_number;
 END IF;
 IF early THEN
 IF NEW.status IS DISTINCT FROM 'skipped' OR NEW.detail_code IS DISTINCT FROM 'before_personal_activation'
 OR NEW.checks#>>'{evidence,evidenceSha256}' IS DISTINCT FROM anchor.evidence_sha256
 OR NEW.checks#>'{evidence,binding}' IS DISTINCT FROM 'null'::jsonb THEN RAISE EXCEPTION 'pre-activation decision required'; END IF;
 ELSIF NEW.detail_code='before_personal_activation' THEN RAISE EXCEPTION 'outside approved historical range'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER personal_start_decision BEFORE INSERT ON polygon_live_activity.decisions FOR EACH ROW EXECUTE FUNCTION polygon_buy.check_start_decision();
CREATE FUNCTION polygon_buy.check_start_range() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a polygon_buy.personal_start_blocks; h jsonb;
BEGIN
 IF NEW.kind='ingest' AND NEW.result->>'kind'='ingest' THEN
 SELECT * INTO a FROM polygon_buy.personal_start_blocks WHERE session_id=NEW.session_id;
 IF FOUND AND (NEW.request#>>'{previous,number}')::bigint<a.block_number
 AND (NEW.request#>>'{finalized,number}')::bigint>=a.block_number THEN
 SELECT value INTO STRICT h FROM jsonb_array_elements(NEW.request->'headers') WHERE (value->>'number')::bigint=a.block_number;
 IF h->>'hash' IS DISTINCT FROM a.block_hash THEN RAISE EXCEPTION 'personal activation chain mismatch'; END IF;
 END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER personal_start_range BEFORE INSERT ON polygon_live_activity.operations FOR EACH ROW EXECUTE FUNCTION polygon_buy.check_start_range();
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon_buy FROM PUBLIC,polygon_executor;


-- The private collector verifies the source bytes, finality, fee policy, depth and
-- current book. This endpoint binds its original quote to one session and login.
CREATE FUNCTION polygon.personal_quote_issue_v1(q jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE sid uuid:=(q->>'sessionId')::uuid; eid text:=q->>'executionId';
 scope polygon_buy.issuer_scopes; a polygon_live_activity.assignments; st polygon.settings_revisions;
 b polygon_buy.bindings; prior polygon_buy.verified_quotes; now_at timestamptz;
 ev jsonb:=q->'event'; m jsonb:=ev#>'{venueReceipt,match}'; fin jsonb:=ev#>'{venueReceipt,finality}';
 est jsonb:=q->'estimate'; f jsonb:=est#>'{fills,0}'; evidence jsonb:=est->'evidence'; book jsonb:=est->'book';
 expires timestamptz; signal_at timestamptz; req jsonb; k text;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required'; END IF;
 SELECT * INTO STRICT scope FROM polygon_buy.issuer_scopes WHERE session_id=sid
 AND issuer_role=session_user AND issuer_oid=(SELECT oid FROM pg_roles WHERE rolname=session_user);
 SELECT * INTO STRICT a FROM polygon_live_activity.assignments WHERE session_id=sid AND stream_id=(q->>'assignmentId')::uuid;
 IF a.owner_address IS DISTINCT FROM scope.wallet OR a.writer_oid=scope.issuer_oid THEN RAISE EXCEPTION 'scope conflict'; END IF;
 SELECT * INTO prior FROM polygon_buy.verified_quotes WHERE session_id=sid AND execution_id=eid;
 IF FOUND THEN
  IF prior.quote IS DISTINCT FROM q THEN RAISE EXCEPTION 'immutable quote conflict' USING ERRCODE='23505'; END IF;
  RETURN jsonb_build_object('reserveId',prior.reserve_id,'observationId',q->'observationId');
 END IF;
 SELECT * INTO STRICT b FROM polygon_buy.bindings WHERE session_id=sid AND run_id=a.run_id;
 SELECT r.* INTO STRICT st FROM polygon.settings_revisions r
 JOIN polygon.paper_sessions s ON (s.id,s.current_settings_revision_id)=(r.session_id,r.id)
 JOIN polygon.user_session_slots sl ON (sl.user_id,sl.current_session_id)=(s.user_id,s.id)
 JOIN polygon.catalog_sources src ON src.id=s.source_id AND src.data_origin='public_api'
 WHERE s.id=sid AND s.user_id=a.user_id AND s.trader_id=a.trader_id
 AND s.trader_revision_id=a.revision_id AND r.id=scope.settings_id AND r.id=(q->>'settingsId')::uuid
 AND s.lifecycle='active' AND r.sizing_mode='fixed' AND polygon_live_activity.new_admission(sid) FOR UPDATE OF s;
 now_at:=clock_timestamp();
 expires:=to_timestamp((q->>'expiresAtMs')::bigint/1000.0);
 signal_at:=to_timestamp((ev->>'signalAtMs')::bigint/1000.0);
 IF (signal_at>=b.bound_at AND expires>now_at AND expires<=signal_at+interval '30 seconds'
 AND signal_at<=now_at AND polygon_live_activity.sha_value(q->'executionId')
 AND ev->>'executionId'=eid AND ev->>'venue'='polymarket' AND ev->>'side'='BUY'
 AND coalesce(q#>>'{normalizedLog,exchange}','0xe111180000d2663c0091e4f400237545b87b996b')=m->>'exchange'
 AND polygon_live_activity.log_shape(q->'normalizedLog')
 AND q#>>'{normalizedLog,transactionHash}'=m->>'transactionHash' AND q#>>'{normalizedLog,owner}'=scope.wallet
 AND q#>>'{normalizedLog,side}'='BUY' AND q#>>'{normalizedLog,tokenId}'=ev->>'outcomeId'
 AND q#>>'{normalizedLog,blockHash}'=fin->>'blockHash' AND q#>>'{normalizedLog,blockNumber}'=fin->>'blockNumber'
 AND q#>>'{normalizedLog,receiptSha256}'=fin->>'receiptSha256'
 AND (q#>>'{normalizedLog,makerAmountFilledRaw}')::numeric*(m#>>'{gross,d}')::numeric=1000000*(m#>>'{gross,n}')::numeric
 AND (q#>>'{normalizedLog,takerAmountFilledRaw}')::numeric*(m#>>'{quantity,d}')::numeric=1000000*(m#>>'{quantity,n}')::numeric
 AND m->>'wallet'=scope.wallet AND m->>'side'='BUY' AND m->>'chainId'='137'
 AND m->>'matchingCount'='1' AND m->>'marketId'=ev->>'marketId' AND m->>'outcomeId'=ev->>'outcomeId'
 AND polygon_live_activity.hash_value(m->'transactionHash') AND (m->>'logIndex')::numeric>=0
 AND NOT EXISTS(SELECT FROM polygon_buy.personal_start_blocks ab WHERE ab.session_id=sid AND (fin->>'blockNumber')::bigint<=ab.block_number)
 AND fin->>'receiptStatus'='1' AND fin->>'canonicalBlockHash'=fin->>'blockHash'
 AND (fin->>'finalizedBlockNumber')::bigint >= (fin->>'blockNumber')::bigint
 AND (fin->>'checkedAtMs')::bigint >= (ev->>'firstSeenMs')::bigint
 AND (ev->>'firstSeenMs')::bigint >= (ev->>'signalAtMs')::bigint
 AND book->>'venue'='polymarket' AND book->>'market'=ev->>'marketId' AND book->>'token'=ev->>'outcomeId'
 AND (book->>'receivedAtMs')::bigint BETWEEN (fin->>'checkedAtMs')::bigint AND extract(epoch FROM now_at)*1000
 AND (book->>'receivedMonotonicNs')::numeric > (fin->>'checkedMonotonicNs')::numeric
 AND (book->>'receivedMonotonicNs')::numeric >= (evidence->>'waitStartedMonotonicNs')::numeric
 AND evidence->'finalityBeforeBook'='true'::jsonb AND jsonb_typeof(evidence->'sourceProof')='object'
 AND jsonb_array_length(est->'fills')=1 AND evidence->>'side'='BUY'
 AND evidence#>>'{policy,quantityStep}' ~ '^(0|1)([.][0-9]{1,12})?$'
 AND (evidence#>>'{policy,quantityStep}')::numeric>0
 AND mod((f#>>'{quantity,n}')::numeric,(f#>>'{quantity,d}')::numeric*(evidence#>>'{policy,quantityStep}')::numeric)=0
 AND evidence->'quantity'=f->'quantity' AND evidence->'cashFee'=f->'cashFee'
 AND live_buy_core.positive(f->'quantity') AND live_buy_core.positive(f->'price')
 AND live_buy_core.nonnegative(f->'cashFee') AND live_buy_core.cmp(f->'price',evidence->'priceLimit')<=0
 AND evidence->'gross'=live_buy_core.mulq(f->'quantity',f->'price')
 AND live_buy_core.cmp(live_buy_core.addq(evidence->'gross',f->'cashFee'),live_buy_core.q(st.fixed_n,st.fixed_d))<=0
 AND length(book->>'evidenceRef')>0 AND length(fin->>'rpcEvidenceRef')>0
 AND length(evidence#>>'{policy,evidenceRef}')>0
 AND ev#>>'{venueReceipt,source}' IN ('polymarket-data-api-maker-finalized-v1','polymarket-rtds-finalized-v1')
 ) IS DISTINCT FROM true THEN RAISE EXCEPTION 'quote incompatible or expired'; END IF;
 FOREACH k IN ARRAY ARRAY['reserveId','settleId','observationId','reserveCommandId','settleCommandId','intentId','fillId','confirmationId'] LOOP
  IF polygon_live_activity.uuid_value(q->k) IS DISTINCT FROM true THEN RAISE EXCEPTION 'invalid quote identity'; END IF;
 END LOOP;
 req:=jsonb_build_object('commandId',q->'reserveCommandId','intentId',q->'intentId',
 'observationId',q->'observationId','expectedVersion',q->'expectedVersion','conditionId',ev->'marketId',
 'tokenId',ev->'outcomeId','sizingRevisionId',st.id,'admissionRevisionId',st.id,
 'evidenceRef',ev#>'{venueReceipt,evidenceRef}','desiredNotional',evidence->'gross',
 'fullQuantity',f->'quantity','quantityStep',live_buy_core.q((evidence#>>'{policy,quantityStep}')::numeric*1000000000000,1000000000000),'priceCap',f->'price',
 'feeCashBound',f->'cashFee','delayMs','0');
 INSERT INTO polygon_buy.admissions VALUES((q->>'reserveId')::uuid,sid,a.run_id,'reserve',req,m->>'transactionHash',
 (q#>>'{normalizedLog,logIndex}')::numeric,ev->>'outcomeId',ev->>'marketId',evidence#>>'{policy,evidenceRef}',
 fin->>'rpcEvidenceRef',evidence#>>'{policy,evidenceRef}',book->>'evidenceRef',now_at,expires);
 INSERT INTO polygon_buy.verified_quotes VALUES(sid,eid,q,(q->>'reserveId')::uuid,(q->>'settleId')::uuid,now_at);
 RETURN jsonb_build_object('reserveId',q->'reserveId','observationId',q->'observationId');
END $fn$;
REVOKE ALL ON FUNCTION polygon.personal_quote_issue_v1(jsonb) FROM PUBLIC,polygon_executor;
-- Look up original results through the same worker guard used for financial writes.
CREATE FUNCTION polygon.personal_quote_lookup_v1(sid uuid,eid text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE access jsonb; cid uuid; result jsonb;
BEGIN
 access:=polygon_buy.writer(sid);
 IF (access->>'http') IS DISTINCT FROM '200' THEN RETURN access; END IF;
 SELECT (quote->>'settleCommandId')::uuid INTO cid FROM polygon_buy.verified_quotes
 WHERE session_id=sid AND execution_id=eid;
 result:=live_buy_core.lookup(sid,cid);
 IF result IS NULL THEN RETURN jsonb_build_object('http',202,'status','unknown'); END IF;
 RETURN jsonb_build_object('http',200,'result',result);
END $fn$;
REVOKE ALL ON FUNCTION polygon.personal_quote_lookup_v1(uuid,text) FROM PUBLIC,polygon_executor;
CREATE FUNCTION polygon.personal_quote_scope_v1(sid uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE access jsonb; body jsonb;
BEGIN
 access:=polygon_buy.writer(sid);
 IF access->>'http' IS DISTINCT FROM '200' THEN RETURN access; END IF;
 SELECT jsonb_build_object('sessionId',s.id,'runId',a.run_id,'streamId',a.stream_id,
 'settingsId',s.current_settings_revision_id,'wallet',a.owner_address,'baseline',st.baseline,
 'checkpoint',st.checkpoint,'armedAt',v00_session.utc(st.armed_at),'boundAt',v00_session.utc(b.bound_at),
 'version',s.version::text,'status',st.status,'lastOperationId',st.last_operation_id,
 'highWatermark',st.high_watermark::text,'lastObservedAt',v00_session.utc(st.last_observed_at),
 'personalStart',polygon_buy.start_receipt(sid),'fixedBudget',live_buy_core.q(r.fixed_n,r.fixed_d))
 INTO body FROM polygon.paper_sessions s
 JOIN polygon.user_session_slots sl ON (sl.user_id,sl.current_session_id)=(s.user_id,s.id)
 JOIN polygon_buy.issuer_scopes scope ON scope.session_id=s.id AND scope.settings_id=s.current_settings_revision_id
 JOIN polygon.settings_revisions r ON (r.id,r.session_id)=(scope.settings_id,s.id)
 JOIN polygon_live_activity.assignments a ON a.session_id=s.id AND a.user_id=s.user_id AND a.owner_address=scope.wallet
 JOIN polygon_live_activity.stream st ON st.session_id=s.id JOIN polygon_buy.bindings b ON b.session_id=s.id AND b.run_id=a.run_id
 WHERE s.id=sid AND s.lifecycle='active';
 IF body IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 RETURN jsonb_build_object('http',200,'result',body);
END $fn$;
REVOKE ALL ON FUNCTION polygon.personal_quote_scope_v1(uuid) FROM PUBLIC,polygon_executor;


-- Both accounting stages execute in this one worker transaction.
CREATE FUNCTION polygon.personal_quote_apply_v1(sid uuid,eid text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $fn$
DECLARE access jsonb; v polygon_buy.verified_quotes; ad polygon_buy.admissions;
 q jsonb; f jsonb; z jsonb:=live_buy_core.q(0,1); req jsonb; cmd uuid;
 settled jsonb; receipt jsonb; captured text; ob polygon_live_activity.observations;
 actual integer; auth_session polygon.paper_sessions; t timestamptz;
BEGIN
 access:=polygon.personal_quote_lookup_v1(sid,eid);
 IF access->>'http' IS DISTINCT FROM '202' THEN RETURN access; END IF;
 SELECT * INTO STRICT v FROM polygon_buy.verified_quotes WHERE session_id=sid AND execution_id=eid;
 SELECT * INTO STRICT ad FROM polygon_buy.admissions WHERE session_id=sid AND id=v.reserve_id;
 q:=v.quote; f:=q#>'{estimate,fills,0}';
 SELECT s.* INTO STRICT auth_session FROM polygon.paper_sessions s
 JOIN polygon.user_session_slots sl ON (sl.user_id,sl.current_session_id)=(s.user_id,s.id)
 JOIN polygon_live_activity.stream st ON st.session_id=s.id AND st.status='observing'
 WHERE s.id=sid AND s.lifecycle='active' AND s.current_settings_revision_id=(q->>'settingsId')::uuid
 AND polygon_live_activity.new_admission(s.id) FOR UPDATE OF s;
 SELECT * INTO STRICT ob FROM polygon_live_activity.observations WHERE session_id=sid AND id=(ad.request->>'observationId')::uuid
 AND transaction_hash=ad.transaction_hash AND log_index=ad.log_index AND classification='accepted'
 AND raw_log=q->'normalizedLog' AND sequence >= (SELECT first_sequence FROM polygon_buy.bindings WHERE session_id=sid);
 SELECT count(*) INTO actual FROM polygon_live_activity.decisions d JOIN polygon_live_activity.evaluations e
 ON (e.session_id,e.observation_id,e.decision_id)=(d.session_id,d.observation_id,d.id)
 WHERE d.session_id=sid AND d.observation_id=ob.id AND d.status='pending'
 AND d.policy_version='paper-buy-queued-v1' AND e.evidence->>'admissionId'=v.reserve_id::text;
 IF actual<>1 OR clock_timestamp()>=ad.expires_at THEN RAISE EXCEPTION 'admission unavailable'; END IF;
 IF EXISTS(SELECT FROM polygon_live_activity.decisions d JOIN polygon_buy.bindings b ON b.session_id=d.session_id
 WHERE d.session_id=sid AND d.sequence>=b.first_sequence AND d.sequence<ob.sequence
 AND d.policy_version='paper-buy-queued-v1' AND NOT EXISTS(SELECT FROM live_buy_core.intents i WHERE i.session_id=sid AND i.observation_id=d.observation_id))
 THEN RAISE EXCEPTION 'earlier observation awaiting decision'; END IF;
 cmd:=(ad.request->>'commandId')::uuid;
 PERFORM live_buy_core.reserve(sid,ad.request);
 INSERT INTO polygon_buy.commands VALUES(sid,cmd,ad.id,jsonb_build_object('session_id',sid,'request',ad.request,'admission_id',ad.id),'reserve');
 PERFORM polygon_buy.publish(sid,cmd);
 -- A virtual fill occurs at DB accounting time. Source and book timestamps
 -- remain verbatim in the quote. Round only the ledger timestamp to wire precision.
 t:=clock_timestamp();
 IF date_trunc('milliseconds',t)<(SELECT admitted_at FROM live_buy_core.intents WHERE session_id=sid AND id=(q->>'intentId')::uuid) THEN
   PERFORM pg_sleep(0.001); t:=clock_timestamp();
 END IF;
 captured:=to_char(t AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
 req:=jsonb_build_object('commandId',q->'settleCommandId','intentId',q->'intentId',
 'expectedVersion',((q->>'expectedVersion')::bigint+1)::text,'evidenceRef',ad.request->'evidenceRef',
 'confirmationId',q->'confirmationId','fills',jsonb_build_array(jsonb_build_object('fillId',q->'fillId',
 'price',f->'price','quantityGross',f->'quantity','quantityFee',z,'cashFee',f->'cashFee','executedAt',captured)));
 INSERT INTO polygon_buy.admissions VALUES(v.settle_id,sid,ad.run_id,'settle',req,ad.transaction_hash,ad.log_index,
 ad.token_id,ad.condition_id,ad.profile_ref,ad.clock_ref,ad.fee_ref,ad.book_ref,ad.issued_at,ad.expires_at);
 settled:=live_buy_core.settle(sid,req); cmd:=(q->>'settleCommandId')::uuid;
 INSERT INTO polygon_buy.commands VALUES(sid,cmd,v.settle_id,jsonb_build_object('session_id',sid,'request',req,'admission_id',v.settle_id),'settle');
 PERFORM polygon_buy.publish(sid,cmd);
 IF clock_timestamp()>=ad.expires_at THEN RAISE EXCEPTION 'quote expired during accounting'; END IF;
 RETURN jsonb_build_object('http',200,'result',settled);
END $fn$;
REVOKE ALL ON FUNCTION polygon.personal_quote_apply_v1(uuid,text) FROM PUBLIC,polygon_executor;


-- The admitted gross can be below the budget after price/quantity rounding.
-- Preserve the old invariant for every historical command.
CREATE FUNCTION polygon_buy.admitted_notional(sid uuid,oid uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT coalesce((SELECT v.quote#>'{estimate,evidence,gross}' FROM polygon_buy.verified_quotes v
 JOIN polygon_buy.admissions a ON a.id=v.reserve_id AND a.session_id=v.session_id
 WHERE v.session_id=sid AND a.request->>'observationId'=oid::text),
 polygon_buy.sized_notional(sid,oid))
$$;
DO $patch$
DECLARE d text; needle text; replacement text;
BEGIN
 d:=pg_get_functiondef('polygon_buy.command_valid(uuid)'::regprocedure);
 needle:='polygon_buy.sized_notional(sid,ob.id)';
 IF cardinality(string_to_array(d,needle))<>2 THEN RAISE EXCEPTION 'unknown command integrity shape'; END IF;
 EXECUTE replace(d,needle,'polygon_buy.admitted_notional(sid,ob.id)');
 d:=pg_get_functiondef('polygon_live_activity.role_valid(oid)'::regprocedure);
 needle:='to_regprocedure(''polygon.live_buy_lookup_v1(jsonb)''))';
 replacement:='to_regprocedure(''polygon.live_buy_lookup_v1(jsonb)''),to_regprocedure(''polygon.personal_quote_scope_v1(uuid)''),to_regprocedure(''polygon.personal_quote_apply_v1(uuid,text)''),to_regprocedure(''polygon.personal_quote_lookup_v1(uuid,text)''))';
 IF cardinality(string_to_array(d,needle))<>2 THEN RAISE EXCEPTION 'unknown role validation shape'; END IF;
 EXECUTE replace(d,needle,replacement);
END $patch$;
-- Fail a transaction whose accepted personal observation was never materialized.
CREATE FUNCTION polygon_buy.check_atomic_apply() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.policy_version='paper-buy-queued-v1' AND EXISTS(
 SELECT FROM polygon_buy.verified_quotes v WHERE v.session_id=NEW.session_id
 AND v.quote->>'observationId'=NEW.observation_id::text
 AND NOT EXISTS(SELECT FROM live_buy_core.receipts r WHERE r.session_id=NEW.session_id AND r.kind='settle'
 AND r.command_id=(v.quote->>'settleCommandId')::uuid))
 THEN RAISE EXCEPTION 'accepted personal buy missing financial commit'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER personal_atomic_fill AFTER INSERT ON polygon_live_activity.decisions
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_buy.check_atomic_apply();


SET CONSTRAINTS ALL IMMEDIATE; COMMIT;
