-- Direct discovery is scoped to the same isolated writer and immutable queue.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind='isolated-public-market-pilot-v1')
    THEN RAISE EXCEPTION 'Expected the isolated Polygon delivery queue'; END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.read_polygon_buy_head(p_session uuid, p_after bigint)
RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $head$
    SELECT jsonb_build_object('signalId',s.id::text,'payload',s.payload,
               'publishedAtMs',floor(extract(epoch FROM s.stored_at)*1000))
    FROM demo_delivery.closed_polygon_scope(p_session) scope
    CROSS JOIN LATERAL (
        SELECT j.signal_id,j.lease_until FROM demo_delivery.jobs j
        WHERE j.session_id=p_session AND j.finished_at IS NULL
        ORDER BY j.signal_id LIMIT 1
    ) head
    JOIN demo_delivery.signals s ON s.id=head.signal_id
    WHERE s.id > p_after AND s.venue='polymarket' AND s.trader_key=scope->>'wallet'
      AND s.payload->>'kind'='polygon-finalized-buy'
      AND s.expires_at>clock_timestamp()
      AND (head.lease_until IS NULL OR head.lease_until<=clock_timestamp())
$head$;
REVOKE ALL ON FUNCTION demo_delivery.read_polygon_buy_head(uuid,bigint) FROM PUBLIC,polygon_executor;

GRANT SELECT ON demo_delivery.jobs,demo_delivery.signals TO polygon_owner;
SET LOCAL ROLE polygon_owner;
DO $issuer$
DECLARE
    body text := pg_get_functiondef('polygon.personal_quote_issue_v1(jsonb)'::regprocedure);
    marker text := 'ev#>>''{venueReceipt,source}'' IN (''polymarket-data-api-maker-finalized-v1'',''polymarket-rtds-finalized-v1'')';
BEGIN
    IF cardinality(string_to_array(body,marker))<>2
    THEN RAISE EXCEPTION 'Unexpected Polygon quote source allowlist'; END IF;
    EXECUTE replace(body,marker,marker || '
    OR (
       ev#>>''{venueReceipt,source}''=''polymarket-polygon-finalized-queue-v1''
       AND ev->>''signalAtMs''=fin->>''blockTimestampMs''
       AND evidence#>''{sourceProof,log}''=q->''normalizedLog''
       AND EXISTS (
         SELECT FROM demo_delivery.closed_polygon_source x
         JOIN demo_delivery.jobs j ON j.session_id=x.session_id
         JOIN demo_delivery.signals sig ON sig.id=j.signal_id
         JOIN polygon_live_activity.observations o ON o.session_id=j.session_id
             AND o.raw_log=sig.payload->''log'' AND o.header=sig.payload->''header''
         JOIN polygon_live_activity.decisions d ON (d.session_id,d.observation_id)=(o.session_id,o.id)
         WHERE x.session_id=sid AND x.run_id=a.run_id AND x.wallet=a.owner_address AND x.cutoff_at>now_at
           AND sig.venue=''polymarket'' AND sig.trader_key=x.wallet AND sig.payload->>''kind''=''polygon-finalized-buy''
           AND sig.id::text=evidence#>>''{sourceProof,signalId}''
           AND floor(extract(epoch FROM sig.stored_at)*1000)::text=evidence#>>''{sourceProof,publishedAtMs}''
           AND o.id::text=q->>''observationId'' AND o.raw_log=q->''normalizedLog''
           AND o.header=evidence#>''{sourceProof,header}''
           AND ev->>''signalAtMs''=((o.header->>''timestampSeconds'')::bigint*1000)::text
           AND d.checks->>''executionAdmission''=''awaiting_quote''
           AND expires<=sig.expires_at AND j.finished_at IS NULL
           AND NOT EXISTS (SELECT FROM demo_delivery.jobs earlier
                           WHERE earlier.session_id=j.session_id AND earlier.finished_at IS NULL
                             AND earlier.signal_id<j.signal_id)
       )
    )');
END
$issuer$;
COMMIT;
