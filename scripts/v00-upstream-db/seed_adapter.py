#!/usr/bin/env python3
"""Operator-only fresh fixture loader; actual provider setup is a separate step."""
import base64
import json
import os
import subprocess
import sys


def load(path):
    with open(path, encoding='utf-8') as stream:
        payload = json.load(stream)
    encoded = base64.b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode()
    # psql17 extended protocol: payload is never part of SQL text/error statements.
    text = ("BEGIN; SET LOCAL ROLE v00_upstream_owner;\n"
            "SELECT v00_upstream.seed_fixture(convert_from(decode($1,'base64'),'UTF8')::jsonb)::text\n"
            "\\bind '" + encoded + "'\n\\g\nCOMMIT;\n")
    command = json.loads(os.environ['V00_UPSTREAM_PSQL_COMMAND_JSON'])
    result = subprocess.run(command + ['-XAt', '-v', 'ON_ERROR_STOP=1'], input=text,
                            text=True, capture_output=True, timeout=30)
    if result.returncode or result.stdout.splitlines()[-1:] != ['COMMIT']:
        raise RuntimeError('fixture transaction not confirmed; inspect privately, do not repeat blindly')
    rows = [line for line in result.stdout.splitlines() if line.startswith('{')]
    if len(rows) != 1:
        raise RuntimeError('unexpected fixture reply')
    reply = json.loads(rows[0])
    if set(reply) != {'subjects_inserted', 'contexts_inserted'}:
        raise RuntimeError('unexpected fixture reply')
    return reply


if __name__ == '__main__':
    print(json.dumps(load(sys.argv[1])))
