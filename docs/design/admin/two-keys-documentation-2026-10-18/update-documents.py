"""Reconcile the scoped admin handoff after verified Figma results. Not a Figma backup."""
import pathlib,json,collections,csv,re
root=pathlib.Path(__file__).resolve().parents[4]
a=root/'docs/design/admin'; pkg=pathlib.Path(__file__).parent
load=lambda p:json.loads(p.read_text())
write=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
data=load(pkg/'states.json'); pairs=load(pkg/'screen-pairs.json'); bykey={x['key']:x for x in pairs}
s=load(a/'sitemap.json'); area=next(x for x in s['sections'] if x['id']=='ADM-14')
url=lambda id:'https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-')
for d in data:
    p=bykey[d['key']]; entry=next((x for x in area['screens'] if x['key']==d['key']),None)
    val={'id':p['ru'],'key':d['key'],'title':d['title'][0],'url':url(p['ru']),'english':{'id':p['en'],'title':'EN · '+d['key']+' · '+d['title'][1],'url':url(p['en'])}}
    if entry is None:area['screens'].append(val)
    else:entry.update(val)
s['revision']='0.19';s['updatedAt']='2026-10-18';s['counts']={'ru':566,'en':566};write(a/'sitemap.json',s)
summary='**566 RU +566 EN корневых макетов**, из них 561 основное состояние и 5 служебных оболочек на язык. Карта 0.19, набор компонентов 0.4.21 (28 наборов /168 вариантов).'
lines=['# Живая карта админки','', 'Текущий срез 18.10.2026: '+summary, '', 'Полный читаемый индекс сформирован из [sitemap.json](sitemap.json). Статус раздела относится к покрытию дизайном, не к реализации или окончательной приёмке. Исторические срезы доступны в истории Git; ниже только текущие разделы.', '', '[Карта в Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2105-5766) · [Последние изменения](two-keys-documentation-2026-10-18/README.md)','']
for sec in s['sections']:
    lines.extend(['## '+sec['id']+' · '+sec['title'],'',sec.get('status','На вычитке')+'. '+sec['description'],'','Состояний: '+str(len(sec['screens']))+'.','','| Состояние | RU | EN |','| --- | --- | --- |'])
    for x in sec['screens']:lines.append('| '+x['title'].replace('|',' / ')+' | [Макет]('+url(x['id'])+') | [Макет]('+url(x['english']['id'])+') |')
    lines.append('')
(a/'sitemap.md').write_text('\n'.join(lines)+'\n')
p=a/'README.md';text=p.read_text(); text=re.sub(r'Текущий срез 16\.10\.2026:.*?Ниже — исторический журнал\.', 'Текущий срез 18.10.2026: '+summary+' [Проверка двух ключей и документация](two-keys-documentation-2026-10-18/README.md) · [Полная карта](sitemap.md). Ниже — исторический журнал.',text,count=1);text=text.replace('Актуальный срез: **216','Исторический срез: **216').replace('## Текущий пакет','## История · пакет');p.write_text(text)
qpath=a/'requirements-coverage-2026-10-16';q=load(qpath/'requirements.json');item=next(x for x in q if x['id']=='B06');item.update(status='готово',priority='—',gap='Два отдельных результата, ожидание браузера, ошибка/повтор нужного ключа, отмена второго шага, запрет повторного использования основного и устаревание показаны. Это дизайн; настоящие проверки WebAuthn и полная ручная приёмка не выполнялись.')
item['evidence']=[{'key':d['key'],'section':'ADM-14','ru':bykey[d['key']]['ru'],'en':bykey[d['key']]['en'],'urlRU':url(bykey[d['key']]['ru']),'urlEN':url(bykey[d['key']]['en'])} for d in data]
write(qpath/'requirements.json',q)
with (qpath/'requirements.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['id','area','requirement','status','gap','priority','source'],extrasaction='ignore',quoting=csv.QUOTE_ALL);writer.writeheader();writer.writerows(q)
counts=dict(collections.Counter(x['status'] for x in q));assert counts=={'готово':81,'частично':21,'отсутствует':2,'отложено':6},counts
p=qpath/'current-status.json';old=load(p);write(p,{'date':'2026-10-18','scope':'Design/documentation coverage after separate key verification; not runtime acceptance','counts':counts,'rootsPerLocale':566,'mainStatesPerLocale':561,'manualPresent':False,'baseCommit':'085d8e6830628b876c5d4f045345a599a3a0bd26','package':'../two-keys-documentation-2026-10-18/README.md','latestPackage':'../two-keys-documentation-2026-10-18/README.md','closed':list(dict.fromkeys(old['closed']+['B06'])),'closedThisPackage':['B06'],'previousSnapshot':{'date':old['date'],'counts':old['counts'],'rootsPerLocale':558,'mainStatesPerLocale':553,'package':old['latestPackage']},'originalCounts':old.get('initialCounts')})
p=qpath/'matrix.md';text=p.read_text();parts=text.splitlines();parts[2]='Срез 18.10.2026 после [раздельной проверки ключей](../two-keys-documentation-2026-10-18/README.md): **81 покрыто, 21 частично, 2 отсутствует, 6 отложено**. Это покрытие дизайном и документацией, не реализация и не полная ручная приёмка.';links='; '.join('['+d['key']+' RU]('+url(bykey[d['key']]['ru'])+') · [EN]('+url(bykey[d['key']]['en'])+')' for d in data);parts=[('| B06 | '+item['requirement']+' | готово | '+item['gap']+' | '+links+' |') if l.startswith('| B06 |') else l for l in parts];p.write_text('\n'.join(parts)+'\n')
p=qpath/'README.md';p.write_text('# Текущий срез · 18.10.2026\n\n**81 покрыто, 21 частично, 2 отсутствует, 6 отложено.** [Пакет двух ключей и документации](../two-keys-documentation-2026-10-18/README.md) закрывает B06 на уровне дизайна. Реальные проверки и полная ручная приёмка открыты. Ниже — исторические срезы.\n\n'+p.read_text().replace('# Текущий срез после','# Исторический срез после'))
for path in [root/'docs/115_admin_console_technical_specification_2026-10-09.md',root/'docs/118_admin_console_figma_design_brief_2026-10-09.md']:
    text=path.read_text();marker='Owner + другой уполномоченный сотрудник восстанавливают денежные функции после аварии.'
    if marker in text:text=text.replace(marker,'Общее поэтапное снятие аварийного ограничения требует владельца и независимого уполномоченного сотрудника. Это не разрешение на восстановительное пополнение: по ADR-0047 §7 два владельца отдельно разрешают ограниченный денежный маршрут и отдельно подтверждают конкретный перевод.')
    if path.name.startswith('115'):
        marker='### 12.4 Funding controls и user UI';text=text.replace(marker,'Ограниченный восстановительный денежный маршрут отличается от общего снятия ограничения. По ADR-0047 §7 его отдельно разрешают два владельца, затем два владельца отдельно подтверждают точный перевод. Общее подтверждение владельцем и сотрудником не заменяет эти согласия.\n\n'+marker)
    text+='\n\n## Уточнение 18.10.2026 · отдельная проверка двух ключей\n\nДля владельца показываются отдельные результаты основного и другого запасного физического ключа. Один запрос не подтверждает оба. Состояния: не проверен, ожидание браузера, подтверждён, ошибка/отмена, повтор уже проверенного ключа, устаревший результат. При ошибке или отмене второго шага первый результат сохраняется только пока действителен для той же учётной записи и той же версии набора ключей. Срок и серверные условия определяются при реализации, новые численные правила не утверждены. Изменение набора, отзыв или истечение действительности аннулирует незавершённую последовательность; чувствительные действия не открываются по старому результату. Только две отдельные действительные проверки разных зарегистрированных ключей завершают настройку. Проверка входа не является денежным согласием.\n\n[Макеты, состояния и границы проверки](design/admin/two-keys-documentation-2026-10-18/README.md). Сценарные переключатели прототипа вынесены из рабочих действий и не реализуются как продуктовые кнопки.\n';path.write_text(text)
p=a/'ui-kit/README.md';p.write_text('18.10.2026: в [проверке двух ключей](../two-keys-documentation-2026-10-18/README.md) переиспользованы существующие таблица, строки, панели и кнопки. Новых компонентов, вариантов и токенов нет; версия набора остаётся 0.4.21. Рабочие действия отделены от служебных переключателей прототипа.\n\n'+p.read_text())
# Update the local guide using its own paragraph indices, independently of native Docs.
p=a/'review-guide-2026-10-13/guide-source.json';g=load(p);paras=g['paras'];g['screenCount']=561;g['updatedAt']='2026-10-18'
for para in paras:
    para['text']=para['text'].replace('553 основных экранов','561 основных экранов').replace('558 RU +558 EN','566 RU +566 EN').replace('Срез 16 октября 2026, карта 0.18','Срез 18 октября 2026, карта 0.19').replace('живая карта 0.18','живая карта 0.19').replace('553 карточки','561 карточка').replace('558 корневых макетов','566 корневых макетов')
for d,number in [(data[0],'14.51'),(data[-1],'14.52')]:
    i=next(i for i,x in enumerate(paras) if x['style']=='HEADING_2' and x['text'].startswith(number+' '));paras[i]['text']=number+' — '+d['title'][0]+'\n'
    for j in range(i+1,min(i+6,len(paras))):
        if paras[j]['text'].startswith('На экране'):paras[j]['text']='На экране: '+d['message'][0]+'\n'
        if paras[j]['text'].startswith('Что проверить:'):paras[j]['text']='Что проверить: основной и запасной ключ имеют независимые результаты; ни один переход не засчитывает оба.\n'
new=[]
for number,d in enumerate([x for x in data if not x.get('existing')],72):
    pair=bykey[d['key']]
    for style,text,links in [('HEADING_2',f'14.{number} — '+d['title'][0],[]),('NORMAL_TEXT','Назначение: отдельный этап проверки двух физических ключей владельца.',[]),('NORMAL_TEXT','На экране: '+d['message'][0],[]),('NORMAL_TEXT','Что проверить: результат относится только к указанному ключу; ошибка или отмена не завершают настройку.',[]),('NORMAL_TEXT','Прототип RU', [{'label':'Прототип RU','url':'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+pair['ru'].replace(':','-')+'&starting-point-node-id='+pair['ru'].replace(':','-')+'&scaling=scale-down'}]),('NORMAL_TEXT','Prototype EN',[{'label':'Prototype EN','url':'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+pair['en'].replace(':','-')+'&starting-point-node-id='+pair['en'].replace(':','-')+'&scaling=scale-down'}])]:new.append({'style':style,'text':text+'\n','links':links})
pos=next(i for i,x in enumerate(paras) if x.get('style')=='HEADING_1' and x['text'].startswith('ADM-15'));paras[pos:pos]=new
index=1
for para in paras:para['startIndex']=index;index+=len(para['text'].encode('utf-16-le'))//2
write(p,g);write(pkg/'guide-new-cards.json',new)
print('Updated current sitemap, coverage, account contract, kit usage and local guide.')
