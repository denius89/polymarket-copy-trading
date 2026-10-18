"""Static synthetic invariants and cross-package reconciliation, not runtime tests."""
from pathlib import Path
from decimal import Decimal as N
import json
P=Path(__file__).parent;load=lambda p:json.loads(p.read_text())
f=load(P/'case-fixtures.json');data=load(P/'screen-content.json');m={d['key']:d for d in data};pairs=load(P/'screen-pairs.json')
checks=[]
assert f['budget']==f['available']+f['spent']+f['reserved']==200
assert sum(x['cost'] for x in f['lots'])==f['spent']==35
assert all(not x['tracked'] for x in f['lots'])
checks+=['budget allocation equals 200 without treating cost as market value','both retained lots are no longer tracking trader exits']
new=f['lots'][1];assert sum(x['quantity'] for x in f['fills'])==new['quantity']==30
assert sum(x['cost'] for x in f['fills'])==new['cost']==15
assert len({x['id'] for x in f['fills']})==2
old=load(P.parent/'order-money-reconciliation-2026-10-18/case-fixtures.json')['trade'];assert old['lateCancelled']['filledShares']==30 and old['lateCancelled']['filledCost']==15 and old['lateCancelled']['reserve']==f['reserved'] and old['lateCancelled']['available']==f['available']
checks+=['lot30 equals the 24+6 unique confirmed fills','session projection agrees with prior late-cancelled terminal snapshot']
decisions=f['decisions'];assert len(decisions)==4 and sum(x['state']=='skipped' for x in decisions)==3
assert all(x['order'] is None for x in decisions if x['state']=='skipped')
budget=next(x for x in decisions if x['id']=='SIG-DEMO-029');admitted=next(x for x in decisions if x['state']=='admitted')
assert budget['desired']==200 and budget['availableAtDecision']==180 and budget['version']==11
assert admitted['desired']==20 and admitted['availableAtDecision']==180 and admitted['version']==12
checks+=['three skips have no order IDs','historical budget skip is not recomputed using later settings12']
assert len(data)==len(pairs)==17 and len({x['ru'] for x in pairs})==len({x['en'] for x in pairs})==17
allowed=set(m)|{'sessions','user-noor','order-history'}
for d in data:
 for a in d['actions']+d.get('scenarios',[])+d.get('filters',[]):assert a[2] in allowed,(d['key'],a)
 for target in d.get('rowLinks',{}).values():assert target in m
assert m['session-decisions-empty']['rows']==[] and m['session-data-loading']['rows']==[]
assert len(m['session-data-error']['rows'])==2
assert all('session-decisions-skipped' in str(m[key]['actions']) for key in ['session-decision-paused','session-decision-budget','session-decision-unowned'])
checks+=['all declared local and historical destinations exist','empty filtered and loading states do not invent rows','read error retains the two known lots','skip detail returns to the skipped selection']
out={'date':'2026-10-18','pass':True,'checks':checks,'scope':'Static fixture consistency and declared graph only','notChecked':['actual event duplication handling','server or venue ledger','permissions','API support or freshness','browser behavior']}
(P/'fixture-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('Passed static fixture checks:',len(checks))
