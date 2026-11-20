#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
umask 077
test -f build-lock.json
test ! -e control
node_image=$(python3 -c 'import json; print(json.load(open("build-lock.json"))["images"]["node"])')
postgres_image=$(python3 -c 'import json; print(json.load(open("build-lock.json"))["images"]["postgres"])')
for image in "$node_image" "$postgres_image"; do
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    docker pull "$image" || docker pull "$image"
  fi
done
docker run --pull never --rm -v "$PWD/api:/work" -w /work "$node_image" \
  sh -ec '
    npm ci --ignore-scripts --no-audit --no-fund --fetch-retries=1
    npm run build --workspace @cct/admin -- --outDir dist-default
    export VITE_STAFF_Q06=1 VITE_STAFF_Q06_ORIGIN=http://127.0.0.1:52486
    export VITE_STAFF_Q06_ORIGIN_SHA256=fdc03d5d4faa27371db32001ef6d37fb86bd0d19fb1a4527b476d1333e44e8c4
    npm run build --workspace @cct/admin -- --mode staff-q06-local
  '
bash "$PWD/run-new.sh"
exec bash "$PWD/start-gateway.sh"
