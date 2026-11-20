\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '10s';
SELECT set_config('pilot_staff.expected_deployment_digest', :'deployment_digest', true) AS _digest \gset
SELECT (pilot_staff.provision(:'provision_json'::jsonb)->>'status' = 'ok') AS provisioned \gset
\if :provisioned
SELECT (pilot_staff.bind_sessions(jsonb_build_object(
  'request_id', :'bind_request_id'::uuid,
  'session_ids', jsonb_build_array(:'session_1'::uuid, :'session_2'::uuid)
))->>'status' = 'ok') AS bound \gset
\if :bound
COMMIT;
\echo Staff targets bound, pilot remains disabled
\else
ROLLBACK;
DO $$ BEGIN RAISE EXCEPTION 'Staff assignment was refused'; END $$;
\endif
\else
ROLLBACK;
DO $$ BEGIN RAISE EXCEPTION 'Staff provisioning was refused'; END $$;
\endif
