-- Scoped derivative of frozen Activity v2 / bound-skip v2; no legacy schema mutation.
CREATE FUNCTION polygon_live_activity.text_match(v jsonb,pattern text) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(jsonb_typeof(v)='string' AND (v#>>'{}')~pattern,false)
$$;
CREATE FUNCTION polygon_live_activity.uint(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 IF NOT polygon_live_activity.text_match(v,'^(0|[1-9][0-9]{0,77})$') THEN RETURN false; END IF;
 RETURN (v#>>'{}')::numeric<=115792089237316195423570985008687907853269984665640564039457584007913129639935;
END $$;
CREATE FUNCTION polygon_live_activity.uuid_value(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT polygon_live_activity.text_match(v,'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
$$;
CREATE FUNCTION polygon_live_activity.hash_value(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT polygon_live_activity.text_match(v,'^0x[0-9a-f]{64}$')
$$;
CREATE FUNCTION polygon_live_activity.sha_value(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT polygon_live_activity.text_match(v,'^[0-9a-f]{64}$')
$$;
CREATE FUNCTION polygon_live_activity.time_value(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE t timestamptz;
BEGIN
 IF NOT polygon_live_activity.text_match(v,'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$') THEN RETURN false; END IF;
 t:=(v#>>'{}')::timestamptz;
 RETURN to_char(t AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')=v#>>'{}';
EXCEPTION WHEN datetime_field_overflow OR invalid_datetime_format THEN RETURN false;
END $$;
CREATE FUNCTION polygon_live_activity.header(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(polygon.exact_keys(v,ARRAY['number','hash','parentHash','timestampSeconds'])
  AND polygon_live_activity.uint(v->'number') AND polygon_live_activity.uint(v->'timestampSeconds')
  AND polygon_live_activity.hash_value(v->'hash') AND polygon_live_activity.hash_value(v->'parentHash'),false)
$$;
CREATE FUNCTION polygon_live_activity.checkpoint(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(polygon.exact_keys(v,ARRAY['number','hash']) AND polygon_live_activity.uint(v->'number')
  AND polygon_live_activity.hash_value(v->'hash'),false)
$$;
CREATE FUNCTION polygon_live_activity.cp(v jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('number',v->'number','hash',v->'hash')
$$;
CREATE FUNCTION polygon_live_activity.log_shape(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE k text;
BEGIN
 IF polygon.exact_keys(v,ARRAY['transactionHash','logIndex','blockNumber','blockHash','orderHash','owner','counterparty',
  'side','tokenId','makerAmountFilledRaw','takerAmountFilledRaw','feeRaw','builder','metadata','rawLogSha256','receiptSha256']) IS DISTINCT FROM true THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['transactionHash','blockHash','orderHash','builder','metadata'] LOOP
  IF NOT polygon_live_activity.hash_value(v->k) THEN RETURN false; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['owner','counterparty'] LOOP
  IF NOT polygon_live_activity.text_match(v->k,'^0x[0-9a-f]{40}$') THEN RETURN false; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['logIndex','blockNumber','tokenId','makerAmountFilledRaw','takerAmountFilledRaw','feeRaw'] LOOP
  IF NOT polygon_live_activity.uint(v->k) THEN RETURN false; END IF;
 END LOOP;
 RETURN COALESCE(v->>'side' IN('BUY','SELL') AND polygon_live_activity.sha_value(v->'rawLogSha256')
  AND polygon_live_activity.sha_value(v->'receiptSha256'),false);
END $$;
CREATE FUNCTION polygon_live_activity.semantic(v jsonb,h jsonb) RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT array_to_string(ARRAY['shadow-chain-log-semantic-v1','137','0xe111180000d2663c0091e4f400237545b87b996b',
 'polygon-137-ctfv2-orderfilled-owner-v1',v->>'transactionHash',v->>'logIndex',v->>'owner',v->>'blockNumber',v->>'blockHash',
 h->>'timestampSeconds',v->>'orderHash',v->>'counterparty',v->>'side',v->>'tokenId',v->>'makerAmountFilledRaw',
 v->>'takerAmountFilledRaw',v->>'feeRaw',v->>'builder',v->>'metadata'],chr(10))||chr(10)
$$;
CREATE FUNCTION polygon_live_activity.digest(v text) RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT encode(sha256(convert_to(v,'UTF8')),'hex')
$$;
CREATE FUNCTION polygon_live_activity.request_shape(p jsonb,kind text) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE v jsonb;
BEGIN
 IF p IS NULL OR jsonb_typeof(p)<>'object' OR octet_length(p::text)>1048576
  OR NOT polygon_live_activity.uuid_value(p->'runId') OR NOT polygon_live_activity.uuid_value(p->'operationId')
  OR NOT polygon_live_activity.uuid_value(p->'sessionId') THEN RETURN false; END IF;
 CASE kind
 WHEN 'lookup' THEN RETURN polygon.exact_keys(p,ARRAY['runId','operationId','sessionId']);
 WHEN 'arm' THEN RETURN polygon.exact_keys(p,ARRAY['runId','operationId','sessionId','baseline','baselineReceivedAt','evidenceSha256'])
  AND polygon_live_activity.header(p->'baseline') AND polygon_live_activity.time_value(p->'baselineReceivedAt')
  AND polygon_live_activity.sha_value(p->'evidenceSha256');
 WHEN 'stop' THEN RETURN polygon.exact_keys(p,ARRAY['runId','operationId','sessionId','status','evidenceSha256'])
  AND COALESCE(p->>'status' IN('stopped','source_unavailable','reconciliation_required'),false)
  AND polygon_live_activity.sha_value(p->'evidenceSha256');
 WHEN 'ingest' THEN
  IF polygon.exact_keys(p,ARRAY['runId','operationId','sessionId','previous','baselineCanonicalHash','finalized','headers','observedAt','evidenceSha256','logs']) IS DISTINCT FROM true
   OR NOT polygon_live_activity.checkpoint(p->'previous') OR NOT polygon_live_activity.hash_value(p->'baselineCanonicalHash')
   OR NOT polygon_live_activity.header(p->'finalized') OR NOT polygon_live_activity.time_value(p->'observedAt')
   OR NOT polygon_live_activity.sha_value(p->'evidenceSha256')
   OR jsonb_typeof(p->'headers') IS DISTINCT FROM 'array' OR jsonb_typeof(p->'logs') IS DISTINCT FROM 'array'
  THEN RETURN false; END IF;
  IF jsonb_array_length(p->'headers') NOT BETWEEN 1 AND 64 OR jsonb_array_length(p->'logs')>128 THEN RETURN false; END IF;
  FOR v IN SELECT value FROM jsonb_array_elements(p->'headers') LOOP
   IF NOT polygon_live_activity.header(v) THEN RETURN false; END IF;
  END LOOP;
  FOR v IN SELECT value FROM jsonb_array_elements(p->'logs') LOOP
   IF NOT polygon_live_activity.log_shape(v) THEN RETURN false; END IF;
  END LOOP;
  RETURN true;
 ELSE RETURN false;
 END CASE;
END $$;
