-- Only the isolated observer consumes demo starts. Keep the original outbox immutable.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM demo_delivery.pilot_marker WHERE kind='isolated-public-market-pilot-v1')
     OR to_regclass('polygon.outbox_events') IS NULL THEN
    RAISE EXCEPTION 'Expected the isolated app and source pilot in one database';
  END IF;
END
$$;
CREATE TABLE IF NOT EXISTS demo_delivery.start_receipts (
    outbox_id uuid PRIMARY KEY REFERENCES polygon.outbox_events(id),
    session_id uuid NOT NULL UNIQUE REFERENCES demo_delivery.subscriptions(session_id),
    venue text NOT NULL,
    wallet text NOT NULL CHECK(wallet ~ '^0x[0-9a-f]{40}$'),
    trader_revision_id uuid NOT NULL,
    FOREIGN KEY (venue,wallet) REFERENCES demo_delivery.traders(venue,trader_key)
);

CREATE OR REPLACE FUNCTION demo_delivery.app_subscription_current(p_session_id uuid)
RETURNS boolean LANGUAGE sql VOLATILE SET search_path=pg_catalog AS $$
  SELECT NOT EXISTS (SELECT FROM demo_delivery.start_receipts WHERE session_id=p_session_id)
    OR EXISTS (
      SELECT FROM polygon.paper_sessions s
        JOIN polygon.user_session_slots sl
          ON (sl.id,sl.user_id,sl.current_session_id)=(s.slot_id,s.user_id,s.id)
      WHERE s.id=p_session_id AND s.lifecycle='active'
        AND s.evaluation_deadline_at>clock_timestamp()
    )
$$;

CREATE OR REPLACE FUNCTION demo_delivery.current_app_traders()
RETURNS TABLE(venue text, trader_key text)
LANGUAGE sql VOLATILE SET search_path=pg_catalog AS $$
  SELECT DISTINCT s.venue,s.trader_key
    FROM demo_delivery.subscriptions s
   WHERE s.trader_key ~ '^0x[0-9a-f]{40}$'
     AND demo_delivery.app_subscription_current(s.session_id)
$$;

CREATE OR REPLACE FUNCTION demo_delivery.ignore_inactive_app_job()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
  IF demo_delivery.app_subscription_current(NEW.session_id) THEN RETURN NEW; END IF;
  RETURN NULL;
END
$$;

CREATE OR REPLACE TRIGGER active_app_subscription
BEFORE INSERT ON demo_delivery.jobs FOR EACH ROW
EXECUTE FUNCTION demo_delivery.ignore_inactive_app_job();

REVOKE ALL ON FUNCTION demo_delivery.app_subscription_current(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION demo_delivery.current_app_traders() FROM PUBLIC;
REVOKE ALL ON FUNCTION demo_delivery.ignore_inactive_app_job() FROM PUBLIC;
