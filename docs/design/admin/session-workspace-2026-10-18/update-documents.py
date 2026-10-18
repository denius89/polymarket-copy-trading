"""Scoped handoff update, idempotent for this package. Does not edit synced sources."""
from pathlib import Path
import json,csv,collections
P=Path(__file__).parent;R=P.resolve().parents[3];A=R/'docs/design/admin'
read=lambda p:json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
D=read(P/'screen-content.json');pairs=read(P/'screen-pairs.json');ids={p['key']:p for p in pairs}
url=lambda id:'https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-')
proto=lambda id:'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-')+'&starting-point-node-id='+id.replace(':','-')+'&scaling=scale-down'
s=read(A/'sitemap.json');sec=next(x for x in s['sections'] if x['id']=='ADM-03')
for d in D:
 p=ids[d['key']];item={'id':p['ru'],'key':d['key'],'title':d['title'][0],'url':url(p['ru']),'english':{'id':p['en'],'title':'EN · '+d['key']+' · '+d['title'][1],'url':url(p['en'])}}
 old=next((x for x in sec['screens'] if x['key']==d['key']),None)
 if old:old.update(item)
 else:sec['screens'].append(item)
sec['status']='Макеты есть · на вычитке';sec['description']='Сессии, позиции и заявки, события трейдера, решения и причины пропуска; частичные и поздние исполнения, отмена остатка. Полная ручная и ролевая приёмка открыта.'
s.update(revision='0.21',updatedAt='2026-10-18',counts={'ru':618,'en':618});save(A/'sitemap.json',s)
summary='**618 RU +618 EN корневых макетов**, из них 613 основных состояний и 5 служебных оболочек на язык. Карта 0.21, набор компонентов 0.4.21 (28 наборов /168 вариантов).'
lines=['# Живая карта админки','','Текущий срез 18.10.2026: '+summary,'','Полный читаемый индекс сформирован из [sitemap.json](sitemap.json). Статус раздела относится к покрытию дизайном, не реализации или полной приёмке. Исторические срезы доступны в Git.','','[Карта в Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2105-5766) · [Последние изменения](session-workspace-2026-10-18/README.md)','']
for section in s['sections']:
 lines+=['## '+section['id']+' · '+section['title'],'',section.get('status','На вычитке')+'. '+section['description'],'',f"Состояний: {len(section['screens'])}.",'','| Состояние | RU | EN |','| --- | --- | --- |']
 lines+=['| '+x['title'].replace('|',' / ')+' | [Макет]('+url(x['id'])+') | [Макет]('+url(x['english']['id'])+') |' for x in section['screens']];lines.append('')
(A/'sitemap.md').write_text('\n'.join(lines)+'\n')
p=A/'README.md';parts=p.read_text().split('\n\n',2);parts[1]='Текущий срез 18.10.2026: '+summary+' [Рабочее место сессии](session-workspace-2026-10-18/README.md) · [Полная карта](sitemap.md). Ниже — исторический журнал.';p.write_text('\n\n'.join(parts))
Q=A/'requirements-coverage-2026-10-16';q=read(Q/'requirements.json');item=next(x for x in q if x['id']=='S04');item.update(status='готово',priority='—',gap='Заполненные RU/EN списки и связанный путь по позиции, заявке, событию трейдера и принятым/пропущенным решениям с конкретными причинами. Период и историческая версия отделены от текущего снимка. Покрытие дизайном; полный ролевой, языковой и серверный проход не закрыт.',keys=['ADM-03/'+d['key'] for d in D]);item['evidence']=[{'key':d['key'],'section':'ADM-03','ru':ids[d['key']]['ru'],'en':ids[d['key']]['en'],'urlRU':url(ids[d['key']]['ru']),'urlEN':url(ids[d['key']]['en'])} for d in D];save(Q/'requirements.json',q)
counts=dict(collections.Counter(x['status'] for x in q));assert counts=={'готово':85,'частично':18,'отсутствует':1,'отложено':6},counts
with (Q/'requirements.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['id','area','requirement','status','gap','priority','source'],extrasaction='ignore',quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(q)
old=read(Q/'current-status.json')
if old.get('mainStatesPerLocale')!=613:
 save(Q/'current-status.json',{'date':'2026-10-18','scope':'Design coverage after populated session workspace; not runtime acceptance','counts':counts,'rootsPerLocale':618,'mainStatesPerLocale':613,'manualPresent':False,'manualPresentScope':'Selected prototype transitions only; full role/RU/EN pass remains open','baseCommit':'3021843883c09c55c74dc08b072a6b28a7de5b97','package':'../session-workspace-2026-10-18/README.md','latestPackage':'../session-workspace-2026-10-18/README.md','closed':list(dict.fromkeys(old['closed']+['S04'])),'closedThisPackage':['S04'],'previousSnapshot':{'counts':old['counts'],'rootsPerLocale':601,'mainStatesPerLocale':596,'package':old['latestPackage']}})
p=Q/'matrix.md';lines=p.read_text().splitlines();lines[2]='Срез 18.10.2026 после [рабочего места сессии](../session-workspace-2026-10-18/README.md): **85 покрыто, 18 частично, 1 отсутствует, 6 отложено**. Покрытие дизайном, не полная приёмка.'
links='; '.join('['+e['key']+' RU]('+e['urlRU']+') · [EN]('+e['urlEN']+')' for e in item['evidence']);lines=[('| S04 | '+item['requirement']+' | готово | '+item['gap']+' | '+links+' |') if x.startswith('| S04 |') else x for x in lines];p.write_text('\n'.join(lines)+'\n')
p=Q/'README.md';marker='# Текущий срез · рабочее место сессии · 18.10.2026'
if not p.read_text().startswith(marker):p.write_text(marker+'\n\n**85 покрыто, 18 частично, 1 отсутствует, 6 отложено.** [Пакет](../session-workspace-2026-10-18/README.md) закрывает S04 на уровне макетов. Глобальные права/фильтры, остальные инциденты и полный ручной проход открыты. Ниже — исторические срезы.\n\n'+p.read_text().replace('# Текущий срез','# Исторический срез'))
append='\n\n## Уточнение 18.10.2026 · рабочее место торговой сессии\n\n[Согласованный учебный снимок, сущности и права](design/admin/session-workspace-2026-10-18/contract.md): позиции, заявки, исходные действия трейдера и решения по сигналам разделены вкладками и связаны точными ID. Решение хранит свои настройки/суммы/время; допуск не равен полному исполнению. Пропуски не создают резерв/заявку и не догоняются, нехватка полной суммы не уменьшает покупку. Ручные и сохранённые после отключения активы не продаются вслед за трейдером.\n\nПри отсутствии текущей цены нет рыночной стоимости и прибыли. Загрузка, пустая подтверждённая выборка и устаревший снимок при ошибке чтения различаются. Альтернативный неподключённый профиль Limitless не обещает поддержанные поля API или вторую активную demo-session. Владелец с разрешённым чтением видит учебные суммы; новые права сотрудникам не вводятся. Paper Alpha: комиссия 0%. Рабочие переходы и сценарии прототипа разделены. 17 состояний на язык, UI kit 0.4.21 без расширения. G04/G05/G06 и полный X01/X04 остаются открыты.\n'
for name in ['115_admin_console_technical_specification_2026-10-09.md','118_admin_console_figma_design_brief_2026-10-09.md']:
 p=R/'docs'/name
 if '## Уточнение 18.10.2026 · рабочее место торговой сессии' not in p.read_text():p.write_text(p.read_text()+append)
p=A/'ui-kit/README.md';text='18.10.2026: [рабочее место сессии](../session-workspace-2026-10-18/README.md) использует существующие связанные кнопки для навигации по разделам и фильтрам, строки, шапку таблицы и панели. Новых семейств/вариантов/токенов нет, версия 0.4.21. Подчёркнутый ID ведёт в свою карточку; служебные сценарии отделены.\n\n'
if text not in p.read_text():p.write_text(text+p.read_text())
p=A/'STYLE_GUIDE.md';txt=p.read_text().replace('**14 · Admin · RU**, 254 состояния.','**14 · Admin · RU**; текущее число макетов — в [живой карте](sitemap.md).').replace('**15 · Admin · EN**, 254 состояния.','**15 · Admin · EN**; текущее число макетов — в [живой карте](sitemap.md).');p.write_text(txt)
p=A/'review-guide-2026-10-13/guide-source.json';g=read(p)
cards=[]
for number,d in enumerate(D,37):
 items=[('HEADING_2',f'03.{number:02d} — '+d['title'][0],[]),('NORMAL_TEXT','Назначение: рабочее место сессии — '+d['title'][0].lower()+'.',[]),('NORMAL_TEXT','На экране / смысл состояния: '+d['body'][0],[]),('NORMAL_TEXT','Что проверить: исходный ID, площадка и снимок совпадают; исторические суммы не выдаются за текущие; переход не создаёт сделку или исправление баланса.',[]),('NORMAL_TEXT','Прототип RU',[{'label':'Прототип RU','url':proto(ids[d['key']]['ru'])}]),('NORMAL_TEXT','Prototype EN',[{'label':'Prototype EN','url':proto(ids[d['key']]['en'])}])]
 cards.extend({'style':style,'text':text+'\n','links':links} for style,text,links in items)
if not any(x['text'].startswith('03.37 — ') for x in g['paras']):
 at=next(i for i,x in enumerate(g['paras']) if x['style']=='HEADING_1' and x['text'].startswith('ADM-04'));g['paras'][at:at]=cards
for x in g['paras']:x['text']=x['text'].replace('596 основных экранов','613 основных экранов').replace('601 RU +601 EN','618 RU +618 EN').replace('карта 0.20','карта 0.21').replace('карты 0.20','карты 0.21').replace('596 карточек','613 карточек').replace('601 корневых макетов','618 корневых макетов')
g.update(screenCount=613,updatedAt='2026-10-18');index=1
for x in g['paras']:x['startIndex']=index;index+=len(x['text'].encode('utf-16-le'))//2
save(p,g);save(P/'guide-new-cards.json',cards)
print('Updated sitemap0.21, 613 pairs; design coverage',counts)
