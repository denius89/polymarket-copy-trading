BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout = '3s';
SET LOCAL ROLE polygon_owner;

CREATE TABLE polygon_buy.tradecraft_expired_quotes (
    session_id uuid NOT NULL,
    admission_id uuid NOT NULL,
    decision_id uuid NOT NULL UNIQUE REFERENCES polygon_live_activity.decisions(id) DEFERRABLE INITIALLY DEFERRED,
    recorded_at timestamptz NOT NULL,
    PRIMARY KEY (session_id, admission_id),
    FOREIGN KEY (session_id, admission_id) REFERENCES polygon_buy.admissions(session_id, id)
);
CREATE TRIGGER immutable_expired_tradecraft_quote BEFORE UPDATE OR DELETE ON polygon_buy.tradecraft_expired_quotes
    FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row();
CREATE TRIGGER immutable_expired_tradecraft_quote_truncate BEFORE TRUNCATE ON polygon_buy.tradecraft_expired_quotes
    FOR EACH STATEMENT EXECUTE FUNCTION polygon.immutable_row();
REVOKE ALL ON polygon_buy.tradecraft_expired_quotes FROM PUBLIC, polygon_executor;

DO $patch$
DECLARE
    body text := pg_get_functiondef('polygon_buy.guard_decision_gap()'::regprocedure);
    scope_gate text := $match$AND NOT EXISTS(SELECT FROM polygon_buy.admissions WHERE session_id=ob.session_id
 AND transaction_hash=ob.transaction_hash AND log_index=ob.log_index)) IS DISTINCT FROM true THEN$match$;
    skip_log text := 'INSERT INTO polygon_buy.personal_log_dispositions VALUES(ob.session_id,ob.transaction_hash,ob.log_index,''skip'');';
BEGIN
    IF cardinality(string_to_array(body, scope_gate)) <> 2 OR cardinality(string_to_array(body, skip_log)) <> 2
    THEN RAISE EXCEPTION 'Unexpected admission closure preimage'; END IF;
    body := replace(body, scope_gate, ') IS DISTINCT FROM true THEN');
    body := replace(body, skip_log, $body$
    IF EXISTS (
        SELECT FROM polygon_buy.admissions a
        WHERE (a.session_id, a.transaction_hash, a.log_index) = (ob.session_id, ob.transaction_hash, ob.log_index)
    ) THEN
        IF polygon_buy.tradecraft_gap_scope(ob.session_id) IS DISTINCT FROM true OR ob.raw_log->>'side' <> 'BUY'
        THEN RAISE EXCEPTION 'existing admission cannot be skipped'; END IF;

        -- The session is already locked by ingestion and the verified issuer also locks it.
        -- Keep the admission, quote and disposition. Record only a terminal decision after expiry.
        INSERT INTO polygon_buy.tradecraft_expired_quotes(session_id, admission_id, decision_id, recorded_at)
        SELECT a.session_id, a.id, NEW.id, clock_timestamp()
        FROM polygon_buy.admissions a
        JOIN polygon_buy.verified_quotes q ON (q.session_id, q.reserve_id) = (a.session_id, a.id)
        WHERE (a.session_id, a.transaction_hash, a.log_index) = (ob.session_id, ob.transaction_hash, ob.log_index)
          AND a.kind = 'reserve' AND a.expires_at <= ob.received_at AND a.expires_at <= clock_timestamp()
          AND q.quote->'normalizedLog' = ob.raw_log
          AND NOT EXISTS (
              SELECT FROM polygon_buy.admissions settlement
              WHERE (settlement.session_id, settlement.transaction_hash, settlement.log_index) =
                    (a.session_id, a.transaction_hash, a.log_index) AND settlement.kind = 'settle'
          )
          AND NOT EXISTS (SELECT FROM polygon_buy.commands c WHERE (c.session_id, c.admission_id) = (a.session_id, a.id))
          AND NOT EXISTS (
              SELECT FROM live_buy_core.intents i WHERE i.session_id = a.session_id
                  AND (i.id = (a.request->>'intentId')::uuid OR i.observation_id = ob.id)
          )
          AND EXISTS (
              SELECT FROM polygon_buy.personal_log_dispositions d
              WHERE (d.session_id, d.transaction_hash, d.log_index, d.disposition) =
                    (a.session_id, a.transaction_hash, a.log_index, 'admission')
          );
        IF NOT FOUND THEN RAISE EXCEPTION 'admission must be expired and unexecuted before skipping'; END IF;
        RETURN NEW;
    END IF;
    $body$ || skip_log);
    EXECUTE body;
END
$patch$;
COMMIT;
