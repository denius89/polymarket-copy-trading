\set ON_ERROR_STOP on
-- POLYGON-SYNTH-01 only. Add once to the existing 2407684 Auth polygon.
-- No provider/network access; no mutation of existing Auth rows or credentials.
BEGIN;
CREATE ROLE polygon_owner NOLOGIN;
CREATE ROLE polygon_executor NOLOGIN;
CREATE SCHEMA polygon AUTHORIZATION polygon_owner;
REVOKE ALL ON SCHEMA polygon FROM PUBLIC;
GRANT USAGE ON SCHEMA v00_session, v00_upstream TO polygon_owner;
GRANT REFERENCES(id) ON v00_session.actors TO polygon_owner;
GRANT REFERENCES(id) ON v00_session.logins TO polygon_owner;
GRANT SELECT(id,actor_id) ON v00_session.logins TO polygon_owner;
GRANT SELECT ON v00_upstream.gate TO polygon_owner;
-- PostgreSQL row locks require UPDATE privilege; this owner has no login or
-- membership grant to runtime. Only the closed definer functions use it.
GRANT UPDATE(epoch) ON v00_upstream.gate TO polygon_owner;
GRANT EXECUTE ON FUNCTION v00_session.utc(timestamptz) TO polygon_owner;
SET LOCAL ROLE polygon_owner;
-- A per-schema REVOKE cannot cancel PostgreSQL's global PUBLIC EXECUTE default.
-- Scope this global default to the new isolated owner, not existing Auth owners.
ALTER DEFAULT PRIVILEGES FOR ROLE polygon_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

CREATE TABLE polygon.profile (
 singleton boolean PRIMARY KEY CHECK(singleton),
 environment text NOT NULL CHECK(environment='shadow-polygon-synthetic-v1'),
 enabled boolean NOT NULL DEFAULT false,
 timezone_database_version text NOT NULL CHECK(timezone_database_version<>''),
 baseline text NOT NULL CHECK(baseline='24076847cf48c911eaa5fb21ca34b5969f89f109')
);
CREATE TABLE polygon.users (
 id uuid PRIMARY KEY, auth_actor_id uuid NOT NULL UNIQUE REFERENCES v00_session.actors(id),
 created_at timestamptz NOT NULL
);
CREATE TABLE polygon.venues (
 id uuid PRIMARY KEY, code text NOT NULL UNIQUE CHECK(code IN ('polymarket','limitless'))
);
CREATE TABLE polygon.catalog_sources (
 id uuid PRIMARY KEY, venue_id uuid NOT NULL REFERENCES polygon.venues,
 version bigint NOT NULL CHECK(version>0), is_catalog_visible boolean NOT NULL,
 paper_start_enabled boolean NOT NULL, data_origin text NOT NULL CHECK(data_origin='synthetic'),
 UNIQUE(id,venue_id)
);
CREATE TABLE polygon.read_scopes (
 id uuid PRIMARY KEY, user_id uuid NOT NULL UNIQUE REFERENCES polygon.users,
 revision bigint NOT NULL CHECK(revision>0)
);
CREATE TABLE polygon.scope_sources (
 scope_id uuid NOT NULL REFERENCES polygon.read_scopes,
 source_id uuid NOT NULL REFERENCES polygon.catalog_sources,
 PRIMARY KEY(scope_id,source_id)
);
CREATE TABLE polygon.traders (
 id uuid PRIMARY KEY, source_id uuid NOT NULL, venue_id uuid NOT NULL,
 control_version bigint NOT NULL CHECK(control_version>0),
 paper_start_enabled boolean NOT NULL, is_catalog_visible boolean NOT NULL,
 current_revision_id uuid NOT NULL, external_trader_id text NOT NULL CHECK(external_trader_id<>''),
 FOREIGN KEY(source_id,venue_id) REFERENCES polygon.catalog_sources(id,venue_id),
 UNIQUE(id,source_id,venue_id), UNIQUE(id,venue_id)
);
CREATE TABLE polygon.trader_revisions (
 id uuid PRIMARY KEY, trader_id uuid NOT NULL, source_id uuid NOT NULL, venue_id uuid NOT NULL,
 display_name text NOT NULL CHECK(display_name<>''), source_ref text NOT NULL CHECK(source_ref<>''),
 observed_at timestamptz NOT NULL, revision bigint NOT NULL CHECK(revision>0),
 created_at timestamptz NOT NULL, catalog_version_at_creation bigint NOT NULL CHECK(catalog_version_at_creation>0),
 FOREIGN KEY(trader_id,source_id,venue_id) REFERENCES polygon.traders(id,source_id,venue_id),
 UNIQUE(id,trader_id,source_id,venue_id), UNIQUE(trader_id,id)
);
ALTER TABLE polygon.traders ADD FOREIGN KEY(id,current_revision_id)
 REFERENCES polygon.trader_revisions(trader_id,id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE polygon.paper_policy_versions (
 id uuid PRIMARY KEY, version bigint NOT NULL UNIQUE CHECK(version>0),
 budget_min numeric NOT NULL CHECK(budget_min=100), budget_max numeric NOT NULL CHECK(budget_max=1000),
 budget_step numeric NOT NULL CHECK(budget_step=10),
 fixed_min numeric NOT NULL CHECK(fixed_min=5), fixed_max numeric NOT NULL CHECK(fixed_max=200),
 fixed_step numeric NOT NULL CHECK(fixed_step=1),
 copy_min numeric NOT NULL CHECK(copy_min=1), copy_max numeric NOT NULL CHECK(copy_max=20),
 copy_step numeric NOT NULL CHECK(copy_step=0.5),
 market_min numeric NOT NULL CHECK(market_min=5), market_max numeric NOT NULL CHECK(market_max=20),
 market_step numeric NOT NULL CHECK(market_step=1),
 daily_min numeric NOT NULL CHECK(daily_min=10), daily_max numeric NOT NULL CHECK(daily_max=30),
 daily_step numeric NOT NULL CHECK(daily_step=1),
 signal_max_age_seconds integer NOT NULL CHECK(signal_max_age_seconds=30),
 calculation_version text NOT NULL CHECK(calculation_version='paper-settings-calculation-v1')
);
CREATE TABLE polygon.paper_controls (
 id uuid PRIMARY KEY, singleton boolean NOT NULL UNIQUE CHECK(singleton),
 version bigint NOT NULL CHECK(version>0), enabled boolean NOT NULL,
 policy_id uuid NOT NULL REFERENCES polygon.paper_policy_versions
);

CREATE TABLE polygon.command_keys (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES polygon.users,
 command_type text NOT NULL CHECK(command_type IN ('C04','C06')),
 client_command_id uuid NOT NULL, request_hash bytea NOT NULL CHECK(octet_length(request_hash)=32),
 receipt_id uuid NOT NULL UNIQUE,
 operation text NOT NULL CHECK(operation IN ('create','update','start')),
 target_draft_id uuid, target_ownership_id uuid, expected_draft_version bigint, target_review_id uuid,
 canonical_request_version text NOT NULL DEFAULT 'command-jcs-v1' CHECK(canonical_request_version='command-jcs-v1'),
 hash_algorithm text NOT NULL DEFAULT 'sha256' CHECK(hash_algorithm='sha256'),
 CHECK(((command_type='C04' AND operation='create' AND target_draft_id IS NULL AND target_ownership_id IS NULL AND expected_draft_version IS NULL AND target_review_id IS NULL)
 OR (command_type='C04' AND operation='update' AND target_draft_id IS NOT NULL AND target_ownership_id IS NOT NULL AND expected_draft_version>0 AND target_review_id IS NULL)
 OR (command_type='C06' AND operation='start' AND target_draft_id IS NOT NULL AND target_ownership_id IS NOT NULL AND expected_draft_version>0 AND target_review_id IS NOT NULL)) IS TRUE),
 UNIQUE(user_id,command_type,client_command_id), UNIQUE(id,user_id,command_type)
);
CREATE TABLE polygon.drafts (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES polygon.users,
 ownership_id uuid NOT NULL UNIQUE, version bigint NOT NULL CHECK(version>0),
 locale text NOT NULL CHECK(locale IN ('ru','en')),
 step text NOT NULL CHECK(step IN ('select_trader','configure','review')),
 entry_context text CHECK(entry_context IN ('catalog','trader_details','session_summary')),
 venue_id uuid REFERENCES polygon.venues, trader_id uuid,
 selected_mode text CHECK(selected_mode IN ('fixed','percent')),
 raw_budget bytea CHECK(octet_length(raw_budget)<=256), raw_fixed_amount bytea CHECK(octet_length(raw_fixed_amount)<=256),
 raw_copy_percent bytea CHECK(octet_length(raw_copy_percent)<=256),
 raw_market_limit_percent bytea CHECK(octet_length(raw_market_limit_percent)<=256),
 raw_daily_buy_limit_percent bytea CHECK(octet_length(raw_daily_buy_limit_percent)<=256), proposed_timezone text,
 last_input_receipt_id uuid NOT NULL, last_saved_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
 used_at timestamptz, used_by_session_id uuid UNIQUE,
 CHECK(trader_id IS NULL OR venue_id IS NOT NULL),
 FOREIGN KEY(trader_id,venue_id) REFERENCES polygon.traders(id,venue_id),
 CHECK(expires_at=last_saved_at+interval '168 hours'),
 CHECK((used_at IS NULL)=(used_by_session_id IS NULL)),
 UNIQUE(id,user_id), UNIQUE(id,ownership_id,user_id)
);
CREATE TABLE polygon.draft_ownerships (
 id uuid PRIMARY KEY, draft_id uuid NOT NULL UNIQUE, user_id uuid NOT NULL REFERENCES polygon.users,
 created_at timestamptz NOT NULL,
 FOREIGN KEY(draft_id,id,user_id) REFERENCES polygon.drafts(id,ownership_id,user_id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(id,draft_id,user_id)
);
ALTER TABLE polygon.drafts ADD FOREIGN KEY(ownership_id,id,user_id)
 REFERENCES polygon.draft_ownerships(id,draft_id,user_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE polygon.user_session_slots (
 id uuid PRIMARY KEY, user_id uuid NOT NULL UNIQUE REFERENCES polygon.users,
 generation bigint NOT NULL CHECK(generation>0), current_session_id uuid,
 UNIQUE(id,user_id)
);

CREATE TABLE polygon.setup_reviews (
 id uuid PRIMARY KEY, draft_id uuid NOT NULL, ownership_id uuid NOT NULL, user_id uuid NOT NULL,
 draft_version bigint NOT NULL CHECK(draft_version>0),
 venue_id uuid REFERENCES polygon.venues, source_id uuid, trader_id uuid, trader_revision_id uuid,
 catalog_version bigint, trader_control_version bigint,
 policy_id uuid NOT NULL REFERENCES polygon.paper_policy_versions,
 paper_control_id uuid NOT NULL REFERENCES polygon.paper_controls,
 paper_control_version bigint NOT NULL CHECK(paper_control_version>0),
 selected_mode text CHECK(selected_mode IN ('fixed','percent')),
 raw_budget bytea, raw_fixed_amount bytea, raw_copy_percent bytea,
 raw_market_limit_percent bytea, raw_daily_buy_limit_percent bytea, proposed_timezone text,
 normalization_valid boolean NOT NULL,
 budget_n numeric, budget_d numeric, fixed_n numeric, fixed_d numeric, copy_percent numeric,
 market_percent numeric, daily_percent numeric, market_n numeric, market_d numeric, daily_n numeric, daily_d numeric,
 slot_observation text NOT NULL CHECK(slot_observation IN ('absent','present')), expected_slot_generation bigint,
 allowed_to_start boolean NOT NULL, primary_reason_code text,
 reason_details jsonb NOT NULL, warnings jsonb NOT NULL,
 checked_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL,
 record_schema_version text NOT NULL DEFAULT 'v1' CHECK(record_schema_version='v1'),
 FOREIGN KEY(ownership_id,draft_id,user_id) REFERENCES polygon.draft_ownerships(id,draft_id,user_id),
 FOREIGN KEY(trader_revision_id,trader_id,source_id,venue_id)
   REFERENCES polygon.trader_revisions(id,trader_id,source_id,venue_id),
 CHECK((trader_id IS NULL AND source_id IS NULL AND trader_revision_id IS NULL AND catalog_version IS NULL AND trader_control_version IS NULL)
    OR (trader_id IS NOT NULL AND source_id IS NOT NULL AND trader_revision_id IS NOT NULL AND venue_id IS NOT NULL AND catalog_version>0 AND trader_control_version>0)),
 CHECK((slot_observation='absent' AND expected_slot_generation IS NULL) OR (slot_observation='present' AND expected_slot_generation>0)),
 CHECK(expires_at=checked_at+interval '10 minutes'), CHECK(created_at=checked_at),
 CHECK(allowed_to_start=(primary_reason_code IS NULL)),
 CHECK(jsonb_typeof(reason_details)='object' AND jsonb_typeof(warnings)='array'),
 CHECK(NOT allowed_to_start OR (normalization_valid AND proposed_timezone IS NOT NULL AND trader_id IS NOT NULL)),
 CHECK((NOT normalization_valid AND budget_n IS NULL AND budget_d IS NULL AND fixed_n IS NULL AND fixed_d IS NULL
   AND copy_percent IS NULL AND market_percent IS NULL AND daily_percent IS NULL AND market_n IS NULL AND market_d IS NULL AND daily_n IS NULL AND daily_d IS NULL)
 OR (normalization_valid AND budget_n>0 AND budget_d>0 AND market_percent IS NOT NULL AND daily_percent IS NOT NULL
   AND market_n>0 AND market_d>0 AND daily_n>0 AND daily_d>0
   AND ((selected_mode='fixed' AND fixed_n>0 AND fixed_d>0 AND copy_percent IS NULL)
     OR (selected_mode='percent' AND fixed_n IS NULL AND fixed_d IS NULL AND copy_percent>0)))),
 UNIQUE(id,draft_id,ownership_id,user_id)
);
ALTER TABLE polygon.command_keys ADD FOREIGN KEY(target_ownership_id,target_draft_id,user_id)
 REFERENCES polygon.draft_ownerships(id,draft_id,user_id);
ALTER TABLE polygon.command_keys ADD FOREIGN KEY(target_review_id,target_draft_id,target_ownership_id,user_id)
 REFERENCES polygon.setup_reviews(id,draft_id,ownership_id,user_id);

CREATE TABLE polygon.paper_sessions (
 id uuid PRIMARY KEY, user_id uuid NOT NULL, slot_id uuid NOT NULL,
 draft_id uuid NOT NULL UNIQUE, review_id uuid NOT NULL UNIQUE, ownership_id uuid NOT NULL,
 venue_id uuid NOT NULL, source_id uuid NOT NULL, trader_id uuid NOT NULL, trader_revision_id uuid NOT NULL,
 start_receipt_id uuid NOT NULL UNIQUE, current_settings_revision_id uuid NOT NULL,
 current_snapshot_version bigint NOT NULL CHECK(current_snapshot_version=1),
 current_ledger_sequence bigint NOT NULL CHECK(current_ledger_sequence=1),
 initial_funding_flow_id uuid NOT NULL,
 version bigint NOT NULL CHECK(version=1), lifecycle text NOT NULL CHECK(lifecycle='active'),
 control_state text NOT NULL CHECK(control_state='copying_not_connected'),
 started_at timestamptz NOT NULL, iana_timezone text NOT NULL, evaluation_deadline_at timestamptz NOT NULL,
 deadline_calculation_version text NOT NULL CHECK(deadline_calculation_version='paper-evaluation-deadline-v1'),
 timezone_database_version text NOT NULL, created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
 CHECK(evaluation_deadline_at>started_at),
 CHECK(created_at=started_at AND updated_at=started_at),
 FOREIGN KEY(slot_id,user_id) REFERENCES polygon.user_session_slots(id,user_id),
 FOREIGN KEY(review_id,draft_id,ownership_id,user_id) REFERENCES polygon.setup_reviews(id,draft_id,ownership_id,user_id),
 FOREIGN KEY(trader_revision_id,trader_id,source_id,venue_id) REFERENCES polygon.trader_revisions(id,trader_id,source_id,venue_id),
 UNIQUE(id,user_id), UNIQUE(id,draft_id), UNIQUE(id,start_receipt_id), UNIQUE(id,slot_id,user_id)
);
ALTER TABLE polygon.drafts ADD FOREIGN KEY(used_by_session_id,id) REFERENCES polygon.paper_sessions(id,draft_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE polygon.user_session_slots ADD FOREIGN KEY(current_session_id,id,user_id)
 REFERENCES polygon.paper_sessions(id,slot_id,user_id) DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE polygon.command_receipts (
 id uuid PRIMARY KEY, key_id uuid NOT NULL UNIQUE, user_id uuid NOT NULL, command_type text NOT NULL,
 outcome text NOT NULL CHECK(outcome IN ('succeeded','rejected')), http_status integer NOT NULL,
 created_at timestamptz NOT NULL, reason_code text,
 result_draft_id uuid, result_ownership_id uuid, result_draft_version bigint,
 change_kind text CHECK(change_kind IN ('created','updated','unchanged')),
 result_last_saved_at timestamptz, result_expires_at timestamptz,
 result_session_id uuid, result_settings_revision_id uuid, related_session_id uuid,
 record_schema_version text NOT NULL DEFAULT 'v1' CHECK(record_schema_version='v1'),
 FOREIGN KEY(key_id,user_id,command_type) REFERENCES polygon.command_keys(id,user_id,command_type),
 FOREIGN KEY(result_ownership_id,result_draft_id,user_id) REFERENCES polygon.draft_ownerships(id,draft_id,user_id),
 FOREIGN KEY(result_session_id,id) REFERENCES polygon.paper_sessions(id,start_receipt_id) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(related_session_id,user_id) REFERENCES polygon.paper_sessions(id,user_id),
 CHECK(command_type IN ('C04','C06')),
 CHECK(reason_code IS NULL OR reason_code IN ('DRAFT_USED','DRAFT_EXPIRED','VERSION_CONFLICT')
 OR (command_type='C06' AND reason_code IN ('SESSION_NOT_SETTLED','CURRENT_SESSION_EXISTS','CAPABILITY_UNAVAILABLE','REVIEW_EXPIRED','REVIEW_STALE','SETUP_INVALID'))),
 CHECK((outcome='rejected' AND reason_code IS NOT NULL AND http_status=409 AND result_draft_id IS NULL
  AND result_ownership_id IS NULL AND result_draft_version IS NULL AND change_kind IS NULL AND result_last_saved_at IS NULL
  AND result_expires_at IS NULL AND result_session_id IS NULL AND result_settings_revision_id IS NULL)
 OR (outcome='succeeded' AND reason_code IS NULL AND related_session_id IS NULL AND
   ((command_type='C04' AND result_draft_id IS NOT NULL AND result_ownership_id IS NOT NULL AND result_draft_version>0
      AND change_kind IS NOT NULL AND result_last_saved_at IS NOT NULL AND result_expires_at=result_last_saved_at+interval '168 hours'
      AND result_session_id IS NULL AND result_settings_revision_id IS NULL
      AND http_status=CASE WHEN change_kind='created' THEN 201 ELSE 200 END)
   OR (command_type='C06' AND result_session_id IS NOT NULL AND result_settings_revision_id IS NOT NULL AND http_status=201
      AND result_draft_id IS NULL AND result_ownership_id IS NULL AND result_draft_version IS NULL AND change_kind IS NULL
      AND result_last_saved_at IS NULL AND result_expires_at IS NULL)))),
 UNIQUE(id,key_id), UNIQUE(id,result_draft_id,result_draft_version), UNIQUE(id,result_session_id)
);
ALTER TABLE polygon.command_keys ADD FOREIGN KEY(receipt_id,id) REFERENCES polygon.command_receipts(id,key_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE polygon.drafts ADD FOREIGN KEY(last_input_receipt_id,id,version)
 REFERENCES polygon.command_receipts(id,result_draft_id,result_draft_version) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE polygon.paper_sessions ADD FOREIGN KEY(start_receipt_id,id)
 REFERENCES polygon.command_receipts(id,result_session_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE polygon.command_receipt_details (
 receipt_id uuid PRIMARY KEY REFERENCES polygon.command_receipts,
 reason_data jsonb NOT NULL CHECK(jsonb_typeof(reason_data)='object'),
 response_data jsonb NOT NULL CHECK(jsonb_typeof(response_data)='object')
);
ALTER TABLE polygon.command_receipts ADD FOREIGN KEY(id) REFERENCES polygon.command_receipt_details(receipt_id) DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE polygon.settings_revisions (
 id uuid PRIMARY KEY, session_id uuid NOT NULL, command_receipt_id uuid NOT NULL,
 sequence bigint NOT NULL CHECK(sequence=1), previous_revision_id uuid CHECK(previous_revision_id IS NULL),
 budget_n numeric NOT NULL CHECK(budget_n>0), budget_d numeric NOT NULL CHECK(budget_d>0),
 sizing_mode text NOT NULL CHECK(sizing_mode IN ('fixed','percent')),
 fixed_n numeric, fixed_d numeric, copy_percent numeric,
 market_percent numeric NOT NULL, daily_percent numeric NOT NULL,
 market_n numeric NOT NULL CHECK(market_n>0), market_d numeric NOT NULL CHECK(market_d>0),
 daily_n numeric NOT NULL CHECK(daily_n>0), daily_d numeric NOT NULL CHECK(daily_d>0),
 policy_id uuid NOT NULL REFERENCES polygon.paper_policy_versions,
 calculation_version text NOT NULL CHECK(calculation_version='paper-settings-calculation-v1'),
 signal_max_age_seconds integer NOT NULL CHECK(signal_max_age_seconds=30), created_at timestamptz NOT NULL,
 record_schema_version text NOT NULL DEFAULT 'v1' CHECK(record_schema_version='v1'),
 FOREIGN KEY(session_id,command_receipt_id) REFERENCES polygon.paper_sessions(id,start_receipt_id),
 CHECK((sizing_mode='fixed' AND fixed_n>0 AND fixed_d>0 AND copy_percent IS NULL)
 OR (sizing_mode='percent' AND fixed_n IS NULL AND fixed_d IS NULL AND copy_percent>0)),
 UNIQUE(session_id,id), UNIQUE(session_id,sequence), UNIQUE(session_id,command_receipt_id)
);
ALTER TABLE polygon.paper_sessions ADD FOREIGN KEY(id,current_settings_revision_id)
 REFERENCES polygon.settings_revisions(session_id,id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE polygon.command_receipts ADD FOREIGN KEY(result_session_id,result_settings_revision_id)
 REFERENCES polygon.settings_revisions(session_id,id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE polygon.funding_flows (
 id uuid PRIMARY KEY, session_id uuid NOT NULL UNIQUE, command_receipt_id uuid NOT NULL,
 journal_id uuid NOT NULL UNIQUE, kind text NOT NULL CHECK(kind='initial'),
 amount_n numeric NOT NULL CHECK(amount_n>0), amount_d numeric NOT NULL CHECK(amount_d>0),
 unit text NOT NULL CHECK(unit='virtual_USD'), created_at timestamptz NOT NULL,
 FOREIGN KEY(session_id,command_receipt_id) REFERENCES polygon.paper_sessions(id,start_receipt_id),
 UNIQUE(session_id,id), UNIQUE(id,journal_id,session_id)
);
CREATE TABLE polygon.journals (
 id uuid PRIMARY KEY, session_id uuid NOT NULL, command_receipt_id uuid NOT NULL,
 funding_flow_id uuid NOT NULL UNIQUE, sequence bigint NOT NULL CHECK(sequence=1),
 created_at timestamptz NOT NULL,
 FOREIGN KEY(funding_flow_id,id,session_id) REFERENCES polygon.funding_flows(id,journal_id,session_id),
 FOREIGN KEY(session_id,command_receipt_id) REFERENCES polygon.paper_sessions(id,start_receipt_id),
 UNIQUE(session_id,sequence), UNIQUE(id,session_id)
);
ALTER TABLE polygon.funding_flows ADD FOREIGN KEY(journal_id,session_id) REFERENCES polygon.journals(id,session_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE polygon.paper_sessions ADD FOREIGN KEY(id,initial_funding_flow_id) REFERENCES polygon.funding_flows(session_id,id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE polygon.journal_entries (
 id uuid PRIMARY KEY, journal_id uuid NOT NULL, session_id uuid NOT NULL,
 account text NOT NULL CHECK(account IN ('paper_cash','virtual_funding_source')),
 amount_n numeric NOT NULL CHECK(amount_n<>0), amount_d numeric NOT NULL CHECK(amount_d>0),
 unit text NOT NULL CHECK(unit='virtual_USD'),
 FOREIGN KEY(journal_id,session_id) REFERENCES polygon.journals(id,session_id), UNIQUE(journal_id,account)
);
CREATE TABLE polygon.session_snapshots (
 id uuid PRIMARY KEY, session_id uuid NOT NULL, settings_revision_id uuid NOT NULL,
 version bigint NOT NULL CHECK(version=1), session_version bigint NOT NULL CHECK(session_version=1),
 ledger_sequence bigint NOT NULL CHECK(ledger_sequence=1),
 calculation_version text NOT NULL CHECK(calculation_version='paper-empty-snapshot-v1'),
 lifecycle text NOT NULL CHECK(lifecycle='active'), control_state text NOT NULL CHECK(control_state='copying_not_connected'),
 content_state text NOT NULL CHECK(content_state='EMPTY'), data_origin text NOT NULL CHECK(data_origin='synthetic'),
 coverage_state text NOT NULL CHECK(coverage_state='no_trade_data'), unit text NOT NULL CHECK(unit='virtual_USD'),
 initial_funding_n numeric NOT NULL, initial_funding_d numeric NOT NULL,
 free_n numeric NOT NULL, free_d numeric NOT NULL, equity_n numeric NOT NULL, equity_d numeric NOT NULL,
 reserved_n numeric NOT NULL CHECK(reserved_n=0), reserved_d numeric NOT NULL CHECK(reserved_d=1),
 position_cost_n numeric NOT NULL CHECK(position_cost_n=0), position_cost_d numeric NOT NULL CHECK(position_cost_d=1),
 position_value_n numeric NOT NULL CHECK(position_value_n=0), position_value_d numeric NOT NULL CHECK(position_value_d=1),
 trading_result_n numeric NOT NULL CHECK(trading_result_n=0), trading_result_d numeric NOT NULL CHECK(trading_result_d=1),
 trade_count bigint NOT NULL CHECK(trade_count=0), position_count bigint NOT NULL CHECK(position_count=0), order_count bigint NOT NULL CHECK(order_count=0),
 as_of timestamptz NOT NULL, created_at timestamptz NOT NULL,
 record_schema_version text NOT NULL DEFAULT 'v1' CHECK(record_schema_version='v1'),
 FOREIGN KEY(session_id,settings_revision_id) REFERENCES polygon.settings_revisions(session_id,id),
 FOREIGN KEY(session_id,ledger_sequence) REFERENCES polygon.journals(session_id,sequence),
 UNIQUE(session_id,version), UNIQUE(session_id,id)
);
ALTER TABLE polygon.paper_sessions ADD FOREIGN KEY(id,current_snapshot_version)
 REFERENCES polygon.session_snapshots(session_id,version) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE polygon.audit_events (
 id uuid PRIMARY KEY, session_id uuid NOT NULL UNIQUE, receipt_id uuid NOT NULL UNIQUE,
 actor_user_id uuid NOT NULL, login_id uuid NOT NULL REFERENCES v00_session.logins(id),
 snapshot_id uuid NOT NULL, kind text NOT NULL CHECK(kind='paper_session.started'),
 outcome text NOT NULL CHECK(outcome='succeeded'), created_at timestamptz NOT NULL,
 FOREIGN KEY(session_id,actor_user_id) REFERENCES polygon.paper_sessions(id,user_id),
 FOREIGN KEY(receipt_id,session_id) REFERENCES polygon.command_receipts(id,result_session_id),
 FOREIGN KEY(session_id,snapshot_id) REFERENCES polygon.session_snapshots(session_id,id)
);
CREATE TABLE polygon.outbox_events (
 id uuid PRIMARY KEY, session_id uuid NOT NULL UNIQUE, receipt_id uuid NOT NULL UNIQUE,
 kind text NOT NULL CHECK(kind='paper_session.started'), schema_version text NOT NULL CHECK(schema_version='v1'),
 consumer_name text NOT NULL CHECK(consumer_name='paper_start_observer'),
 snapshot_version bigint NOT NULL CHECK(snapshot_version=1),
 delivery_state text NOT NULL CHECK(delivery_state='pending'),
 payload jsonb NOT NULL CHECK(payload='{}'::jsonb),
 created_at timestamptz NOT NULL,
 FOREIGN KEY(receipt_id,session_id) REFERENCES polygon.command_receipts(id,result_session_id),
 FOREIGN KEY(session_id,snapshot_version) REFERENCES polygon.session_snapshots(session_id,version)
);
CREATE TABLE polygon.start_plans (
 id uuid PRIMARY KEY, key_id uuid NOT NULL UNIQUE REFERENCES polygon.command_keys,
 receipt_id uuid NOT NULL UNIQUE REFERENCES polygon.command_receipts DEFERRABLE INITIALLY DEFERRED,
 user_id uuid NOT NULL REFERENCES polygon.users, login_id uuid NOT NULL REFERENCES v00_session.logins(id),
 review_id uuid NOT NULL REFERENCES polygon.setup_reviews,
 started_at timestamptz NOT NULL, deadline_at timestamptz NOT NULL,
 transaction_id bigint NOT NULL, upstream_epoch bigint NOT NULL,
 CHECK(deadline_at=started_at+interval '5 seconds')
);

CREATE FUNCTION polygon.immutable_row() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'immutable polygon history'; END $$;
DO $$ DECLARE n text; BEGIN
 FOREACH n IN ARRAY ARRAY['users','venues','trader_revisions','paper_policy_versions','draft_ownerships','setup_reviews',
 'command_keys','command_receipts','command_receipt_details','settings_revisions','funding_flows','journals',
 'journal_entries','session_snapshots','audit_events','outbox_events','start_plans','paper_sessions'] LOOP
 EXECUTE format('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON polygon.%I FOR EACH ROW EXECUTE FUNCTION polygon.immutable_row()',n);
 END LOOP;
END $$;
COMMIT;
