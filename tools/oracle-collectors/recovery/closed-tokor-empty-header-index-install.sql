-- Optimize the unused header index for empty historical ranges only.
BEGIN;
SET LOCAL lock_timeout='2s';
SET LOCAL statement_timeout='8s';
SET LOCAL ROLE polygon_owner;
DO $patch$
DECLARE
    f constant regprocedure := 'polygon_live_activity.state_valid(uuid)'::regprocedure;
    body text := pg_get_functiondef(f);
    target constant text := 'f21854c017e20cbdf8ce34337953a3601f7695bf2ee0bcde048c6cd8af59b854';
BEGIN
    IF current_database() <> 'shadow_v00' OR NOT EXISTS (
        SELECT FROM polygon_live_activity.assignments
        WHERE session_id = '1c6d9f24-0f84-4a13-82f2-e712ff6919cf'
          AND owner_address = '0xa19cbababc312f9df185e49d7004c249ed1ade6b'
    ) THEN RAISE EXCEPTION 'closed Tokor session mismatch'; END IF;
    IF encode(sha256(convert_to(body,'UTF8')),'hex') = target THEN RETURN; END IF;
    IF encode(sha256(convert_to(body,'UTF8')),'hex') <> '34e77b26c5e1453afd8295fae38e41511775fba689b49ed55fb982fadff77c5b'
    THEN RAISE EXCEPTION 'closed history version mismatch'; END IF;
    body:=replace(replace(replace(replace(body, $val$heads jsonb;prior_seen jsonb;$val$, $val$heads jsonb;need_header_map boolean;header_deadline numeric;prior_seen jsonb;$val$), $val$   heads:='{}';prev:=cp;$val$, $val$   heads:='{}';prev:=cp;
   need_header_map:=(o.request->'logs') IS DISTINCT FROM '[]'::jsonb;
   header_deadline:=extract(epoch FROM (o.request->>'observedAt')::timestamptz);$val$), $val$     OR (h->>'timestampSeconds')::numeric>extract(epoch FROM (o.request->>'observedAt')::timestamptz) THEN RETURN false; END IF;$val$, $val$     OR (h->>'timestampSeconds')::numeric>header_deadline THEN RETURN false; END IF;$val$), $val$    heads:=heads||jsonb_build_object(h->>'number',h);prev:=polygon_live_activity.cp(h);$val$, $val$    -- Log validation looks up headers by block number. An empty log list
    -- has no lookups. Evaluate the original expression for a null key too,
    -- so a malformed header raises the same error in either case.
    IF need_header_map OR (h->>'number') IS NULL THEN
     heads:=heads||jsonb_build_object(h->>'number',h);
    END IF;
    prev:=polygon_live_activity.cp(h);$val$);
    IF encode(sha256(convert_to(body,'UTF8')),'hex') <> target
    THEN RAISE EXCEPTION 'history substitution mismatch'; END IF;
    EXECUTE body;
    IF encode(sha256(convert_to(pg_get_functiondef(f),'UTF8')),'hex') <> target
    THEN RAISE EXCEPTION 'installed history mismatch'; END IF;
END $patch$;
COMMIT;
