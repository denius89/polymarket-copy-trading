-- Cut repeated work in the pinned closed Polygon history validator.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';
SELECT set_config('cct.range_closed_session', :'expected_closed_session'::uuid::text, true) AS closed_session,
       set_config('cct.range_closed_operation', :'expected_closed_operation'::uuid::text, true) AS closed_operation
\gset

SET LOCAL ROLE polygon_owner;
DO $patch$
DECLARE
    sid constant uuid := current_setting('cct.range_closed_session')::uuid;
    op constant uuid := current_setting('cct.range_closed_operation')::uuid;
    definition text := pg_get_functiondef('polygon_live_activity.state_valid(uuid)'::regprocedure);
    old_declaration constant text := 'DECLARE history_row record;';
    old_loop constant text := 'FOR history_row IN';
    old_anchor constant text := $old$COALESCE((
          SELECT fresh_segment.next_checkpoint->'hash'
          FROM polygon_buy.closed_fresh_segments fresh_segment
          JOIN polygon_live_activity.operations fresh_start
            ON (fresh_start.session_id,fresh_start.id)=(fresh_segment.session_id,fresh_segment.operation_id)
          WHERE fresh_segment.session_id=sid AND fresh_start.ordinal<o.ordinal
        ),(
          SELECT polygon_buy.coverage_gap(sid)#>'{through,hash}'
          FROM polygon_buy.segment_starts g JOIN polygon_live_activity.operations start
             ON (start.session_id,start.id)=(g.session_id,g.operation_id)
          WHERE g.session_id=sid AND start.ordinal<o.ordinal
        ),st.baseline->'hash')$old$;
    old_checks constant text := 'FOR checked_row IN';
    old_count constant text := 'END LOOP;' || chr(10) || '   IF history_row.observations<>ac+ex';
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM polygon_buy.closed_fresh_segments
                      WHERE session_id = sid AND operation_id = op)
       OR md5(definition) IS DISTINCT FROM '7fca5c55bc68bdef1b68d2f3b6d8c6d0'
       OR strpos(definition, format('IF sid=%L::uuid THEN', sid)) = 0
       OR cardinality(string_to_array(definition, old_declaration)) <> 2
       OR cardinality(string_to_array(definition, old_loop)) <> 2
       OR cardinality(string_to_array(definition, old_anchor)) <> 2
       OR cardinality(string_to_array(definition, old_checks)) <> 2
       OR cardinality(string_to_array(definition, old_count)) <> 2
       OR EXISTS (
           SELECT FROM unnest(ARRAY['polygon_buy.closed_fresh_segments'::regclass,
                                    'polygon_buy.segment_starts'::regclass]) AS anchors(relation)
           WHERE NOT EXISTS (
               SELECT FROM pg_constraint c JOIN pg_attribute a ON a.attrelid = c.conrelid
               WHERE c.conrelid = anchors.relation AND c.contype = 'p'
                 AND c.conkey = ARRAY[a.attnum] AND a.attname = 'session_id'
           )
       )
    THEN RAISE EXCEPTION 'Expected the isolated Polygon history implementation'; END IF;

    definition := replace(definition, old_declaration, old_declaration ||
      ' fresh_ordinal bigint; fresh_hash jsonb; personal_ordinal bigint; personal_hash jsonb;');
    definition := replace(definition, old_loop, format($new$
 IF sid=%L::uuid THEN
    SELECT start.ordinal, segment.next_checkpoint->'hash' INTO fresh_ordinal, fresh_hash
    FROM polygon_buy.closed_fresh_segments segment
    JOIN polygon_live_activity.operations start
      ON (start.session_id,start.id)=(segment.session_id,segment.operation_id)
    WHERE segment.session_id=sid;
    SELECT start.ordinal, polygon_buy.coverage_gap(sid)#>'{through,hash}' INTO personal_ordinal, personal_hash
    FROM polygon_buy.segment_starts segment
    JOIN polygon_live_activity.operations start
      ON (start.session_id,start.id)=(segment.session_id,segment.operation_id)
    WHERE segment.session_id=sid;
 END IF;
 %s$new$, sid, old_loop));
    definition := replace(definition, old_anchor, format($new$(CASE WHEN sid=%L::uuid THEN COALESCE(
          CASE WHEN fresh_ordinal<o.ordinal THEN fresh_hash END,
          CASE WHEN personal_ordinal<o.ordinal THEN personal_hash END, st.baseline->'hash')
        ELSE %s END)$new$, sid, old_anchor));

    -- jsonb_array_elements('[]') has no rows. Keep the counts and receipt check
    -- outside the branch, including detection of an unexpected observation.
    definition := replace(definition, old_checks,
       format('IF sid<>%L::uuid OR o.request->''logs'' IS DISTINCT FROM ''[]''::jsonb THEN', sid)
       || chr(10) || '   ' || old_checks);
    definition := replace(definition, old_count,
       'END LOOP;' || chr(10) || '   END IF;' || chr(10) || '   IF history_row.observations<>ac+ex');
    EXECUTE definition;
END
$patch$;

COMMIT;
