\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL SERIALIZABLE;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '10s';
SELECT set_config('pilot_staff.expected_deployment_digest', :'previous_digest', true) AS _digest \gset
SELECT (pilot_staff.prepare_renewal(:'renewal_json'::jsonb)->>'status'='ok') AS prepared \gset
\if :prepared
COMMIT;
\echo Staff period prepared, access remains disabled
\else
ROLLBACK;
DO $$ BEGIN RAISE EXCEPTION 'Staff renewal was refused'; END $$;
\endif
