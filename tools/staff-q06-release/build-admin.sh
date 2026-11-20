#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
node_image=$(python3 -c 'import json; print(json.load(open("release-lock.json"))["nodeImage"])')
docker run --rm --pull never -v "$PWD/src:/work" -w /work \
  -e VITE_STAFF_Q06 -e VITE_STAFF_Q06_ORIGIN -e VITE_STAFF_Q06_ORIGIN_SHA256 \
  "$node_image" sh -ec 'npm ci --ignore-scripts --no-audit --no-fund && npm run build:admin'
