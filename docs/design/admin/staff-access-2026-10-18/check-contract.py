"""Checks the handoff examples and their boundaries, never a running authorization engine."""
import json
from pathlib import Path
P=Path(__file__).parent
D=json.loads((P/'screen-content.json').read_text());B={x['key']:x for x in D};M=json.loads((P/'role-matrix.json').read_text());E=json.loads((P/'existing-critical-routes.json').read_text())
checks=[]
def check(name,p):
 assert p,name
 checks.append(name)
check('29 unique paired states',len(D)==len(B)==29)
check('18 sections explicitly included',len(M['sections'])==18 and len({r[0].split(' · ')[0] for r in M['sections']})==18)
check('7 independent action types',M['actions']==['read','create','edit','publish','run','stop','export'])
check('example grants no owner, export or money',all(M[k] is False for k in ['ownerPrivileges','export','financialData']))
check('Polymarket demo only',M['venues']==['Polymarket'] and M['environment']=='demo')
check('explicit time boundary',M['expiresAt']=='2026-10-19T18:00:00Z')
check('section actions shown independently',len(B['access-role-actions']['rows'])==7)
check('role version conflict separate from save',B['access-role-conflict']['actions'][0][2]=='access-role-editor')
check('all control targets exist',all(a[2] in B for d in D for a in d['actions']+d['scenarios']))
check('all detail targets exist',all(v in B or v in E for d in D for v in list(d.get('rowLinks',{}).values())+[x for x in d.get('rowTargets',[]) if x]))
check('no owner escalation from restricted working actions',all(B[a[2]]['actor']!='owner' for d in D if d['actor'] not in ['owner','expired','revoked'] for a in d['actions']))
check('expiry and full revocation remain separate',not B['access-expired']['actions'] and not B['access-revoked']['actions'])
check('export denial returns to same auditor view',B['access-export-denied']['actions'][0][2]=='access-audit-read')
check('export revocation does not offer retry or download',B['access-export-revoked']['actions']==[['Вернуться в журнал','Return to log','access-audit-read']])
check('sample download confined to ready example',len([d for d in D if d.get('sampleDownload')])==1 and B['access-export-ready']['sampleDownload'])
check('export preparation and error both represented',all(k in B for k in ['access-export-preparing','access-export-error']))
check('critical denial does not prompt owner login',B['access-critical-denied']['actions'][0][2]=='access-operations-home')
check('no unlabelled paid alpha fee',all('комиссия Shadow 0%' in d['body'][0] or '1%' not in d['body'][0] for d in D))
check('limited client has no numeric balances',not any('$' in ''.join(r) for r in B['access-user-limited']['rows']))
check('limited session has no numeric positions or profit',not any('$' in ''.join(r) for r in B['access-session-limited']['rows']))
check('critical rules retain delayed recipient and independent owners','24 часа' in B['access-critical-rules']['rows'][2][2] and 'Два разных владельца' in B['access-critical-rules']['rows'][3][2])
check('marketing publication needs permission, not owner approval','нового согласования владельцем нет' in B['access-marketing']['body'][0])
result={'pass':True,'scope':'Static synthetic design contract only, not server authorization','checks':checks,'count':len(checks)}
(P/'contract-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
