-- Included by 001. Exact e4224c6 C05 with only source-dependent warning expression.
CREATE OR REPLACE FUNCTION polygon.c05_validate(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; b jsonb:=p->'request'; d polygon.drafts; ctl polygon.paper_controls; policy polygon.paper_policy_versions;
 tr polygon.traders; src polygon.catalog_sources; slot polygon.user_session_slots; review polygon.setup_reviews;
 calc jsonb; reasons jsonb:='[]'; cap text; t timestamptz;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','request']) OR NOT polygon.exact_keys(b,ARRAY['requestSchemaVersion','draftId','expectedDraftVersion','proposedTimezone'])
  OR b->>'requestSchemaVersion' IS DISTINCT FROM 'v1' OR NOT polygon.uuid_text(b->>'draftId') OR NOT polygon.version_text(b->>'expectedDraftVersion')
  OR jsonb_typeof(b->'expectedDraftVersion')<>'string'
  OR jsonb_typeof(b->'proposedTimezone') NOT IN ('null','string') THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO d FROM polygon.drafts WHERE id=(b->>'draftId')::uuid AND user_id=(a->>'user_id')::uuid FOR SHARE;
 IF d.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 IF d.version<>(b->>'expectedDraftVersion')::bigint THEN RETURN polygon.err('VERSION_CONFLICT',409); END IF;
 IF d.proposed_timezone IS DISTINCT FROM b->>'proposedTimezone' THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 t:=date_trunc('milliseconds',clock_timestamp());
 IF d.used_at IS NOT NULL THEN RETURN polygon.err('DRAFT_USED',409); END IF;
 IF t>=d.expires_at THEN RETURN polygon.err('DRAFT_EXPIRED',409); END IF;
 IF d.trader_id IS NOT NULL AND NOT polygon.visible_trader(d.trader_id,d.venue_id,(a->>'scope_id')::uuid) THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 SELECT * INTO slot FROM polygon.user_session_slots WHERE user_id=d.user_id FOR SHARE;
 SELECT * INTO ctl FROM polygon.paper_controls WHERE singleton;
 SELECT * INTO policy FROM polygon.paper_policy_versions WHERE id=ctl.policy_id;
 IF policy.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 SELECT * INTO tr FROM polygon.traders WHERE id=d.trader_id;
 SELECT * INTO src FROM polygon.catalog_sources WHERE id=tr.source_id;
 calc:=polygon.numeric_settings(polygon.draft_form(d),policy); cap:=polygon.capability(d.trader_id,ctl);
 IF slot.current_session_id IS NOT NULL THEN reasons:=reasons||jsonb_build_array(polygon.reason('CURRENT_SESSION_EXISTS')); END IF;
 IF cap IS NOT NULL THEN reasons:=reasons||jsonb_build_array(polygon.reason('CAPABILITY_UNAVAILABLE',cap)); END IF;
 IF d.venue_id IS NULL THEN reasons:=reasons||jsonb_build_array(polygon.reason('VENUE_REQUIRED')); END IF;
 IF d.trader_id IS NULL THEN reasons:=reasons||jsonb_build_array(polygon.reason('TRADER_REQUIRED')); END IF;
 IF d.selected_mode IS NULL THEN reasons:=reasons||jsonb_build_array(polygon.reason('SIZING_MODE_REQUIRED')); END IF;
 IF d.proposed_timezone IS NULL THEN reasons:=reasons||jsonb_build_array(polygon.reason('TIMEZONE_REQUIRED')); END IF;
 IF calc->'fieldErrors'<>'[]'::jsonb THEN reasons:=reasons||jsonb_build_array(polygon.reason('NUMERIC_SETTINGS_INVALID')); END IF;
 INSERT INTO polygon.setup_reviews(id,draft_id,ownership_id,user_id,draft_version,venue_id,source_id,trader_id,trader_revision_id,catalog_version,trader_control_version,
 policy_id,paper_control_id,paper_control_version,selected_mode,raw_budget,raw_fixed_amount,raw_copy_percent,raw_market_limit_percent,raw_daily_buy_limit_percent,proposed_timezone,
 normalization_valid,budget_n,budget_d,fixed_n,fixed_d,copy_percent,market_percent,daily_percent,market_n,market_d,daily_n,daily_d,
 slot_observation,expected_slot_generation,allowed_to_start,primary_reason_code,reason_details,warnings,checked_at,expires_at,created_at)
 VALUES(gen_random_uuid(),d.id,d.ownership_id,d.user_id,d.version,d.venue_id,src.id,tr.id,tr.current_revision_id,src.version,tr.control_version,
 policy.id,ctl.id,ctl.version,d.selected_mode,d.raw_budget,d.raw_fixed_amount,d.raw_copy_percent,d.raw_market_limit_percent,d.raw_daily_buy_limit_percent,d.proposed_timezone,
 (calc->>'normalizationValid')::boolean,(calc#>>'{budget,n}')::numeric,(calc#>>'{budget,d}')::numeric,
 (calc#>>'{fixedAmount,n}')::numeric,(calc#>>'{fixedAmount,d}')::numeric,(calc->>'copyPercent')::numeric,(calc->>'marketLimitPercent')::numeric,(calc->>'dailyBuyLimitPercent')::numeric,
 (calc#>>'{effectiveMarketLimit,n}')::numeric,(calc#>>'{effectiveMarketLimit,d}')::numeric,(calc#>>'{effectiveDailyBuyLimit,n}')::numeric,(calc#>>'{effectiveDailyBuyLimit,d}')::numeric,
 CASE WHEN slot.id IS NULL THEN 'absent' ELSE 'present' END,slot.generation,reasons='[]'::jsonb,reasons#>>'{0,code}',jsonb_build_object('reasons',reasons,'fieldErrors',calc->'fieldErrors'),
 (CASE WHEN src.data_origin='synthetic' THEN '[{"code":"SYNTHETIC_DATA","params":{}}]'::jsonb ELSE '[]'::jsonb END)||'[{"code":"COPYING_NOT_CONNECTED","params":{}}]'::jsonb,t,t+interval '10 minutes',t) RETURNING * INTO review;
 RETURN jsonb_build_object('http',200,'raw_encoding','utf8-base64-v1','review',polygon.review_body(review));
END $$;
