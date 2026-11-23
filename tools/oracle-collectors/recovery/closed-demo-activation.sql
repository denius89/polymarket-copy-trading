-- Closed app only. A venue adapter owns provisioning and must reconcile by request_id.
BEGIN;
SET LOCAL search_path=pg_catalog;
SET LOCAL lock_timeout='3s';

DO $gate$
BEGIN
    IF current_database()<>'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker WHERE kind='isolated-public-market-pilot-v1')
       OR NOT EXISTS (SELECT FROM polygon_live.installation
                      WHERE singleton AND database_name=current_database())
       OR to_regprocedure('demo_delivery.consume_ready_demo_sessions()') IS NULL
    THEN RAISE EXCEPTION 'Expected the closed app and financial queue'; END IF;
END
$gate$;

CREATE TABLE demo_delivery.activation_requests (
    request_id uuid PRIMARY KEY REFERENCES demo_delivery.start_receipts(outbox_id),
    session_id uuid UNIQUE NOT NULL REFERENCES demo_delivery.subscriptions,
    attempt bigint NOT NULL DEFAULT 0 CHECK (attempt >= 0),
    attempt_after timestamptz NOT NULL DEFAULT clock_timestamp(),
    token uuid,
    lease_until timestamptz,
    activated_at timestamptz,
    worker_instance uuid,
    CHECK ((token IS NULL)=(lease_until IS NULL)),
    CHECK ((activated_at IS NULL)=(worker_instance IS NULL)),
    CHECK (activated_at IS NULL OR token IS NULL)
);
ALTER TABLE demo_delivery.activation_requests OWNER TO polygon_owner;
REVOKE ALL ON TABLE demo_delivery.activation_requests FROM PUBLIC,polygon_executor;

CREATE FUNCTION demo_delivery.activation_release()
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $identity$
    SELECT operator_run_id FROM polygon_live.installation
    WHERE singleton AND database_name=current_database()
$identity$;

CREATE FUNCTION demo_delivery.enqueue_confirmed_activations()
RETURNS integer LANGUAGE plpgsql SET search_path=pg_catalog AS $enqueue$
DECLARE
    enqueued integer;
BEGIN
    INSERT INTO demo_delivery.activation_requests(request_id,session_id)
        SELECT r.outbox_id,r.session_id
        FROM demo_delivery.start_receipts r
        WHERE demo_delivery.app_subscription_current(r.session_id)
          AND NOT EXISTS (SELECT FROM demo_delivery.activation_requests j WHERE j.request_id=r.outbox_id)
        ORDER BY r.outbox_id LIMIT 64 ON CONFLICT DO NOTHING;
    GET DIAGNOSTICS enqueued=ROW_COUNT;
    RETURN enqueued;
END
$enqueue$;

CREATE OR REPLACE FUNCTION demo_delivery.consume_ready_demo_sessions()
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $poll$
DECLARE
    starts jsonb;
    writers integer;
BEGIN
    starts:=demo_delivery.consume_confirmed_starts();
    writers:=demo_delivery.bind_confirmed_writers();
    RETURN starts || jsonb_build_object('writers',writers,
        'activationRequests',demo_delivery.enqueue_confirmed_activations());
END
$poll$;

CREATE FUNCTION demo_delivery.claim_activation()
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $claim$
DECLARE
    claimed jsonb;
BEGIN
    IF current_setting('transaction_isolation')<>'read committed' THEN
        RAISE EXCEPTION 'Activation claims require READ COMMITTED';
    END IF;

    WITH candidate AS (
        SELECT j.request_id
        FROM demo_delivery.activation_requests j
        WHERE j.activated_at IS NULL AND j.attempt_after<=statement_timestamp()
          AND (j.lease_until IS NULL OR j.lease_until<=statement_timestamp())
          AND demo_delivery.app_subscription_current(j.session_id)
        ORDER BY j.attempt_after,j.request_id
        LIMIT 1 FOR UPDATE OF j SKIP LOCKED
    ), leased AS (
        UPDATE demo_delivery.activation_requests j
           SET token=gen_random_uuid(), lease_until=clock_timestamp()+interval '90 seconds',
               attempt=j.attempt+1
          FROM candidate c WHERE j.request_id=c.request_id
        RETURNING j.request_id,j.session_id,j.token,j.attempt
    )
    SELECT jsonb_build_object('requestId',j.request_id,'sessionId',j.session_id,
           'token',j.token,'attempt',j.attempt,'venue',r.venue,
           'wallet',r.wallet,'traderRevisionId',r.trader_revision_id)
      INTO claimed
      FROM leased j JOIN demo_delivery.start_receipts r ON (r.outbox_id,r.session_id)=(j.request_id,j.session_id);
    RETURN claimed;
END
$claim$;

CREATE FUNCTION demo_delivery.finish_activation(request uuid, lease uuid, instance uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $finish$
DECLARE
    seat record;
BEGIN
    IF instance IS NULL THEN RETURN false; END IF;
    SELECT r.venue,r.session_id INTO seat
    FROM demo_delivery.activation_requests j JOIN demo_delivery.start_receipts r
      ON (r.outbox_id,r.session_id)=(j.request_id,j.session_id)
    JOIN polygon.paper_sessions s ON s.id=r.session_id
    JOIN polygon.user_session_slots slot
      ON (slot.id,slot.user_id,slot.current_session_id)=(s.slot_id,s.user_id,s.id)
    WHERE j.request_id=request AND s.lifecycle='active' AND s.evaluation_deadline_at>clock_timestamp()
    FOR SHARE OF slot,s;
    IF NOT FOUND OR NOT EXISTS (
        SELECT FROM demo_delivery.session_writers w
        WHERE w.session_id=seat.session_id
          AND w.writer_oid=demo_delivery.app_financial_writer(seat.session_id,seat.venue)
    ) THEN RETURN false; END IF;

    UPDATE demo_delivery.activation_requests
       SET activated_at=clock_timestamp(),worker_instance=instance,token=NULL,lease_until=NULL
     WHERE request_id=request AND token=lease AND lease_until>clock_timestamp() AND activated_at IS NULL;
    RETURN FOUND;
END
$finish$;

CREATE FUNCTION demo_delivery.defer_activation(request uuid, lease uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $defer$
BEGIN
    UPDATE demo_delivery.activation_requests
       SET attempt_after=clock_timestamp()+make_interval(secs=>LEAST(120,5*attempt)),
           token=NULL,lease_until=NULL
     WHERE request_id=request AND token=lease AND lease_until>clock_timestamp() AND activated_at IS NULL;
    RETURN FOUND;
END
$defer$;

ALTER FUNCTION demo_delivery.claim_activation() OWNER TO polygon_owner;
ALTER FUNCTION demo_delivery.finish_activation(uuid,uuid,uuid) OWNER TO polygon_owner;
ALTER FUNCTION demo_delivery.defer_activation(uuid,uuid) OWNER TO polygon_owner;
ALTER FUNCTION demo_delivery.enqueue_confirmed_activations() OWNER TO polygon_owner;
ALTER FUNCTION demo_delivery.activation_release() OWNER TO polygon_owner;
REVOKE ALL ON FUNCTION demo_delivery.activation_release(),demo_delivery.enqueue_confirmed_activations(),
    demo_delivery.claim_activation(),demo_delivery.finish_activation(uuid,uuid,uuid),
    demo_delivery.defer_activation(uuid,uuid) FROM PUBLIC,polygon_executor;
COMMIT;
