\set ON_ERROR_STOP on
-- Fresh isolated V00 email-entry namespace only. Operator installs; never runtime.
BEGIN;
CREATE ROLE v00_email_owner NOLOGIN;
CREATE ROLE v00_email_ingress NOLOGIN;
CREATE ROLE v00_email_executor NOLOGIN;
CREATE ROLE v00_email_witness NOLOGIN;
CREATE ROLE v00_email_observer NOLOGIN;
GRANT v00_upstream_owner TO v00_email_owner;
CREATE SCHEMA v00_email AUTHORIZATION v00_email_owner;
REVOKE ALL ON SCHEMA v00_email FROM PUBLIC;
GRANT SELECT(email,banned_until) ON auth.users TO v00_email_owner;
GRANT EXECUTE ON FUNCTION v00_upstream_crypto.digest(bytea,text) TO v00_email_owner;
SET LOCAL ROLE v00_email_owner;
ALTER DEFAULT PRIVILEGES IN SCHEMA v00_email REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- Operator allowlist, not an authenticated context binding. No plaintext address.
CREATE TABLE v00_email.directory (
  address_digest text PRIMARY KEY CHECK(address_digest ~ '^[0-9a-f]{64}$'),
  address_key_id text NOT NULL CHECK(address_key_id='email-address-1'),
  actor_id uuid NOT NULL UNIQUE REFERENCES v00_upstream.subjects,
  enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE v00_email.contexts (
  id uuid PRIMARY KEY,
  proof_digest text NOT NULL CHECK(proof_digest ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  access_confirmed boolean NOT NULL DEFAULT false,
  revoked_at timestamptz,
  stage text NOT NULL DEFAULT 'ready' CHECK(stage IN ('ready','email_verification','totp_verification','completed')),
  address_digest text REFERENCES v00_email.directory,
  binding_operation_id uuid,
  actor_id uuid REFERENCES v00_upstream.subjects,
  current_email_challenge_id uuid,
  factor_version uuid REFERENCES v00_upstream.factors,
  totp_challenge_id uuid,
  totp_issued_at timestamptz,
  totp_expires_at timestamptz,
  failures integer NOT NULL DEFAULT 0 CHECK(failures BETWEEN 0 AND 5),
  paused_until timestamptz,
  CHECK(expires_at=created_at+interval '30 minutes'),
  CHECK((address_digest IS NULL)=(binding_operation_id IS NULL)),
  CHECK((actor_id IS NULL)=(stage IN ('ready','email_verification'))),
  CHECK((totp_challenge_id IS NULL)=(totp_issued_at IS NULL)),
  CHECK((totp_challenge_id IS NULL)=(totp_expires_at IS NULL)),
  CHECK(totp_expires_at IS NULL OR (factor_version IS NOT NULL AND totp_expires_at>totp_issued_at AND totp_expires_at<=expires_at))
);
CREATE TABLE v00_email.materials (
  context_id uuid PRIMARY KEY REFERENCES v00_email.contexts,
  secret_id uuid NOT NULL UNIQUE,
  key_id text NOT NULL CHECK(key_id='email-cipher-1'),
  cipher_format text NOT NULL CHECK(cipher_format='v00-test-email-xchacha20poly1305-v1'),
  nonce text NOT NULL CHECK(octet_length(decode(nonce,'base64'))=24 AND nonce=encode(decode(nonce,'base64'),'base64')),
  ciphertext text NOT NULL CHECK(octet_length(decode(ciphertext,'base64')) BETWEEN 17 AND 270
    AND ciphertext=replace(encode(decode(ciphertext,'base64'),'base64'),E'\n','')),
  reveal_until timestamptz NOT NULL,
  UNIQUE(key_id,nonce)
);
CREATE TABLE v00_email.admissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  context_id uuid NOT NULL REFERENCES v00_email.contexts,
  operation_id uuid NOT NULL,
  action text NOT NULL CHECK(action IN ('C01','C02','C03','AUTH_TOTP_VERIFY')),
  fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
  comparison_hmac text NOT NULL CHECK(comparison_hmac ~ '^[0-9a-f]{64}$'),
  comparison_key_id text NOT NULL,
  executor_id uuid NOT NULL,
  executor_proof_digest text NOT NULL CHECK(executor_proof_digest ~ '^[0-9a-f]{64}$'),
  epoch bigint NOT NULL CHECK(epoch>0),
  captured_at timestamptz NOT NULL,
  deadline_at timestamptz NOT NULL,
  challenge_id uuid,
  locale text CHECK(locale IN ('ru','en')),
  UNIQUE(context_id,operation_id),
  UNIQUE(context_id,operation_id,action),
  UNIQUE(id,context_id,operation_id),
  CHECK(deadline_at=captured_at+interval '10 seconds'),
  CHECK((action='C01')=(challenge_id IS NULL)),
  CHECK((action IN ('C01','C03'))=(locale IS NOT NULL))
);
ALTER TABLE v00_email.contexts ADD FOREIGN KEY(id,binding_operation_id)
  REFERENCES v00_email.admissions(context_id,operation_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE v00_email.send_dispatches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  admission_id uuid NOT NULL UNIQUE REFERENCES v00_email.admissions,
  address_digest text NOT NULL REFERENCES v00_email.directory,
  provider_user_id uuid NOT NULL REFERENCES v00_upstream.subjects(provider_user_id),
  before_generation_id uuid REFERENCES v00_upstream.generations,
  sealed_at timestamptz NOT NULL
);
CREATE TABLE v00_email.send_observations (
  dispatch_id uuid PRIMARY KEY REFERENCES v00_email.send_dispatches,
  generation_id uuid NOT NULL UNIQUE REFERENCES v00_upstream.generations,
  observed_at timestamptz NOT NULL,
  accepted_at timestamptz NOT NULL,
  CHECK(observed_at>=accepted_at)
);
CREATE TABLE v00_email.challenges (
  id uuid PRIMARY KEY,
  context_id uuid NOT NULL REFERENCES v00_email.contexts,
  send_admission_id uuid NOT NULL UNIQUE REFERENCES v00_email.admissions,
  dispatch_id uuid NOT NULL UNIQUE REFERENCES v00_email.send_observations(dispatch_id),
  generation_id uuid NOT NULL UNIQUE REFERENCES v00_upstream.generations,
  issued_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  replaced_by_id uuid REFERENCES v00_email.challenges DEFERRABLE INITIALLY DEFERRED,
  consumed_by_operation_id uuid,
  UNIQUE(id,context_id),
  CHECK(expires_at>issued_at AND expires_at<=issued_at+interval '10 minutes'),
  CHECK(replaced_by_id IS NULL OR consumed_by_operation_id IS NULL)
);
ALTER TABLE v00_email.contexts ADD FOREIGN KEY(current_email_challenge_id,id)
  REFERENCES v00_email.challenges(id,context_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE v00_email.verify_dispatches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  admission_id uuid NOT NULL UNIQUE REFERENCES v00_email.admissions,
  challenge_id uuid NOT NULL UNIQUE REFERENCES v00_email.challenges,
  generation_id uuid NOT NULL UNIQUE REFERENCES v00_upstream.generations,
  provider_user_id uuid NOT NULL REFERENCES v00_upstream.subjects(provider_user_id),
  sealed_at timestamptz NOT NULL
);
CREATE TABLE v00_email.consumptions (
  dispatch_id uuid PRIMARY KEY REFERENCES v00_email.verify_dispatches,
  provider_user_id uuid NOT NULL,
  provider_txid bigint NOT NULL,
  observed_at timestamptz NOT NULL,
  UNIQUE(provider_user_id,provider_txid),
  UNIQUE(dispatch_id,provider_txid)
);
CREATE TABLE v00_email.verify_observations (
  dispatch_id uuid PRIMARY KEY,
  provider_txid bigint NOT NULL,
  provider_session_id uuid NOT NULL UNIQUE,
  observed_at timestamptz NOT NULL,
  FOREIGN KEY(dispatch_id,provider_txid) REFERENCES v00_email.consumptions(dispatch_id,provider_txid)
);
CREATE TABLE v00_email.results (
  context_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  action text NOT NULL,
  result jsonb NOT NULL,
  historical_http_status integer NOT NULL CHECK(historical_http_status IN (200,202,401)),
  resolved_at timestamptz NOT NULL,
  login_id uuid UNIQUE,
  PRIMARY KEY(context_id,operation_id),
  FOREIGN KEY(context_id,operation_id,action) REFERENCES v00_email.admissions(context_id,operation_id,action),
  FOREIGN KEY(context_id,operation_id,login_id) REFERENCES v00_session.results(context_id,operation_id,login_id) DEFERRABLE INITIALLY DEFERRED,
  CHECK(result->>'kind' IS NOT NULL AND result->>'kind' IN ('email_dispatch_accepted','auth_step_required','verification_rejected','login_completed')),
  CHECK((result->>'kind'='login_completed')=(login_id IS NOT NULL))
);
CREATE TABLE v00_email.negative_proofs (
  admission_id uuid PRIMARY KEY REFERENCES v00_email.admissions,
  context_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  challenge_id uuid NOT NULL REFERENCES v00_email.challenges,
  generation_id uuid NOT NULL REFERENCES v00_upstream.generations,
  kind text NOT NULL CHECK(kind IN ('live_mismatch','expired_current')),
  checked_at timestamptz NOT NULL,
  transaction_id bigint NOT NULL,
  FOREIGN KEY(context_id,operation_id) REFERENCES v00_email.results DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY(admission_id,context_id,operation_id) REFERENCES v00_email.admissions(id,context_id,operation_id)
);
CREATE TABLE v00_email.plans (
  context_id uuid PRIMARY KEY REFERENCES v00_email.contexts,
  operation_id uuid NOT NULL,
  admission_id uuid NOT NULL UNIQUE REFERENCES v00_email.admissions,
  action text NOT NULL,
  transaction_id bigint NOT NULL,
  FOREIGN KEY(context_id,operation_id) REFERENCES v00_email.results DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE v00_email.used_steps (
  factor_version uuid NOT NULL REFERENCES v00_upstream.factors,
  step bigint NOT NULL CHECK(step>=0),
  context_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  PRIMARY KEY(factor_version,step),
  FOREIGN KEY(context_id,operation_id) REFERENCES v00_email.results DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE v00_email.audit (
  ordinal bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  context_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  kind text NOT NULL CHECK(kind IN ('email_dispatch_accepted','email_stage','verification_rejected','completion')),
  recorded_at timestamptz NOT NULL,
  UNIQUE(context_id,operation_id),
  FOREIGN KEY(context_id,operation_id) REFERENCES v00_email.results DEFERRABLE INITIALLY DEFERRED
);
DO $$ DECLARE tab text; BEGIN
  FOREACH tab IN ARRAY ARRAY['admissions','send_dispatches','send_observations','verify_dispatches','consumptions','verify_observations','results','negative_proofs','plans','used_steps','audit'] LOOP
    EXECUTE format('CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON v00_email.%I FOR EACH ROW EXECUTE FUNCTION v00_upstream.immutable()',tab);
  END LOOP;
END $$;
GRANT USAGE ON SCHEMA v00_email TO v00_email_ingress,v00_email_executor,v00_email_witness,v00_email_observer;
COMMIT;
