#!/usr/bin/env python3
"""Operator-run RLS negative control. Requires actual listed AND unlisted users.

V00_LISTED_USER / V00_UNLISTED_USER are synthetic UUIDs, not email or tokens.
No fixture creates, writes to provider rows or seals commit from this script.
"""
import json
import os
import uuid
from verify_storage import quote, sql


def main():
    listed = str(uuid.UUID(os.environ['V00_LISTED_USER']))
    unlisted = str(uuid.UUID(os.environ['V00_UNLISTED_USER']))
    if listed == unlisted:
        raise ValueError('distinct existing users required')
    prerequisites = json.loads(sql("SELECT jsonb_build_object('listed_exists',EXISTS(SELECT 1 FROM auth.users WHERE id=" + quote(listed) + "),"
        "'unlisted_exists',EXISTS(SELECT 1 FROM auth.users WHERE id=" + quote(unlisted) + "),"
        "'listed_allowed',EXISTS(SELECT 1 FROM v00_db.provider_allowlist WHERE user_id=" + quote(listed) + "),"
        "'unlisted_allowed',EXISTS(SELECT 1 FROM v00_db.provider_allowlist WHERE user_id=" + quote(unlisted) + "));",role=None))
    if prerequisites != dict(listed_exists=True,unlisted_exists=True,listed_allowed=True,unlisted_allowed=False):
        raise ValueError('RLS control prerequisites not satisfied')
    cases = []
    def case(name, expected, actual):
        cases.append(dict(case=name,expected=expected,actual=actual,verdict='pass' if expected==actual else 'fail'))
    case('RLS01-listed-read', '1', sql('SELECT count(id) FROM auth.users WHERE id=' + quote(listed) + ';'))
    case('RLS02-existing-unlisted-hidden', '0', sql('SELECT count(id) FROM auth.users WHERE id=' + quote(unlisted) + ';'))
    case('RLS03-listed-rowlock', listed, sql('BEGIN; SELECT id FROM auth.users WHERE id=' + quote(listed) + ' FOR UPDATE; ROLLBACK;'))
    for name, role, statement in [
        ('RLS04-owner-write-denied','v00_db_owner','UPDATE auth.users SET id=id WHERE id=' + quote(listed) + ';'),
        ('RLS05-executor-provider-read-denied','v00_db_executor','SELECT id FROM auth.users WHERE id=' + quote(listed) + ';'),
        ('RLS06-executor-allowlist-write-denied','v00_db_executor','INSERT INTO v00_db.provider_allowlist(user_id) VALUES(' + quote(unlisted) + ');')]:
        denied = False
        try:
            sql('BEGIN;' + statement + 'ROLLBACK;',role=role)
        except RuntimeError as error:
            denied = 'row-level security' in str(error) or 'permission denied' in str(error)
        case(name,True,denied)
    flags = json.loads(sql("SELECT jsonb_agg(jsonb_build_object('table',relname,'rls',relrowsecurity) ORDER BY relname) FROM pg_class WHERE oid IN ('auth.users'::regclass,'auth.sessions'::regclass);",role=None))
    case('RLS07-provider-RLS-remains-on',[{'table':'sessions','rls':True},{'table':'users','rls':True}],flags)
    bypass = sql("SELECT count(*) FROM pg_roles WHERE rolname IN ('v00_db_owner','v00_db_executor','v00_db_observer') AND (rolsuper OR rolbypassrls);",role=None)
    case('RLS08-no-bypass','0',bypass)
    print(json.dumps(dict(profile='v00-provider-rls-v1',cases=cases),indent=2))
    return int(any(row['verdict']!='pass' for row in cases))


if __name__ == '__main__':
    raise SystemExit(main())
