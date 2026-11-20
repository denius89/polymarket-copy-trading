-- Local private component, not an installer for the live application.
CREATE SCHEMA live_buy_core;
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
