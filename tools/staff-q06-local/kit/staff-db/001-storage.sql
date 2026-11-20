\set ON_ERROR_STOP on
-- Fresh disposable database only. Never apply to C7 or an existing live run.
BEGIN;
CREATE ROLE pilot_staff_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE pilot_staff_auth NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE pilot_staff_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE pilot_staff_operator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE SCHEMA pilot_staff AUTHORIZATION pilot_staff_owner;
REVOKE ALL ON SCHEMA pilot_staff FROM PUBLIC;
SET LOCAL ROLE pilot_staff_owner;
-- Per-schema REVOKE cannot remove PostgreSQL's global default PUBLIC EXECUTE.
-- This owner is new and dedicated to this profile, so remove its global default.
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
CREATE DOMAIN pilot_staff.u AS uuid CHECK (VALUE::text ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$');
CREATE DOMAIN pilot_staff.h AS text CHECK (VALUE ~ '^[0-9a-f]{64}$');
CREATE TABLE pilot_staff.control (
 singleton boolean PRIMARY KEY CHECK(singleton), run_id pilot_staff.u NOT NULL UNIQUE,
 deployment_digest pilot_staff.h NOT NULL, origin text NOT NULL CHECK(origin ~ '^https://[^/[:space:]]+$'),
 opened_at timestamptz NOT NULL, cutoff_at timestamptz NOT NULL,
 enabled boolean NOT NULL DEFAULT false, closed_at timestamptz,
 profile text NOT NULL DEFAULT 'paper-readonly-secret-v1' CHECK(profile='paper-readonly-secret-v1'),
 epoch bigint NOT NULL DEFAULT 1 CHECK(epoch>0),
 CHECK(cutoff_at=((opened_at AT TIME ZONE 'Europe/Warsaw')::date+1+time '23:00') AT TIME ZONE 'Europe/Warsaw'),
 CHECK(cutoff_at>opened_at), CHECK(closed_at IS NULL OR NOT enabled)
);
CREATE TABLE pilot_staff.principals (
 id pilot_staff.u PRIMARY KEY, ordinal smallint UNIQUE NOT NULL CHECK(ordinal IN(1,2)),
 display_label text NOT NULL, current_permit_id pilot_staff.u NOT NULL,
 CHECK(display_label=CASE ordinal WHEN 1 THEN 'владелец 1' ELSE 'владелец 2' END)
);
CREATE TABLE pilot_staff.permits (
 id pilot_staff.u PRIMARY KEY, principal_id pilot_staff.u NOT NULL REFERENCES pilot_staff.principals(id),
 version bigint NOT NULL CHECK(version>0), digest pilot_staff.h NOT NULL,
 created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, revoked_at timestamptz,
 UNIQUE(principal_id,version), UNIQUE(id,principal_id), CHECK(expires_at>created_at),
 CHECK(revoked_at IS NULL OR revoked_at>=created_at)
);
ALTER TABLE pilot_staff.principals ADD FOREIGN KEY(current_permit_id,id)
 REFERENCES pilot_staff.permits(id,principal_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE pilot_staff.targets (
 ordinal smallint PRIMARY KEY CHECK(ordinal IN(1,2)), user_id uuid NOT NULL UNIQUE,
 display_label text NOT NULL, session_id uuid UNIQUE, UNIQUE(ordinal,session_id),
 CHECK(display_label=CASE ordinal WHEN 1 THEN 'участник пилота 1' ELSE 'участник пилота 2' END)
);
-- Assignment is fixed and versioned for this deployment; no caller-supplied grants.
CREATE TABLE pilot_staff.assignments (
 principal_id pilot_staff.u PRIMARY KEY REFERENCES pilot_staff.principals(id),
 version bigint NOT NULL DEFAULT 1 CHECK(version=1), enabled boolean NOT NULL DEFAULT true,
 scopes text[] NOT NULL DEFAULT ARRAY['session.summary','session.settings','session.financial_snapshot','pilot.sessions.list','pilot.session.events','pilot.own_access']::text[],
 CHECK(scopes=ARRAY['session.summary','session.settings','session.financial_snapshot','pilot.sessions.list','pilot.session.events','pilot.own_access']::text[])
);
CREATE TABLE pilot_staff.contexts (
 id pilot_staff.u PRIMARY KEY, proof_digest pilot_staff.h NOT NULL, network_digest pilot_staff.h NOT NULL,
 created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, epoch bigint NOT NULL,
 CHECK(expires_at>created_at AND expires_at<=created_at+interval '10 minutes')
);
CREATE TABLE pilot_staff.operations (
 context_id pilot_staff.u PRIMARY KEY REFERENCES pilot_staff.contexts(id), operation_id pilot_staff.u NOT NULL,
 fingerprint pilot_staff.h NOT NULL, permit_id uuid NOT NULL, login_id pilot_staff.u,
 outcome text NOT NULL CHECK(outcome IN('succeeded','rejected')), result jsonb NOT NULL,
 completed_at timestamptz NOT NULL, UNIQUE(context_id,operation_id),
 CHECK((outcome='succeeded')=(login_id IS NOT NULL)),
 CHECK(result->>'kind'=CASE outcome WHEN 'succeeded' THEN 'pilot_login_completed' ELSE 'pilot_login_rejected' END),
 CHECK(result->>'operationId'=operation_id::text), CHECK(jsonb_typeof(result)='object')
);
CREATE TABLE pilot_staff.logins (
 id pilot_staff.u PRIMARY KEY, principal_id pilot_staff.u NOT NULL REFERENCES pilot_staff.principals(id),
 permit_id pilot_staff.u NOT NULL, context_id pilot_staff.u NOT NULL UNIQUE, operation_id pilot_staff.u NOT NULL,
 method text NOT NULL DEFAULT 'pilot_secret' CHECK(method='pilot_secret'),
 issued_at timestamptz NOT NULL, absolute_expires_at timestamptz NOT NULL, idle_expires_at timestamptz NOT NULL,
 cookie_digest pilot_staff.h NOT NULL, delivery_deadline timestamptz NOT NULL,
 cookie_envelope jsonb, envelope_erased_at timestamptz, confirmed_at timestamptz, revoked_at timestamptz,
 epoch bigint NOT NULL,
 FOREIGN KEY(permit_id,principal_id) REFERENCES pilot_staff.permits(id,principal_id),
 FOREIGN KEY(context_id,operation_id) REFERENCES pilot_staff.operations(context_id,operation_id) DEFERRABLE INITIALLY DEFERRED,
 UNIQUE(id,principal_id), UNIQUE(id,context_id,operation_id),
 CHECK(absolute_expires_at=issued_at+interval '8 hours'), CHECK(idle_expires_at=issued_at+interval '30 minutes'),
 CHECK(delivery_deadline>issued_at AND delivery_deadline<=issued_at+interval '5 minutes'),
 CHECK((cookie_envelope IS NULL)=(envelope_erased_at IS NOT NULL)),
 CHECK(confirmed_at IS NULL OR envelope_erased_at IS NOT NULL),
 CHECK(revoked_at IS NULL OR envelope_erased_at IS NOT NULL)
);
CREATE UNIQUE INDEX one_active_login ON pilot_staff.logins(principal_id) WHERE revoked_at IS NULL;
CREATE INDEX active_permit_logins ON pilot_staff.logins(permit_id,id) WHERE revoked_at IS NULL;
CREATE INDEX pending_envelopes ON pilot_staff.logins(delivery_deadline,id) WHERE cookie_envelope IS NOT NULL;
ALTER TABLE pilot_staff.operations ADD FOREIGN KEY(login_id,context_id,operation_id)
 REFERENCES pilot_staff.logins(id,context_id,operation_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE pilot_staff.envelope_nonces (
 key_id pilot_staff.u NOT NULL, nonce text NOT NULL CHECK(nonce ~ '^[0-9a-f]{48}$'),
 login_id pilot_staff.u NOT NULL UNIQUE REFERENCES pilot_staff.logins(id), PRIMARY KEY(key_id,nonce)
);
CREATE TABLE pilot_staff.slots (
 principal_id pilot_staff.u PRIMARY KEY REFERENCES pilot_staff.principals(id),
 login_id pilot_staff.u UNIQUE, generation bigint NOT NULL DEFAULT 0 CHECK(generation>=0),
 FOREIGN KEY(login_id,principal_id) REFERENCES pilot_staff.logins(id,principal_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE pilot_staff.logout_contexts (
 id pilot_staff.u PRIMARY KEY, proof_digest pilot_staff.h NOT NULL,
 target_login_id pilot_staff.u NOT NULL REFERENCES pilot_staff.logins(id),
 authorizing_login_id pilot_staff.u NOT NULL REFERENCES pilot_staff.logins(id),
 source_context_id pilot_staff.u REFERENCES pilot_staff.logout_contexts(id),
 mode text NOT NULL CHECK(mode IN('original_login','current_staff')),
 created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 CHECK(expires_at=created_at+interval '15 minutes'),
 CHECK(mode<>'original_login' OR authorizing_login_id=target_login_id)
);
CREATE TABLE pilot_staff.logout_results (
 context_id pilot_staff.u PRIMARY KEY REFERENCES pilot_staff.logout_contexts(id),
 operation_id pilot_staff.u NOT NULL, target_login_id pilot_staff.u NOT NULL REFERENCES pilot_staff.logins(id),
 result jsonb NOT NULL, completed_at timestamptz NOT NULL,
 CHECK(result->>'kind'='logout_completed'), CHECK(result->>'targetLoginId'=target_login_id::text)
);
CREATE TABLE pilot_staff.requests (
 id pilot_staff.u PRIMARY KEY, proof_digest pilot_staff.h NOT NULL, fingerprint pilot_staff.h NOT NULL,
 route text NOT NULL, scope text NOT NULL, network_digest pilot_staff.h, binding_digest pilot_staff.h NOT NULL,
 admitted_at timestamptz NOT NULL, deadline_at timestamptz NOT NULL,
 CHECK(deadline_at>admitted_at AND deadline_at<=admitted_at+interval '5 seconds')
);
CREATE INDEX request_budget ON pilot_staff.requests(route,scope,admitted_at);
CREATE INDEX request_route_time ON pilot_staff.requests(route,admitted_at);
CREATE INDEX request_network ON pilot_staff.requests(network_digest,admitted_at);
CREATE TABLE pilot_staff.audit (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id pilot_staff.u NOT NULL,
 action text NOT NULL CHECK(action IN('provision','activate','bind_sessions','permit_revoked','permit_rotated','pilot_closed',
 'context_prepared','login_completed','login_rejected','login_replaced','login_outcome_read','cookie_recovered','own_me',
 'logout_prepared','logout_continued','logout_completed','logout_outcome_read','session_list','session_read','session_events','access_denied','cookie_windows_expired')),
 principal_id pilot_staff.u REFERENCES pilot_staff.principals(id), login_id pilot_staff.u REFERENCES pilot_staff.logins(id),
 context_id uuid, operation_id uuid, target_session_id uuid, snapshot_version bigint,
 profile_epoch bigint NOT NULL, assignment_version bigint, recorded_at timestamptz NOT NULL,
 actor_service text NOT NULL DEFAULT session_user,
 UNIQUE(request_id,action), CHECK((target_session_id IS NULL)=(snapshot_version IS NULL))
);
CREATE INDEX audit_context_kind ON pilot_staff.audit(context_id,action,operation_id);
CREATE INDEX audit_login_kind ON pilot_staff.audit(login_id,action);
CREATE TABLE pilot_staff.read_evidence (
 audit_id uuid NOT NULL REFERENCES pilot_staff.audit(id), target_ordinal smallint NOT NULL REFERENCES pilot_staff.targets(ordinal),
 session_id uuid NOT NULL, snapshot_id uuid NOT NULL, snapshot_version bigint NOT NULL, settings_revision_id uuid NOT NULL,
 granted_group text NOT NULL CHECK(granted_group IN('session.summary','session.settings','session.financial_snapshot','pilot.sessions.list','pilot.session.events')),
 FOREIGN KEY(target_ordinal,session_id) REFERENCES pilot_staff.targets(ordinal,session_id),
 PRIMARY KEY(audit_id,session_id,granted_group)
);
CREATE TABLE pilot_staff.cookie_erasures (
 login_id pilot_staff.u PRIMARY KEY REFERENCES pilot_staff.logins(id), audit_id uuid NOT NULL REFERENCES pilot_staff.audit(id),
 erased_at timestamptz NOT NULL, reason text NOT NULL CHECK(reason='deadline')
);
-- C7's full WebAuthn chain is intentionally not installed in this new profile.
CREATE FUNCTION pilot_staff.immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'immutable pilot evidence' USING ERRCODE='23514'; END $$;
DO $$DECLARE n text; BEGIN
 FOREACH n IN ARRAY ARRAY['operations','logout_results','requests','audit','read_evidence','contexts','logout_contexts','envelope_nonces','cookie_erasures'] LOOP
  EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON pilot_staff.%I FOR EACH ROW EXECUTE FUNCTION pilot_staff.immutable()',n);
 END LOOP;
END $$;
CREATE FUNCTION pilot_staff.protect_target() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' OR (to_jsonb(NEW)-'session_id') IS DISTINCT FROM (to_jsonb(OLD)-'session_id')
 OR (OLD.session_id IS NOT NULL AND NEW.session_id IS DISTINCT FROM OLD.session_id)
 THEN RAISE EXCEPTION 'immutable pilot target' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER protect_target BEFORE UPDATE OR DELETE ON pilot_staff.targets FOR EACH ROW EXECUTE FUNCTION pilot_staff.protect_target();
CREATE FUNCTION pilot_staff.protect_permit() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' OR (to_jsonb(NEW)-'revoked_at') IS DISTINCT FROM (to_jsonb(OLD)-'revoked_at')
 OR OLD.revoked_at IS NOT NULL THEN RAISE EXCEPTION 'immutable permit version' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER protect_permit BEFORE UPDATE OR DELETE ON pilot_staff.permits FOR EACH ROW EXECUTE FUNCTION pilot_staff.protect_permit();
CREATE FUNCTION pilot_staff.protect_login() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' OR (to_jsonb(NEW)-ARRAY['cookie_envelope','envelope_erased_at','confirmed_at','revoked_at'])
 IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['cookie_envelope','envelope_erased_at','confirmed_at','revoked_at'])
 OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at)
 OR (OLD.envelope_erased_at IS NOT NULL AND (NEW.envelope_erased_at IS DISTINCT FROM OLD.envelope_erased_at OR NEW.cookie_envelope IS NOT NULL))
 OR (OLD.confirmed_at IS NOT NULL AND NEW.confirmed_at IS DISTINCT FROM OLD.confirmed_at)
 OR (NEW.cookie_envelope IS NOT NULL AND NEW.cookie_envelope IS DISTINCT FROM OLD.cookie_envelope)
 THEN RAISE EXCEPTION 'immutable login provenance' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER protect_login BEFORE UPDATE OR DELETE ON pilot_staff.logins FOR EACH ROW EXECUTE FUNCTION pilot_staff.protect_login();
REVOKE ALL ON ALL TABLES IN SCHEMA pilot_staff FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA pilot_staff FROM PUBLIC;
GRANT USAGE ON SCHEMA pilot_staff TO pilot_staff_auth,pilot_staff_reader,pilot_staff_operator;
COMMIT;
