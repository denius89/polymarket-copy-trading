CREATE TABLE polygon_live_activity.calls(
 session_id uuid NOT NULL,operation_id uuid NOT NULL,kind text NOT NULL CHECK(kind IN('arm','ingest','stop')),
 wrapper jsonb NOT NULL,wrapper_digest text NOT NULL,created_at timestamptz NOT NULL,
 PRIMARY KEY(session_id,operation_id),
 FOREIGN KEY(operation_id,session_id) REFERENCES polygon_live_activity.operations(id,session_id) DEFERRABLE INITIALLY DEFERRED,
 CHECK(polygon.exact_keys(wrapper,ARRAY['session_id','request']) AND wrapper->>'session_id'=session_id::text),
 CHECK(wrapper_digest=polygon_live_activity.digest(kind||chr(10)||wrapper::text))
);
CREATE TRIGGER immutable_call BEFORE UPDATE OR DELETE ON polygon_live_activity.calls FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE FUNCTION polygon_live_activity.calls_valid(sid uuid) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE o polygon_live_activity.operations;c polygon_live_activity.calls;b polygon_live_activity.bound_requests;
BEGIN
 FOR o IN SELECT * FROM polygon_live_activity.operations WHERE session_id=sid LOOP
  SELECT * INTO c FROM polygon_live_activity.calls WHERE session_id=sid AND operation_id=o.id;
  IF c.operation_id IS NULL OR c.kind<>o.kind OR c.created_at<>o.created_at THEN RETURN false; END IF;
  IF o.kind='ingest' THEN
   SELECT * INTO b FROM polygon_live_activity.bound_requests WHERE session_id=sid AND operation_id=o.id;
   IF b.operation_id IS NULL OR c.wrapper->'request' IS DISTINCT FROM b.request THEN RETURN false; END IF;
  ELSIF c.wrapper->'request' IS DISTINCT FROM o.request THEN RETURN false; END IF;
 END LOOP;
 RETURN NOT EXISTS(SELECT FROM polygon_live_activity.calls call_row WHERE call_row.session_id=sid AND NOT EXISTS(
 SELECT FROM polygon_live_activity.operations op_row WHERE op_row.session_id=sid AND op_row.id=call_row.operation_id));
END $$;
CREATE FUNCTION polygon_live_activity.assert_calls() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF polygon_live_activity.calls_valid(COALESCE(NEW.session_id,OLD.session_id)) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'missing immutable scoped request' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER complete_call AFTER INSERT OR UPDATE OR DELETE ON polygon_live_activity.calls
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_live_activity.assert_calls();
CREATE CONSTRAINT TRIGGER complete_call AFTER INSERT OR UPDATE OR DELETE ON polygon_live_activity.operations
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION polygon_live_activity.assert_calls();
CREATE FUNCTION polygon_live_activity.dispatch(p jsonb,k text) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE b jsonb;a jsonb;sid uuid;op uuid;c polygon_live_activity.calls;o polygon_live_activity.operations;
BEGIN
 IF polygon.exact_keys(p,ARRAY['session_id','request']) IS DISTINCT FROM true
 OR polygon_live_activity.uuid_value(p->'session_id') IS DISTINCT FROM true OR octet_length(p::text)>4194304
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 b:=CASE WHEN k='ingest' THEN p#>'{request,ingest}' ELSE p->'request' END;
 IF polygon_live_activity.request_shape(b,k) IS DISTINCT FROM true OR p->>'session_id' IS DISTINCT FROM b->>'sessionId'
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 sid:=(p->>'session_id')::uuid;op:=(b->>'operationId')::uuid;
 a:=polygon_live_activity.writer_guard(b);IF a->>'http'<>'200' THEN RETURN a; END IF;
 IF k='lookup' THEN RETURN polygon_live_activity.inner_lookup(b); END IF;
 SELECT * INTO c FROM polygon_live_activity.calls WHERE session_id=sid AND operation_id=op;
 IF FOUND THEN
  IF c.kind<>k OR c.wrapper IS DISTINCT FROM p THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409); END IF;
  SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=sid AND id=op;
  RETURN jsonb_build_object('http',200,'result',o.result);
 END IF;
 CASE k
 WHEN 'arm' THEN a:=polygon_live_activity.inner_arm(b);
 WHEN 'ingest' THEN a:=polygon_live_activity.inner_bound(p->'request');
 WHEN 'stop' THEN a:=polygon_live_activity.inner_stop(b);
 ELSE RETURN polygon.err('INVALID_REQUEST',400);
 END CASE;
 IF a->>'http'='200' THEN
  SELECT * INTO STRICT o FROM polygon_live_activity.operations WHERE session_id=sid AND id=op;
  INSERT INTO polygon_live_activity.calls VALUES(sid,op,k,p,polygon_live_activity.digest(k||chr(10)||p::text),o.created_at);
 END IF;
 RETURN a;
END $$;
CREATE FUNCTION polygon.live_activity_arm(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_live_activity.dispatch(p,'arm') $$;
CREATE FUNCTION polygon.live_activity_ingest(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_live_activity.dispatch(p,'ingest') $$;
CREATE FUNCTION polygon.live_activity_lookup(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_live_activity.dispatch(p,'lookup') $$;
CREATE FUNCTION polygon.live_activity_stop(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$ SELECT polygon_live_activity.dispatch(p,'stop') $$;
