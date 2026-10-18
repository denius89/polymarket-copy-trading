from pathlib import Path
import json,collections,csv
P=Path(__file__).parent;R=P.resolve().parents[3];A=R/'docs/design/admin'
load=lambda p:json.loads(p.read_text())
write=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
if load(A/'review-guide-2026-10-13/guide-source.json').get('screenCount',0)>=596:
 raise SystemExit('Archived one-time update already applied; do not duplicate guide cards.')
D=load(P/'screen-content.json');pairs=load(P/'screen-pairs.json');pair={x['key']:x for x in pairs};url=lambda id:'https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-');proto=lambda id:'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-')+'&starting-point-node-id='+id.replace(':','-')+'&scaling=scale-down'
s=load(A/'sitemap.json');oldCounts=s['counts'].copy()
for d in D:
 sec=next(x for x in s['sections'] if x['id']==d['section']);ids=pair[d['key']];item={'id':ids['ru'],'key':d['key'],'title':d['title'][0],'url':url(ids['ru']),'english':{'id':ids['en'],'title':'EN · '+d['key']+' · '+d['title'][1],'url':url(ids['en'])}}
 old=next((x for x in sec['screens'] if x['key']==d['key']),None)
 if old:old.update(item)
 else:sec['screens'].append(item)
s['revision']='0.20';s['updatedAt']='2026-10-18';s['counts']={'ru':601,'en':601};write(A/'sitemap.json',s)
summary='**601 RU +601 EN корневых макетов**, из них 596 основных состояний и 5 служебных оболочек на язык. Карта 0.20, набор компонентов 0.4.21 (28 наборов /168 вариантов).'
lines=['# Живая карта админки','','Текущий срез 18.10.2026: '+summary,'','Полный читаемый индекс сформирован из [sitemap.json](sitemap.json). Статус раздела относится к покрытию дизайном, не реализации или полной приёмке. Исторические срезы доступны в Git.','', '[Карта в Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2105-5766) · [Последние изменения](order-money-reconciliation-2026-10-18/README.md)','']
for sec in s['sections']:
 lines+=['## '+sec['id']+' · '+sec['title'],'',sec.get('status','На вычитке')+'. '+sec['description'],'',f"Состояний: {len(sec['screens'])}.",'','| Состояние | RU | EN |','| --- | --- | --- |']
 lines+=['| '+x['title'].replace('|',' / ')+' | [Макет]('+url(x['id'])+') | [Макет]('+url(x['english']['id'])+') |' for x in sec['screens']];lines.append('')
(A/'sitemap.md').write_text('\n'.join(lines)+'\n')
p=A/'README.md';parts=p.read_text().split('\n\n',2);parts[1]='Текущий срез 18.10.2026: '+summary+' [Заявки и денежная сверка](order-money-reconciliation-2026-10-18/README.md) · [Полная карта](sitemap.md). Ниже — исторический журнал.';p.write_text('\n\n'.join(parts))
Q=A/'requirements-coverage-2026-10-16';q=load(Q/'requirements.json');closure={'S05':[x for x in D if x['section']=='ADM-03'],'R02':[x for x in D if x['section']=='ADM-05'],'R03':[x for x in D if x['key'].endswith(('-error','-insufficient','evidence')) or x['key'] in ['order-cancel-unknown','order-late-check-error']]}
for item in q:
 if item['id'] not in closure:continue
 item['status']='готово';item['priority']='—';item['gap']='Покрыто отдельными RU/EN макетами: исходный объект, исполнение/удержания, подтверждение, ошибка проверки и нехватка данных. Это дизайн; фактические источники, права, окончательность и серверная сверка не проверены.'
 item['evidence']=[{'key':d['key'],'section':d['section'],'ru':pair[d['key']]['ru'],'en':pair[d['key']]['en'],'urlRU':url(pair[d['key']]['ru']),'urlEN':url(pair[d['key']]['en'])} for d in closure[item['id']]]
write(Q/'requirements.json',q);counts=dict(collections.Counter(x['status'] for x in q));assert counts=={'готово':84,'частично':19,'отсутствует':1,'отложено':6},counts
with (Q/'requirements.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['id','area','requirement','status','gap','priority','source'],extrasaction='ignore',quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(q)
old=load(Q/'current-status.json');write(Q/'current-status.json',{'date':'2026-10-18','scope':'Design coverage after order fills/cancellation and typed money readback; not runtime acceptance','counts':counts,'rootsPerLocale':601,'mainStatesPerLocale':596,'manualPresent':False,'baseCommit':'8d0ee205ef3fdea1dce634ccf78e5302d8f97352','package':'../order-money-reconciliation-2026-10-18/README.md','latestPackage':'../order-money-reconciliation-2026-10-18/README.md','closed':list(dict.fromkeys(old['closed']+list(closure))),'closedThisPackage':list(closure),'previousSnapshot':{'counts':old['counts'],'rootsPerLocale':566,'mainStatesPerLocale':561,'package':old['latestPackage']}})
p=Q/'matrix.md';lines=p.read_text().splitlines();lines[2]='Срез 18.10.2026 после [заявки и денежной сверки](../order-money-reconciliation-2026-10-18/README.md): **84 покрыто, 19 частично, 1 отсутствует, 6 отложено**. Это покрытие дизайном, не реализация или полная ручная приёмка.'
for item in q:
 if item['id'] not in closure:continue
 links='; '.join('['+e['key']+' RU]('+e['urlRU']+') · [EN]('+e['urlEN']+')' for e in item['evidence']);lines=[('| '+item['id']+' | '+item['requirement']+' | готово | '+item['gap']+' | '+links+' |') if x.startswith('| '+item['id']+' |') else x for x in lines]
p.write_text('\n'.join(lines)+'\n');p=Q/'README.md';p.write_text('# Текущий срез · заявки и денежная сверка · 18.10.2026\n\n**84 покрыто, 19 частично, 1 отсутствует, 6 отложено.** [Пакет](../order-money-reconciliation-2026-10-18/README.md) закрывает S05/R02/R03 на уровне макетов. S04, остальные типы инцидентов, ролевая и полная ручная приёмка остаются открыты. Ниже — исторические срезы.\n\n'+p.read_text().replace('# Текущий срез','# Исторический срез'))
append='\n\n## Уточнение 18.10.2026 · частичное исполнение и денежная сверка\n\n[Контракт и независимые учебные снимки](design/admin/order-money-reconciliation-2026-10-18/contract.md) дополняют разделы 6–7. Запрос отмены и её принятие отделены от окончательно сверённого неисполненного остатка. Поздно полученное исполнение, произошедшее до отмены, сохраняется; повтор наблюдения не добавляет его снова. Неизвестный исход и ошибка чтения не освобождают резерв. Снимок после позднего исполнения не откатывается к ранней версии при повторной проверке. Новых прав вручную торговать или отменять заявки за клиента нет.\n\nДенежная сверка типизирована: полная выплата партнёру, поступление своих средств, клиентское пополнение и исходный клиентский вывод. Для каждого — исходная идентичность, выполняемая проверка, достаточное подтверждение, ошибка чтения и недостаток/конфликт данных. Повторяется только чтение, не отправка. Подтверждённое получение не равно подтверждённой доступности клиентского остатка. Удержание завершённого вывода расходуется, а не возвращается в доступные средства. Собственное пополнение не считается доходом или новым партнёрским начислением. Автоматического снятия ограничений/закрытия инцидента нет.\n\nВсе сети, активы, контракты, подтверждения и суммы этих маршрутов — изолированные примеры; поддержка площадок проверяется при интеграции. Комиссия Paper Alpha 0%; частичных партнёрских выплат нет. Служебные исходы прототипа отделены от рабочих действий. Реальные переводы и работающая авторизация не запускались.\n'
for name in ['115_admin_console_technical_specification_2026-10-09.md','118_admin_console_figma_design_brief_2026-10-09.md']:
 p=R/'docs'/name;p.write_text(p.read_text()+append)
p=A/'ui-kit/README.md';p.write_text('18.10.2026: [заявки и денежная сверка](../order-money-reconciliation-2026-10-18/README.md) используют действующие панели, таблицу, строки и кнопки. Кнопки читают результат, не отправляют сделку/платёж; сценарии прототипа отделены. Новых компонентов/вариантов/токенов нет, версия 0.4.21 сохранена.\n\n'+p.read_text())
# Local guide uses local paragraph positions only.
p=A/'review-guide-2026-10-13/guide-source.json';g=load(p);paras=g['paras'];g['screenCount']=596;g['updatedAt']='2026-10-18'
for x in paras:x['text']=x['text'].replace('561 основных экранов','596 основных экранов').replace('566 RU +566 EN','601 RU +601 EN').replace('карта 0.19','карта 0.20').replace('карты 0.19','карты 0.20').replace('561 карточка','596 карточек').replace('566 корневых макетов','601 корневых макетов')
newCards={}
for section,number,nextSection in [('ADM-03',23,'ADM-04'),('ADM-05',9,'ADM-06')]:
 cards=[]
 for n,d in enumerate([d for d in D if d['section']==section],number):
  items=[('HEADING_2',section[-2:]+f'.{n:02d} — '+d['title'][0],[]),('NORMAL_TEXT','Назначение: показать состояние исходной операции, средства и безопасный следующий шаг.',[]),('NORMAL_TEXT','На экране / смысл состояния: '+d['body'][0],[]),('NORMAL_TEXT','Что проверить: исходный объект и версия не подменяются; подтверждённое исполнение/удержания не теряются; чтение не отправляет операцию.',[]),('NORMAL_TEXT','Прототип RU',[{'label':'Прототип RU','url':proto(pair[d['key']]['ru'])}]),('NORMAL_TEXT','Prototype EN',[{'label':'Prototype EN','url':proto(pair[d['key']]['en'])}])]
  cards.extend({'style':style,'text':text+'\n','links':links} for style,text,links in items)
 newCards[section]={'before':nextSection,'paras':cards};i=next(i for i,x in enumerate(paras) if x['style']=='HEADING_1' and x['text'].startswith(nextSection));paras[i:i]=cards
index=1
for x in paras:x['startIndex']=index;index+=len(x['text'].encode('utf-16-le'))//2
write(p,g);write(P/'guide-new-cards.json',newCards)
print('Updated 596 paired-state handoff; coverage',counts)
