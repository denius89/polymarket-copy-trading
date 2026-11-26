-- Apply on the isolated database after the canonical Polygon waiting queue.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';
SELECT set_config('cct.expiry_closed_session', :'expected_closed_session'::uuid::text, true),
       set_config('cct.expiry_closed_operation', :'expected_closed_operation'::uuid::text, true);

DO $patch$
DECLARE
    target regprocedure;
    definition text;
    old_join text;
    keyed_join text;
    spec record;
    closed_session constant uuid := current_setting('cct.expiry_closed_session')::uuid;
    closed_operation constant uuid := current_setting('cct.expiry_closed_operation')::uuid;
    original text := pg_get_functiondef(to_regprocedure('demo_delivery.expire_next_polygon_job(uuid)'));
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind = 'isolated-public-market-pilot-v1')
       OR NOT EXISTS (SELECT FROM polygon_buy.closed_fresh_segments
                      WHERE session_id = closed_session AND operation_id = closed_operation)
       OR coalesce(strpos(original, closed_session::text), 0) = 0
       OR coalesce(strpos(original, closed_operation::text), 0) = 0
    THEN RAISE EXCEPTION 'Expected the isolated Polygon delivery queue'; END IF;

    -- Preserve the existing JSON proof check. Canonical payloads also carry
    -- these two keys, allowing the indexed lookup before comparing the proof.
    FOR spec IN SELECT * FROM (VALUES
        ('demo_delivery.expire_next_polygon_job(uuid)',
         'o.session_id=p_session AND o.raw_log=s.payload->''log''', 's.payload', 2),
        ('demo_delivery.closed_expire_one_after_guard(uuid)',
         'o.session_id=p_session AND o.raw_log=s.payload->''log''', 's.payload', 1),
        ('demo_delivery.closed_expiry_after_writer_guard(uuid,bigint,uuid,text)',
         'AND o.raw_log = s.payload->''log'' AND o.header = s.payload->''header''', 's.payload', 1)
    ) AS changes(signature, match, payload, appearances) LOOP
        target := to_regprocedure(spec.signature);
        definition := pg_get_functiondef(target);
        old_join := spec.match;
        IF definition IS NULL OR cardinality(string_to_array(definition, old_join)) <> spec.appearances + 1
        THEN RAISE EXCEPTION 'Unexpected closed expiry function: %', spec.signature; END IF;
        keyed_join := old_join || format($key$
              AND o.transaction_hash = %1$s#>>'{log,transactionHash}'
              AND o.log_index = CASE
                  WHEN %1$s#>>'{log,logIndex}' ~ '^(0|[1-9][0-9]{0,77})$'
                  THEN (%1$s#>>'{log,logIndex}')::numeric END$key$, spec.payload);
        EXECUTE replace(definition, old_join, keyed_join);
    END LOOP;
END
$patch$;

COMMIT;
