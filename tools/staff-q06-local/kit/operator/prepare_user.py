"""Create credentials for the synthetic user API in this disposable stage."""
import json
from pathlib import Path
import secrets
import sys

database, profile = sys.argv[1:]
if database != "pilot_trial_local":
    raise ValueError("Expected the isolated Q06 database")
config_dir = Path("usercfg")
credential = secrets.token_hex(32)
cursor = {"keyId": secrets.token_hex(16), "hex": secrets.token_hex(32)}
password = secrets.token_hex(24)
(config_dir / "credential.json").write_text(json.dumps({
    "credential": {"id": "credential-1", "hex": credential},
}))
(config_dir / "cursor.json").write_text(json.dumps({
    "format": "q02-cursor-keyset-v1", "enabled": True,
    "issuerKeyId": cursor["keyId"], "keys": [cursor], "revoked": [],
}))
(config_dir / "config.json").write_text(json.dumps({
    "profile": "polygon-paper-v1", "origin": "https://localhost:18443",
    "databaseUrl": f"postgresql://pilot_http_user:{password}@pgtrial:5432/{database}",
    "credentialKeyFile": "/run/pilot/credential.json",
    "cursorKeyFile": "/run/pilot/cursor.json", "calendarProfile": json.loads(profile),
    "startEnabled": False, "bindHost": "0.0.0.0", "port": 8080,
    "ingress": {"mode": "direct-test"},
}))
Path("control/user-role.sql").write_text(
    "CREATE ROLE pilot_http_user LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS "
    f"PASSWORD '{password}' IN ROLE polygon_executor;\n",
)
