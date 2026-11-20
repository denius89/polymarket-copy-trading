set -euo pipefail
cd -- "$(dirname -- "$0")"
umask 077
readarray -t ips < control/ips
for role in gateway client; do
 name=localhost
 test "$role" = gateway || name=staff-local-client
 openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -days 2 -subj "/CN=$name" -addext "subjectAltName=DNS:$name" -keyout "gatewaycfg/$role.key" -out "gatewaycfg/$role.crt" >/dev/null 2>&1
done
openssl x509 -in gatewaycfg/client.crt -outform DER | sha256sum | cut -d' ' -f1 > gatewaycfg/client.sha256
python3 - "${ips[1]}" "${ips[2]}" <<'PY'
import json,pathlib,sys
p=pathlib.Path.cwd(); b=json.loads((p/'control/material/runtime-binding.json').read_text())
cfg=dict(format='pilot-edge-v1',enabled=True,deploymentDigest=b['deploymentDigest'],cutoffAt=b['cutoffAt'],networkKeyFile=str(p/'gatewaycfg/network'))
for role,host in zip(('auth','reader'),sys.argv[1:]):
    cfg[role]=dict(host=host,port=8080,ingressKeyFile=str(p/('gatewaycfg/ingress-'+role)))
(p/'gatewaycfg/gateway.json').write_text(json.dumps(cfg))
PY
exec env PYTHONPATH="$PWD/operator:$PWD/gateway/v00-polygon" python3 -B "$PWD/gateway-local.py"
