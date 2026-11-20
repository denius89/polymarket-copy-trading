BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout = '3s';
SET LOCAL ROLE polygon_owner;
SET LOCAL search_path = pg_catalog;

-- Extend the already installed read-equivalent history fast path to the current Tradecraft demo.
DO $patch$
DECLARE
    tradecraft_id uuid;
    breakthebank_id uuid;
    definition text;
    previous text;
    revised text;
BEGIN
    SELECT session_id INTO STRICT tradecraft_id FROM polygon_buy.current_tradecraft_gap
    WHERE polygon_buy.tradecraft_gap_scope(session_id);
    SELECT session_id INTO STRICT breakthebank_id FROM polygon_buy.current_breakthebank_segment
    WHERE polygon_buy.decision_gap_scope(session_id);

    -- The complete bound check starts with the full state check and retains its existing locks.
    definition := pg_get_functiondef('polygon_live_activity.bound_state_valid(uuid)'::regprocedure);
    IF position('BEGIN'||chr(10)||' IF polygon_live_activity.state_valid(sid) IS DISTINCT FROM true THEN RETURN false;END IF;' IN definition)=0
    THEN RAISE EXCEPTION 'Bound validation no longer includes full history'; END IF;

    definition := pg_get_functiondef('polygon_live_activity.writer_guard(jsonb)'::regprocedure);
    previous := format('IF (s.id<>%L::uuid AND polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true)
 OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true', breakthebank_id);
    revised := format('IF (s.id NOT IN (%L::uuid,%L::uuid) AND polygon_live_activity.state_valid(s.id) IS DISTINCT FROM true)
 OR polygon_live_activity.bound_state_valid(s.id) IS DISTINCT FROM true', breakthebank_id, tradecraft_id);
    IF cardinality(string_to_array(definition, previous)) <> 2 THEN RAISE EXCEPTION 'Unexpected writer check'; END IF;
    EXECUTE replace(definition, previous, revised);

    definition := pg_get_functiondef('polygon_live_activity.inner_bound(jsonb)'::regprocedure);
    previous := format('b:=p->''ingest'';a:=polygon_live_activity.writer_guard(b);IF a->>''http''<>''200'' THEN RETURN a;END IF;
 IF (b->>''sessionId'')::uuid<>%L::uuid AND polygon_live_activity.bound_state_valid', breakthebank_id);
    revised := format('b:=p->''ingest'';a:=polygon_live_activity.writer_guard(b);IF a->>''http''<>''200'' THEN RETURN a;END IF;
 IF (b->>''sessionId'')::uuid NOT IN (%L::uuid,%L::uuid) AND polygon_live_activity.bound_state_valid', breakthebank_id, tradecraft_id);
    IF cardinality(string_to_array(definition, previous)) <> 2 THEN RAISE EXCEPTION 'Unexpected ingest check'; END IF;
    EXECUTE replace(definition, previous, revised);

    -- Existing fast path compares every header, parent, timestamp and the exact final header.
    definition := pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure);
    previous := format('IF sid=%L::uuid AND o.request->''logs''=''[]''::jsonb THEN', breakthebank_id);
    revised := format('IF sid IN (%L::uuid,%L::uuid) AND o.request->''logs''=''[]''::jsonb THEN', breakthebank_id, tradecraft_id);
    IF cardinality(string_to_array(definition, previous)) <> 2 THEN RAISE EXCEPTION 'Unexpected empty-range header check'; END IF;
    EXECUTE replace(definition, previous, revised);
END
$patch$;
COMMIT;
