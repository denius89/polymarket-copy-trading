#!/bin/bash
set -euo pipefail
umask 077
root=/opt/shadow-v00-integrated
db=shadow-v00-integrated-db-1
auth=shadow-v00-integrated-auth-1
work=$(mktemp -d "$root/physical-check.XXXXXXXX")
suffix=${work##*.}
base_in="/tmp/v00-physical-$suffix"
target="v00-physical-restore-$suffix"
auth_stopped=false

cleanup() {
    docker rm -fv "$target" >/dev/null 2>&1 || true
    docker exec "$db" rm -rf -- "$base_in" >/dev/null 2>&1 || true
    if [[ "$auth_stopped" == true ]]; then docker start "$auth" >/dev/null || true; fi
}
trap cleanup EXIT

snapshot() {
    docker exec "$1" psql -XAtq -v ON_ERROR_STOP=1 -U postgres -d shadow_v00 -c "
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL ROLE v00_db_observer;
SELECT v00_db.snapshot('{}'::jsonb);
COMMIT;"
}
rights() {
    docker exec "$1" psql -XAtq -v ON_ERROR_STOP=1 -U postgres -d shadow_v00 -c "
BEGIN READ ONLY;
SELECT jsonb_build_object(
  'policies',(SELECT jsonb_agg(to_jsonb(p) ORDER BY p.tablename,p.policyname)
               FROM pg_policies p WHERE schemaname='auth' AND tablename IN ('users','sessions')),
  'roles',(SELECT jsonb_agg(jsonb_build_array(rolname,rolcanlogin,rolsuper,rolbypassrls) ORDER BY rolname)
            FROM pg_roles WHERE rolname IN ('v00_db_owner','v00_db_executor','v00_db_observer','v00_controller')),
  'triggers',(SELECT jsonb_agg(pg_get_triggerdef(t.oid) ORDER BY t.tgname)
               FROM pg_trigger t WHERE tgname LIKE 'v00_%' AND tgrelid IN ('auth.users'::regclass,'auth.sessions'::regclass)),
  'allowlist',(SELECT jsonb_agg(user_id ORDER BY user_id) FROM v00_db.provider_allowlist),
  'executor_auth_id_read',has_column_privilege('v00_db_executor','auth.users','id','SELECT'),
  'observer_snapshot_exec',has_function_privilege('v00_db_observer','v00_db.snapshot(jsonb)','EXECUTE'),
  'executor_seal_exec',has_function_privilege('v00_db_executor','v00_db.seal_email(jsonb)','EXECUTE'),
  'controller_executor_member',pg_has_role('v00_controller','v00_db_executor','MEMBER')
);
SET LOCAL ROLE v00_db_owner;
SELECT jsonb_build_object('visible_users',count(id)) FROM auth.users;
COMMIT;"
}
t0=$(python3 -c 'import time; print(time.monotonic_ns())')
test "$(docker ps -q --filter name='^v00-controller-')" = ""
docker stop "$auth" >/dev/null
auth_stopped=true
snapshot "$db" > "$work/source.json"
rights "$db" > "$work/source-rights.jsonl"
docker exec -u postgres "$db" pg_basebackup -U postgres -D "$base_in" -X stream --checkpoint=fast
docker exec -u postgres "$db" pg_verifybackup "$base_in"
mkdir "$work/base" "$work/restored"
docker cp "$db:$base_in/." "$work/base"
cp -a "$work/base/." "$work/restored/"
docker start "$auth" >/dev/null
auth_stopped=false
docker run -d --network none --name "$target" --memory 768m \
    -v "$work/restored:/var/lib/postgresql/data" postgres:17.11-bookworm \
    postgres -c listen_addresses= -c default_transaction_read_only=on >/dev/null
for ((i=0; i<45; i++)); do
    if docker exec "$target" psql -XAt -U postgres -d shadow_v00 -c 'select 1' >/dev/null 2>&1; then break; fi
    sleep 1
done
test "$(docker exec "$target" psql -XAt -U postgres -d shadow_v00 -c 'show default_transaction_read_only')" = on
snapshot "$target" > "$work/restored.json"
rights "$target" > "$work/restored-rights.jsonl"
cmp -s "$work/source-rights.jsonl" "$work/restored-rights.jsonl"
echo "restored_rights_catalog_and_visibility_match=true"
python3 "$root/packages/scripts/v00-db/compare_snapshots.py" "$work/source.json" "$work/restored.json" | tee "$work/comparison.json"
python3 - "$t0" <<'ELAPSED'
import sys,time
print("local_seconds_from_quiesce_to_comparison="+str(round((time.monotonic_ns()-int(sys.argv[1]))/1e9,3)))
ELAPSED
printf 'private_artifact_path=%s\n' "$work"
