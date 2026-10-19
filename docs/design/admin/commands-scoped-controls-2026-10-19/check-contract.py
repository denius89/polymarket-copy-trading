"""Static design assertions and expected-case traceability; no runtime policy engine."""
from pathlib import Path
import json,re
P=Path(__file__).parent
read=lambda n:json.loads((P/n).read_text())
N=read('screen-content.json');U=read('updated-screen-content.json');D=N+U
by={d['key']:d for d in D};cmd=read('command-matrix.json');sc=read('scope-matrix.json');ext=read('external-links.json')
checks=[]
def check(name,condition):
    checks.append({'name':name,'pass':bool(condition)});assert condition,name
check('87 new and eight updated unique bilingual states',len(N)==87 and len(U)==8 and len(by)==95 and all(len(d['title'])==len(d['body'])==2 and all(d['title']) and all(d['body']) for d in D))
check('all rows have three bilingual semantic columns',all(len(d['headers'])==3 and all(len(r)==6 and all(r) for r in d['rows']) for d in D))
targets=set(by)|set(ext)|{'login','profile'}
check('all action and scenario destinations resolve',all(a[2] in targets for d in D for a in d['actions']+d.get('scenarios',[])))
check('all row destinations resolve',all(t in targets for d in D for t in list(d.get('rowLinks',{}).values())+d.get('rowTargets',[])))
check('nine distinct commands and intents',len(cmd)==9 and len({c['key'] for c in cmd})==9 and len({c['id'] for c in cmd})==9)
for c in cmd:
    check(c['key']+' preserves exact command in result and unknown state',all(c['id'] in json.dumps(by[k],ensure_ascii=False) for k in [c['review'],c['result'],c['unknown']]))
    check(c['key']+' unknown offers only status read and list',by[c['unknown']]['actions'][0][2]==c['result'] and not any(a[2]==c['review'] for a in by[c['unknown']]['actions']))
check('calculation acceptance is distinct from completion',by['command-rating-calculate']['actions'][0][2]=='command-pending' and by['command-pending']['actions'][0][2]=='command-rating-calculate-result')
check('publishing rules does not switch catalog', 'каталог ещё не переключён' in by['command-rating-publish-result']['body'][0])
check('full calculation switches catalog atomically','каталог переключён целиком' in by['command-rating-calculate-result']['body'][0])
check('rollback creates R3 without rewriting trades',all(x in json.dumps(by['command-rating-restore-result'],ensure_ascii=False) for x in ['R-3','Сделки и прежние решения не переписываются']))
check('eligible old snapshot only; no score on stale data', 'только пока пригоден' in json.dumps(by['command-pending'],ensure_ascii=False) and 'скрывает число' in by['command-stale']['body'][0] and 'не показывает ноль' in by['command-stale']['body'][0])
check('resume does not bypass emergency block','аварийной блокировки' in json.dumps(by['command-collector-resume'],ensure_ascii=False))
check('diagnostics does not edit events or publish rating','Не исправляет исходные события' in json.dumps(by['command-validator-run-result'],ensure_ascii=False))
check('simulation leaves publication unchanged','Пользовательский каталог и действующая методика не меняются' in json.dumps(by['command-rating-simulate-result'],ensure_ascii=False))
check('Limitless remains unverified and separate','не наследует профиль Polymarket' in by['command-limitless']['body'][0])
check('eight scope families, two distinct source types',len(sc)==8 and {s['key'] for s in sc}=={'staff','user','data-source','treasury-source','signer','network','asset','route'})
for s in sc:
    b='scope-'+s['key'];review=s.get('old',b+'-review')
    check(s['key']+' application and independent recovery chain',by[review]['actions'][0][2]==b+'-active' and by[b+'-active']['actions'][0][2]==b+'-recover' and by[b+'-recover']['actions'][0][2]==b+'-waiting' and by[b+'-waiting']['scenarios'][0][2]==b+'-second' and by[b+'-second']['actions'][0][2]==b+'-restored')
    check(s['key']+' pins object in every critical phase',all(s['object'] in json.dumps(by[k],ensure_ascii=False) for k in [review,b+'-active',b+'-recover',b+'-second',b+'-restored']))
    check(s['key']+' recovery approval has distinct identity',by[b+'-second']['hideAccount'] and 'владельца B' in by[b+'-second']['body'][0] and 'RST-'+s['key'].upper()+'-1' in json.dumps(by[b+'-second'],ensure_ascii=False))
check('first actor has no product action to second actor',all(not any(a[2]=='scope-'+s['key']+'-second' for a in by['scope-'+s['key']+'-waiting']['actions']) for s in sc))
check('treasury activation requires two owners',any('Два разных действующих владельца' in r[2] for r in by['scope-treasury-source-recover']['rows']))
check('other recoveries allow independent authorized staff',all(any('Владелец + независимый уполномоченный сотрудник' in r[2] for r in by['scope-'+s['key']+'-recover']['rows']) for s in sc if not s.get('treasury')))
check('preparation does not create approval',all('Подготовка ещё не создаёт согласие' in by['scope-'+s['key']+'-recover']['body'][0] for s in sc))
check('staff recovery does not restore sessions or approvals','Старые сеансы и подтверждения не восстанавливаются' in json.dumps(by['scope-staff-restored'],ensure_ascii=False))
check('staff stop records revocation and owner alerts','уведомления обоим владельцам отправлены' in json.dumps(by['scope-staff-active'],ensure_ascii=False))
check('signer isolation is not provider key revocation','не отзыв ключа у площадки' in json.dumps(by['scope-signer-active'],ensure_ascii=False))
check('unknown recovery retains denial and blocks duplicates','Локальный запрет новых отправок сохраняется' in by['scope-recovery-unknown']['body'][0] and 'Повтор восстановления' in by['scope-recovery-unknown']['body'][0])
check('partial application cannot claim full stop','Не показывать «полностью применено»' in by['scope-apply-partial']['body'][0])
check('route recovery does not authorize transfer','не подтверждает перевод' in json.dumps(by['scope-route-restored'],ensure_ascii=False))
check('two approvals do not bypass global blocks','Обычное восстановление не выполняется' in by['scope-recovery-blocked']['body'][0])
check('same identity cannot confirm twice','Одна и та же личность' in by['scope-approval-denied']['body'][0])
check('denied role has no route to owner data',all(d['denied'] and len(d['actions'])==1 and d['actions'][0][2]=='login' for d in [by['command-denied'],by['scope-denied']]))
addresses=[x for d in D for r in d['rows'] for x in r if x.startswith('0x')]
check('all shown hex addresses are full synthetic addresses',addresses and all(re.fullmatch(r'0x[0-9a-f]{40}',x) for x in addresses))
cases=read('acceptance-cases.json')
check('186 expected conditions have design witnesses',len(cases['cases'])==186 and all(c['evidenceKey'] in by for c in cases['cases']))
check('expected matrix is not labeled runtime tests','not executed runtime' in cases['scope'])
(P/'contract-checks.json').write_text(json.dumps({'scope':'Static design contract; expected-case coverage is not runtime authorization or safety acceptance','checks':checks,'passed':len(checks),'expectedCases':186},ensure_ascii=False,indent=2)+'\n')
print(f'{len(checks)} static design checks passed; 186 expected conditions traced, not executed runtime tests')
