-- Closed Oracle only. Read the canonical scope under the existing venue writer.
BEGIN;
SET LOCAL search_path=pg_catalog;
SET LOCAL lock_timeout='3s';

DO $gate$
BEGIN
    IF current_database()<>'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker WHERE kind='isolated-public-market-pilot-v1')
       OR demo_delivery.activation_release() IS NULL
       OR to_regprocedure('limitless_buy.writer_scope(uuid)') IS NULL
    THEN RAISE EXCEPTION 'Expected the closed Limitless finance database'; END IF;
END
$gate$;

CREATE FUNCTION polygon.closed_limitless_runtime_scope(p_session uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $scope$
DECLARE
    binding limitless_buy.bindings;
    result jsonb;
BEGIN
    binding:=limitless_buy.writer_scope(p_session);
    IF binding.session_id IS NULL THEN RETURN NULL; END IF;
    SELECT jsonb_build_object(
      'sessionId',s.id,'ownerId',s.user_id,'traderRevisionId',s.trader_revision_id,
      'settingsRevisionId',binding.settings_id,'wallet',binding.wallet,'maxBuyDebitMicros',binding.buy_cap::text,
      'runId',i.operator_run_id
    ) INTO result
    FROM polygon.paper_sessions s
    JOIN polygon.user_session_slots sl ON (sl.id,sl.user_id,sl.current_session_id)=(s.slot_id,s.user_id,s.id)
    JOIN polygon.venues v ON v.id=s.venue_id AND v.code='limitless'
    JOIN polygon_live.installation i ON i.singleton AND i.database_name=current_database()
    WHERE s.id=binding.session_id AND s.user_id=binding.owner_id AND s.current_settings_revision_id=binding.settings_id
      AND s.lifecycle='active' AND s.evaluation_deadline_at>clock_timestamp();
    RETURN result;
END
$scope$;

ALTER FUNCTION polygon.closed_limitless_runtime_scope(uuid) OWNER TO polygon_owner;
REVOKE ALL ON FUNCTION polygon.closed_limitless_runtime_scope(uuid) FROM PUBLIC,polygon_executor;
COMMIT;
