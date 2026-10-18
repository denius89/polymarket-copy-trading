"""Static design checks, not authorization/API/runtime tests."""
from pathlib import Path
import json
P=Path(__file__).parent
D=json.loads((P/'screen-content.json').read_text())
E=json.loads((P/'external-links.json').read_text())
by={d['key']:d for d in D}
checks=[]
def check(name, ok):
    checks.append({'name':name,'pass':bool(ok)})
    assert ok,name
check('42 unique bilingual state records',len(D)==42 and len(by)==42 and all(len(d['title'])==2 and all(d['title']) and len(d['body'])==2 and all(d['body']) for d in D))
targets=set(by)|set(E)|{'profile','login'}
for d in D:
    for action in d['actions']+d.get('scenarios',[]): assert action[2] in targets,(d['key'],action)
    for target in list(d.get('rowLinks',{}).values())+d.get('rowTargets',[]): assert target in targets,(d['key'],target)
check('all designed transition targets resolve',True)
check('three semantic column headers and bilingual cells',all(len(d['headers'])==3 and all(len(r)==6 and all(r) for r in d['rows']) for d in D))
check('delayed filtered record returns to same saved view',by['market-stale']['actions'][0][2]=='market-filtered' and by['market-filtered']['rowLinks']['PM-MKT-DEMO-02']=='market-stale')
check('exact search opens exact market',by['market-search']['query']=='PM-MKT-DEMO-01' and by['market-search']['rowLinks']['PM-MKT-DEMO-01']=='market-detail')
check('market state is separate from freshness', 'прошлое наблюдение' in by['market-stale']['body'][0] and 'текущее не подтверждено' in by['market-stale']['body'][0])
check('Limitless profile remains unverified', 'не подключён' in by['market-limitless']['body'][0] and 'не подтверждены' in by['market-limitless']['body'][0])
check('missing price is unavailable rather than zero',any('Нет подтверждённого снимка' in r[2] and 'ноль' in r[4] for r in by['market-detail']['rows']))
check('loading empty error and denied remain separate',all(by[k].get('empty') for k in ['market-loading','market-empty','market-error','market-denied']))
check('data sources distinct from treasury', 'Денежные источники' in by['source-catalog']['body'][0])
check('gap has typed source interval and incident',all(t in json.dumps(by['source-gap'],ensure_ascii=False) for t in ['SRC-PM-HIST','11:52–11:57','INC-DATA-DEMO-01']))
check('restored response does not close history gap', 'не доказывает' in by['source-quality']['body'][0] and 'ещё не подтверждено' in json.dumps(by['source-gap'],ensure_ascii=False))
check('collector outcome unknown uses existing reconciliation state',any(a[2]=='data-collector-unknown' for a in by['source-settings']['scenarios']))
check('collector conflict requires new review', 'заново проверьте' in by['source-settings-conflict']['body'][0])
check('confirmed failure is not unknown', 'неизвестный исход' in by['source-settings-failed']['body'][0])
check('incomplete locale blocks enabling', 'блокируют включение' in by['locale-incomplete']['body'][0] and not any(a[2]=='locale-enabled' for a in by['locale-incomplete']['actions']))
check('future language example does not change RU EN launch', 'Не расширяет согласованный запуск RU/EN' in by['locale-ready']['body'][0])
check('publish permission does not force owner approval',any('Владелец не нужен' in r[4] for r in by['locale-ready']['rows']))
check('locale disable keeps preferences and versions', 'сохранённое предпочтение' in by['locale-disable-review']['body'][0] and 'прежние версии не удаляются' in by['locale-disable-review']['body'][0])
check('fallback disabling is blocked',by['locale-fallback-blocked']['rows'][0][2]=='Публикация запрещена')
check('seven typed scope targets exist',len(by['restriction-type-options']['rows'])==7 and len(set(by['restriction-type-options']['rowTargets']))==7)
check('asset requires network and exact contract',any('точный контракт' in r[2] for r in by['restriction-asset']['rows']))
check('route requires all linked identities',any('Источник + подписант + сеть + актив + получатель' in r[2] for r in by['restriction-route']['rows']))
check('incompatible venues do not create restriction','Ограничение не создано' in by['restriction-invalid']['body'][0])
check('scope does not bypass global restrictions','сохраняют приоритет' in by['restriction-preview']['body'][0])
check('denied examples lead only to staff sign-in',all([a[2] for a in by[k]['actions']]==['login'] for k in ['market-denied','source-settings-denied']))
check('new states have no arbitrary external endpoint inputs',not any('http' in str(d.get('query','')) for d in D))
(P/'contract-checks.json').write_text(json.dumps({'scope':'Static design contract only','checks':checks,'passed':len(checks)},ensure_ascii=False,indent=2)+'\n')
print(f'{len(checks)} static contract checks passed')
