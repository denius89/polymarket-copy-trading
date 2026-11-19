\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE polygon_owner;
CREATE FUNCTION polygon.receipt_reply(receipt uuid, lookup boolean DEFAULT false) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE r polygon.command_receipts; k polygon.command_keys; dt polygon.command_receipt_details; body jsonb; result jsonb; reply jsonb;
BEGIN
 SELECT * INTO r FROM polygon.command_receipts WHERE id=receipt;
 SELECT * INTO k FROM polygon.command_keys WHERE id=r.key_id;
 SELECT * INTO dt FROM polygon.command_receipt_details WHERE receipt_id=r.id;
 IF r.id IS NULL OR r.record_schema_version<>'v1' OR k.id IS NULL OR dt.receipt_id IS NULL OR k.receipt_id<>r.id THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 IF r.outcome='succeeded' THEN
  IF dt.reason_data<>'{}' THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  IF r.command_type='C04' THEN
   IF NOT polygon.exact_keys(dt.response_data,ARRAY['fieldErrors']) OR jsonb_typeof(dt.response_data->'fieldErrors')<>'array'
   THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
   result:=jsonb_build_object('draftId',r.result_draft_id,'ownershipId',r.result_ownership_id,'draftVersion',r.result_draft_version::text,
    'changeKind',r.change_kind,'lastSavedAt',v00_session.utc(r.result_last_saved_at),'expiresAt',v00_session.utc(r.result_expires_at));
  ELSE
   IF dt.response_data<>'{}' THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
   result:=jsonb_build_object('sessionId',r.result_session_id,'settingsRevisionId',r.result_settings_revision_id,'snapshotVersion','1','sessionVersion','1');
  END IF;
 ELSE
  IF NOT polygon.exact_keys(dt.reason_data,ARRAY['reasons']) OR jsonb_typeof(dt.reason_data->'reasons')<>'array'
   OR jsonb_array_length(dt.reason_data->'reasons')=0 OR dt.reason_data#>>'{reasons,0,code}' IS DISTINCT FROM r.reason_code
   OR dt.response_data<>'{}' THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 END IF;
 body:=jsonb_build_object('receiptId',r.id,'recordSchemaVersion',r.record_schema_version,'commandType',r.command_type,'outcome',r.outcome,
 'createdAt',v00_session.utc(r.created_at),'reasonCode',r.reason_code,'reasonDetails',
 CASE WHEN r.outcome='succeeded' THEN '[]'::jsonb ELSE dt.reason_data->'reasons' END,'result',result);
 IF r.command_type='C04' AND r.outcome='succeeded' THEN body:=body||dt.response_data; END IF;
 reply:=jsonb_build_object('http',CASE WHEN lookup THEN 200 ELSE r.http_status END,
 'command_ref',jsonb_build_object('actorRealm','user','actorId',k.user_id,'commandType',k.command_type,'clientCommandId',k.client_command_id),'receipt',body);
 IF lookup THEN reply:=reply||jsonb_build_object('status',CASE r.outcome WHEN 'succeeded' THEN 'committed' ELSE 'rejected' END); END IF;
 RETURN reply;
END $$;
CREATE FUNCTION polygon.reject(key polygon.command_keys, reasons jsonb, related uuid DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 INSERT INTO polygon.command_receipts(id,key_id,user_id,command_type,outcome,http_status,created_at,reason_code,related_session_id)
 VALUES(key.receipt_id,key.id,key.user_id,key.command_type,'rejected',409,date_trunc('milliseconds',clock_timestamp()),reasons#>>'{0,code}',related);
 INSERT INTO polygon.command_receipt_details VALUES(key.receipt_id,jsonb_build_object('reasons',reasons),'{}');
 RETURN polygon.receipt_reply(key.receipt_id);
END $$;
CREATE FUNCTION polygon.c04_save(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; b jsonb:=p->'request'; d polygon.drafts; k polygon.command_keys; ctl polygon.paper_controls;
 policy polygon.paper_policy_versions; intention bytea; form jsonb; calc jsonb; t timestamptz; change text; reason_code text;
 target uuid; updating boolean; rid uuid:=gen_random_uuid();
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','draft_id','request','raw_encoding']) OR p->>'raw_encoding' IS DISTINCT FROM 'utf8-base64-v1'
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 updating:=p->'draft_id'<>'null';
 IF updating AND NOT polygon.uuid_text(p->>'draft_id') THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 IF NOT polygon.c04_shape(b,updating) THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 intention:=polygon.command_hash((a->>'user_id')::uuid,'C04',CASE WHEN updating THEN 'update' ELSE 'create' END,(p->>'draft_id')::uuid,b);
 SELECT * INTO k FROM polygon.command_keys WHERE user_id=(a->>'user_id')::uuid AND command_type='C04' AND client_command_id=(b->>'clientCommandId')::uuid;
 IF FOUND THEN
  IF k.canonical_request_version<>'command-jcs-v1' OR k.hash_algorithm<>'sha256' THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  IF k.request_hash IS DISTINCT FROM intention THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409); END IF;
  RETURN polygon.receipt_reply(k.receipt_id);
 END IF;
 IF updating THEN
  SELECT * INTO d FROM polygon.drafts WHERE id=(p->>'draft_id')::uuid AND user_id=(a->>'user_id')::uuid FOR UPDATE;
  IF d.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 END IF;
 IF b->'venueId'<>'null' AND NOT EXISTS(SELECT 1 FROM polygon.venues WHERE id=(b->>'venueId')::uuid) THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 IF b->'traderId'<>'null' AND NOT polygon.visible_trader((b->>'traderId')::uuid,(b->>'venueId')::uuid,(a->>'scope_id')::uuid)
 THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 SELECT * INTO ctl FROM polygon.paper_controls WHERE singleton;
 SELECT * INTO policy FROM polygon.paper_policy_versions WHERE id=ctl.policy_id;
 IF policy.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 t:=date_trunc('milliseconds',clock_timestamp());
 INSERT INTO polygon.command_keys(id,user_id,command_type,client_command_id,request_hash,receipt_id,operation,target_draft_id,target_ownership_id,expected_draft_version)
 VALUES(gen_random_uuid(),(a->>'user_id')::uuid,'C04',(b->>'clientCommandId')::uuid,intention,rid,
 CASE WHEN updating THEN 'update' ELSE 'create' END,d.id,d.ownership_id,(b->>'expectedDraftVersion')::bigint) RETURNING * INTO k;
 IF updating THEN
  reason_code:=CASE WHEN d.used_at IS NOT NULL THEN 'DRAFT_USED' WHEN t>=d.expires_at THEN 'DRAFT_EXPIRED'
    WHEN d.version<>(b->>'expectedDraftVersion')::bigint THEN 'VERSION_CONFLICT' END;
  IF reason_code IS NOT NULL THEN RETURN polygon.reject(k,jsonb_build_array(polygon.reason(reason_code))); END IF;
 END IF;
 form:=b-'requestSchemaVersion'-'clientCommandId'-'expectedDraftVersion';
 calc:=polygon.numeric_settings(form,policy);
 IF NOT updating THEN
  INSERT INTO polygon.drafts(id,user_id,ownership_id,version,locale,step,entry_context,venue_id,trader_id,selected_mode,
  raw_budget,raw_fixed_amount,raw_copy_percent,raw_market_limit_percent,raw_daily_buy_limit_percent,proposed_timezone,
  last_input_receipt_id,last_saved_at,expires_at,created_at,updated_at)
  VALUES(gen_random_uuid(),k.user_id,gen_random_uuid(),1,b->>'locale',b->>'step',b->>'entryContext',(b->>'venueId')::uuid,(b->>'traderId')::uuid,b->>'selectedMode',
  polygon.raw_bytes(b->>'rawBudget'),polygon.raw_bytes(b->>'rawFixedAmount'),polygon.raw_bytes(b->>'rawCopyPercent'),polygon.raw_bytes(b->>'rawMarketLimitPercent'),polygon.raw_bytes(b->>'rawDailyBuyLimitPercent'),b->>'proposedTimezone',rid,t,t+interval '168 hours',t,t)
  RETURNING * INTO d;
  INSERT INTO polygon.draft_ownerships VALUES(d.ownership_id,d.id,d.user_id,t); change:='created';
 ELSIF polygon.draft_form(d)=form THEN change:='unchanged';
 ELSE
  UPDATE polygon.drafts SET version=version+1,locale=b->>'locale',step=b->>'step',entry_context=b->>'entryContext',venue_id=(b->>'venueId')::uuid,
  trader_id=(b->>'traderId')::uuid,selected_mode=b->>'selectedMode',raw_budget=polygon.raw_bytes(b->>'rawBudget'),raw_fixed_amount=polygon.raw_bytes(b->>'rawFixedAmount'),
  raw_copy_percent=polygon.raw_bytes(b->>'rawCopyPercent'),raw_market_limit_percent=polygon.raw_bytes(b->>'rawMarketLimitPercent'),raw_daily_buy_limit_percent=polygon.raw_bytes(b->>'rawDailyBuyLimitPercent'),
  proposed_timezone=b->>'proposedTimezone',last_input_receipt_id=rid,last_saved_at=t,expires_at=t+interval '168 hours',updated_at=t
  WHERE id=d.id RETURNING * INTO d; change:='updated';
 END IF;
 INSERT INTO polygon.command_receipts(id,key_id,user_id,command_type,outcome,http_status,created_at,
 result_draft_id,result_ownership_id,result_draft_version,change_kind,result_last_saved_at,result_expires_at)
 VALUES(rid,k.id,k.user_id,'C04','succeeded',CASE WHEN change='created' THEN 201 ELSE 200 END,t,d.id,d.ownership_id,d.version,change,d.last_saved_at,d.expires_at);
 INSERT INTO polygon.command_receipt_details VALUES(rid,'{}',jsonb_build_object('fieldErrors',calc->'fieldErrors'));
 RETURN polygon.receipt_reply(rid);
END $$;
CREATE FUNCTION polygon.review_body(r polygon.setup_reviews) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('reviewId',r.id,'draftId',r.draft_id,'ownershipId',r.ownership_id,'recordSchemaVersion',r.record_schema_version,
 'draftVersion',r.draft_version::text,'ownerKind','user','ownerUserId',r.user_id,'venueId',r.venue_id,
 'catalogSourceId',r.source_id,'traderId',r.trader_id,'traderRevisionId',r.trader_revision_id,
 'catalogVersion',r.catalog_version::text,'traderControlVersion',r.trader_control_version::text,
 'policyVersionId',r.policy_id,'paperControlId',r.paper_control_id,'paperControlVersion',r.paper_control_version::text,
 'selectedMode',r.selected_mode,'rawBudget',polygon.raw_encoded(r.raw_budget),'rawFixedAmount',polygon.raw_encoded(r.raw_fixed_amount),'rawCopyPercent',polygon.raw_encoded(r.raw_copy_percent),
 'rawMarketLimitPercent',polygon.raw_encoded(r.raw_market_limit_percent),'rawDailyBuyLimitPercent',polygon.raw_encoded(r.raw_daily_buy_limit_percent),'proposedTimezone',r.proposed_timezone,
 'normalizationValid',r.normalization_valid,'budget',polygon.money(r.budget_n,r.budget_d),'fixedAmount',polygon.money(r.fixed_n,r.fixed_d),
 'copyPercent',polygon.percent(r.copy_percent),'marketLimitPercent',polygon.percent(r.market_percent),'dailyBuyLimitPercent',polygon.percent(r.daily_percent),
 'effectiveMarketLimit',polygon.money(r.market_n,r.market_d),'effectiveDailyBuyLimit',polygon.money(r.daily_n,r.daily_d),
 'expectedSlot',CASE WHEN r.slot_observation='absent' THEN jsonb_build_object('state','absent') ELSE jsonb_build_object('state','present','generation',r.expected_slot_generation::text) END,
 'allowedToStart',r.allowed_to_start,'requiresAuthentication',false,'primaryReasonCode',r.primary_reason_code,
 'reasonDetails',r.reason_details->'reasons','fieldErrors',r.reason_details->'fieldErrors','warnings',r.warnings,
 'checkedAt',v00_session.utc(r.checked_at),'expiresAt',v00_session.utc(r.expires_at),'createdAt',v00_session.utc(r.created_at))
$$;
CREATE FUNCTION polygon.c05_validate(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
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
 '[{"code":"SYNTHETIC_DATA","params":{}},{"code":"COPYING_NOT_CONNECTED","params":{}}]',t,t+interval '10 minutes',t) RETURNING * INTO review;
 RETURN jsonb_build_object('http',200,'raw_encoding','utf8-base64-v1','review',polygon.review_body(review));
END $$;
COMMIT;
