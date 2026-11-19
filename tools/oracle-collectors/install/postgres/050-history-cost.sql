BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout='3s';
SET LOCAL ROLE polygon_owner;
SET LOCAL search_path=pg_catalog;
DO $patch$
DECLARE sid uuid; d text; n text; until_marker text; old_loop text;
BEGIN
 SELECT session_id INTO STRICT sid FROM polygon_buy.current_breakthebank_segment WHERE polygon_buy.decision_gap_scope(session_id);
 -- bound_state_valid performs this exact state_valid check first. Keep the
 -- entire bound check, receipt check, authorization, and row locks.
 d:=pg_get_functiondef('polygon_live_activity.bound_state_valid(uuid)'::regprocedure);
 IF position('BEGIN'||chr(10)||' IF polygon_live_activity.state_valid(sid) IS DISTINCT FROM true THEN RETURN false;END IF;' IN d)=0
 THEN RAISE EXCEPTION 'bound check no longer implies state check'; END IF;
 d:=pg_get_functiondef('polygon_live_activity.writer_guard(jsonb)'::regprocedure);
 n:='IF polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true
 OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'writer check changed'; END IF;
 EXECUTE replace(d,n,format('IF (s.id<>%L::uuid AND polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true)
 OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true',sid));
 d:=pg_get_functiondef('polygon_live_activity.inner_bound(jsonb)'::regprocedure);
 n:='b:=p->''ingest'';a:=polygon_live_activity.writer_guard(b);IF a->>''http''<>''200'' THEN RETURN a;END IF;
 IF polygon_live_activity.bound_state_valid((b->>''sessionId'')::uuid) IS DISTINCT FROM true';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'ingest precheck changed'; END IF;
 EXECUTE replace(d,n,replace(n,'IF polygon_live_activity.bound_state_valid',format('IF (b->>''sessionId'')::uuid<>%L::uuid AND polygon_live_activity.bound_state_valid',sid)));

 -- A successful empty range has no observations needing random header lookup.
 -- Check EVERY header in order, including its height, parent and timestamp,
 -- plus the exact final header. All remaining replay checks are shared.
 d:=pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure);
 n:='   heads:=''{}'';prev:=cp;';
 until_marker:='   prior_seen:=''{}'';ac:=0;ex:=0;du:=0;';
 IF cardinality(string_to_array(d,n))<>2 OR cardinality(string_to_array(d,until_marker))<>2 THEN RAISE EXCEPTION 'history loop changed'; END IF;
 old_loop:=n||split_part(split_part(d,n,2),until_marker,1);
 IF old_loop<>$old$   heads:='{}';prev:=cp;
   FOR h IN SELECT value FROM jsonb_array_elements(o.request->'headers') LOOP
    IF (h->>'number')::numeric<>(prev->>'number')::numeric+1 OR h->'parentHash' IS DISTINCT FROM prev->'hash'
     OR (h->>'timestampSeconds')::numeric>extract(epoch FROM (o.request->>'observedAt')::timestamptz) THEN RETURN false; END IF;
    heads:=heads||jsonb_build_object(h->>'number',h);prev:=polygon_live_activity.cp(h);
   END LOOP;
   IF h IS DISTINCT FROM o.request->'finalized' THEN RETURN false; END IF;
$old$ THEN RAISE EXCEPTION 'historical header rules changed'; END IF;
 n:='DECLARE i polygon_live_activity.assignments;';
 IF cardinality(string_to_array(d,n))<>2 THEN RAISE EXCEPTION 'history declaration changed'; END IF;
 d:=replace(d,n,'DECLARE base_number numeric; observed_epoch numeric; i polygon_live_activity.assignments;');
 EXECUTE replace(d,old_loop,format($fast$   IF sid=%L::uuid AND o.request->'logs'='[]'::jsonb THEN
    base_number:=(cp->>'number')::numeric;
    observed_epoch:=extract(epoch FROM (o.request->>'observedAt')::timestamptz);
    IF (o.request->'headers'->-1) IS DISTINCT FROM o.request->'finalized' OR EXISTS(
     SELECT FROM (
      SELECT value AS hdr, ord, lag(value->'hash',1,cp->'hash') OVER (ORDER BY ord) AS parent
      FROM jsonb_array_elements(o.request->'headers') WITH ORDINALITY AS src(value,ord)
     ) seq WHERE (hdr->>'number')::numeric<>base_number+ord
     OR hdr->'parentHash' IS DISTINCT FROM parent
     OR (hdr->>'timestampSeconds')::numeric>observed_epoch
    ) THEN RETURN false; END IF;
   ELSE
$fast$,sid)||old_loop||'   END IF;'||chr(10));
END $patch$;
COMMIT;
