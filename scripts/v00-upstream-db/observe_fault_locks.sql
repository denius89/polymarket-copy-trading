-- Operator-only read-only observation. Never run with the application runtime role.
-- Set PGAPPNAME=v00-ub07-* on the dedicated probe connections; no query/parameters.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SELECT jsonb_build_object(
  'schema','v00-upstream-lock-observation-v1',
  'observed_at',clock_timestamp(),
  'backends',COALESCE((SELECT jsonb_agg(jsonb_build_object(
    'pid',a.pid,'application_name',a.application_name,'state',a.state,
    'wait_event_type',a.wait_event_type,'wait_event',a.wait_event,
    'blocking_pids',pg_blocking_pids(a.pid)) ORDER BY a.pid)
    FROM pg_stat_activity a WHERE a.datname=current_database()
      AND a.application_name LIKE 'v00-ub07-%' AND a.pid<>pg_backend_pid()),'[]'::jsonb),
  'locks',COALESCE((SELECT jsonb_agg(jsonb_build_object(
    'pid',l.pid,'locktype',l.locktype,'mode',l.mode,'granted',l.granted,
    'relation',CASE WHEN l.relation IS NULL THEN NULL ELSE l.relation::regclass::text END,
    'transactionid',l.transactionid::text,'virtualxid',l.virtualxid,
    'page',l.page,'tuple',l.tuple) ORDER BY l.pid,l.locktype,l.mode)
    FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid
    WHERE a.datname=current_database() AND a.application_name LIKE 'v00-ub07-%'
      AND a.pid<>pg_backend_pid()),'[]'::jsonb));
COMMIT;
