\set ON_ERROR_STOP on
\timing on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '8s';

-- Choose one batch of 32 already recorded expiry proofs and compare the two
-- discovery paths. No open job is leased or completed by this check.
WITH recent AS MATERIALIZED (
    SELECT w.signal_id, w.session_id, w.observation_id, s.payload
    FROM demo_delivery.polygon_waiting_outcomes w
    JOIN demo_delivery.signals s ON s.id = w.signal_id
    WHERE w.session_id = :'pm_session'::uuid AND w.reason = 'signal_expired'
    ORDER BY w.signal_id DESC LIMIT 32
), old_matches AS MATERIALIZED (
    SELECT w.signal_id, o.id
    FROM recent w
    CROSS JOIN LATERAL (
        SELECT o.id FROM polygon_live_activity.observations o
        WHERE o.session_id = w.session_id AND o.raw_log = w.payload->'log'
          AND o.header = w.payload->'header'
        OFFSET 0
    ) o
), keyed_matches AS MATERIALIZED (
    SELECT w.signal_id, o.id
    FROM recent w
    CROSS JOIN LATERAL (
        SELECT o.id FROM polygon_live_activity.observations o
        WHERE o.session_id = w.session_id AND o.raw_log = w.payload->'log'
          AND o.header = w.payload->'header'
          AND o.transaction_hash = w.payload#>>'{log,transactionHash}'
          AND o.log_index = CASE WHEN w.payload#>>'{log,logIndex}' ~ '^(0|[1-9][0-9]{0,77})$'
                                 THEN (w.payload#>>'{log,logIndex}')::numeric END
        OFFSET 0
    ) o
), expected AS (
    SELECT signal_id, observation_id AS id FROM recent
), disagreement AS (
    (SELECT * FROM old_matches EXCEPT ALL SELECT * FROM expected)
    UNION ALL (SELECT * FROM expected EXCEPT ALL SELECT * FROM old_matches)
    UNION ALL (SELECT * FROM keyed_matches EXCEPT ALL SELECT * FROM expected)
    UNION ALL (SELECT * FROM expected EXCEPT ALL SELECT * FROM keyed_matches)
)
SELECT (SELECT count(*) FROM expected) AS samples,
       (SELECT count(*) FROM disagreement) AS mismatches,
       ((SELECT count(*) FROM expected) = 32 AND NOT EXISTS (SELECT FROM disagreement)) AS matches
\gset
\echo samples=:samples mismatches=:mismatches
\if :matches
\else
DO $$ BEGIN RAISE EXCEPTION 'Expiry observation lookup differs'; END $$;
\endif
COMMIT;
