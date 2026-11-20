\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '10s';
SELECT set_config('pilot_staff.expected_deployment_digest', :'deployment_digest', true) AS _digest \gset
SELECT (reply->>'status' = 'ok') AS closed
FROM (SELECT pilot_staff.close_pilot(jsonb_build_object('request_id', :'request_id'::uuid)) AS reply) outcome \gset
\if :closed
COMMIT;
\echo Staff pilot closed
\else
ROLLBACK;
\echo Staff pilot closure was refused
DO $$ BEGIN RAISE EXCEPTION 'Staff pilot closure was refused'; END $$;
\endif
