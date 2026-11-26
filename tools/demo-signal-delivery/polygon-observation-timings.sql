\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '8s';

-- Output only queue IDs and ages, with the same two-hour window as the journal.
-- Observation creation can precede COMMIT. A predecessor finished_at timestamp
-- marks the queue decision written in its transaction, also before COMMIT.
WITH recent AS MATERIALIZED (
    SELECT s.id, s.occurred_at, s.stored_at, s.expires_at,
           s.payload #>> '{log,transactionHash}' AS tx,
           (s.payload #>> '{log,logIndex}')::integer AS log_index,
           j.finished_at
    FROM demo_delivery.signals s
    JOIN demo_delivery.jobs j ON (j.signal_id, j.session_id) = (s.id, :'pm_session'::uuid)
    WHERE s.id > (SELECT coalesce(max(id),0) - 10000 FROM demo_delivery.signals)
      AND s.venue = 'polymarket'
      AND s.payload->>'kind' = 'polygon-finalized-buy'
      AND s.occurred_at >= now() - interval '2 hours'
), ordered AS (
    SELECT recent.*,
           max(coalesce(finished_at, statement_timestamp())) OVER (
               ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
           ) AS previous_finished_at
    FROM recent
)
SELECT jsonb_build_object(
    'signalId', s.id,
    'insertionAgeMs', floor(extract(epoch FROM s.stored_at - s.occurred_at) * 1000)::bigint,
    'observationAgeMs', floor(extract(epoch FROM observation.created_at - s.occurred_at) * 1000)::bigint,
    'predecessorsFinishedAgeMs', floor(extract(epoch FROM s.previous_finished_at - s.occurred_at) * 1000)::bigint,
    'observationAfterDeadline', observation.created_at >= s.expires_at,
    'priorJobUnfinishedAtDeadline', s.previous_finished_at >= s.expires_at,
    'outcome', outcome.reason
)
FROM ordered s
LEFT JOIN LATERAL (
    SELECT min(op.created_at) AS created_at
    FROM polygon_live_activity.observations o
    JOIN polygon_live_activity.decisions d ON (d.session_id, d.observation_id) = (o.session_id, o.id)
    JOIN polygon_live_activity.operations op ON (op.session_id, op.id) = (o.session_id, o.operation_id)
    WHERE o.session_id = :'pm_session'::uuid AND o.transaction_hash = s.tx AND o.log_index = s.log_index
      AND d.checks->>'executionAdmission' = 'awaiting_quote'
      AND d.checks #>> '{evidence,signalId}' = s.id::text
) observation ON true
LEFT JOIN demo_delivery.polygon_waiting_outcomes outcome
    ON (outcome.signal_id, outcome.session_id) = (s.id, :'pm_session'::uuid)
ORDER BY s.id;

COMMIT;
