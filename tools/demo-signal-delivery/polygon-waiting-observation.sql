-- Install in an isolated copy with the closed source and pending-job migrations.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker
                      WHERE kind = 'isolated-public-market-pilot-v1')
    THEN RAISE EXCEPTION 'Expected the isolated Polygon delivery queue'; END IF;
END
$gate$;

CREATE FUNCTION demo_delivery.polygon_waiting_shape(e jsonb)
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path = pg_catalog AS $shape$
    SELECT coalesce(polygon.exact_keys(e,ARRAY['schemaVersion','kind','signalId','binding','evidenceSha256'])
      AND e->>'schemaVersion' = 'polygon-queue-waiting-v1' AND e->>'kind' = 'awaiting_quote'
      AND jsonb_typeof(e->'signalId') = 'string' AND e->>'signalId' ~ '^[1-9][0-9]{0,17}$'
      AND e->'binding' = 'null'::jsonb AND polygon_live_activity.sha_value(e->'evidenceSha256'),false)
$shape$;

-- Historical rows still match after the queue is completed. Initial inserts
-- additionally require the current scoped writer and an unfinished job.
CREATE FUNCTION demo_delivery.polygon_waiting_valid(ob_id uuid, e jsonb, initial boolean)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $valid$
    SELECT demo_delivery.polygon_waiting_shape(e) AND EXISTS (
        SELECT FROM polygon_live_activity.observations o
        JOIN demo_delivery.jobs j ON j.session_id = o.session_id
        JOIN demo_delivery.closed_polygon_source enrolled ON enrolled.session_id = o.session_id
        JOIN demo_delivery.signals s ON s.id = j.signal_id AND s.trader_key = enrolled.wallet
        WHERE o.id = ob_id AND o.classification = 'accepted' AND o.raw_log->>'side' = 'BUY'
          AND s.id = (CASE WHEN demo_delivery.polygon_waiting_shape(e) THEN e->>'signalId' END)::bigint
          AND s.venue = 'polymarket' AND s.payload->>'kind' = 'polygon-finalized-buy'
          AND s.execution_key = '137:' || o.transaction_hash || ':' || o.log_index::text
          AND s.payload->'log' = o.raw_log AND s.payload->'header' = o.header
          AND e->>'evidenceSha256' = o.raw_log->>'receiptSha256'
          AND (NOT initial OR (j.finished_at IS NULL
               AND demo_delivery.closed_polygon_scope(o.session_id) IS NOT NULL))
    )
$valid$;

DO $patch$
DECLARE definition text;
BEGIN
    definition := pg_get_functiondef('polygon_live_activity.evidence_shape(jsonb)'::regprocedure);
    IF cardinality(string_to_array(definition, 'SELECT ')) <> 2
    THEN RAISE EXCEPTION 'Unexpected Polygon evidence shape'; END IF;
    EXECUTE replace(definition,'SELECT ','SELECT demo_delivery.polygon_waiting_shape(v) OR ');

    definition := pg_get_functiondef('polygon_live_activity.write_decision(uuid,jsonb,timestamptz)'::regprocedure);
    IF cardinality(string_to_array(definition,'pending:=polygon_buy.pending_shape(e);')) <> 2
       OR cardinality(string_to_array(definition,'CASE WHEN pending THEN ''queued'' ELSE ''blocked'' END')) <> 2
    THEN RAISE EXCEPTION 'Unexpected Polygon decision writer'; END IF;
    definition := replace(definition,'pending:=polygon_buy.pending_shape(e);',
      'pending:=polygon_buy.pending_shape(e) OR demo_delivery.polygon_waiting_shape(e);');
    definition := replace(definition,'(pending AND polygon_buy.pending_valid(oid,e,t) IS DISTINCT FROM true)',
      '(pending AND polygon_buy.pending_valid(oid,e,t) IS DISTINCT FROM true
        AND demo_delivery.polygon_waiting_valid(oid,e,true) IS DISTINCT FROM true)');
    EXECUTE replace(definition,'CASE WHEN pending THEN ''queued'' ELSE ''blocked'' END',
      'CASE WHEN demo_delivery.polygon_waiting_shape(e) THEN ''awaiting_quote''
            WHEN pending THEN ''queued'' ELSE ''blocked'' END');

    definition := pg_get_functiondef('polygon_live_activity.bound_state_valid(uuid)'::regprocedure);
    IF cardinality(string_to_array(definition,'AND polygon_buy.pending_valid(ob.id,ev.evidence,ev.created_at)))')) <> 2
    THEN RAISE EXCEPTION 'Unexpected Polygon bound integrity check'; END IF;
    EXECUTE replace(definition,'AND polygon_buy.pending_valid(ob.id,ev.evidence,ev.created_at)))',
      'AND polygon_buy.pending_valid(ob.id,ev.evidence,ev.created_at))
       OR (de.policy_version=''paper-buy-queued-v1'' AND de.status=''pending''
         AND de.reason_code IS NULL AND de.detail_code IS NULL
         AND de.checks=jsonb_build_object(''evidence'',ev.evidence,''executionAdmission'',''awaiting_quote'')
         AND demo_delivery.polygon_waiting_valid(ob.id,ev.evidence,false)))');

    -- The installed personal writer records an immutable skip disposition by
    -- default. A canonical waiting row is neither a skip nor a quote admission.
    IF to_regprocedure('polygon_buy.guard_decision_gap()') IS NOT NULL THEN
        definition := pg_get_functiondef('polygon_buy.guard_decision_gap()'::regprocedure);
        IF cardinality(string_to_array(definition,'IF NOT polygon_buy.decision_gap_scope(NEW.session_id) THEN')) <> 2
        THEN RAISE EXCEPTION 'Unexpected Polygon skip disposition guard'; END IF;
        EXECUTE replace(definition,'IF NOT polygon_buy.decision_gap_scope(NEW.session_id) THEN',
          'IF demo_delivery.polygon_waiting_shape(e) AND NEW.status=''pending''
               AND demo_delivery.polygon_waiting_valid(NEW.observation_id,e,true)
           THEN RETURN NEW; END IF;
           IF NOT polygon_buy.decision_gap_scope(NEW.session_id) THEN');
    END IF;
END
$patch$;

GRANT USAGE ON SCHEMA demo_delivery TO polygon_owner;
REVOKE ALL ON FUNCTION demo_delivery.polygon_waiting_shape(jsonb),
    demo_delivery.polygon_waiting_valid(uuid,jsonb,boolean) FROM PUBLIC,polygon_executor;
GRANT EXECUTE ON FUNCTION demo_delivery.polygon_waiting_shape(jsonb),
    demo_delivery.polygon_waiting_valid(uuid,jsonb,boolean) TO polygon_owner;

CREATE TABLE demo_delivery.polygon_waiting_expiries (
    session_id uuid NOT NULL,
    signal_id bigint NOT NULL,
    observation_id uuid NOT NULL UNIQUE REFERENCES polygon_live_activity.observations(id),
    expired_at timestamptz NOT NULL,
    PRIMARY KEY (signal_id,session_id),
    FOREIGN KEY (signal_id,session_id) REFERENCES demo_delivery.jobs
);
CREATE TRIGGER polygon_waiting_expiries_immutable
    BEFORE UPDATE OR DELETE ON demo_delivery.polygon_waiting_expiries
    FOR EACH ROW EXECUTE FUNCTION live_buy_core.immutable();
GRANT SELECT ON demo_delivery.polygon_waiting_expiries TO polygon_owner;

CREATE FUNCTION demo_delivery.complete_polygon_expiry(p_session uuid,p_signal bigint,p_token uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $expiry$
DECLARE
    target uuid;
BEGIN
    IF current_setting('transaction_isolation') <> 'serializable'
       OR demo_delivery.closed_polygon_scope(p_session) IS NULL
       OR (polygon_buy.writer(p_session)->>'http') IS DISTINCT FROM '200'
    THEN RETURN false; END IF;

    SELECT o.id INTO target
    FROM demo_delivery.jobs j
    JOIN demo_delivery.signals s ON s.id = j.signal_id
    JOIN polygon_live_activity.observations o ON o.session_id = j.session_id
       AND o.raw_log = s.payload->'log' AND o.header = s.payload->'header'
    JOIN polygon_live_activity.decisions d ON (d.session_id,d.observation_id) = (o.session_id,o.id)
    WHERE (j.signal_id,j.session_id,j.lease_token) = (p_signal,p_session,p_token)
      AND j.finished_at IS NULL AND j.lease_until > clock_timestamp()
      AND s.expires_at <= clock_timestamp()
      AND d.checks->>'executionAdmission' = 'awaiting_quote'
      AND d.checks#>>'{evidence,signalId}' = s.id::text
      AND demo_delivery.polygon_waiting_valid(o.id,d.checks->'evidence',false)
      AND NOT EXISTS (SELECT FROM live_buy_core.intents i WHERE (i.session_id,i.observation_id) = (o.session_id,o.id))
      AND NOT EXISTS (SELECT FROM polygon_buy.admissions a WHERE
          (a.session_id,a.transaction_hash,a.log_index) = (o.session_id,o.transaction_hash,o.log_index)
          AND a.expires_at > clock_timestamp())
    FOR UPDATE OF j;
    IF target IS NULL THEN RETURN false; END IF;
    INSERT INTO demo_delivery.polygon_waiting_expiries VALUES (p_session,p_signal,target,clock_timestamp());
    UPDATE demo_delivery.jobs SET finished_at = clock_timestamp(),finish_reason = 'acknowledged',
        lease_token = NULL,lease_until = NULL WHERE (signal_id,session_id) = (p_signal,p_session);
    PERFORM pg_notify('demo_delivery_ready','');
    RETURN true;
END
$expiry$;
REVOKE ALL ON FUNCTION demo_delivery.complete_polygon_expiry(uuid,bigint,uuid)
    FROM PUBLIC,polygon_executor;

CREATE FUNCTION demo_delivery.polygon_waiting_open(ob_id uuid,e jsonb)
RETURNS boolean LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $open$
    SELECT demo_delivery.polygon_waiting_valid(ob_id,e,true) AND EXISTS (
        SELECT FROM polygon_live_activity.observations o
        JOIN demo_delivery.jobs j ON j.session_id = o.session_id
        JOIN demo_delivery.signals s ON s.id = j.signal_id
        WHERE o.id = ob_id AND s.id::text = e->>'signalId' AND j.finished_at IS NULL
          AND j.lease_until > clock_timestamp() AND s.expires_at > clock_timestamp()
          AND j.lease_token::text = current_setting('demo_delivery.polygon_lease',true)
    )
$open$;
REVOKE ALL ON FUNCTION demo_delivery.polygon_waiting_open(uuid,jsonb) FROM PUBLIC,polygon_executor;
GRANT EXECUTE ON FUNCTION demo_delivery.polygon_waiting_open(uuid,jsonb) TO polygon_owner;

DO $admission$
DECLARE
    definition text;
    kind text := 'OR de.policy_version IS DISTINCT FROM ''paper-buy-queued-v1'' OR de.status IS DISTINCT FROM ''pending''';
    guard text := 'AND d.policy_version=''paper-buy-queued-v1'' AND e.evidence->>''admissionId''=v.reserve_id::text;';
    order_prefix text := 'd.policy_version=''paper-buy-queued-v1'' AND NOT EXISTS';
    order_guard text := 'd.policy_version=''paper-buy-queued-v1''
      AND NOT EXISTS (SELECT FROM demo_delivery.polygon_waiting_expiries skipped
                      WHERE (skipped.session_id,skipped.observation_id)=(d.session_id,d.observation_id))
      AND NOT EXISTS';
BEGIN
    definition := pg_get_functiondef('polygon_buy.dispatch(jsonb,text)'::regprocedure);
    IF cardinality(string_to_array(definition,kind)) <> 2
    THEN RAISE EXCEPTION 'Unexpected Polygon financial dispatch'; END IF;
    definition := replace(definition,kind,kind || '
      OR (de.checks->>''executionAdmission''=''awaiting_quote''
          AND NOT demo_delivery.polygon_waiting_open(ob.id,de.checks->''evidence''))');
    IF cardinality(string_to_array(definition, 'AND NOT EXISTS(SELECT FROM live_buy_core.intents x WHERE x.session_id=sid AND x.observation_id=d.observation_id)')) <> 2
    THEN RAISE EXCEPTION 'Unexpected Polygon dispatch ordering'; END IF;
    EXECUTE replace(definition,
        'AND NOT EXISTS(SELECT FROM live_buy_core.intents x WHERE x.session_id=sid AND x.observation_id=d.observation_id)',
        'AND NOT EXISTS (SELECT FROM demo_delivery.polygon_waiting_expiries skipped
                         WHERE (skipped.session_id,skipped.observation_id)=(d.session_id,d.observation_id))
         AND NOT EXISTS(SELECT FROM live_buy_core.intents x WHERE x.session_id=sid AND x.observation_id=d.observation_id)');

    IF to_regprocedure('polygon.personal_quote_apply_v1(uuid,text)') IS NOT NULL THEN
        definition := pg_get_functiondef('polygon.personal_quote_apply_v1(uuid,text)'::regprocedure);
        IF cardinality(string_to_array(definition,guard)) <> 2
           OR cardinality(string_to_array(definition,order_prefix)) <> 2
        THEN RAISE EXCEPTION 'Unexpected Polygon personal quote application'; END IF;
        definition := replace(definition,guard,
          'AND d.policy_version=''paper-buy-queued-v1''
           AND (e.evidence->>''admissionId''=v.reserve_id::text OR
             (d.checks->>''executionAdmission''=''awaiting_quote''
              AND (ad.token_id,ad.condition_id)=(ob.raw_log->>''tokenId'',q#>>''{event,marketId}'')
              AND demo_delivery.polygon_waiting_open(ob.id,e.evidence)));');
        EXECUTE replace(definition,order_prefix,order_guard);
    END IF;
END
$admission$;

DO $projection$
DECLARE
    definition text := pg_get_functiondef('polygon_buy.item(polygon_live_activity.observations,polygon_live_activity.decisions)'::regprocedure);
    marker text := 'IF d.policy_version=''paper-bound-skip-v1'' THEN RETURN body;END IF;';
BEGIN
    IF cardinality(string_to_array(definition,marker)) <> 2
    THEN RAISE EXCEPTION 'Unexpected Polygon Activity projection'; END IF;
    EXECUTE replace(definition,marker,marker || '
        IF d.checks->>''executionAdmission''=''awaiting_quote'' THEN
            IF EXISTS (SELECT FROM demo_delivery.polygon_waiting_expiries skipped
                       WHERE (skipped.session_id,skipped.observation_id)=(ob.session_id,ob.id)) THEN
                RETURN body || jsonb_build_object(''decision'', (body->''decision'') ||
                    jsonb_build_object(''status'',''skipped'',''reasonCode'',''context_invalid'',
                                       ''detailCode'',''signal_expired'',''copy'',NULL));
            END IF;
            IF NOT EXISTS (SELECT FROM live_buy_core.intents waiting
                WHERE (waiting.session_id,waiting.observation_id)=(ob.session_id,ob.id))
            THEN RETURN body; END IF;
        END IF;');
END
$projection$;
COMMIT;
