-- Reuse the mandatory deferred Activity validator already installed for Tokor.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind = 'isolated-public-market-pilot-v1')
       OR encode(sha256(convert_to(pg_get_functiondef(
          'polygon_live_activity.finish_queued_buy()'::regprocedure),'UTF8')),'hex')
          IS DISTINCT FROM '30493dde67e2af81ccec615daadfdba3492237ed291d15a39aa4fed7cf48bac0'
       OR NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid='polygon_live_activity.checked_buy_flush'::regclass
                      AND tgfoid='polygon_live_activity.finish_queued_buy()'::regprocedure
                      AND tgenabled='O' AND tgdeferrable AND tginitdeferred
                      HAVING count(*) = 9)
    THEN RAISE EXCEPTION 'Expected the existing Tokor deferred-validation profile'; END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.queue_waiting_range_validation(p_session uuid,p_operation uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $queue$
DECLARE
    transaction_id xid8 := pg_current_xact_id_if_assigned();
BEGIN
    IF current_setting('transaction_isolation') <> 'serializable'
       OR p_session IS DISTINCT FROM '1c6d9f24-0f84-4a13-82f2-e712ff6919cf'::uuid
       OR transaction_id IS NULL OR demo_delivery.closed_polygon_scope(p_session) IS NULL
       OR NOT EXISTS (
           SELECT
           FROM polygon_live_activity.stream st
           JOIN polygon_live_activity.operations op
             ON (op.session_id,op.id)=(st.session_id,st.last_range_operation_id)
           JOIN polygon_live_activity.observations ob ON (ob.session_id,ob.operation_id)=(op.session_id,op.id)
           JOIN polygon_live_activity.decisions d ON (d.session_id,d.observation_id)=(ob.session_id,ob.id)
           WHERE st.session_id=p_session AND st.status='observing'
             AND st.last_operation_id=p_operation AND op.id=p_operation
             AND op.kind='ingest' AND op.result->>'kind'='ingest'
             AND op.xmin=transaction_id::xid AND ob.xmin=transaction_id::xid AND d.xmin=transaction_id::xid
             AND d.checks->>'executionAdmission'='awaiting_quote'
             AND demo_delivery.polygon_waiting_valid(ob.id,d.checks->'evidence',true)
       )
    THEN RETURN false; END IF;

    INSERT INTO polygon_live_activity.checked_buy_flush(transaction_id,session_id,deferred_buy)
    VALUES (transaction_id,p_session,true);
    RETURN true;
END
$queue$;

REVOKE ALL ON FUNCTION demo_delivery.queue_waiting_range_validation(uuid,uuid)
    FROM PUBLIC,polygon_executor;
DO $grant$
DECLARE writer_name name;
BEGIN
    SELECT a.writer_role INTO STRICT writer_name
    FROM demo_delivery.closed_polygon_source s
    JOIN polygon_live_activity.assignments a
      ON (a.session_id,a.run_id,a.writer_oid,a.owner_address) =
         (s.session_id,s.run_id,s.writer_oid,s.wallet)
    WHERE s.session_id='1c6d9f24-0f84-4a13-82f2-e712ff6919cf'::uuid
      AND a.writer_role::regrole::oid=a.writer_oid AND polygon_live_activity.role_valid(a.writer_oid);
    EXECUTE format('GRANT EXECUTE ON FUNCTION demo_delivery.queue_waiting_range_validation(uuid,uuid) TO %I',
                   writer_name);
END
$grant$;
COMMIT;
