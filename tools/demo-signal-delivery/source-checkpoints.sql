-- Progress is separate from delivery leases. A source block and all jobs for it
-- commit together, so reconnecting cannot skip a partially published block.
CREATE TABLE demo_delivery.source_cursors (
    venue text NOT NULL,
    trader_key text NOT NULL,
    height bigint NOT NULL CHECK (height >= 0),
    block_hash text NOT NULL CHECK (block_hash ~ '^0x[0-9a-f]{64}$'),
    PRIMARY KEY (venue, trader_key),
    FOREIGN KEY (venue, trader_key) REFERENCES demo_delivery.traders(venue, trader_key)
);

CREATE TABLE demo_delivery.source_blocks (
    venue text NOT NULL,
    trader_key text NOT NULL,
    height bigint NOT NULL,
    block_hash text NOT NULL CHECK (block_hash ~ '^0x[0-9a-f]{64}$'),
    parent_hash text NOT NULL CHECK (parent_hash ~ '^0x[0-9a-f]{64}$'),
    events jsonb NOT NULL CHECK (jsonb_typeof(events) = 'array'),
    PRIMARY KEY (venue, trader_key, height),
    FOREIGN KEY (venue, trader_key) REFERENCES demo_delivery.source_cursors(venue, trader_key)
);

CREATE OR REPLACE FUNCTION demo_delivery.commit_source_block(
    p_venue text, p_trader text, p_height bigint, p_hash text, p_parent text, p_events jsonb
) RETURNS jsonb LANGUAGE plpgsql SET search_path = pg_catalog AS $$
DECLARE
    cursor_row demo_delivery.source_cursors;
    prior demo_delivery.source_blocks;
    stable_events jsonb;
    event jsonb;
    event_index bigint;
    last_index bigint := -1;
    count_enqueued bigint := 0;
    enqueued_now bigint;
    signal_now bigint;
BEGIN
    IF current_setting('transaction_isolation') <> 'read committed'
       OR p_height IS NULL OR p_height < 1
       OR p_hash !~ '^0x[0-9a-f]{64}$' OR p_parent !~ '^0x[0-9a-f]{64}$'
       OR p_hash IS NULL OR p_parent IS NULL
       OR jsonb_typeof(p_events) IS DISTINCT FROM 'array'
       OR jsonb_array_length(p_events) > 4096
       OR octet_length(p_events::text) > 8388608 THEN
        RAISE EXCEPTION 'Invalid source block';
    END IF;

    -- Lock in the same order as publish() and subscribe().
    PERFORM 1 FROM demo_delivery.traders
      WHERE (venue, trader_key) = (p_venue, p_trader) FOR UPDATE;
    SELECT * INTO cursor_row FROM demo_delivery.source_cursors
      WHERE (venue, trader_key) = (p_venue, p_trader) FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Source cursor is not initialized'; END IF;

    FOR event IN SELECT value FROM jsonb_array_elements(p_events) LOOP
        IF jsonb_typeof(event) IS DISTINCT FROM 'object'
           OR (event->>'logIndex' ~ '^(0|[1-9][0-9]{0,14})$') IS DISTINCT FROM true
           OR COALESCE(length(event->>'executionKey'),0) NOT BETWEEN 1 AND 256
           OR event->>'occurredAt' IS NULL OR event->>'firstReceivedAt' IS NULL OR event->>'expiresAt' IS NULL
           OR jsonb_typeof(event->'payload') IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'Invalid source event';
        END IF;
        event_index := (event->>'logIndex')::bigint;
        IF event_index <= last_index THEN RAISE EXCEPTION 'Source events are out of order'; END IF;
        last_index := event_index;
    END LOOP;
    IF (SELECT count(DISTINCT value->>'executionKey') FROM jsonb_array_elements(p_events)) <> jsonb_array_length(p_events)
    THEN RAISE EXCEPTION 'Duplicate execution in source block'; END IF;
    SELECT COALESCE(jsonb_agg(value - 'firstReceivedAt' ORDER BY ordinal), '[]'::jsonb) INTO stable_events
      FROM jsonb_array_elements(p_events) WITH ORDINALITY AS item(value,ordinal);

    IF p_height <= cursor_row.height THEN
        SELECT * INTO prior FROM demo_delivery.source_blocks
          WHERE (venue, trader_key, height) = (p_venue, p_trader, p_height);
        IF NOT FOUND OR ROW(prior.block_hash,prior.parent_hash,prior.events)
                        IS DISTINCT FROM ROW(p_hash,p_parent,stable_events)
        THEN RAISE EXCEPTION 'Conflicting source block replay'; END IF;
        RETURN jsonb_build_object('replayed',true,'height',cursor_row.height,'enqueued',0);
    END IF;
    IF p_height <> cursor_row.height + 1 OR p_parent <> cursor_row.block_hash
    THEN RAISE EXCEPTION 'Source checkpoint does not continue'; END IF;

    INSERT INTO demo_delivery.source_blocks VALUES (p_venue,p_trader,p_height,p_hash,p_parent,stable_events);
    FOR event IN SELECT value FROM jsonb_array_elements(p_events) LOOP
        SELECT published.signal_id,published.enqueued INTO STRICT signal_now,enqueued_now
          FROM demo_delivery.publish(p_venue,p_trader,event->>'executionKey',
               (event->>'occurredAt')::timestamptz,(event->>'firstReceivedAt')::timestamptz,
               (event->>'expiresAt')::timestamptz,event->'payload') published;
        count_enqueued := count_enqueued + enqueued_now;
        IF enqueued_now > 0 AND (event->>'expiresAt')::timestamptz <= clock_timestamp() THEN
            UPDATE demo_delivery.jobs SET finished_at=clock_timestamp(),finish_reason='expired'
                WHERE signal_id=signal_now;
        END IF;
    END LOOP;
    UPDATE demo_delivery.source_cursors SET height = p_height, block_hash = p_hash
      WHERE (venue, trader_key) = (p_venue, p_trader);
    RETURN jsonb_build_object('replayed',false,'height',p_height,'enqueued',count_enqueued);
END
$$;

REVOKE EXECUTE ON FUNCTION demo_delivery.commit_source_block(text,text,bigint,text,text,jsonb) FROM PUBLIC;
