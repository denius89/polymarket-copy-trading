\set ON_ERROR_STOP on
-- Pass breakthebank, tradecraft (current session UUIDs) and since (UTC timestamp)
-- as psql variables. Use the existing restricted database operator connection.
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '5s';

WITH requested(trader, session_id) AS (
    VALUES ('BreakTheBank', :'breakthebank'::uuid), ('Tradecraft', :'tradecraft'::uuid)
), active AS (
    SELECT s.id
    FROM polygon.paper_sessions s
    JOIN polygon.user_session_slots slot ON slot.current_session_id = s.id
), evidence AS (
    SELECT r.trader, a.id AS current_id, st.status, st.checkpoint->>'number' AS block,
           st.last_observed_at, sn.data->'freeCash' AS available_cash,
           jsonb_array_length(sn.data->'positions') AS position_count,
           purchase.settled_at, purchase.item, purchase.previous, purchase.settled,
           purchase.condition_id, purchase.token_id, purchase.posted_snapshot,
           purchase.receipt_recorded
    FROM requested r
    LEFT JOIN active a ON a.id = r.session_id
    LEFT JOIN polygon_live_activity.stream st ON st.session_id = a.id
    LEFT JOIN live_buy_core.heads h ON h.session_id = a.id
    LEFT JOIN live_buy_core.snapshots sn ON (sn.session_id, sn.version) = (h.session_id, h.version)
    LEFT JOIN LATERAL (
        SELECT ex.settled_at, polygon_buy.item(ob, d) AS item,
               before.data AS previous, after.data AS settled, after.id AS posted_snapshot,
               i.condition_id, i.token_id, receipt.command_id IS NOT NULL AS receipt_recorded
        FROM live_buy_core.executions ex
        JOIN live_buy_core.intents i ON (i.session_id, i.id) = (ex.session_id, ex.intent_id)
        LEFT JOIN polygon_live_activity.observations ob ON (ob.session_id, ob.id) = (i.session_id, i.observation_id)
        LEFT JOIN polygon_live_activity.decisions d ON (d.session_id, d.observation_id) = (ob.session_id, ob.id)
        LEFT JOIN live_buy_core.snapshots before ON (before.session_id, before.version) = (ex.session_id, ex.version - 1)
        LEFT JOIN live_buy_core.snapshots after ON (after.session_id, after.version) = (ex.session_id, ex.version)
        LEFT JOIN polygon_buy.ledger_index li ON (li.session_id, li.command_id) = (ex.session_id, ex.command_id)
        LEFT JOIN live_buy_core.receipts receipt ON (receipt.session_id, receipt.command_id) = (li.session_id, li.command_id)
            AND receipt.kind = 'settle'
        WHERE ex.session_id = a.id AND ex.settled_at >= :'since'::timestamptz
        ORDER BY ex.version
        LIMIT 1
    ) purchase ON true
), amounts AS (
    SELECT e.*, item#>'{decision,copy}' AS fill,
           CASE WHEN previous->'cash' IS NOT NULL AND settled->'cash' IS NOT NULL
               THEN live_buy_core.subq(previous->'cash', settled->'cash') END AS debit,
           CASE WHEN previous IS NOT NULL AND settled IS NOT NULL THEN live_buy_core.subq(
               COALESCE(settled_position.quantity, live_buy_core.q(0, 1)),
               COALESCE(previous_position.quantity, live_buy_core.q(0, 1))
           ) END AS added_shares
    FROM evidence e
    LEFT JOIN LATERAL (
        SELECT p->'quantity' AS quantity FROM jsonb_array_elements(e.previous->'positions') p
        WHERE p->>'conditionId' = e.condition_id AND p->>'tokenId' = e.token_id
    ) previous_position ON true
    LEFT JOIN LATERAL (
        SELECT p->'quantity' AS quantity FROM jsonb_array_elements(e.settled->'positions') p
        WHERE p->>'conditionId' = e.condition_id AND p->>'tokenId' = e.token_id
    ) settled_position ON true
)
SELECT trader, status AS recorded_stream_status, block, last_observed_at,
       available_cash, position_count, settled_at, debit, added_shares,
       CASE
           WHEN :'breakthebank'::uuid = :'tradecraft'::uuid THEN 'duplicate_session_selection'
           WHEN current_id IS NULL THEN 'session_not_current'
           WHEN status IS NULL OR available_cash IS NULL THEN 'collector_not_connected'
           WHEN settled_at IS NULL THEN 'waiting_for_purchase'
           WHEN receipt_recorded
                AND item#>>'{decision,status}' = 'filled'
                AND fill->>'snapshotId' = posted_snapshot::text
                AND fill->'quantityNet' = added_shares
                AND CASE WHEN fill->'notional' IS NOT NULL AND fill->'cashFee' IS NOT NULL
                         THEN live_buy_core.addq(fill->'notional', fill->'cashFee') = debit END
               THEN 'purchase_reconciled'
           ELSE 'purchase_mismatch'
       END AS result
FROM amounts
ORDER BY trader;

ROLLBACK;
