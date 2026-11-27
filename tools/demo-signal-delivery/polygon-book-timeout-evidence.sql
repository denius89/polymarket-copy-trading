-- A gate timeout is evidence from the same enrolled writer and unexpired lease.
-- Persist it separately so a serialization rollback during completion can be reconciled.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL search_path=pg_catalog;
DO $gate$
BEGIN
    IF current_database()<>'shadow_v00' OR NOT EXISTS (
        SELECT FROM demo_delivery.pilot_marker WHERE kind='isolated-public-market-pilot-v1'
    ) THEN RAISE EXCEPTION 'Expected isolated Polygon queue'; END IF;
END $gate$;

CREATE TABLE demo_delivery.polygon_book_timeouts (
    session_id uuid NOT NULL,
    signal_id bigint NOT NULL,
    observation_id uuid NOT NULL UNIQUE REFERENCES polygon_live_activity.observations(id),
    lease_token uuid NOT NULL,
    observed_at timestamptz NOT NULL,
    PRIMARY KEY (signal_id,session_id),
    FOREIGN KEY (signal_id,session_id) REFERENCES demo_delivery.jobs
);
REVOKE ALL ON demo_delivery.polygon_book_timeouts FROM PUBLIC,polygon_executor;
CREATE TRIGGER polygon_book_timeouts_immutable BEFORE UPDATE OR DELETE ON demo_delivery.polygon_book_timeouts
FOR EACH ROW EXECUTE FUNCTION live_buy_core.immutable();

DO $install$
DECLARE
    body text := pg_get_functiondef('demo_delivery.complete_polygon_refusal(uuid,bigint,uuid,text)'::regprocedure);
    reason_gate constant text := 'IF p_reason IS NULL OR p_reason NOT IN';
    finalize constant text := 'INSERT INTO demo_delivery.polygon_waiting_outcomes VALUES (p_session,p_signal,target,p_reason,clock_timestamp());';
    note constant text := $note$IF p_reason='record_book_timeout' THEN
        IF current_setting('transaction_isolation')<>'serializable' OR demo_delivery.closed_polygon_scope(p_session) IS NULL
        THEN RETURN false; END IF;
        SELECT o.id INTO target
        FROM demo_delivery.jobs j JOIN demo_delivery.signals s ON s.id=j.signal_id
        JOIN polygon_live_activity.observations o ON (o.session_id,o.raw_log,o.header)=(j.session_id,s.payload->'log',s.payload->'header')
        JOIN polygon_live_activity.decisions d ON (d.session_id,d.observation_id)=(o.session_id,o.id)
        WHERE (j.session_id,j.signal_id,j.lease_token)=(p_session,p_signal,p_token)
          AND j.finished_at IS NULL AND j.lease_until>clock_timestamp() AND s.expires_at>clock_timestamp()
          AND d.checks->>'executionAdmission'='awaiting_quote' AND d.checks#>>'{evidence,signalId}'=p_signal::text
          AND demo_delivery.polygon_waiting_valid(o.id,d.checks->'evidence',false)
          AND NOT EXISTS(SELECT FROM live_buy_core.intents i WHERE (i.session_id,i.observation_id)=(p_session,o.id))
          AND NOT EXISTS(SELECT FROM polygon_buy.admissions a WHERE
              (a.session_id,a.transaction_hash,a.log_index)=(p_session,o.transaction_hash,o.log_index))
        FOR UPDATE OF j;
        IF target IS NULL THEN RETURN false; END IF;
        INSERT INTO demo_delivery.polygon_book_timeouts VALUES(p_session,p_signal,target,p_token,clock_timestamp())
        ON CONFLICT (signal_id,session_id) DO NOTHING;
        RETURN true;
    END IF;
    $note$;
    apply_note constant text := $reason$IF p_reason='signal_expired' AND EXISTS (
        SELECT FROM demo_delivery.polygon_book_timeouts t
        JOIN polygon_live_activity.observations o ON (o.session_id,o.id)=(t.session_id,t.observation_id)
        WHERE (t.session_id,t.signal_id,t.observation_id)=(p_session,p_signal,target)
          AND NOT EXISTS(SELECT FROM polygon_buy.admissions a WHERE
              (a.session_id,a.transaction_hash,a.log_index)=(p_session,o.transaction_hash,o.log_index))
    ) THEN p_reason:='book_unavailable'; END IF;
    $reason$;
BEGIN
    IF cardinality(string_to_array(body,reason_gate))<>2 OR cardinality(string_to_array(body,finalize))<>2
    THEN RAISE EXCEPTION 'Unexpected Polygon queue refusal function'; END IF;
    EXECUTE replace(replace(body,reason_gate,note||reason_gate),finalize,apply_note||finalize);
END $install$;
COMMIT;
