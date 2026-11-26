-- Derive a process profile from a leased C06 request and the bound venue role.
BEGIN;
SET LOCAL search_path=pg_catalog;
SET LOCAL lock_timeout='3s';

DO $gate$
BEGIN
    IF current_database()<>'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker WHERE kind='isolated-public-market-pilot-v1')
       OR demo_delivery.activation_release() IS NULL
    THEN RAISE EXCEPTION 'Expected the closed activation database'; END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.activation_runtime_profile(p_request uuid,p_token uuid)
RETURNS jsonb LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $profile$
    SELECT jsonb_build_object(
      'requestId',a.request_id,'sessionId',s.id,'ownerId',s.user_id,'traderRevisionId',r.trader_revision_id,
      'settingsRevisionId',settings.id,'venue',r.venue,'wallet',r.wallet,'runId',demo_delivery.activation_release(),
      'fixedDebit',jsonb_build_object('n',settings.fixed_n::text,'d',settings.fixed_d::text),
      'sessionExpiresAt',s.evaluation_deadline_at,
      'writerRole',role.rolname
    )
    FROM demo_delivery.activation_requests a
    JOIN demo_delivery.start_receipts r ON (r.outbox_id,r.session_id)=(a.request_id,a.session_id)
    JOIN polygon.paper_sessions s ON (s.id,s.trader_revision_id)=(r.session_id,r.trader_revision_id)
    JOIN polygon.user_session_slots slot
      ON (slot.id,slot.user_id,slot.current_session_id)=(s.slot_id,s.user_id,s.id)
    JOIN polygon.settings_revisions settings ON (settings.id,settings.session_id)=(s.current_settings_revision_id,s.id)
    JOIN demo_delivery.session_writers w
      ON w.session_id=s.id AND w.writer_oid=demo_delivery.app_financial_writer(s.id,r.venue)
    JOIN pg_roles role ON role.oid=w.writer_oid
    WHERE a.request_id=p_request AND a.token=p_token AND a.lease_until>clock_timestamp()+interval '25 seconds'
      AND a.activated_at IS NULL AND s.lifecycle='active'
      AND s.evaluation_deadline_at>clock_timestamp()+interval '15 seconds'
      AND settings.sizing_mode='fixed' AND settings.fixed_n>0 AND settings.fixed_d>0
$profile$;

ALTER FUNCTION demo_delivery.activation_runtime_profile(uuid,uuid) OWNER TO polygon_owner;
REVOKE ALL ON FUNCTION demo_delivery.activation_runtime_profile(uuid,uuid) FROM PUBLIC,polygon_executor;
COMMIT;
