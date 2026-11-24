-- Operator-only attachment of an already authorised observing session to an existing source.
-- In a SERIALIZABLE transaction, set demo_delivery.attach_config locally to the approved
-- cluster, two current session UUIDs, wallet, and cutoff. Never create or move a source cursor.
DO $attach$
DECLARE
    cfg jsonb := current_setting('demo_delivery.attach_config', true)::jsonb;
    source_session_id uuid := (cfg->>'source')::uuid;
    target_session_id uuid := (cfg->>'target')::uuid;
    expected_wallet text := cfg->>'wallet';
    cutoff timestamptz := (cfg->>'cutoff')::timestamptz;
    seed demo_delivery.closed_polygon_source;
    target polygon_live_activity.assignments;
    stream polygon_live_activity.stream;
    cursor demo_delivery.source_cursors;
BEGIN
    IF current_database() <> 'shadow_v00'
       OR (SELECT system_identifier::text FROM pg_control_system()) IS DISTINCT FROM cfg->>'cluster'
       OR current_setting('transaction_isolation') <> 'serializable'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker WHERE kind='isolated-public-market-pilot-v1')
       OR target_session_id IS NULL OR source_session_id IS NULL OR source_session_id=target_session_id OR expected_wallet IS NULL
       OR cutoff IS NULL OR cutoff <= clock_timestamp()
    THEN RAISE EXCEPTION 'Invalid closed dual enrollment'; END IF;
    SELECT x.* INTO STRICT seed FROM demo_delivery.closed_polygon_source x
    JOIN polygon_live_activity.assignments a
      ON (a.session_id,a.run_id,a.writer_oid,a.owner_address)=(x.session_id,x.run_id,x.writer_oid,x.wallet)
    JOIN polygon.paper_sessions p ON p.id=x.session_id AND p.lifecycle='active'
    JOIN polygon.user_session_slots sl ON (sl.user_id,sl.current_session_id)=(p.user_id,p.id)
    JOIN polygon_live_activity.stream st ON st.session_id=p.id AND st.status='observing'
    WHERE x.session_id=source_session_id AND x.wallet=expected_wallet AND x.cutoff_at>=cutoff
      AND a.database_name=current_database() AND polygon_live_activity.role_valid(a.writer_oid);
    SELECT a.* INTO STRICT target FROM polygon_live_activity.assignments a
    JOIN polygon.paper_sessions p ON (p.id,p.user_id,p.trader_id,p.trader_revision_id)=
                                    (a.session_id,a.user_id,a.trader_id,a.revision_id)
    JOIN polygon.user_session_slots sl ON (sl.user_id,sl.current_session_id)=(p.user_id,p.id)
    JOIN polygon_buy.issuer_scopes i ON (i.session_id,i.wallet,i.settings_id)=
                                      (p.id,a.owner_address,p.current_settings_revision_id)
    JOIN polygon_buy.bindings b ON (b.session_id,b.run_id)=(p.id,a.run_id)
    WHERE a.session_id=target_session_id AND a.run_id=seed.run_id AND a.owner_address=seed.wallet
      AND a.database_name=current_database() AND p.lifecycle='active' AND a.writer_oid<>seed.writer_oid
      AND a.user_id<>(SELECT user_id FROM polygon.paper_sessions WHERE id=seed.session_id)
      AND polygon_live_activity.role_valid(a.writer_oid)
    FOR UPDATE OF sl,p;
    IF has_function_privilege(target.writer_oid,
        'demo_delivery.publish_closed_polygon_range(uuid,jsonb)', 'EXECUTE')
    THEN RAISE EXCEPTION 'Subscriber writer already has permission to publish'
        USING ERRCODE='42501'; END IF;
    SELECT * INTO STRICT stream FROM polygon_live_activity.stream WHERE session_id=target_session_id
        AND status='observing' FOR UPDATE;
    SELECT * INTO STRICT cursor FROM demo_delivery.source_cursors WHERE venue='polymarket'
        AND trader_key=seed.wallet FOR UPDATE;
    IF stream.checkpoint IS DISTINCT FROM jsonb_build_object('number',cursor.height::text,'hash',cursor.block_hash)
    THEN RAISE EXCEPTION 'Subscriber checkpoint differs from shared source cursor'; END IF;
    INSERT INTO demo_delivery.subscriptions VALUES (target_session_id,'polymarket',seed.wallet,stream.armed_at);
    INSERT INTO demo_delivery.closed_polygon_source VALUES (target_session_id,target.run_id,target.writer_oid,seed.wallet,cutoff);
    INSERT INTO demo_delivery.session_writers VALUES (target_session_id,target.writer_oid);
    EXECUTE format('GRANT USAGE ON SCHEMA demo_delivery TO %I',target.writer_role);
    EXECUTE format('GRANT EXECUTE ON FUNCTION demo_delivery.closed_polygon_scope(uuid),
       demo_delivery.read_polygon_buy_head(uuid,bigint),demo_delivery.polygon_waiting_evaluations(uuid,jsonb),
       demo_delivery.claim_polygon_quote(uuid,jsonb),demo_delivery.acknowledge_polygon_result(bigint,uuid,uuid),
       demo_delivery.expire_next_polygon_job(uuid),demo_delivery.complete_polygon_refusal(uuid,bigint,uuid,text),
       demo_delivery.reconcile_closed_polygon_results(uuid,bigint,bigint) TO %I',target.writer_role);
END
$attach$;
