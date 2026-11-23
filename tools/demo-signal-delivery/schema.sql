-- Isolated PostgreSQL prototype. Run in a dedicated database.
CREATE SCHEMA demo_delivery;
REVOKE ALL ON SCHEMA demo_delivery FROM PUBLIC;

CREATE TABLE demo_delivery.traders (
    venue text NOT NULL CHECK (venue IN ('polymarket', 'limitless')),
    trader_key text NOT NULL CHECK (length(trader_key) BETWEEN 1 AND 256),
    PRIMARY KEY (venue, trader_key)
);

CREATE TABLE demo_delivery.subscriptions (
    session_id uuid PRIMARY KEY,
    venue text NOT NULL,
    trader_key text NOT NULL,
    active_from timestamptz NOT NULL,
    FOREIGN KEY (venue, trader_key) REFERENCES demo_delivery.traders
);
CREATE INDEX subscriptions_by_trader
    ON demo_delivery.subscriptions (venue, trader_key, active_from);

CREATE TABLE demo_delivery.session_writers (
    session_id uuid PRIMARY KEY REFERENCES demo_delivery.subscriptions,
    writer_oid oid NOT NULL
);

CREATE TABLE demo_delivery.signals (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    venue text NOT NULL,
    trader_key text NOT NULL,
    execution_key text NOT NULL CHECK (length(execution_key) BETWEEN 1 AND 256),
    occurred_at timestamptz NOT NULL,
    first_received_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK (expires_at >= occurred_at),
    stored_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object' AND octet_length(payload::text) <= 16384),
    UNIQUE (venue, trader_key, execution_key),
    FOREIGN KEY (venue, trader_key) REFERENCES demo_delivery.traders
);

CREATE TABLE demo_delivery.jobs (
    signal_id bigint NOT NULL REFERENCES demo_delivery.signals,
    session_id uuid NOT NULL REFERENCES demo_delivery.subscriptions,
    lease_token uuid,
    lease_until timestamptz,
    finished_at timestamptz,
    finish_reason text CHECK (finish_reason IN ('acknowledged', 'expired')),
    PRIMARY KEY (signal_id, session_id),
    CHECK ((lease_token IS NULL) = (lease_until IS NULL)),
    CHECK ((finished_at IS NULL) = (finish_reason IS NULL)),
    CHECK (finished_at IS NULL OR lease_token IS NULL)
);
CREATE INDEX pending_jobs_by_session
    ON demo_delivery.jobs (session_id, signal_id) WHERE finished_at IS NULL;
CREATE INDEX pending_jobs_by_signal
    ON demo_delivery.jobs (signal_id, session_id) WHERE finished_at IS NULL;

CREATE FUNCTION demo_delivery.subscribe(p_session uuid, p_venue text, p_trader text)
RETURNS void LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF current_setting('transaction_isolation') <> 'read committed'
    THEN RAISE EXCEPTION 'Subscription changes require READ COMMITTED'; END IF;
    -- Serialize activation against publishing for the same trader.
    PERFORM 1 FROM demo_delivery.traders
        WHERE (venue, trader_key) = (p_venue, p_trader) FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Trader was not resolved'; END IF;
    INSERT INTO demo_delivery.subscriptions VALUES (p_session, p_venue, p_trader, clock_timestamp())
        ON CONFLICT (session_id) DO NOTHING;
    IF NOT FOUND AND NOT EXISTS (
        SELECT FROM demo_delivery.subscriptions
        WHERE session_id = p_session AND (venue, trader_key) = (p_venue, p_trader)
    ) THEN RAISE EXCEPTION 'Session already follows another trader'; END IF;
END
$$;

CREATE FUNCTION demo_delivery.publish(
    p_venue text, p_trader text, p_execution text, p_occurred timestamptz,
    p_first_received timestamptz, p_expires timestamptz, p_payload jsonb
) RETURNS TABLE(signal_id bigint, enqueued bigint)
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
DECLARE
    existing demo_delivery.signals;
BEGIN
    IF current_setting('transaction_isolation') <> 'read committed'
    THEN RAISE EXCEPTION 'Publishing requires READ COMMITTED'; END IF;
    PERFORM 1 FROM demo_delivery.traders
        WHERE (venue, trader_key) = (p_venue, p_trader) FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Trader was not resolved'; END IF;
    SELECT * INTO existing FROM demo_delivery.signals
        WHERE (venue, trader_key, execution_key) = (p_venue, p_trader, p_execution);
    IF FOUND THEN
        IF (existing.occurred_at, existing.expires_at, existing.payload)
            IS DISTINCT FROM (p_occurred, p_expires, p_payload) THEN
            RAISE EXCEPTION 'Conflicting replay for an existing execution';
        END IF;
        RETURN QUERY SELECT existing.id, 0::bigint;
        RETURN;
    END IF;
    INSERT INTO demo_delivery.signals
        (venue, trader_key, execution_key, occurred_at, first_received_at, expires_at, payload)
        VALUES (p_venue, p_trader, p_execution, p_occurred, p_first_received, p_expires, p_payload)
        RETURNING id INTO signal_id;
    INSERT INTO demo_delivery.jobs (signal_id, session_id)
        SELECT signal_id, subscription.session_id
        FROM demo_delivery.subscriptions subscription
        WHERE (venue, trader_key) = (p_venue, p_trader) AND active_from <= LEAST(p_occurred, p_first_received);
    GET DIAGNOSTICS enqueued = ROW_COUNT;
    IF enqueued > 0 THEN PERFORM pg_notify('demo_delivery_ready', ''); END IF;
    RETURN NEXT;
END
$$;

CREATE FUNCTION demo_delivery.claim(p_max integer, p_lease interval)
RETURNS TABLE(signal_id bigint, session_id uuid, lease_token uuid, expires_at timestamptz,
              payload jsonb, status text, venue text, execution_key text)
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF p_max IS NULL OR p_max NOT BETWEEN 1 AND 500
       OR p_lease IS NULL OR p_lease <= interval '0 seconds' OR p_lease > interval '1 minute'
    THEN RAISE EXCEPTION 'Invalid claim limits'; END IF;
    RETURN QUERY
    WITH candidates AS (
        SELECT j.signal_id, j.session_id, s.expires_at, s.expires_at <= statement_timestamp() AS expired
        FROM demo_delivery.jobs j JOIN demo_delivery.signals s ON s.id = j.signal_id
        WHERE j.finished_at IS NULL AND (j.lease_until IS NULL OR j.lease_until <= statement_timestamp())
          AND NOT EXISTS (
            SELECT FROM demo_delivery.jobs earlier
            WHERE earlier.session_id = j.session_id AND earlier.signal_id < j.signal_id
              AND earlier.finished_at IS NULL
          )
        ORDER BY j.signal_id, j.session_id
        LIMIT p_max FOR UPDATE OF j SKIP LOCKED
    ), claimed AS (
        UPDATE demo_delivery.jobs j
        SET lease_token = CASE WHEN NOT c.expired THEN gen_random_uuid() END,
            lease_until = CASE WHEN NOT c.expired THEN LEAST(clock_timestamp() + p_lease, c.expires_at) END,
            finished_at = CASE WHEN c.expired THEN clock_timestamp() END,
            finish_reason = CASE WHEN c.expired THEN 'expired' END
        FROM candidates c
        WHERE (j.signal_id, j.session_id) = (c.signal_id, c.session_id)
        RETURNING j.signal_id, j.session_id, j.lease_token, j.finish_reason
    )
    SELECT c.signal_id, c.session_id, c.lease_token, s.expires_at,
           CASE WHEN c.finish_reason IS NULL THEN s.payload END,
           COALESCE(c.finish_reason, 'claimed'), s.venue, s.execution_key
    FROM claimed c JOIN demo_delivery.signals s ON s.id = c.signal_id;
END
$$;

CREATE FUNCTION demo_delivery.acknowledge(p_signal bigint, p_session uuid, p_token uuid)
RETURNS boolean LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    UPDATE demo_delivery.jobs j
    SET finished_at = clock_timestamp(), finish_reason = 'acknowledged', lease_token = NULL, lease_until = NULL
    FROM demo_delivery.signals s
    WHERE (j.signal_id, j.session_id, j.lease_token) = (p_signal, p_session, p_token)
      AND s.id = j.signal_id AND j.finished_at IS NULL
      AND j.lease_until > clock_timestamp() AND s.expires_at > clock_timestamp();
    IF NOT FOUND THEN RETURN false; END IF;
    IF EXISTS (
        SELECT FROM demo_delivery.jobs later
        WHERE later.session_id = p_session AND later.signal_id > p_signal AND later.finished_at IS NULL
    ) THEN PERFORM pg_notify('demo_delivery_ready', ''); END IF;
    RETURN true;
END
$$;

CREATE FUNCTION demo_delivery.acknowledge_bound(
    p_signal bigint, p_session uuid, p_token uuid, p_venue text, p_execution text
)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM demo_delivery.session_writers w
        JOIN demo_delivery.subscriptions subscription USING (session_id)
        JOIN demo_delivery.signals signal
          ON (signal.venue, signal.trader_key) = (subscription.venue, subscription.trader_key)
        WHERE w.session_id = p_session AND w.writer_oid = session_user::regrole::oid
          AND signal.id = p_signal AND signal.venue = p_venue AND signal.execution_key = p_execution
    ) THEN RETURN false; END IF;
    RETURN demo_delivery.acknowledge(p_signal, p_session, p_token);
END
$$;

REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA demo_delivery FROM PUBLIC;
