-- Run as the operator in a separately verified closed database.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL search_path = pg_catalog;

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind='isolated-public-market-pilot-v1')
       OR NOT EXISTS (SELECT FROM polygon_live.installation
                      WHERE singleton AND database_name=current_database())
    THEN
        RAISE EXCEPTION 'Expected the closed app and delivery queue in one database';
    END IF;
END
$gate$;

GRANT USAGE ON SCHEMA demo_delivery TO polygon_owner;
GRANT SELECT, INSERT ON demo_delivery.traders, demo_delivery.start_receipts TO polygon_owner;
GRANT SELECT, INSERT ON demo_delivery.subscriptions TO polygon_owner;
-- SELECT FOR UPDATE in the existing subscribe routine requires one update privilege.
GRANT UPDATE (trader_key) ON demo_delivery.traders TO polygon_owner;
GRANT EXECUTE ON FUNCTION demo_delivery.subscribe(uuid,text,text),
    demo_delivery.current_app_traders(), demo_delivery.app_subscription_current(uuid)
    TO polygon_owner;

CREATE FUNCTION demo_delivery.consume_confirmed_starts() RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $observer$
DECLARE
    seat record;
    existing demo_delivery.subscriptions;
    subscribed integer:=0;
    conflicts integer:=0;
    capacity integer:=0;
BEGIN
    IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'Subscription changes require READ COMMITTED';
    END IF;
    -- Same lock order and keys as the existing venue checkout. Serialize the
    -- wallet capacity check and the matching subscription/receipt write.
    PERFORM pg_advisory_xact_lock(hashtextextended('isolated-public-market-pilot-v1:limitless',0));
    PERFORM pg_advisory_xact_lock(hashtextextended('isolated-public-market-pilot-v1:polymarket',0));

    FOR seat IN
        SELECT ev.id AS outbox_id,s.id AS session_id,t.current_revision_id AS revision_id,
               v.code AS venue,t.external_trader_id AS wallet
        FROM polygon.outbox_events ev
        JOIN polygon.command_receipts receipt ON (receipt.id,receipt.result_session_id)=(ev.receipt_id,ev.session_id)
        JOIN polygon.paper_sessions s ON (s.id,s.start_receipt_id,s.user_id)=(ev.session_id,ev.receipt_id,receipt.user_id)
        JOIN polygon.user_session_slots slot ON (slot.id,slot.user_id,slot.current_session_id)=(s.slot_id,s.user_id,s.id)
        JOIN polygon.traders t ON (t.id,t.source_id,t.venue_id,t.current_revision_id)=
                                  (s.trader_id,s.source_id,s.venue_id,s.trader_revision_id)
        JOIN polygon.catalog_sources source ON (source.id,source.venue_id)=(s.source_id,s.venue_id)
        JOIN polygon.venues v ON v.id=s.venue_id
        WHERE ev.kind='paper_session.started' AND ev.schema_version='v1'
          AND ev.consumer_name='paper_start_observer' AND ev.delivery_state='pending'
          AND ev.payload='{}'::jsonb AND receipt.command_type='C06' AND receipt.outcome='succeeded'
          AND s.lifecycle='active' AND s.evaluation_deadline_at>clock_timestamp()
          AND v.code IN ('polymarket','limitless') AND t.external_trader_id~'^0x[0-9a-f]{40}$'
          AND source.data_origin='public_api' AND source.paper_start_enabled AND t.paper_start_enabled
          AND polygon_live.source_admitted(s.user_id,s.source_id,s.trader_id,s.trader_revision_id,s.venue_id)
          AND NOT EXISTS (SELECT FROM demo_delivery.start_receipts done WHERE done.outbox_id=ev.id)
          AND (EXISTS (SELECT FROM demo_delivery.current_app_traders() a
                       WHERE (a.venue,a.trader_key)=(v.code,t.external_trader_id))
               OR (SELECT count(*) FROM demo_delivery.current_app_traders() a WHERE a.venue=v.code)<4)
        ORDER BY ev.created_at,ev.id
        LIMIT 64
        FOR SHARE OF slot,s,t,source SKIP LOCKED
    LOOP
        SELECT * INTO existing FROM demo_delivery.subscriptions WHERE session_id=seat.session_id;
        IF FOUND AND (existing.venue,existing.trader_key) IS DISTINCT FROM (seat.venue,seat.wallet) THEN
            conflicts:=conflicts+1;
            CONTINUE;
        END IF;
        IF NOT EXISTS (SELECT FROM demo_delivery.current_app_traders() a
                       WHERE (a.venue,a.trader_key)=(seat.venue,seat.wallet))
           AND (SELECT count(*) FROM demo_delivery.current_app_traders() a WHERE a.venue=seat.venue)>=4
        THEN
            capacity:=capacity+1;
            CONTINUE;
        END IF;
        INSERT INTO demo_delivery.traders VALUES(seat.venue,seat.wallet) ON CONFLICT DO NOTHING;
        PERFORM demo_delivery.subscribe(seat.session_id,seat.venue,seat.wallet);
        INSERT INTO demo_delivery.start_receipts(outbox_id,session_id,venue,wallet,trader_revision_id)
        VALUES(seat.outbox_id,seat.session_id,seat.venue,seat.wallet,seat.revision_id);
        subscribed:=subscribed+1;
    END LOOP;
    RETURN jsonb_build_object('subscribed',subscribed,'capacity',capacity,'conflicts',conflicts);
END
$observer$;

ALTER FUNCTION demo_delivery.consume_confirmed_starts() OWNER TO polygon_owner;
REVOKE ALL ON FUNCTION demo_delivery.consume_confirmed_starts() FROM PUBLIC,polygon_executor;
COMMIT;
