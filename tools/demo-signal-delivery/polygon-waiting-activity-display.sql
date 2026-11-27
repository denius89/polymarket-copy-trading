-- Apply after polygon-waiting-observation.sql on the isolated personal schema.
BEGIN;
SET LOCAL search_path = pg_catalog;

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind='isolated-public-market-pilot-v1')
       OR to_regclass('polygon_buy.verified_quotes') IS NULL
    THEN RAISE EXCEPTION 'Expected the closed personal quotation schema'; END IF;
END
$gate$;

SET LOCAL ROLE polygon_owner;
CREATE FUNCTION polygon_buy.waiting_trade_display(body jsonb, quote jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path = pg_catalog AS $display$
    SELECT CASE WHEN nullif(quote#>>'{estimate,evidence,display,marketTitle}','') IS NOT NULL
                     AND nullif(quote#>>'{estimate,evidence,display,outcomeTitle}','') IS NOT NULL
                     AND nullif(quote#>>'{event,marketId}','') IS NOT NULL
           THEN jsonb_set(body,'{trade}',(body->'trade') || jsonb_build_object(
                'conditionId',quote#>'{event,marketId}',
                'marketTitle',quote#>'{estimate,evidence,display,marketTitle}',
                'outcome',quote#>'{estimate,evidence,display,outcomeTitle}'))
           ELSE body END
$display$;
REVOKE ALL ON FUNCTION polygon_buy.waiting_trade_display(jsonb,jsonb) FROM PUBLIC,polygon_executor;

DO $patch$
DECLARE
    definition text := pg_get_functiondef('polygon_buy.item(polygon_live_activity.observations,polygon_live_activity.decisions)'::regprocedure);
    marker text := ' IN' || 'TO cost,gross,net,qfee,cfee,fills FROM live_buy_core.fills f WHERE session_id=ob.session_id AND intent_id=i.id;';
BEGIN
    IF cardinality(string_to_array(definition,marker)) <> 2
       OR position('awaiting_quote' in definition) = 0
    THEN RAISE EXCEPTION 'Unexpected closed Polygon Activity projection'; END IF;
    EXECUTE replace(definition,marker,marker || '
      IF d.checks->>''executionAdmission''=''awaiting_quote'' THEN
        body:=polygon_buy.waiting_trade_display(body,(
          SELECT q.quote FROM polygon_buy.verified_quotes q
          WHERE q.session_id=ob.session_id AND q.quote->>''observationId''=ob.id::text
            AND q.quote->''normalizedLog''=ob.raw_log
            AND q.quote->>''settleCommandId''=e.command_id::text
            AND q.quote#>>''{event,marketId}''=i.condition_id
            AND q.quote#>>''{event,outcomeId}''=i.token_id));
      END IF;');
END
$patch$;
COMMIT;
