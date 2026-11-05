\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE polygon_owner;
CREATE FUNCTION polygon.slot_body(s polygon.user_session_slots) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN s.id IS NULL THEN jsonb_build_object('state','absent') ELSE jsonb_build_object('state','present','generation',s.generation::text) END
$$;
CREATE FUNCTION polygon.c06_shape(b jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
BEGIN
 IF NOT polygon.exact_keys(b,ARRAY['requestSchemaVersion','clientCommandId','reviewId','expectedDraftVersion','expectedSlot'])
  OR b->>'requestSchemaVersion' IS DISTINCT FROM 'v1' OR NOT polygon.uuid_text(b->>'clientCommandId')
  OR NOT polygon.uuid_text(b->>'reviewId') OR NOT polygon.version_text(b->>'expectedDraftVersion')
  OR jsonb_typeof(b->'expectedDraftVersion')<>'string' THEN RETURN false; END IF;
 RETURN (b->'expectedSlot'='{"state":"absent"}'::jsonb OR
  (polygon.exact_keys(b->'expectedSlot',ARRAY['state','generation']) AND b#>>'{expectedSlot,state}'='present'
   AND jsonb_typeof(b#>'{expectedSlot,generation}')='string' AND polygon.version_text(b#>>'{expectedSlot,generation}'))) IS TRUE;
END $$;
CREATE FUNCTION polygon.c06_prepare(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; b jsonb:=p->'request'; intention bytea; r polygon.setup_reviews; d polygon.drafts;
 k polygon.command_keys; slot polygon.user_session_slots; ctl polygon.paper_controls; tr polygon.traders;
 src polygon.catalog_sources; plan polygon.start_plans; reason_code text; cap text; t timestamptz; observed jsonb;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','request']) OR NOT polygon.c06_shape(b) THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO k FROM polygon.command_keys WHERE user_id=(a->>'user_id')::uuid AND command_type='C06' AND client_command_id=(b->>'clientCommandId')::uuid;
 IF FOUND THEN
  IF k.canonical_request_version<>'command-jcs-v1' OR k.hash_algorithm<>'sha256' THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  IF k.target_review_id IS DISTINCT FROM (b->>'reviewId')::uuid THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409); END IF;
  SELECT * INTO r FROM polygon.setup_reviews WHERE id=k.target_review_id AND user_id=k.user_id;
  IF r.id IS NULL OR r.record_schema_version<>'v1' THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  intention:=polygon.command_hash(k.user_id,'C06','start',r.draft_id,b,polygon.review_body(r));
  IF k.request_hash IS DISTINCT FROM intention THEN RETURN polygon.err('KEY_REUSE_CONFLICT',409); END IF;
  RETURN polygon.receipt_reply(k.receipt_id);
 END IF;
 SELECT * INTO r FROM polygon.setup_reviews WHERE id=(b->>'reviewId')::uuid AND user_id=(a->>'user_id')::uuid;
 IF r.id IS NULL THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 IF r.record_schema_version<>'v1' THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 intention:=polygon.command_hash(r.user_id,'C06','start',r.draft_id,b,polygon.review_body(r));
 SELECT * INTO slot FROM polygon.user_session_slots WHERE user_id=r.user_id FOR UPDATE;
 SELECT * INTO d FROM polygon.drafts WHERE id=r.draft_id AND user_id=r.user_id FOR UPDATE;
 IF d.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 SELECT * INTO ctl FROM polygon.paper_controls WHERE singleton;
 IF ctl.id IS NULL OR NOT EXISTS(SELECT 1 FROM polygon.paper_policy_versions WHERE id=ctl.policy_id) THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 SELECT * INTO tr FROM polygon.traders WHERE id=r.trader_id;
 SELECT * INTO src FROM polygon.catalog_sources WHERE id=r.source_id;
 IF r.trader_id IS NOT NULL AND (tr.id IS NULL OR src.id IS NULL) THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 IF tr.id IS NOT NULL AND NOT polygon.visible_trader(tr.id,tr.venue_id,(a->>'scope_id')::uuid) THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 t:=date_trunc('milliseconds',clock_timestamp()); cap:=polygon.capability(r.trader_id,ctl);
 observed:=CASE WHEN r.slot_observation='absent' THEN jsonb_build_object('state','absent') ELSE jsonb_build_object('state','present','generation',r.expected_slot_generation::text) END;
 reason_code:=CASE
  WHEN d.used_at IS NOT NULL THEN 'DRAFT_USED'
  WHEN t>=d.expires_at THEN 'DRAFT_EXPIRED'
  WHEN d.version<>(b->>'expectedDraftVersion')::bigint OR r.draft_version<>(b->>'expectedDraftVersion')::bigint OR b->'expectedSlot'<>observed THEN 'VERSION_CONFLICT'
  WHEN slot.current_session_id IS NOT NULL THEN 'CURRENT_SESSION_EXISTS'
  WHEN cap IS NOT NULL THEN 'CAPABILITY_UNAVAILABLE'
  WHEN t>=r.expires_at THEN 'REVIEW_EXPIRED'
  WHEN r.policy_id<>ctl.policy_id OR r.paper_control_id<>ctl.id OR r.paper_control_version<>ctl.version
    OR r.ownership_id<>d.ownership_id OR (tr.id IS NOT NULL AND (tr.current_revision_id<>r.trader_revision_id OR tr.control_version<>r.trader_control_version OR src.version<>r.catalog_version))
    OR polygon.slot_body(slot)<>observed THEN 'REVIEW_STALE'
  WHEN NOT r.allowed_to_start OR NOT r.normalization_valid THEN 'SETUP_INVALID' END;
 INSERT INTO polygon.command_keys(id,user_id,command_type,client_command_id,request_hash,receipt_id,operation,target_draft_id,target_ownership_id,expected_draft_version,target_review_id)
 VALUES(gen_random_uuid(),r.user_id,'C06',(b->>'clientCommandId')::uuid,intention,gen_random_uuid(),'start',r.draft_id,r.ownership_id,(b->>'expectedDraftVersion')::bigint,r.id) RETURNING * INTO k;
 IF reason_code IS NOT NULL THEN RETURN polygon.reject(k,jsonb_build_array(polygon.reason(reason_code,cap)),
  CASE WHEN reason_code='CURRENT_SESSION_EXISTS' THEN slot.current_session_id END); END IF;
 INSERT INTO polygon.start_plans VALUES(gen_random_uuid(),k.id,k.receipt_id,r.user_id,(a->>'login_id')::uuid,r.id,t,t+interval '5 seconds',txid_current(),(a->>'epoch')::bigint)
 RETURNING * INTO plan;
 RETURN jsonb_build_object('http',200,'prepared',true,'ticket_id',plan.id,'started_at',v00_session.utc(t),'iana_timezone',r.proposed_timezone);
END $$;

CREATE FUNCTION polygon.c06_finish(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; plan polygon.start_plans; r polygon.setup_reviews; k polygon.command_keys; slot polygon.user_session_slots;
 pr polygon.profile; sid uuid:=gen_random_uuid(); settings_id uuid:=gen_random_uuid(); snapshot_id uuid:=gen_random_uuid();
 flow_id uuid:=gen_random_uuid(); journal_id uuid:=gen_random_uuid(); ddl timestamptz; t timestamptz;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth','ticket_id','evaluation_deadline_at','deadline_calculation_version','timezone_database_version'])
  OR NOT polygon.uuid_text(p->>'ticket_id') OR p->>'deadline_calculation_version' IS DISTINCT FROM 'paper-evaluation-deadline-v1'
  OR COALESCE(p->>'evaluation_deadline_at','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$'
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth'); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO plan FROM polygon.start_plans WHERE id=(p->>'ticket_id')::uuid;
 IF plan.id IS NULL OR plan.transaction_id<>txid_current() OR plan.user_id<>(a->>'user_id')::uuid
  OR plan.login_id<>(a->>'login_id')::uuid OR plan.upstream_epoch<>(a->>'epoch')::bigint
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT * INTO pr FROM polygon.profile WHERE singleton;
 IF p->>'timezone_database_version' IS DISTINCT FROM pr.timezone_database_version THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 t:=date_trunc('milliseconds',clock_timestamp());
 IF t>=plan.deadline_at THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 BEGIN ddl:=(p->>'evaluation_deadline_at')::timestamptz;
 EXCEPTION WHEN datetime_field_overflow OR invalid_datetime_format THEN RETURN polygon.err('INVALID_REQUEST',400); END;
 IF v00_session.utc(ddl) IS DISTINCT FROM p->>'evaluation_deadline_at' OR ddl<=plan.started_at THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 SELECT * INTO r FROM polygon.setup_reviews WHERE id=plan.review_id;
 SELECT * INTO k FROM polygon.command_keys WHERE id=plan.key_id;
 -- Locks and guards from prepare remain held in this exact transaction. Time can advance.
 IF t>=r.expires_at OR EXISTS(SELECT 1 FROM polygon.drafts WHERE id=r.draft_id AND t>=expires_at)
 THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 SELECT * INTO slot FROM polygon.user_session_slots WHERE user_id=r.user_id FOR UPDATE;
 IF slot.id IS NULL THEN
  INSERT INTO polygon.user_session_slots VALUES(gen_random_uuid(),r.user_id,1,NULL) RETURNING * INTO slot;
 ELSE
  IF slot.current_session_id IS NOT NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
  UPDATE polygon.user_session_slots SET generation=generation+1 WHERE id=slot.id RETURNING * INTO slot;
 END IF;
 INSERT INTO polygon.paper_sessions VALUES(sid,r.user_id,slot.id,r.draft_id,r.id,r.ownership_id,r.venue_id,r.source_id,r.trader_id,r.trader_revision_id,
 k.receipt_id,settings_id,1,1,flow_id,1,'active','copying_not_connected',plan.started_at,r.proposed_timezone,ddl,
 'paper-evaluation-deadline-v1',pr.timezone_database_version,plan.started_at,plan.started_at);
 INSERT INTO polygon.settings_revisions VALUES(settings_id,sid,k.receipt_id,1,NULL,r.budget_n,r.budget_d,r.selected_mode,
 r.fixed_n,r.fixed_d,r.copy_percent,r.market_percent,r.daily_percent,r.market_n,r.market_d,r.daily_n,r.daily_d,
 r.policy_id,'paper-settings-calculation-v1',30,plan.started_at,'v1');
 INSERT INTO polygon.funding_flows VALUES(flow_id,sid,k.receipt_id,journal_id,'initial',r.budget_n,r.budget_d,'virtual_USD',plan.started_at);
 INSERT INTO polygon.journals VALUES(journal_id,sid,k.receipt_id,flow_id,1,plan.started_at);
 INSERT INTO polygon.journal_entries VALUES
 (gen_random_uuid(),journal_id,sid,'paper_cash',r.budget_n,r.budget_d,'virtual_USD'),
 (gen_random_uuid(),journal_id,sid,'virtual_funding_source',-r.budget_n,r.budget_d,'virtual_USD');
 INSERT INTO polygon.session_snapshots VALUES(snapshot_id,sid,settings_id,1,1,1,'paper-empty-snapshot-v1',
 'active','copying_not_connected','EMPTY','synthetic','no_trade_data','virtual_USD',
 r.budget_n,r.budget_d,r.budget_n,r.budget_d,r.budget_n,r.budget_d,0,1,0,1,0,1,0,1,0,0,0,plan.started_at,plan.started_at,'v1');
 INSERT INTO polygon.command_receipts(id,key_id,user_id,command_type,outcome,http_status,created_at,result_session_id,result_settings_revision_id)
 VALUES(k.receipt_id,k.id,k.user_id,'C06','succeeded',201,plan.started_at,sid,settings_id);
 INSERT INTO polygon.command_receipt_details VALUES(k.receipt_id,'{}','{}');
 UPDATE polygon.user_session_slots SET current_session_id=sid WHERE id=slot.id;
 UPDATE polygon.drafts SET used_at=plan.started_at,used_by_session_id=sid,updated_at=plan.started_at WHERE id=r.draft_id;
 INSERT INTO polygon.audit_events VALUES(gen_random_uuid(),sid,k.receipt_id,r.user_id,plan.login_id,snapshot_id,'paper_session.started','succeeded',plan.started_at);
 INSERT INTO polygon.outbox_events VALUES(gen_random_uuid(),sid,k.receipt_id,'paper_session.started','v1','paper_start_observer',1,'pending','{}',plan.started_at);
 RETURN polygon.receipt_reply(k.receipt_id);
END $$;
COMMIT;
