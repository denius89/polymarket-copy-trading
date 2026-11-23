-- Display annotations live beside the immutable financial snapshot.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
SET LOCAL ROLE polygon_owner;

CREATE FUNCTION polygon_buy.position_display_labels(sid uuid, snapshot_data jsonb)
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $labels$
 SELECT COALESCE(jsonb_agg(jsonb_build_object(
    'conditionId',p.value->'conditionId','tokenId',p.value->'tokenId',
    'marketTitle',label.binding->'marketTitle','outcome',label.binding->'outcome') ORDER BY p.ordinal),'[]'::jsonb)
 FROM jsonb_array_elements(snapshot_data->'positions') WITH ORDINALITY p(value,ordinal)
 JOIN LATERAL (
   SELECT v.evidence->'binding' AS binding
   FROM live_buy_core.intents i
   JOIN live_buy_core.executions x ON (x.session_id,x.intent_id)=(i.session_id,i.id)
   JOIN polygon_live_activity.observations o ON (o.session_id,o.id)=(i.session_id,i.observation_id)
   JOIN polygon_live_activity.evaluations v ON (v.session_id,v.observation_id)=(o.session_id,o.id)
   WHERE i.session_id=sid AND i.condition_id=p.value->>'conditionId' AND i.token_id=p.value->>'tokenId'
     AND x.version<=(snapshot_data->>'version')::bigint
     AND o.raw_log->>'side'='BUY' AND o.raw_log->>'tokenId'=i.token_id
     AND v.evidence#>>'{binding,conditionId}'=i.condition_id
     AND v.evidence#>>'{binding,tokenId}'=i.token_id
     AND jsonb_typeof(v.evidence#>'{binding,marketTitle}')='string'
     AND jsonb_typeof(v.evidence#>'{binding,outcome}')='string'
     AND char_length(btrim(v.evidence#>>'{binding,marketTitle}')) BETWEEN 1 AND 2048
     AND char_length(btrim(v.evidence#>>'{binding,outcome}')) BETWEEN 1 AND 256
     AND v.evidence#>>'{binding,marketTitle}' !~ '[[:cntrl:]]'
     AND v.evidence#>>'{binding,outcome}' !~ '[[:cntrl:]]'
   ORDER BY x.version DESC,i.id
   LIMIT 1
 ) label ON true
$labels$;
REVOKE ALL ON FUNCTION polygon_buy.position_display_labels(uuid,jsonb) FROM PUBLIC,polygon_executor;

DO $patch$
DECLARE definition text; declared text; tail text;
BEGIN
 definition:=pg_get_functiondef('polygon.buy_session_read_v1(jsonb)'::regprocedure);
 declared:='DECLARE a jsonb;sid uuid;s polygon.paper_sessions;r polygon_live_activity.release_record;b polygon_buy.bindings;';
 tail:='RETURN jsonb_build_object(''http'',200)||polygon_buy.body(sid);';
 IF cardinality(string_to_array(definition,declared))<>2
   OR cardinality(string_to_array(definition,tail))<>2
 THEN RAISE EXCEPTION 'position read baseline differs'; END IF;
 definition:=replace(definition,declared,declared||' payload jsonb;');
 EXECUTE replace(definition,tail,$body$payload:=polygon_buy.body(sid);
 RETURN jsonb_build_object('http',200,'positionLabels',polygon_buy.position_display_labels(sid,payload->'financial'))||payload;$body$);
END
$patch$;

COMMIT;
