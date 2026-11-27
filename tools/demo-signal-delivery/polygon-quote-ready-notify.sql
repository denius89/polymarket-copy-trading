-- Notify after the waiting observation has committed and can be claimed.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind = 'isolated-public-market-pilot-v1')
    THEN RAISE EXCEPTION 'Expected the isolated Polygon delivery queue'; END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.notify_polygon_quote_ready()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $notify$
BEGIN
    PERFORM pg_notify('demo_delivery_ready', '');
    RETURN NULL;
END
$notify$;

CREATE TRIGGER notify_polygon_quote_ready
    AFTER INSERT ON polygon_live_activity.decisions
    FOR EACH ROW WHEN (
        NEW.status = 'pending' AND NEW.checks->>'executionAdmission' = 'awaiting_quote'
    )
    EXECUTE FUNCTION demo_delivery.notify_polygon_quote_ready();

REVOKE ALL ON FUNCTION demo_delivery.notify_polygon_quote_ready() FROM PUBLIC;
COMMIT;
