"""Scoped admin handoff update. Keeps historical slices and unrelated local work."""
from pathlib import Path
import json,csv,collections,re
P=Path(__file__).parent;R=P.resolve().parents[3];A=R/'docs/design/admin';Q=A/'requirements-coverage-2026-10-16'
read=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
D=read(P/'screen-content.json');pairs=read(P/'screen-pairs.json');ids={p['key']:p for p in pairs}
url=lambda id:'https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-')
proto=lambda id:'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-')+'&starting-point-node-id='+id.replace(':','-')+'&scaling=scale-down'
s=read(A/'sitemap.json');sections={x['id']:x for x in s['sections']};oldcounts={k:len(v['screens']) for k,v in sections.items()}
for d in D:
 p=ids[d['key']];sec=sections[d['section']];item={'id':p['ru'],'key':d['key'],'title':d['title'][0],'url':url(p['ru']),'english':{'id':p['en'],'title':'EN · '+d['key']+' · '+d['title'][1],'url':url(p['en'])}}
 old=next((x for x in sec['screens'] if x['key']==d['key']),None)
 if old:old.update(item)
 else:sec['screens'].append(item)
sections['ADM-14']['description']='Сотрудники, роли, 18 разделов и 7 типов действий, области и сроки, итоговый доступ, запреты, отзыв и критические полномочия. Приглашения B04 и полный сквозной проход ещё открыты.'
sections['ADM-12']['description']='Журнал действий и отдельное право экспорта: ограниченная выборка, подготовка, готовность, ошибка и отзыв до выдачи файла.'
s.update(revision='0.22',updatedAt='2026-10-18',counts={'ru':647,'en':647});save(A/'sitemap.json',s)
summary='**647 RU +647 EN корневых макетов**, из них 642 основных состояния и 5 служебных оболочек на язык. Карта 0.22, набор компонентов 0.4.21 (28 наборов /168 вариантов).'
lines=['# Живая карта админки','','Текущий срез 18.10.2026: '+summary,'','Полный читаемый индекс сформирован из [sitemap.json](sitemap.json). Статус относится к покрытию дизайном, не реализации или полной приёмке. Исторические срезы доступны в Git.','','[Карта в Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2105-5766) · [Последние изменения](staff-access-2026-10-18/README.md)','']
for sec in s['sections']:
 lines+=['## '+sec['id']+' · '+sec['title'],'',sec.get('status','На вычитке')+'. '+sec['description'],'',f"Состояний: {len(sec['screens'])}.",'','| Состояние | RU | EN |','| --- | --- | --- |']
 lines+=['| '+x['title'].replace('|',' / ')+' | [Макет]('+url(x['id'])+') | [Макет]('+url(x['english']['id'])+') |' for x in sec['screens']];lines.append('')
(A/'sitemap.md').write_text('\n'.join(lines)+'\n')
p=A/'README.md';parts=p.read_text().split('\n\n',2);parts[1]='Текущий срез 18.10.2026: '+summary+' [Права сотрудников](staff-access-2026-10-18/README.md) · [Полная карта](sitemap.md). Ниже — исторический журнал.';p.write_text('\n\n'.join(parts))
q=read(Q/'requirements.json');closed=['G06','B02','A02']
gaps={'G06':'Добавлены отдельные ролевые проекции RU/EN: скрытые разделы, финансовые данные и вложенные связи не раскрываются; прямые запросы, истечение срока, отзыв и критические действия отделены. Покрытие дизайном; полная проверка всех старых экранов и серверных границ остаётся в X01/X04.', 'B02':'Показаны 18 разделов, 7 независимых типов действий, площадка, среда, тип данных, срок, получатель, версии и итоговое назначение; отказ самоэскалации и конфликт. Учебные значения не утверждают пресеты или поставщика приглашений.', 'A02':'Ограниченный просмотр и отдельный экспорт: запрет, параметры, подготовка, готовность, ошибка и отзыв до скачивания. Синтетический CSV не является публичной ссылкой на рабочие данные; серверная выдача ещё не реализована.'}
keysets={'G06':[d for d in D if d['actor']!='owner'],'B02':[d for d in D if d['key'] in ['access-role-editor','access-role-scope','access-role-actions','access-role-preview','access-role-saved','access-role-conflict','access-self-denied']],'A02':[d for d in D if d['section']=='ADM-12']}
for id in closed:
 x=next(x for x in q if x['id']==id);x.update(status='готово',priority='—',gap=gaps[id],keys=[d['section']+'/'+d['key'] for d in keysets[id]])
 x['evidence']=[{'key':d['key'],'section':d['section'],'ru':ids[d['key']]['ru'],'en':ids[d['key']]['en'],'urlRU':url(ids[d['key']]['ru']),'urlEN':url(ids[d['key']]['en'])} for d in keysets[id]]
save(Q/'requirements.json',q);counts=dict(collections.Counter(x['status'] for x in q));assert counts=={'готово':88,'частично':15,'отсутствует':1,'отложено':6},counts
with (Q/'requirements.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['id','area','requirement','status','gap','priority','source'],extrasaction='ignore',quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(q)
old=read(Q/'current-status.json')
if old.get('rootsPerLocale')!=647:save(Q/'current-status.json',{'date':'2026-10-18','scope':'Staff access design coverage; not server authorization or full role acceptance','counts':counts,'rootsPerLocale':647,'mainStatesPerLocale':642,'manualPresent':False,'manualPresentScope':'Selected permission and critical routes only; complete P-01–P-18/X01/X04 remains open','baseCommit':'aee81a20a383a6d998f6fce74e6e2227d846e07f','package':'../staff-access-2026-10-18/README.md','latestPackage':'../staff-access-2026-10-18/README.md','closed':list(dict.fromkeys(old['closed']+closed)),'closedThisPackage':closed,'previousSnapshot':{'counts':old['counts'],'rootsPerLocale':618,'mainStatesPerLocale':613,'package':old['latestPackage']}})
p=Q/'matrix.md';lines=p.read_text().splitlines();lines[2]='Срез 18.10.2026 после [прав сотрудников](../staff-access-2026-10-18/README.md): **88 покрыто, 15 частично, 1 отсутствует, 6 отложено**. Покрытие дизайном, не полная приёмка.'
for x in q:
 if x['id'] not in closed:continue
 links='; '.join('['+e['key']+' RU]('+e['urlRU']+') · [EN]('+e['urlEN']+')' for e in x['evidence']);lines=[('| '+x['id']+' | '+x['requirement']+' | готово | '+x['gap']+' | '+links+' |') if line.startswith('| '+x['id']+' |') else line for line in lines]
p.write_text('\n'.join(lines)+'\n')
p=Q/'README.md';marker='# Текущий срез · права сотрудников · 18.10.2026'
if not p.read_text().startswith(marker):p.write_text(marker+'\n\n**88 покрыто, 15 частично, 1 отсутствует, 6 отложено.** [Пакет](../staff-access-2026-10-18/README.md) закрывает G06/B02/A02 на уровне макетов. X01/X04 и серверная проверка открыты. Следом каталог источников, оставшиеся настройки/состояния и сквозная вычитка. Ниже — исторические срезы.\n\n'+p.read_text().replace('# Текущий срез','# Исторический срез'))
append='\n\n## Уточнение 18.10.2026 · права сотрудников и критические действия\n\n[Полная матрица и границы доступа](design/admin/staff-access-2026-10-18/contract.md): 18 разделов, 7 типов действий, площадка, среда, данные и срок. Сохранение черновика и выдача действующих полномочий разделены. Итог показывает все действующие назначения; пример содержит одно назначение, не новые пресеты по умолчанию. Самоэскалация и выдача владельческих прав кастомной ролью запрещены. Ограничения применяются к списку, карточке, вложенным данным, суммам, счётчикам, обновлениям и экспорту. Ошибка или запрет не превращаются в нулевые суммы.\n\nОтзыв права экспорта блокирует выдачу уже готового файла, но не отменяет разрешённое чтение. Блокировка аккаунта, отзыв назначения и окончание срока — отдельные состояния; открытая вкладка не сохраняет права. Отправленное внешнее действие не объявляется отменённым.\n\nОбычный тариф, пользовательский VIP и обычная полная выплата — владелец; второе независимое согласие действует только по ADR-0046/0047. Новые реквизиты после второго владельца ждут 24 часа. Полный технический режим и жёсткий денежный запрет не обходятся двумя согласиями. Общая аварийная разблокировка и денежный маршрут восстановления различаются. Тексты и маркетинг публикуются по выданным правам без нового согласования владельцем. Новая проверка личности не выдаёт недостающие полномочия.\n\n29 состояний на язык, карта 0.22 — 647 корней /642 основных состояния; набор компонентов 0.4.21 без новых семейств. Покрытие дизайном, не реализация серверных проверок. Полные X01/X04 и приглашение B04 остаются открыты. Paper Alpha — комиссия Shadow 0%, реальные действия выключены; 1% только неактивный будущий пример.\n'
for name in ['115_admin_console_technical_specification_2026-10-09.md','118_admin_console_figma_design_brief_2026-10-09.md']:
 p=R/'docs'/name
 if '## Уточнение 18.10.2026 · права сотрудников и критические действия' not in p.read_text():p.write_text(p.read_text()+append)
for p,text in [(A/'ui-kit/README.md','18.10.2026: [права сотрудников](../staff-access-2026-10-18/README.md) используют существующие связанные навигацию, строки, шапки, панели, кнопки и семь отдельных флажков. Набор 0.4.21 не расширялся. Меню собирается по правам из существующих компонентов; новые варианты ролей не создаются.\n\n'),(A/'STYLE_GUIDE.md','18.10.2026: ограниченные роли показывают только разрешённые меню и данные; запрет не обозначается нулевой суммой. Рабочие действия отделены от сценариев прототипа. [Матрица и правила](staff-access-2026-10-18/contract.md).\n\n')]:
 if text not in p.read_text():p.write_text(text+p.read_text())
p=A/'review-new-skills-2026-10-18/REPORT.md';text='\n\n## Последующая правка · 18.10.2026 · права сотрудников\n\n[Пакет ролей и критических действий](../staff-access-2026-10-18/README.md): 29 состояний на язык. G06/B02/A02 покрыты макетами; 88 покрыто, 15 частично, 1 отсутствует, 6 отложено. Исходный аудит выше остаётся историческим; полные P-01–P-18/X01/X04, серверная авторизация и интеграции не приняты. Доказательства и пределы — в QA пакета.\n'
if '## Последующая правка · 18.10.2026 · права сотрудников' not in p.read_text():p.write_text(p.read_text()+text)
# Match the existing guide structure and preserve all earlier cards.
p=A/'review-guide-2026-10-13/guide-source.json';g=read(p);cards=[];groups=[]
for secid in sorted({d['section'] for d in D}):
 sec=sections[secid];extra=[d for d in D if d['section']==secid];first=len(sec['screens'])-len(extra)+1;paras=[]
 for n,d in enumerate(extra,first):
  heading=secid[-2:]+'.'+f'{n:02d}'+' — '+d['title'][0]
  items=[('HEADING_2',heading,[]),('NORMAL_TEXT','Назначение: '+d['title'][0].lower()+'.',[]),('NORMAL_TEXT','На экране: '+d['body'][0],[]),('NORMAL_TEXT','Что проверить: роль, область, срок и версия совпадают; запрет не раскрывает закрытые данные; просмотр не разрешает изменение или экспорт. Учебные переходы не выполняют настоящие операции.',[]),('NORMAL_TEXT','Прототип RU',[{'label':'Прототип RU','url':proto(ids[d['key']]['ru'])}]),('NORMAL_TEXT','Prototype EN',[{'label':'Prototype EN','url':proto(ids[d['key']]['en'])}])]
  paras.extend({'style':st,'text':tx+'\n','links':ls} for st,tx,ls in items)
 if not any(x['text'].startswith(paras[0]['text']) for x in g['paras']):
  start=next(i for i,x in enumerate(g['paras']) if x['style']=='HEADING_1' and x['text'].startswith(secid))
  end=next((i for i in range(start+1,len(g['paras'])) if g['paras'][i]['style']=='HEADING_1'),len(g['paras']));g['paras'][end:end]=paras
 cards+=paras;groups.append({'section':secid,'paras':paras})
for x in g['paras']:
 if x['style']!='HEADING_2':x['text']=x['text'].replace('613 основных экранов','642 основных экранов').replace('618 RU +618 EN','647 RU +647 EN').replace('карта 0.21','карта 0.22').replace('карты 0.21','карты 0.22').replace('613 карточек','642 карточек').replace('618 корневых макетов','647 корневых макетов')
g.update(screenCount=642,updatedAt='2026-10-18');index=1
for x in g['paras']:x['startIndex']=index;index+=len(x['text'].encode('utf-16-le'))//2
save(p,g);save(P/'guide-new-cards.json',groups)
print(json.dumps({'revision':'0.22','roots':647,'main':642,'coverage':counts,'sectionCounts':{k:len(v['screens']) for k,v in sections.items()}},ensure_ascii=False))
