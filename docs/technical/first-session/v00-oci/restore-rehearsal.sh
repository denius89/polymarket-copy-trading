#!/bin/bash
set -euo pipefail
umask 077

# This exercise creates only synthetic data in private, disposable PostgreSQL containers.
image=postgres:17.11-bookworm
expected_image=sha256:839fbb5a4942a7758dd93e18b42ea5649807491a0545b5eeeb8f0b8bb11857a5
test "$(docker image inspect --format '{{.Architecture}} {{.Id}}' "$image")" = "arm64 $expected_image"
run=$(date -u +%Y%m%dT%H%M%S)-$$
work=$(mktemp -d /opt/shadow-v00/restore-rehearsal.XXXXXXXX)
src="v00-pitr-$run-source"
before="v00-pitr-$run-before"
after="v00-pitr-$run-after"
gap="v00-pitr-$run-gap"

cleanup() {
    for name in "$gap" "$after" "$before" "$src"; do
        docker rm -fv "$name" >/dev/null 2>&1 || true
    done
}
trap cleanup EXIT

sql() {
    docker exec "$1" psql -XAt -v ON_ERROR_STOP=1 -U postgres -d postgres -c "$2"
}
wait_sql() {
    local name=$1
    for ((i=0; i<45; i++)); do
        if sql "$name" 'select 1' >/dev/null 2>&1; then return 0; fi
        sleep 1
    done
    docker logs --tail 12 "$name" >&2
    return 1
}
tick() {
    python3 -c 'import time; print(time.monotonic_ns())'
}
elapsed() {
    python3 -c 'import sys; print(round((int(sys.argv[2])-int(sys.argv[1]))/1e9,3))' "$1" "$(tick)"
}
await_archive() {
    local segment=$1
    for ((i=0; i<30; i++)); do
        if docker exec "$src" test -s "/tmp/v00-wal/$segment"; then return 0; fi
        sleep 1
    done
    return 1
}

docker run -d --network none --name "$src" --memory 768m \
    -e POSTGRES_HOST_AUTH_METHOD=trust "$image" postgres -c listen_addresses= \
    -c archive_mode=on -c 'archive_command=test ! -f /tmp/v00-wal/%f && cp %p /tmp/v00-wal/%f.tmp && sync -f /tmp/v00-wal/%f.tmp && mv /tmp/v00-wal/%f.tmp /tmp/v00-wal/%f' >/dev/null
docker exec -u postgres "$src" mkdir -p /tmp/v00-wal
wait_sql "$src"
# Ensure the image entrypoint has finished bootstrapping and final settings are active.
for ((i=0; i<30; i++)); do
    if [[ "$(sql "$src" 'show archive_mode' 2>/dev/null || true)" == on ]]; then break; fi
    sleep 1
done
test "$(sql "$src" 'show archive_mode')" = on
sql "$src" "
CREATE ROLE v00_fixture_reader NOLOGIN;
CREATE SCHEMA auth_fixture;
CREATE SCHEMA shadow_fixture;
CREATE TABLE auth_fixture.access (id integer PRIMARY KEY, state text NOT NULL);
CREATE TABLE shadow_fixture.event (seq integer PRIMARY KEY, name text NOT NULL);
INSERT INTO auth_fixture.access VALUES (1,'active');
INSERT INTO shadow_fixture.event VALUES (1,'seed');
GRANT USAGE ON SCHEMA auth_fixture, shadow_fixture TO v00_fixture_reader;
GRANT SELECT ON auth_fixture.access, shadow_fixture.event TO v00_fixture_reader;
" >/dev/null

docker exec -u postgres "$src" pg_basebackup -D /tmp/v00-base -X stream --checkpoint=fast
docker exec -u postgres "$src" pg_verifybackup /tmp/v00-base
mkdir "$work/base" "$work/wal" "$work/wal-gap"
docker cp "$src:/tmp/v00-base/." "$work/base"

sql "$src" "INSERT INTO shadow_fixture.event VALUES (2,'start')" >/dev/null
before_lsn=$(sql "$src" "SELECT pg_create_restore_point('v00_before_revoke')")
before_segment=$(sql "$src" "SELECT pg_walfile_name('$before_lsn')")
sql "$src" 'SELECT pg_switch_wal()' >/dev/null
await_archive "$before_segment"

sql "$src" "BEGIN; UPDATE auth_fixture.access SET state='revoked' WHERE id=1; INSERT INTO shadow_fixture.event VALUES (3,'revoke'); COMMIT;" >/dev/null
after_lsn=$(sql "$src" "SELECT pg_create_restore_point('v00_after_revoke')")
after_segment=$(sql "$src" "SELECT pg_walfile_name('$after_lsn')")
test "$before_segment" != "$after_segment"
target_timestamp=$(sql "$src" 'SELECT extract(epoch FROM clock_timestamp())')
sql "$src" 'SELECT pg_switch_wal()' >/dev/null
await_archive "$after_segment"

# This row represents a confirmed source commit beyond the selected target.
sql "$src" "INSERT INTO shadow_fixture.event VALUES (4,'beyond_target')" >/dev/null
incident_timestamp=$(sql "$src" 'SELECT extract(epoch FROM clock_timestamp())')
docker cp "$src:/tmp/v00-wal/." "$work/wal"
cp -a "$work/wal/." "$work/wal-gap/"
rm -- "$work/wal-gap/$after_segment"
chmod 0755 "$work/wal" "$work/wal-gap"
find "$work/wal" "$work/wal-gap" -type f -exec chmod 0644 {} +

(
    cd "$work"
    find base wal -type f -print0 | sort -z | xargs -0 sha256sum > artifact-sha256.txt
    sha256sum -c --quiet artifact-sha256.txt
)
echo "artifact_sha256_manifest=verified_locally"
echo "expected_lsn_before=$before_lsn expected_lsn_after=$after_lsn distinct_segments=true"

start_restore() {
    local name=$1 target=$2 archive=$3
    local data="$work/$target-$archive"
    mkdir "$data"
    cp -a "$work/base/." "$data/"
    touch "$data/recovery.signal"
    docker run -d --network none --name "$name" --memory 768m \
        -v "$data:/var/lib/postgresql/data" -v "$work/$archive:/archive:ro" \
        "$image" postgres -c listen_addresses= -c archive_mode=off \
        -c "restore_command=cp /archive/%f %p" \
        -c "recovery_target_name=$target" -c recovery_target_action=pause >/dev/null
}
wait_paused() {
    local name=$1
    for ((i=0; i<30; i++)); do
        if [[ "$(sql "$name" 'select pg_is_in_recovery() and pg_is_wal_replay_paused()' 2>/dev/null || true)" == t ]]; then return 0; fi
        sleep 1
    done
    docker logs --tail 12 "$name" >&2
    return 1
}
verify_target() {
    local name=$1 expected=$2 result
    result=$(sql "$name" "SET ROLE v00_fixture_reader;
SELECT (SELECT state FROM auth_fixture.access WHERE id=1),
       (SELECT string_agg(name, ',' ORDER BY seq) FROM shadow_fixture.event),
       has_table_privilege(current_user,'auth_fixture.access','UPDATE'),
       current_setting('transaction_read_only');")
    result=$(printf '%s\n' "$result" | tail -1)
    echo "$name state=$result replay_lsn=$(sql "$name" 'select pg_last_wal_replay_lsn()')"
    test "$result" = "$expected"
}

t0=$(tick)
start_restore "$before" v00_before_revoke wal
wait_paused "$before"
verify_target "$before" 'active|seed,start|f|on'
echo "local_seconds_to_verified_before_target=$(elapsed "$t0")"
t0=$(tick)
start_restore "$after" v00_after_revoke wal
wait_paused "$after"
verify_target "$after" 'revoked|seed,start,revoke|f|on'
echo "local_seconds_to_verified_after_target=$(elapsed "$t0")"

start_restore "$gap" v00_after_revoke wal-gap
for ((i=0; i<30; i++)); do
    if [[ "$(docker inspect --format '{{.State.Running}}' "$gap")" == false ]]; then break; fi
    sleep 1
done
test "$(docker inspect --format '{{.State.Running}}' "$gap")" = false
test "$(docker inspect --format '{{.State.ExitCode}}' "$gap")" -ne 0
docker logs "$gap" 2>&1 | grep 'recovery ended before configured recovery target was reached' >/dev/null
echo "missing_wal_target_refused=true"
python3 -c 'import sys; print("seconds_between_target_and_incident_fixture="+str(round(float(sys.argv[2])-float(sys.argv[1]),3)))' "$target_timestamp" "$incident_timestamp"
# Artifacts contain synthetic data, still keep the parent private. No cloud delivery is claimed.
printf 'private_artifact_path=%s\n' "$work"
