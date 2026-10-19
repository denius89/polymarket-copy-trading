"""Update only the requested design handoff; preserve research and frozen packages."""
from pathlib import Path
import json,csv,collections
P=Path(__file__).parent; R=P.resolve().parents[3]; A=R/'docs/design/admin'; Q=A/'requirements-coverage-2026-10-16'
read=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
N=read(P/'screen-content.json'); U=read(P/'updated-screen-content.json'); D=N+U
newpairs=read(P/'screen-pairs.json'); ext=read(P/'external-links.json')
ids={p['key']:p for p in newpairs}
for d in U:ids[d['key']]={'key':d['key'],'section':d['section'],**ext[d['key']]}
url=lambda i:'https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id='+i.replace(':','-')
proto=lambda i:'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+i.replace(':','-')+'&starting-point-node-id='+i.replace(':','-')+'&scaling=scale-down'
s=read(A/'sitemap.json'); sections={x['id']:x for x in s['sections']}
for d in D:
    p=ids[d['key']]; sec=sections[d['section']]
    item={'id':p['ru'],'key':d['key'],'title':d['title'][0],'url':url(p['ru']),'english':{'id':p['en'],'title':'EN · '+d['key']+' · '+d['title'][1],'url':url(p['en'])}}
    old=next((x for x in sec['screens'] if x['key']==d['key']),None)
    if old:old.update(item)
    else:sec['screens'].append(item)
sections['ADM-07']['description']='Девять команд сбора, проверки и рейтинга; раздельные права, принятие/выполнение/результат, отказы, неизвестность и отдельное переключение полного каталога.'
sections['ADM-17']['description']='Точные области, восемь семейств объектов, применение всеми исполнителями, независимое восстановление, неизвестность/неполное применение и приоритет глобальных запретов.'
s.update(revision='0.24',updatedAt='2026-10-19',counts={'ru':776,'en':776});save(A/'sitemap.json',s)
summary='**776 RU +776 EN корневых макетов**, из них 771 основное состояние и 5 служебных оболочек на язык. Карта 0.24, набор компонентов 0.4.21 (28 наборов /168 вариантов).'
lines=['# Живая карта админки','','Текущий срез 19.10.2026: '+summary,'','Покрытие дизайном, не реализация или полная приёмка. [Машиночитаемая карта](sitemap.json).','','[Последние изменения](commands-scoped-controls-2026-10-19/README.md)','']
for sec in s['sections']:
    lines+=['## '+sec['id']+' · '+sec['title'],'',sec.get('status','На вычитке')+'. '+sec['description'],'',f"Состояний: {len(sec['screens'])}.",'','| Состояние | RU | EN |','| --- | --- | --- |']
    lines+=['| '+x['title'].replace('|',' / ')+' | [Макет]('+url(x['id'])+') | [Макет]('+url(x['english']['id'])+') |' for x in sec['screens']];lines.append('')
(A/'sitemap.md').write_text('\n'.join(lines)+'\n')
p=A/'README.md'; parts=p.read_text().split('\n\n',2)
parts[1]='Текущий срез 19.10.2026: '+summary+' [Команды и ограничения](commands-scoped-controls-2026-10-19/README.md) · [Полная карта](sitemap.md). Ниже — история.'
p.write_text('\n\n'.join(parts))
q=read(Q/'requirements.json'); closed=['T05','E04']
gaps={'T05':'Покрыты матрица девяти команд/полномочий, точные версии и входы, принятие/выполнение/подтверждённый результат, неизвестность, отказ, конфликт, отзыв права и ограничения. Публикация методики отделена от полного расчёта и переключения каталога. Это дизайн и ожидаемые условия; серверная авторизация/конкурентность и полный X01/X04 открыты.',
      'E04':'Покрыты точные типы staff/user/source/signer/network/asset/route: источник данных и собственный денежный источник разделены. Семь существующих подтверждений обновлены; восемь семейств имеют применение и независимое восстановление, полные реквизиты, версии/связи, неполноту/неизвестность и запреты. Полный технический и денежный запреты сохраняют приоритет. Это дизайн, не приёмка реального исполнения.'}
for x in q:
    if x['id'] not in closed:continue
    rows=[d for d in D if d['section']==('ADM-07' if x['id']=='T05' else 'ADM-17')]
    x.update(status='готово',priority='—',gap=gaps[x['id']],keys=[d['section']+'/'+d['key'] for d in rows])
    x['evidence']=[{'key':d['key'],'section':d['section'],'ru':ids[d['key']]['ru'],'en':ids[d['key']]['en'],'urlRU':url(ids[d['key']]['ru']),'urlEN':url(ids[d['key']]['en'])} for d in rows]
save(Q/'requirements.json',q);counts=dict(collections.Counter(x['status'] for x in q));assert counts=={'готово':93,'частично':11,'отложено':6},counts
with (Q/'requirements.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['id','area','requirement','status','gap','priority','source'],extrasaction='ignore',quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(q)
old=read(Q/'current-status.json')
if old.get('rootsPerLocale')!=776:save(Q/'current-status.json',{'date':'2026-10-19','scope':'Command/scoped-control design coverage; not server or full role/client acceptance','counts':counts,'rootsPerLocale':776,'mainStatesPerLocale':771,'manualPresent':False,'manualPresentScope':'Selected command/stop/recovery routes only; full X01/X04 open','baseCommit':'89f7795e5552950afc2d235bf63a91551defc75b','package':'../commands-scoped-controls-2026-10-19/README.md','latestPackage':'../commands-scoped-controls-2026-10-19/README.md','closed':list(dict.fromkeys(old['closed']+closed)),'closedThisPackage':closed,'previousSnapshot':old.get('previousSnapshot') if old.get('latestPackage')=='../commands-scoped-controls-2026-10-19/README.md' else {'counts':old['counts'],'rootsPerLocale':689,'mainStatesPerLocale':684,'package':old['latestPackage']}})
p=Q/'matrix.md';lines=p.read_text().splitlines();lines[2]='Срез 19.10.2026 после [команд и областей](../commands-scoped-controls-2026-10-19/README.md): **93 покрыто, 11 частично, 0 отсутствует, 6 отложено**. Только покрытие дизайном.'
for x in q:
    if x['id'] not in closed:continue
    links='; '.join('['+e['key']+' RU]('+e['urlRU']+') · [EN]('+e['urlEN']+')' for e in x['evidence'])
    lines=[('| '+x['id']+' | '+x['requirement']+' | готово | '+x['gap']+' | '+links+' |') if l.startswith('| '+x['id']+' |') else l for l in lines]
p.write_text('\n'.join(lines)+'\n')
p=Q/'README.md';mark='# Текущий срез · команды и области · 19.10.2026'
if not p.read_text().startswith(mark):p.write_text(mark+'\n\n**93 покрыто, 11 частично, 0 отсутствует, 6 отложено.** [Пакет](../commands-scoped-controls-2026-10-19/README.md) закрывает T05/E04 на уровне дизайна. Реальные права/исполнение и полные X01/X04 остаются открыты. Ниже — история.\n\n'+p.read_text().replace('# Текущий срез','# Исторический срез'))
append='\n\n## Уточнение 19.10.2026 · команды данных и области ограничений\n\n[Контракт](design/admin/commands-scoped-controls-2026-10-19/contract.md): девять команд, раздельные права, версии/снимки, защита от повторного намерения, принятие/выполнение/полный результат, отказ и неизвестность. Настройка методики не переключает каталог до отдельного полного пригодного расчёта; непригодный старый снимок не сохраняет видимый балл. Обычная пауза сборщика не требует ответа внешнего API и не снимает аварийный запрет.\n\nВсе семь типов области с двумя подтипами источника имеют точное подтверждение и восемь семейств применения/независимого восстановления. Остановка собственного денежного источника — один владелец, повторная активация — два разных владельца. Для остальных аварийных восстановлений — владелец и независимый уполномоченный сотрудник; владелец B в примере не делает двух владельцев обязательными всегда. Подготовка не создаёт согласие; REC и RST — разные запросы. При неизвестном эффекте или неполном подтверждении запрет сохраняется; повтор запрещён. Глобальные запреты не обходятся. Восстановление маршрута не разрешает перевод; для восстановительного пополнения действуют отдельные два владельца для маршрута и операции.\n\n87 новых и 8 обновлённых состояний на язык; карта 0.24 — 776 корней /771 основное состояние; UI kit 0.4.21 без новых компонентов. T05/E04 покрыты дизайном, не серверной реализацией или полной приёмкой. Полные X01/X04 открыты; Paper Alpha — комиссия Shadow 0%, реальные действия выключены.\n'
for n in ['115_admin_console_technical_specification_2026-10-09.md','118_admin_console_figma_design_brief_2026-10-09.md']:
    p=R/'docs'/n
    if '## Уточнение 19.10.2026 · команды данных и области ограничений' not in p.read_text():p.write_text(p.read_text()+append)
for p,text in [(A/'ui-kit/README.md','19.10.2026: [команды и области](../commands-scoped-controls-2026-10-19/README.md) используют существующие таблицы, панели, кнопки, навигацию и токены. Набор 0.4.21 не расширялся. Разделены владелец A, независимый участник и подтверждённый эффект.\n\n'),(A/'STYLE_GUIDE.md','19.10.2026: [критические команды](commands-scoped-controls-2026-10-19/contract.md) различают принятие, выполнение, полный результат, отказ и неизвестность; согласие не равно эффекту. Все реквизиты полные; рабочие действия отделены от учебных сценариев.\n\n')]:
    if text not in p.read_text():p.write_text(text+p.read_text())
p=A/'review-new-skills-2026-10-18/REPORT.md';text='\n\n## Последующая правка · 19.10.2026 · команды и области\n\n[Пакет](../commands-scoped-controls-2026-10-19/README.md): 87 новых и 8 обновлённых состояний на язык; T05/E04 покрыты дизайном. Матрица: 93 покрыто, 11 частично, 0 отсутствует, 6 отложено. Матрицы ожидаемых условий не являются исполненными проверками реальных прав; полные X01/X04 и реализация открыты.\n'
if '## Последующая правка · 19.10.2026 · команды и области' not in p.read_text():p.write_text(p.read_text()+text)
gp=A/'review-guide-2026-10-13/guide-source.json';g=read(gp);patches=read(P/'guide-updated-paragraphs.json') if (P/'guide-updated-paragraphs.json').exists() else []
for d in U:
    link=proto(ids[d['key']]['ru'])
    at=next(i for i,x in enumerate(g['paras']) if any(z['url']==link for z in x.get('links',[])))
    start=next(i for i in range(at,-1,-1) if g['paras'][i]['style']=='HEADING_2')
    changes={start:g['paras'][start]['text'].split(' — ')[0]+' — '+d['title'][0]+'\n',start+1:'Назначение: '+d['title'][0].lower()+'.\n',start+2:'На экране: '+d['body'][0]+'\n'}
    for i,new in changes.items():
        oldtext=g['paras'][i]['text']
        if oldtext!=new:patches.append({'old':oldtext,'new':new});g['paras'][i]['text']=new
groups=[];additional=[]
known_guide_urls={z['url'] for p in g['paras'] for z in p.get('links',[])}
for secid in sorted({d['section'] for d in N}):
    extra=[d for d in N if d['section']==secid];first=len(sections[secid]['screens'])-len(extra)+1;paras=[];missing=[]
    for n,d in enumerate(extra,first):
        title=secid[-2:]+'.'+f'{n:02d}'+' — '+d['title'][0]
        items=[('HEADING_2',title,[]),('NORMAL_TEXT','Назначение: '+d['title'][0].lower()+'.',[]),('NORMAL_TEXT','На экране: '+d['body'][0],[]),('NORMAL_TEXT','Что проверить: точные объект, область, версия и намерение; полномочия и независимость личности; согласие отдельно от подтверждённого эффекта; неизвестность не разрешает повтор. Все результаты учебные.',[]),('NORMAL_TEXT','Прототип RU',[{'label':'Прототип RU','url':proto(ids[d['key']]['ru'])}]),('NORMAL_TEXT','Prototype EN',[{'label':'Prototype EN','url':proto(ids[d['key']]['en'])}])]
        block=[{'style':st,'text':tx+'\n','links':links} for st,tx,links in items]
        paras.extend(block)
        if proto(ids[d['key']]['ru']) not in known_guide_urls:missing.extend(block)
    if missing:
        start=next(i for i,x in enumerate(g['paras']) if x['style']=='HEADING_1' and x['text'].startswith(secid))
        end=next((i for i in range(start+1,len(g['paras'])) if g['paras'][i]['style']=='HEADING_1'),len(g['paras']));g['paras'][end:end]=missing
        additional.append({'section':secid,'paras':missing})
    groups.append({'section':secid,'paras':paras})
for x in g['paras']:
    if x['style']!='HEADING_2':x['text']=x['text'].replace('684 основных экранов','763 основных экранов').replace('689 RU +689 EN','776 RU +776 EN').replace('карта 0.23','карта 0.24').replace('карты 0.23','карты 0.24').replace('684 карточек','771 карточка').replace('689 корневых макетов','776 корневых макетов')
    if 'Срез 18 октября 2026, карта 0.24' in x['text']:x['text']=x['text'].replace('Срез 18 октября 2026','Срез 19 октября 2026')
for p in g['paras']:
    if p['style']!='HEADING_2':p['text']=p['text'].replace('763 основных экранов','771 основных экранов').replace('768 RU +768 EN','776 RU +776 EN')
g.update(screenCount=771,updatedAt='2026-10-19');i=1
for x in g['paras']:x['startIndex']=i;i+=len(x['text'].encode('utf-16-le'))//2
save(gp,g);save(P/'guide-new-cards.json',groups);save(P/'guide-additional-cards.json',additional);save(P/'guide-updated-paragraphs.json',patches)
print(json.dumps({'roots':776,'main':771,'new':87,'updated':8,'coverage':counts,'guidePatches':len(patches),'sections':{k:len(v['screens']) for k,v in sections.items()}},ensure_ascii=False))
