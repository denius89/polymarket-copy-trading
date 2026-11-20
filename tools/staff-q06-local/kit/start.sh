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
  sh -ec 'npm ci --ignore-scripts --no-audit --no-fund --fetch-retries=1 && npm run build:admin'
bash "$PWD/run-new.sh"
exec bash "$PWD/start-gateway.sh"
