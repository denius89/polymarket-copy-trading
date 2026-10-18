"""Scoped handoff update; unrelated local research and frozen packages stay intact."""
from pathlib import Path
import json, csv, collections
P = Path(__file__).parent
R = P.resolve().parents[3]
A = R/'docs/design/admin'
Q = A/'requirements-coverage-2026-10-16'
read = lambda p: json.loads(p.read_text())
def save(p, value): p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
D = read(P/'screen-content.json')
pairs = read(P/'screen-pairs.json')
ids = {p['key']:p for p in pairs}
url = lambda i: 'https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id='+i.replace(':','-')
proto = lambda i: 'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+i.replace(':','-')+'&starting-point-node-id='+i.replace(':','-')+'&scaling=scale-down'
s = read(A/'sitemap.json')
sections = {x['id']:x for x in s['sections']}
for d in D:
    p = ids[d['key']]
    item = {'id':p['ru'],'key':d['key'],'title':d['title'][0],'url':url(p['ru']), 'english':{'id':p['en'],'title':'EN · '+d['key']+' · '+d['title'][1],'url':url(p['en'])}}
    old = next((x for x in sections[d['section']]['screens'] if x['key']==d['key']), None)
    if old: old.update(item)
    else: sections[d['section']]['screens'].append(item)
sections['ADM-06']['description'] = 'Каталог рынков и источников, поиск, сохранённая выборка, актуальность, задержки, пропуски и история качества; состояние рынка отдельно от подключения.'
sections['ADM-16']['description'] = 'Тексты, версии и переводы; готовность, включение и отключение языка, резервный язык и конфликт. RU/EN — фактический стартовый набор.'
s.update(revision='0.23', updatedAt='2026-10-18', counts={'ru':689,'en':689})
save(A/'sitemap.json',s)
summary = '**689 RU +689 EN корневых макетов**, из них 684 основных состояния и 5 служебных оболочек на язык. Карта 0.23, набор компонентов 0.4.21 (28 наборов /168 вариантов).'
lines = ['# Живая карта админки','','Текущий срез 18.10.2026: '+summary,'','Полный индекс из [sitemap.json](sitemap.json). Статус — покрытие дизайном, не реализация или полная приёмка.','','[Последние изменения](market-source-settings-2026-10-18/README.md)','']
for sec in s['sections']:
    lines += ['## '+sec['id']+' · '+sec['title'],'',sec.get('status','На вычитке')+'. '+sec['description'],'',f"Состояний: {len(sec['screens'])}.",'','| Состояние | RU | EN |','| --- | --- | --- |']
    lines += ['| '+x['title'].replace('|',' / ')+' | [Макет]('+url(x['id'])+') | [Макет]('+url(x['english']['id'])+') |' for x in sec['screens']]
    lines.append('')
(A/'sitemap.md').write_text('\n'.join(lines)+'\n')
p = A/'README.md'
parts = p.read_text().split('\n\n',2)
parts[1] = 'Текущий срез 18.10.2026: '+summary+' [Каталог и настройки](market-source-settings-2026-10-18/README.md) · [Полная карта](sitemap.md). Ниже — исторический журнал.'
p.write_text('\n\n'.join(parts))
q = read(Q/'requirements.json')
closed = ['D02','D03','L03']
keysets = {'D02':[d for d in D if d['section']=='ADM-06'], 'D03':[d for d in D if d['key'] in ['source-detail','source-quality','source-gap','source-incident']], 'L03':[d for d in D if d['section']=='ADM-16'], 'T05':[d for d in D if d['section']=='ADM-07'], 'E04':[d for d in D if d['section']=='ADM-17']}
gaps = {
 'D02':'Покрыты каталог рынков и источников, точный поиск и подготовленная выборка, карточки, свежесть/задержки/пропуски, пустой ответ, ошибка и запрет. Только дизайн и вымышленные записи; произвольные фильтры, runtime и реальные поля API не проверены.',
 'D03':'История качества связана с источником, рынком, затронутой функцией, интервалом и инцидентом. Возврат ответа не закрывает пропуск автоматически. Реальные потоки и восстановление истории не проверялись.',
 'L03':'Готовность, обязательные тексты и проверка носителем; включение/отключение, резервный язык и конфликт покрыты макетами. BN — только будущий учебный кандидат; старт остаётся RU/EN. Реальная публикация не выполнялась.',
 'T05':'Добавлены отдельные поля сборщика, владелец/отказ, проверка версии, конфликт, подтверждённый отказ и связь с неизвестным исходом. Полная матрица всех команд валидатора/рейтинга, конкурентность и серверная проверка остаются на вычитке.',
 'E04':'Добавлены выбор семи типов, точные учебные объекты и связи, запрет несовместимых площадок, конфликт и проверка последствий. Полный проход применения и восстановления каждого типа по всем ограничениям ещё открыт; новые полномочия не утверждены.'}
for x in q:
    if x['id'] not in keysets: continue
    rows = keysets[x['id']]
    x.update(gap=gaps[x['id']], keys=[d['section']+'/'+d['key'] for d in rows])
    if x['id'] in closed: x.update(status='готово',priority='—')
    x['evidence'] = [{'key':d['key'],'section':d['section'],'ru':ids[d['key']]['ru'],'en':ids[d['key']]['en'],'urlRU':url(ids[d['key']]['ru']),'urlEN':url(ids[d['key']]['en'])} for d in rows]
save(Q/'requirements.json',q)
counts = dict(collections.Counter(x['status'] for x in q))
assert counts == {'готово':91,'частично':13,'отложено':6}, counts
with (Q/'requirements.csv').open('w',newline='') as f:
    w = csv.DictWriter(f,fieldnames=['id','area','requirement','status','gap','priority','source'],extrasaction='ignore',quoting=csv.QUOTE_ALL)
    w.writeheader();w.writerows(q)
old = read(Q/'current-status.json')
if old.get('rootsPerLocale') != 689:
    save(Q/'current-status.json',{'date':'2026-10-18','scope':'Catalog, data quality and language design coverage; not runtime or complete acceptance','counts':counts,'rootsPerLocale':689,'mainStatesPerLocale':684,'manualPresent':False,'manualPresentScope':'Selected catalog/settings routes only; full X01/X04 remains open','baseCommit':'1c85185b2c1059cb5b7cc8638146f9e76e1638e1','package':'../market-source-settings-2026-10-18/README.md','latestPackage':'../market-source-settings-2026-10-18/README.md','closed':list(dict.fromkeys(old['closed']+closed)),'closedThisPackage':closed,'improvedNotClosed':['T05','E04'],'previousSnapshot':{'counts':old['counts'],'rootsPerLocale':647,'mainStatesPerLocale':642,'package':old['latestPackage']}})
p = Q/'matrix.md'; lines = p.read_text().splitlines()
lines[2] = 'Срез 18.10.2026 после [каталога и настроек](../market-source-settings-2026-10-18/README.md): **91 покрыто, 13 частично, 0 отсутствует, 6 отложено**. Покрытие дизайном, не полная приёмка.'
for x in q:
    if x['id'] not in keysets: continue
    links = '; '.join('['+e['key']+' RU]('+e['urlRU']+') · [EN]('+e['urlEN']+')' for e in x['evidence'])
    lines = [('| '+x['id']+' | '+x['requirement']+' | '+x['status']+' | '+x['gap']+' | '+links+' |') if l.startswith('| '+x['id']+' |') else l for l in lines]
p.write_text('\n'.join(lines)+'\n')
p = Q/'README.md'; marker = '# Текущий срез · каталог и настройки · 18.10.2026'
if not p.read_text().startswith(marker): p.write_text(marker+'\n\n**91 покрыто, 13 частично, 0 отсутствует, 6 отложено.** [Пакет](../market-source-settings-2026-10-18/README.md) закрывает D02/D03/L03 на уровне макетов; T05/E04 дополнены и остаются частичными. X01/X04 и серверная проверка открыты. Ниже — история.\n\n'+p.read_text().replace('# Текущий срез','# Исторический срез'))
append = '\n\n## Уточнение 18.10.2026 · каталог рынков и настройки\n\n[Контракт и границы](design/admin/market-source-settings-2026-10-18/contract.md): рынки и источники рыночных данных отдельно от денежных источников; состояние рынка, подключения, свежесть и полнота независимы. Неизвестная цена не равна нулю; восстановленный ответ не закрывает исторический пропуск. Поиск, сохранённая выборка, карточки и качество связаны.\n\nСборщик: отдельные поля, права, проверка и конфликт версии, подтверждённый отказ; неизвестный исход читается по той же команде. Числа P-1/P-2 учебные, API-возможности не утверждаются. Языки: обязательные тексты и проверка носителем, включение/отключение новой версией по праву публикации без дублирующего владельца, защита английского резервного языка. BN — учебный будущий кандидат, не расширение запуска RU/EN.\n\nОбласть ограничения: семь типов и точные объекты, совместимость площадки/среды/связей, последствия, конфликт и запрет. Это не универсальный обход полного отключения и не новые права; E04 и T05 остаются частичными до полного прохода.\n\n42 новых состояния на язык, карта 0.23 — 689 корней /684 основных состояния; UI kit 0.4.21 без расширения. D02/D03/L03 покрыты дизайном. Paper Alpha — комиссия Shadow 0%, реальные действия выключены; полные X01/X04 открыты.\n'
for name in ['115_admin_console_technical_specification_2026-10-09.md','118_admin_console_figma_design_brief_2026-10-09.md']:
    p = R/'docs'/name
    if '## Уточнение 18.10.2026 · каталог рынков и настройки' not in p.read_text(): p.write_text(p.read_text()+append)
for p, text in [(A/'ui-kit/README.md','18.10.2026: [каталог и настройки](../market-source-settings-2026-10-18/README.md) используют текущие связанные поля поиска/выбора/ввода, таблицы, панели, кнопки и навигацию. Набор 0.4.21 не расширялся.\n\n'),(A/'STYLE_GUIDE.md','18.10.2026: [рынки и источники](market-source-settings-2026-10-18/contract.md): состояние рынка, качество данных и подключение разделены. Точные ID, семантические заголовки, прошлый снимок с временем; запрет не подменяет данные нулём.\n\n')]:
    if text not in p.read_text(): p.write_text(text+p.read_text())
p = A/'review-new-skills-2026-10-18/REPORT.md'
text = '\n\n## Последующая правка · 18.10.2026 · каталог и настройки\n\n[Пакет](../market-source-settings-2026-10-18/README.md): 42 состояния на язык. D02/D03/L03 покрыты макетами, T05/E04 дополнены и остаются частичными: 91 покрыто, 13 частично, 0 отсутствует, 6 отложено. Исходный аудит выше исторический; полные X01/X04, приглашение B04 и реализация открыты.\n'
if '## Последующая правка · 18.10.2026 · каталог и настройки' not in p.read_text(): p.write_text(p.read_text()+text)
gpath = A/'review-guide-2026-10-13/guide-source.json'
g = read(gpath); groups = []
for secid in sorted({d['section'] for d in D}):
    extra = [d for d in D if d['section']==secid]
    first = len(sections[secid]['screens'])-len(extra)+1
    paras = []
    for n,d in enumerate(extra,first):
        heading = secid[-2:]+'.'+f'{n:02d}'+' — '+d['title'][0]
        items = [('HEADING_2',heading,[]),('NORMAL_TEXT','Назначение: '+d['title'][0].lower()+'.',[]),('NORMAL_TEXT','На экране: '+d['body'][0],[]),('NORMAL_TEXT','Что проверить: точные объект, площадка, среда и версия; неизвестное не равно нулю; запрет не обходится; возврат сохраняет контекст. Учебные примеры не меняют фактические настройки.',[]),('NORMAL_TEXT','Прототип RU',[{'label':'Прототип RU','url':proto(ids[d['key']]['ru'])}]),('NORMAL_TEXT','Prototype EN',[{'label':'Prototype EN','url':proto(ids[d['key']]['en'])}])]
        paras.extend({'style':st,'text':tx+'\n','links':ls} for st,tx,ls in items)
    if not any(x['text']==paras[0]['text'] for x in g['paras']):
        start = next(i for i,x in enumerate(g['paras']) if x['style']=='HEADING_1' and x['text'].startswith(secid))
        end = next((i for i in range(start+1,len(g['paras'])) if g['paras'][i]['style']=='HEADING_1'),len(g['paras']))
        g['paras'][end:end] = paras
    groups.append({'section':secid,'paras':paras})
for x in g['paras']:
    if x['style']!='HEADING_2': x['text'] = x['text'].replace('642 основных экранов','684 основных экранов').replace('647 RU +647 EN','689 RU +689 EN').replace('карта 0.22','карта 0.23').replace('карты 0.22','карты 0.23').replace('642 карточек','684 карточек').replace('647 корневых макетов','689 корневых макетов')
g.update(screenCount=684,updatedAt='2026-10-18')
index = 1
for x in g['paras']: x['startIndex']=index;index+=len(x['text'].encode('utf-16-le'))//2
save(gpath,g);save(P/'guide-new-cards.json',groups)
print(json.dumps({'revision':'0.23','roots':689,'main':684,'coverage':counts,'sectionCounts':{k:len(v['screens']) for k,v in sections.items()}},ensure_ascii=False))
