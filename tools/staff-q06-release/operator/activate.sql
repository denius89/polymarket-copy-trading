\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '10s';
SELECT set_config('pilot_staff.expected_deployment_digest', :'deployment_digest', true) AS _digest \gset
SELECT (pilot_staff.activate(jsonb_build_object('request_id', :'request_id'::uuid))->>'status' = 'ok') AS activated \gset
\if :activated
COMMIT;
\echo Staff pilot activated
\else
ROLLBACK;
DO $$ BEGIN RAISE EXCEPTION 'Staff pilot activation was refused'; END $$;
\endif
