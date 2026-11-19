\set ON_ERROR_STOP on
-- Independent constants for accepted T01/T02 boundaries. Offline clone only.
BEGIN;
DO $$ BEGIN IF current_setting('polygon.disposable_test',true) IS DISTINCT FROM 'offline-clone' THEN RAISE EXCEPTION 'offline clone required'; END IF; END $$;
CREATE TEMP TABLE numeric_checks(label text PRIMARY KEY);
CREATE FUNCTION pg_temp.assert_true(ok boolean, label text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'numeric assertion failed: %',label; END IF; INSERT INTO numeric_checks VALUES(label); END $$;
CREATE FUNCTION pg_temp.encode_form(p jsonb) RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE k text;
BEGIN
 FOREACH k IN ARRAY ARRAY['rawBudget','rawFixedAmount','rawCopyPercent','rawMarketLimitPercent','rawDailyBuyLimitPercent'] LOOP
  p:=jsonb_set(p,ARRAY[k],COALESCE(to_jsonb(replace(encode(convert_to(p->>k,'UTF8'),'base64'),E'\n','')),'null'::jsonb));
 END LOOP;
 RETURN p;
END $$;
DO $$
DECLARE policy polygon.paper_policy_versions; base jsonb; p jsonb; r jsonb; sample text; i integer:=0; failed boolean;
BEGIN
 SELECT * INTO STRICT policy FROM polygon.paper_policy_versions;
 base:='{"selectedMode":"fixed","rawBudget":"200","rawFixedAmount":"20","rawCopyPercent":"bad inactive","rawMarketLimitPercent":"10","rawDailyBuyLimitPercent":"15"}';
 r:=polygon.numeric_settings(pg_temp.encode_form(base),policy);
 PERFORM pg_temp.assert_true(r->>'normalizationValid'='true' AND r->'fieldErrors'='[]'::jsonb,'fixed_valid_ignores_inactive');
 FOREACH sample IN ARRAY ARRAY['20','020','20.00','20,000'] LOOP
  i:=i+1; r:=polygon.numeric_settings(pg_temp.encode_form(base||jsonb_build_object('rawFixedAmount',sample)),policy);
  PERFORM pg_temp.assert_true(r->'fixedAmount'='{"n":"20","d":"1"}'::jsonb,'equivalent_numeric_distinct_raw_'||i);
 END LOOP;
 i:=0;
 FOREACH sample IN ARRAY ARRAY[' 200','200 ','+200','-200','2e2','NaN','Infinity','.5','20.','2,0.0','２００','٢٠٠'] LOOP
  i:=i+1; r:=polygon.numeric_settings(pg_temp.encode_form(base||jsonb_build_object('rawBudget',sample)),policy);
  PERFORM pg_temp.assert_true(r#>>'{fieldErrors,0,code}'='INVALID_DECIMAL' AND jsonb_array_length(r->'fieldErrors')=1,'invalid_ascii_grammar_'||i);
 END LOOP;
 r:=polygon.numeric_settings(pg_temp.encode_form(base||'{"rawBudget":null}'),policy);
 PERFORM pg_temp.assert_true(r#>>'{fieldErrors,0,code}'='REQUIRED' AND r->'budget'='null'::jsonb,'null_is_required');
 r:=polygon.numeric_settings(pg_temp.encode_form(base||'{"rawBudget":""}'),policy);
 PERFORM pg_temp.assert_true(r#>>'{fieldErrors,0,code}'='REQUIRED','empty_is_required');
 r:=polygon.numeric_settings(pg_temp.encode_form(base||'{"rawBudget":"1,000"}'),policy);
 PERFORM pg_temp.assert_true(r#>'{fieldErrors,0}'='{"field":"rawBudget","code":"OUT_OF_RANGE","params":{"min":{"n":"100","d":"1"},"max":{"n":"1000","d":"1"},"unit":"virtual_USD"}}'::jsonb,'comma_is_decimal_not_thousands');
 r:=polygon.numeric_settings(pg_temp.encode_form(base||'{"rawBudget":"105"}'),policy);
 PERFORM pg_temp.assert_true(r#>'{fieldErrors,0}'='{"field":"rawBudget","code":"INVALID_STEP","params":{"step":{"n":"10","d":"1"},"origin":{"n":"100","d":"1"},"unit":"virtual_USD"}}'::jsonb,'budget_step_origin');
 r:=polygon.numeric_settings(pg_temp.encode_form(base||'{"rawFixedAmount":"21"}'),policy);
 PERFORM pg_temp.assert_true(r#>'{fieldErrors,0}'='{"field":"rawFixedAmount","code":"FIXED_LIMIT_EXCEEDED","params":{"max":{"n":"20","d":"1"},"unit":"virtual_USD"}}'::jsonb,'fixed_dependent_cap');
 r:=polygon.numeric_settings(pg_temp.encode_form(base||'{"rawFixedAmount":"201"}'),policy);
 PERFORM pg_temp.assert_true(r#>>'{fieldErrors,0,code}'='OUT_OF_RANGE','absolute_range_precedes_dependent_cap');
 r:=polygon.numeric_settings(pg_temp.encode_form(base||'{"rawBudget":"bad","rawFixedAmount":"21"}'),policy);
 PERFORM pg_temp.assert_true(jsonb_array_length(r->'fieldErrors')=1 AND r#>>'{fieldErrors,0,field}'='rawBudget','invalid_dependency_no_invented_cap');
 p:=base||'{"selectedMode":"percent","rawFixedAmount":"bad inactive","rawCopyPercent":"3,50"}';
 r:=polygon.numeric_settings(pg_temp.encode_form(p),policy);
 PERFORM pg_temp.assert_true(r->>'normalizationValid'='true' AND r->>'copyPercent'='3.50' AND r->'fixedAmount'='null'::jsonb,'percent_exact_and_inactive_fixed');
 r:=polygon.numeric_settings(pg_temp.encode_form(p||'{"rawCopyPercent":"3.2"}'),policy);
 PERFORM pg_temp.assert_true(r#>'{fieldErrors,0}'='{"field":"rawCopyPercent","code":"INVALID_STEP","params":{"step":"0.50","origin":"1.00","unit":"percentage_points"}}'::jsonb,'percent_half_point_step');
 r:=polygon.numeric_settings(pg_temp.encode_form(p||'{"rawBudget":"110","rawMarketLimitPercent":"7","rawDailyBuyLimitPercent":"13"}'),policy);
 PERFORM pg_temp.assert_true(r->'effectiveMarketLimit'='{"n":"77","d":"10"}'::jsonb AND r->'effectiveDailyBuyLimit'='{"n":"143","d":"10"}'::jsonb,'reduced_fraction_exact');
 r:=polygon.numeric_settings(pg_temp.encode_form(p||'{"rawMarketLimitPercent":"20","rawDailyBuyLimitPercent":"10"}'),policy);
 PERFORM pg_temp.assert_true(r->>'normalizationValid'='true','market_above_daily_allowed');
 r:=polygon.numeric_settings(pg_temp.encode_form(base||'{"selectedMode":null}'),policy);
 PERFORM pg_temp.assert_true(r->>'normalizationValid'='false' AND r->'fieldErrors'='[]'::jsonb AND r->'fixedAmount'='null'::jsonb,'no_default_mode');
 r:=polygon.numeric_settings(pg_temp.encode_form(p||'{"rawBudget":"bad","rawCopyPercent":"bad","rawMarketLimitPercent":"bad","rawDailyBuyLimitPercent":"bad"}'),policy);
 PERFORM pg_temp.assert_true((SELECT jsonb_agg(value->>'field') FROM jsonb_array_elements(r->'fieldErrors'))=
  '["rawBudget","rawCopyPercent","rawMarketLimitPercent","rawDailyBuyLimitPercent"]'::jsonb,'four_errors_fixed_order');
 p:=pg_temp.encode_form(base); p:=p||jsonb_build_object('rawBudget',encode(decode('32303000','hex'),'base64'));
 r:=polygon.numeric_settings(p,policy);
 PERFORM pg_temp.assert_true(r#>>'{fieldErrors,0,code}'='INVALID_DECIMAL' AND polygon.raw_bytes(p->>'rawBudget')=decode('32303000','hex'),'nul_raw_preserved_invalid_decimal');
 PERFORM pg_temp.assert_true(polygon.raw_encoded(polygon.raw_bytes(''))='' AND polygon.raw_bytes(NULL) IS NULL,'empty_and_null_codec_distinct');
 failed:=false; BEGIN PERFORM polygon.raw_bytes('MjA'); EXCEPTION WHEN OTHERS THEN failed:=true; END;
 PERFORM pg_temp.assert_true(failed,'base64_padding_required');
 failed:=false; BEGIN PERFORM polygon.raw_bytes('/w=='); EXCEPTION WHEN OTHERS THEN failed:=true; END;
 PERFORM pg_temp.assert_true(failed,'invalid_utf8_rejected');
 failed:=false; BEGIN PERFORM polygon.raw_bytes('7aCA'); EXCEPTION WHEN OTHERS THEN failed:=true; END;
 PERFORM pg_temp.assert_true(failed,'utf8_surrogate_rejected');
 failed:=false; BEGIN PERFORM polygon.raw_bytes(replace(encode(convert_to(repeat('x',65),'UTF8'),'base64'),E'\n','')); EXCEPTION WHEN OTHERS THEN failed:=true; END;
 PERFORM pg_temp.assert_true(failed,'65_scalars_rejected');
 PERFORM pg_temp.assert_true(octet_length(polygon.raw_bytes(replace(encode(convert_to(repeat('😀',64),'UTF8'),'base64'),E'\n','')))=256,'64_non_bmp_scalars_preserved');
 PERFORM pg_temp.assert_true(polygon.raw_bytes(replace(encode(decode(repeat('00',64),'hex'),'base64'),E'\n',''))=decode(repeat('00',64),'hex'),'64_nul_scalars_preserved');
 -- Independent Python json.dumps(sort_keys, ensure_ascii=False, compact)+SHA256
 -- oracle for this ASCII-key/no-float JCS domain. Raw includes NUL/emoji/quote/backslash/LF.
 p:=pg_temp.encode_form(base||'{"requestSchemaVersion":"v1","clientCommandId":"22222222-2222-4222-8222-222222222222","locale":"ru","step":"configure","entryContext":null,"venueId":null,"traderId":null,"proposedTimezone":"UTC"}');
 p:=p||jsonb_build_object('rawCopyPercent',encode(decode('00f09f9880225c0a','hex'),'base64'));
 PERFORM pg_temp.assert_true(encode(polygon.command_hash('11111111-1111-4111-8111-111111111111','C04','create',NULL,p),'hex')=
  '4a6dd629b94a495d2a83f278825af9c6cb3c06dc455c143d6114ca89d7218a3f','jcs_hash_public_raw_nul_unicode');
 PERFORM pg_temp.assert_true(polygon.command_hash('11111111-1111-4111-8111-111111111111','C04','create',NULL,p)<>
  polygon.command_hash('11111111-1111-4111-8111-111111111111','C04','create',NULL,p||'{"rawFixedAmount":"MjAuMDA="}'),'hash_distinguishes_20_and_20_decimal');
END $$;
SELECT jsonb_build_object('suite','polygon-paper-numeric-v1','passed',count(*),'labels',jsonb_agg(label ORDER BY label)) FROM numeric_checks;
ROLLBACK;
