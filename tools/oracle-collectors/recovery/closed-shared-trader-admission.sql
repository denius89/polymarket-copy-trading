-- Apply inside one serializable transaction as the closed database operator.
-- Set shadow.closed_shared_trader_input locally on the same connection first.
DO $share$
DECLARE
    config jsonb := current_setting('shadow.closed_shared_trader_input', true)::jsonb;
    account jsonb;
    source record;
    scope_id uuid;
    added_admission int;
    added_visibility int;
    selected_sources int := 0;
BEGIN
    IF current_setting('transaction_isolation') <> 'serializable'
       OR polygon.exact_keys(config, ARRAY[
           'databaseName','databaseOid','systemIdentifier','runId','accounts']) IS DISTINCT FROM true
       OR config->>'databaseName' IS DISTINCT FROM current_database()
       OR config->>'databaseOid' IS DISTINCT FROM (
           SELECT oid::text FROM pg_database WHERE datname=current_database())
       OR config->>'systemIdentifier' IS DISTINCT FROM (
           SELECT system_identifier::text FROM pg_control_system())
       OR NOT EXISTS (
           SELECT FROM polygon_live.installation
           WHERE singleton AND database_name=current_database()
             AND operator_run_id::text=config->>'runId'
             AND profile='empty-completion-public-skip-v1')
       OR jsonb_typeof(config->'accounts') IS DISTINCT FROM 'array'
    THEN
        RAISE EXCEPTION 'closed dual catalog or transaction mismatch';
    END IF;

    IF jsonb_array_length(config->'accounts') <> 2 OR EXISTS (
        SELECT FROM jsonb_array_elements(config->'accounts') a(value)
        WHERE polygon.exact_keys(a.value,ARRAY['ownerId','currentSessionId']) IS DISTINCT FROM true
          OR polygon.uuid_text(a.value->>'ownerId') IS DISTINCT FROM true
          OR polygon.uuid_text(a.value->>'currentSessionId') IS DISTINCT FROM true
    ) THEN
        RAISE EXCEPTION 'two exact owner and current session pairs required';
    END IF;

    IF config#>>'{accounts,0,ownerId}'=config#>>'{accounts,1,ownerId}'
       OR config#>>'{accounts,0,currentSessionId}'=config#>>'{accounts,1,currentSessionId}'
    THEN
        RAISE EXCEPTION 'owners and sessions must be distinct';
    END IF;

    -- Lock both exact owners' slots and read scopes before changing either owner.
    FOR account IN SELECT value FROM jsonb_array_elements(config->'accounts')
                   ORDER BY value->>'ownerId'
    LOOP
        PERFORM FROM polygon.user_session_slots sl
        JOIN polygon.paper_sessions s ON (s.slot_id,s.id,s.user_id)=(sl.id,sl.current_session_id,sl.user_id)
        JOIN polygon.read_scopes rs ON rs.user_id=sl.user_id
        WHERE sl.user_id=(account->>'ownerId')::uuid
          AND s.id=(account->>'currentSessionId')::uuid
          AND s.lifecycle='active' AND s.evaluation_deadline_at>clock_timestamp()
        FOR UPDATE OF sl,rs;
        IF NOT FOUND THEN RAISE EXCEPTION 'input does not match an active closed session'; END IF;
    END LOOP;

    FOR source IN
        WITH pinned AS (
            SELECT 'polymarket' AS venue_code, p.source_id,p.venue_id,p.trader_id,p.revision_id,
                   p.database_name,p.operator_run_id,p.purpose
            FROM polygon_live.public_source p WHERE p.singleton
            UNION ALL
            SELECT 'limitless',p.source_id,p.venue_id,p.trader_id,p.revision_id,
                   p.database_name,p.operator_run_id,p.purpose
            FROM polygon_live.limitless_source p WHERE p.singleton
        )
        SELECT p.* FROM pinned p
        JOIN polygon.venues v ON (v.id,v.code)=(p.venue_id,p.venue_code)
        JOIN polygon.catalog_sources c ON (c.id,c.venue_id)=(p.source_id,p.venue_id)
        JOIN polygon.traders t ON (t.id,t.source_id,t.venue_id,t.current_revision_id)=
                                  (p.trader_id,p.source_id,p.venue_id,p.revision_id)
        WHERE p.database_name=current_database() AND p.operator_run_id::text=config->>'runId'
          AND p.purpose='empty_session_only'
          AND c.data_origin='public_api' AND c.paper_start_enabled AND t.paper_start_enabled
          AND EXISTS (
              SELECT FROM polygon_live.admissions a
              WHERE a.source_id=p.source_id
                AND a.user_id IN ((config#>>'{accounts,0,ownerId}')::uuid,
                                  (config#>>'{accounts,1,ownerId}')::uuid))
        ORDER BY p.venue_code
    LOOP
        selected_sources := selected_sources+1;
        FOR account IN SELECT value FROM jsonb_array_elements(config->'accounts')
                       ORDER BY value->>'ownerId'
        LOOP
            SELECT rs.id INTO STRICT scope_id FROM polygon.read_scopes rs
            WHERE rs.user_id=(account->>'ownerId')::uuid;

            INSERT INTO polygon_live.admissions(user_id,source_id)
            VALUES ((account->>'ownerId')::uuid,source.source_id) ON CONFLICT DO NOTHING;
            GET DIAGNOSTICS added_admission=ROW_COUNT;

            INSERT INTO polygon.scope_sources(scope_id,source_id)
            VALUES (scope_id,source.source_id) ON CONFLICT DO NOTHING;
            GET DIAGNOSTICS added_visibility=ROW_COUNT;

            IF added_admission+added_visibility>0 THEN
                UPDATE polygon.read_scopes rs SET revision=rs.revision+1 WHERE rs.id=scope_id;
            END IF;

            IF polygon_live.source_admitted((account->>'ownerId')::uuid,source.source_id,
                    source.trader_id,source.revision_id,source.venue_id) IS DISTINCT FROM true
            THEN
                RAISE EXCEPTION 'exact admitted profile verification failed';
            END IF;
        END LOOP;
    END LOOP;
    IF selected_sources<>2 THEN RAISE EXCEPTION 'both published closed venue sources required'; END IF;
END
$share$;
