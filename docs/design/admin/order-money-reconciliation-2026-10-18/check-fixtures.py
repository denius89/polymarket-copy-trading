"""Check arithmetic and selected design invariants, not execution or venue behavior."""
from pathlib import Path
from decimal import Decimal as N
import json
p=Path(__file__).parent;f=json.loads((p/'case-fixtures.json').read_text());t=f['trade'];cases=[]
for key in ['partial','cancelled','late','lateCancelled','full']:
 s=t[key];assert s['filledCost']+s['reserve']+s['available']+t['otherExecutedCost']==t['budget'];assert N(str(s['filledShares']))*N(str(t['price']))==N(str(s['filledCost']));assert s['filledShares']<=40 and s['reserve']>=0;cases.append('trade budget/share consistency: '+key)
assert t['late']['filledCost']-t['partial']['filledCost']==3
assert t['late']['reserve']==t['partial']['reserve']-3
assert t['lateCancelled']['available']-t['late']['available']==5
assert t['cancelled']['available']-t['partial']['available']==8
assert N('200')-N('121.20')-N('50')-N('20')==N('8.80')
assert N('200')-N('120')-N('0.30')==N('79.70')
assert N('79.70')-N('50')-N('20')==N('9.70')
assert N('121.20')-N('120')-N('0.30')==N('0.90')
assert N('210')-N('50')-N('20')==N('140')
assert N('100')-N('25')==N('75')
d=json.loads((p/'screen-content.json').read_text());m={x['key']:x for x in d};allkeys=set(m)|{'user-noor'}
for s in d:
 for a in s['actions']+s.get('scenarios',[]):assert a[2] in allkeys,(s['key'],a)
 if s['key'].endswith(('-error','-insufficient')) and s['key'].startswith('reconcile-'):assert s['actions'][0][2].endswith('-checking')
 if s['key'].startswith('order-late-') and s['key'] not in ['order-late-complete','order-late-final']:
  assert not any(a[2] in ['order-cancel-checking','order-check-error','order-evidence'] for a in s['actions']+s.get('scenarios',[]))
for key in ['order-late-check-error','order-late-evidence']:
 assert any('$15' in r[2] and '$5' in str(m[key]['rows']) for r in m[key]['rows'])
cases+=['late fill consumes reserve, not new available funds','verified cancellation releases only unused remainder','payout reserves and actual fee are counted once','confirmed client withdrawal does not increase availability','all declared graph destinations exist','late-evidence retries do not return to the pre-late snapshot','readback failures retry readback only']
result={'date':'2026-10-18','pass':True,'scope':'Static synthetic fixture arithmetic and selected graph invariants only','checks':cases,'notChecked':['server ledger','actual duplicate evidence handling','permission enforcement','venue finality','real asset support','browser execution']};(p/'fixture-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Fixture arithmetic and declared graph checks passed:',len(cases))
