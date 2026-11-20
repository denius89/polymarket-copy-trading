set -euo pipefail
cd -- "$(dirname -- "$0")"
stage=$PWD
umask 077
node_image=$(python3 -c 'import json; print(json.load(open("build-lock.json"))["images"]["node"])')
pg_image=$(python3 -c 'import json; print(json.load(open("build-lock.json"))["images"]["postgres"])')
db=pilot_trial_local
project=staff-acceptance
netid=$(docker network create --internal "$project")
export POSTGRES_PASSWORD=$(openssl rand -hex 24)
dbid=$(docker run -d --pull never --name "$project-db" --network "$netid" --network-alias pgtrial -e "POSTGRES_DB=$db" -e POSTGRES_PASSWORD "$pg_image")
for i in $(seq 1 30); do
 docker exec -u postgres "$dbid" pg_isready -h 127.0.0.1 -U postgres -d "$db" >/dev/null 2>&1 && break
 sleep 1
done
psql_db() { docker exec -i -u postgres "$dbid" psql -XqAt -U postgres -d "$db" -v ON_ERROR_STOP=1 "$@"; }
profile=$(docker run --pull never --rm --network none "$node_image" node -p 'JSON.stringify({node:process.versions.node,icu:process.versions.icu,tzdb:process.versions.tz,temporalPolyfill:"0.5.1"})')
export FIXTURE_TZ=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["tzdb"])' "$profile")
install -d -m 700 control usercfg
python3 operator/prepare_user.py "$db" "$profile"
export USER_KEY=$(python3 -c 'import json; print(json.load(open("usercfg/credential.json"))["credential"]["hex"])')
test -f api/node_modules/pg/lib/index.js
test -f api/apps/admin/dist/index.html
docker run --pull never --rm --network "$netid" -v "$PWD:/work" -w /work -e POSTGRES_PASSWORD -e USER_KEY -e FIXTURE_TZ "$node_image" node polygon-live-buy-compose-20261113/q06-fixture.mjs
psql_db < control/user-role.sql >/dev/null
install -d -m 700 authcfg readercfg gatewaycfg control
python3 - "$stage" <<'PY'
import datetime,json,pathlib,sys,uuid
from zoneinfo import ZoneInfo
p=pathlib.Path(sys.argv[1]); targets=json.loads((p/'targets.json').read_text())
now=datetime.datetime.now(datetime.timezone.utc)
zone=ZoneInfo('Europe/Warsaw')
cutoff=datetime.datetime.combine(now.astimezone(zone).date()+datetime.timedelta(days=1),datetime.time(23),zone).astimezone(datetime.timezone.utc)
fmt=lambda t:t.isoformat(timespec='milliseconds').replace('+00:00','Z')
descriptor=dict(version='pilot-staff-deployment-v1',runId=str(uuid.uuid4()),origin='https://localhost:18443',openedAt=fmt(now),cutoffAt=fmt(cutoff))
(p/'control/descriptor-input.json').write_text(json.dumps(dict(descriptor=descriptor,targetUserIds=[t['user'] for t in targets])))
PY
python3 operator/provision_material.py "$stage/control/descriptor-input.json" "$stage/control/material"
python3 - "$stage" "$db" <<'PY'
import json,pathlib,secrets,sys,uuid
p=pathlib.Path(sys.argv[1]); db=sys.argv[2]; m=p/'control/material'
b=json.loads((m/'runtime-binding.json').read_text())
targets=json.loads((p/'targets.json').read_text())
roles=[]
for role, names in [('auth',('permit','context','login','cipher')),('reader',('login','logout'))]:
    d=p/(role+'cfg')
    secret=secrets.token_hex(24)
    (d/'password').write_text(secret)
    roles.append(f"CREATE ROLE pilot_http_{role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD '{secret}' IN ROLE pilot_staff_{role};")
    keypaths={}
    for name in (*names,'ingress-'+role):
        candidates=[f for f in m.iterdir() if f.name in (name,name+'.key',name+'.bin')]
        assert len(candidates)==1 and candidates[0].stat().st_size==32
        (d/name).write_bytes(candidates[0].read_bytes())
        if name in names:keypaths[name]='/run/pilot/'+name
    if role=='auth':keypaths['cipherKeyId']=b['cipherKeyId']
    cfg=dict(version='pilot-staff-runtime-v1',enabled=True,role=role,runId=b['runId'],deploymentDigest=b['deploymentDigest'],cutoffAt=b['cutoffAt'],bindHost='0.0.0.0',port=8080,dbTransport='isolated-private-network',database=dict(host='pgtrial',port=5432,name=db,user='pilot_http_'+role,passwordFile='/run/pilot/password'),ingressKeyFile='/run/pilot/ingress-'+role,keys=keypaths)
    (d/'config.json').write_text(json.dumps(cfg))
    (p/'gatewaycfg'/('ingress-'+role)).write_bytes((d/('ingress-'+role)).read_bytes())
network=[f for f in m.iterdir() if f.name in ('network','network.key','network.bin')]
assert len(network)==1 and network[0].stat().st_size==32
(p/'gatewaycfg/network').write_bytes(network[0].read_bytes())
roles.append('CREATE ROLE pilot_http_operator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE pilot_staff_operator;')
(p/'control/roles.sql').write_text('\n'.join(roles))
def statement(method,value):
    payload=json.dumps(value,ensure_ascii=True,separators=(',',':'))
    return f"DO $$ DECLARE r jsonb; BEGIN r:=pilot_staff.{method}($payload${payload}$payload$::jsonb); IF r->>'status' IS DISTINCT FROM 'ok' THEN RAISE EXCEPTION 'operator RPC refused: {method}'; END IF; END $$;"
operations=[('provision',json.loads((m/'provision.json').read_text())),('bind_sessions',dict(request_id=str(uuid.uuid4()),session_ids=[t['session'] for t in targets])),('activate',dict(request_id=str(uuid.uuid4())))]
sql=['SET SESSION AUTHORIZATION pilot_http_operator;']
for method,value in operations:
    sql.extend(['BEGIN ISOLATION LEVEL SERIALIZABLE;',f"SET LOCAL pilot_staff.expected_deployment_digest='{b['deploymentDigest']}';",statement(method,value),'COMMIT;'])
(p/'control/activate.sql').write_text('\n'.join(sql))
PY
psql_db < control/roles.sql >/dev/null
psql_db < control/activate.sql >/dev/null
printf 'CLEAN_PILOT_ACTIVATED\n'
chown -R 1000:1000 authcfg
chown -R 1001:1001 readercfg
chown -R 1002:1002 usercfg
start_role() {
 local role=$1 uid=$2
 shift 2
 docker run -d --pull never --network "$netid" --name "$project-$role" --user "$uid:$uid" --read-only --cap-drop ALL --security-opt no-new-privileges:true --memory 192m --pids-limit 32 --tmpfs /tmp:rw,noexec,nosuid,nodev,mode=1777 --mount "type=bind,src=$stage/api,dst=/input,readonly" --mount "type=bind,src=$stage/${role}cfg,dst=/run/pilot,readonly" --workdir /input/apps/api -e POLYGON_DISPOSABLE_HTTP=offline-http-clone -e POLYGON_API_CONFIG=/run/pilot/config.json --entrypoint node "$node_image" "$@"
}
start_role user 1002 src/runtime.ts
start_role auth 1000 src/pilot/runtime.ts /run/pilot/config.json
start_role reader 1001 src/pilot/runtime.ts /run/pilot/config.json
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$project-user" "$project-auth" "$project-reader" > control/ips
