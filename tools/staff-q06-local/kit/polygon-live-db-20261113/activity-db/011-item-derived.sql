-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE OR REPLACE FUNCTION polygon_live_activity.item(ob polygon_live_activity.observations,d polygon_live_activity.decisions) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE b jsonb;
BEGIN
 SELECT evidence->'binding' INTO b FROM polygon_live_activity.evaluations WHERE observation_id=ob.id AND decision_id=d.id;
 RETURN jsonb_build_object('activityId',d.id,'sequence',ob.sequence::text,
  'source',jsonb_build_object('venueCode','polymarket','externalTraderId',ob.raw_log->'owner','transactionHash',ob.raw_log->'transactionHash',
   'identityStatus','verified_log','sourceOccurredAt',v00_session.utc(to_timestamp((ob.header->>'timestampSeconds')::double precision)),
   'receivedAt',v00_session.utc(ob.received_at),'recordHash',ob.record_hash),
  'trade',jsonb_build_object('conditionId',b->'conditionId','tokenId',ob.raw_log->'tokenId','marketTitle',b->'marketTitle','outcome',b->'outcome','side',ob.raw_log->'side',
   'size',NULL,'price',NULL,'sizeUnit',NULL,'priceUnit',NULL),
  'decision',jsonb_build_object('status',d.status,'reasonCode',d.reason_code,'detailCode',d.detail_code,'decidedAt',v00_session.utc(d.decided_at),
   'policyVersion',d.policy_version,'copy',NULL));
END $$;
