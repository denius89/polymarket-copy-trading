
const page=await figma.getNodeByIdAsync("1981:29");await figma.setCurrentPageAsync(page);
const created=[],mutated=[],frames=[],links=[];const track=n=>{created.push(n.id);return n;};
const styles=await figma.getLocalTextStylesAsync(),styleMap=new Map(styles.map(s=>[s.name,s]));for(const s of styles)await figma.loadFontAsync(s.fontName);
const vs=await figma.variables.getLocalVariablesAsync(),vm=new Map(vs.map(v=>[v.name,v])),vi=new Map(vs.map(v=>[v.id,v]));const cs=await figma.variables.getLocalVariableCollectionsAsync(),cm=new Map(cs.map(c=>[c.id,c]));
function resolve(v){const c=cm.get(v.variableCollectionId),x=v.valuesByMode[c.modes.find(m=>m.name==='Dark')?.modeId??c.defaultModeId];return x?.type==='VARIABLE_ALIAS'?resolve(vi.get(x.id)):x;}
function fill(name){const v=vm.get(name),rgb=resolve(v);return figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:rgb.r,g:rgb.g,b:rgb.b}},'color',v);}
function bind(n,k,name){n.setBoundVariable(k,vm.get(name));}
function box(parent,name,dir,w,color){const n=track(figma.createAutoLayout(dir));parent.appendChild(n);n.name=name;n.resize(w,80);n.fills=color?[fill(color)]:[];n.primaryAxisSizingMode=dir==='VERTICAL'?'AUTO':'FIXED';n.counterAxisSizingMode=dir==='VERTICAL'?'FIXED':'AUTO';bind(n,'itemSpacing','spacing/4');return n;}
function text(parent,label,style='Body/Small',w=parent.width,color='color/text/primary'){const t=track(figma.createText());parent.appendChild(t);t.name=label.slice(0,55);t.textStyleId=styleMap.get(style).id;t.characters=label;t.textAutoResize='HEIGHT';t.resize(w,t.height);t.fills=[fill(color)];return t;}
const masters={};for(const [key,id]of Object.entries({sidebar:'1981:16',nav:'2032:67',navSelected:'2032:74',primary:'2081:38',secondary:'2081:65',danger:'2081:119',field:'2081:150',fieldError:'2081:155',check:'2081:486',unchecked:'2081:483',disabledCheck:'2081:485',alertInfo:'2081:580',alertSuccess:'2081:581',alertWarning:'2081:582',alertDanger:'2081:583',status:'2081:356',metadata:'2137:26727'}))masters[key]=await figma.getNodeByIdAsync(id);
function inst(parent,key,props,width){const n=track(masters[key].createInstance());parent.appendChild(n);const vals={};for(const [name,value]of Object.entries(props)){const prop=Object.keys(n.componentProperties).find(p=>p.split('#')[0]===name);if(prop)vals[prop]=value;}n.setProperties(vals);if(width)n.resize(width,n.height);return n;}
const P=(a,b)=>[a,b];

const locale="RU",ru=locale==="RU",specs=[{"key":"marketing-delivery-paused","ru":"Доставка до паузы","en":"Delivery before pause","type":"delivery"}],T=(a,b)=>ru?a:b,pending=[],built=[],removed=[];
const base=await figma.getNodeByIdAsync("2337:26585");const fonts=new Map();for(const t of base.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);for(const f of fonts.values())await figma.loadFontAsync(f);
masters.metric=await figma.getNodeByIdAsync("1981:3");
const rowMaster=await figma.getNodeByIdAsync("2375:1233"),headerMaster=await figma.getNodeByIdAsync("2375:1261"),metadataHeader=await figma.getNodeByIdAsync("2202:634"),taMaster=await figma.getNodeByIdAsync("1978:921"),selectMaster=await figma.getNodeByIdAsync("2081:181"),down=await figma.getNodeByIdAsync("2258:1122");
function comp(parent,master,props,w){const n=track(master.createInstance());parent.appendChild(n);const vals={};for(const[k,v]of Object.entries(props)){const p=Object.keys(n.componentProperties).find(x=>x.split("#")[0]===k);if(p)vals[p]=v;}n.setProperties(vals);if(w)n.resize(w,n.height);return n;}
function card(parent,title,w=1144){const n=box(parent,title||"Card","VERTICAL",w,"color/bg/surface");for(const k of ["paddingTop","paddingBottom","paddingLeft","paddingRight"])bind(n,k,"spacing/6");bind(n,"cornerRadius","radius/lg");n.strokes=[fill("color/border/default")];n.strokeWeight=1;if(title)text(n,title,"Heading/Small",w-48);return n;}
function action(parent,label,target,style="secondary"){const n=inst(parent,style,{Label:label,"Show icon":false});n.name="Marketing action · "+target;pending.push({id:n.id,target});return n;}
function actions(parent,arr){if(!arr.length)return;const n=box(parent,"Actions","HORIZONTAL",parent.width-parent.paddingLeft-parent.paddingRight);n.layoutWrap="WRAP";for(const [a,b,k,st]of arr)action(n,T(a,b),k,st||"secondary");return n;}
function lines(parent,arr,w=parent.width-parent.paddingLeft-parent.paddingRight){for(const[a,b]of arr)text(parent,T(a,b),"Body/Small",w,"color/text/secondary");}
function field(parent,label,value,hint="",w=1096,select=false){const n=select?comp(parent,selectMaster,{Label:label,Value:value,Hint:hint},w):inst(parent,"field",{Label:label,Value:value,Hint:hint},w);if(select){const i=n.findOne(x=>x.type==="INSTANCE"&&x.name==="Icon");if(i){i.swapComponent(down);i.resize(20,20);mutated.push(i.id);}}return n;}
function area(parent,label,value,hint="",error=false){const n=comp(parent,taMaster,{Label:label,Value:value,Hint:hint,State:error?"Error":"Default"},532);n.primaryAxisSizingMode="AUTO";n.counterAxisSizingMode="FIXED";for(const ch of n.children){if(ch.type==="TEXT"){ch.textAutoResize="HEIGHT";ch.resize(532,ch.height);}else if(ch.type==="FRAME"){ch.resize(532,ch.height);ch.primaryAxisSizingMode="AUTO";for(const t of ch.findAllWithCriteria({types:["TEXT"]})){t.textAutoResize="HEIGHT";t.resize(532-ch.paddingLeft-ch.paddingRight,t.height);}const th=Math.max(72,...ch.children.filter(t=>t.type==="TEXT").map(t=>t.height+ch.paddingTop+ch.paddingBottom));ch.resize(532,th);ch.primaryAxisSizingMode="FIXED";}}return n;}
function notice(parent,title,body,kind="Info"){return inst(parent,"alert"+kind,{Title:title,Body:body},1144);}
function table(parent,title,heads,rows){const n=box(parent,title,"VERTICAL",1144,"color/bg/surface");bind(n,"cornerRadius","radius/lg");n.itemSpacing=0;const h=box(n,"Table title","VERTICAL",1144);for(const k of ["paddingTop","paddingBottom","paddingLeft","paddingRight"])bind(h,k,"spacing/6");text(h,title,"Heading/Small",1096);const hi=comp(n,metadataHeader,{},1144);const vals={};heads.forEach((v,i)=>{const k=Object.keys(hi.componentProperties).find(x=>x.split("#")[0]==="Column "+(i+1));if(k)vals[k]=v;});hi.setProperties(vals);for(const [a,b,c,target]of rows){const r=inst(n,"metadata",{Title:a,Detail:b,Meta:c},1144);if(target)pending.push({id:r.id,target});}return n;}
function stats(parent,list){const row=box(parent,"Metrics","HORIZONTAL",1144);for(const[a,b,c]of list){const n=inst(row,"metric",{Title:a,Value:b,Hint:c},370.667);n.primaryAxisSizingMode="AUTO";for(const t of n.findAllWithCriteria({types:["TEXT"]})){t.textAutoResize="HEIGHT";t.resize(322.667,t.height);}}}
const titleRU="Откройте каталог трейдеров",titleEN="Explore the trader catalog";
const bodyRU="Сравните доступных трейдеров и изучите их профили. Вы сами выбираете, кого копировать.";
const bodyEN="Compare available traders and explore their profiles. You choose whom to copy.";
const oldRU="Познакомьтесь с каталогом трейдеров.",oldEN="Discover the trader catalog.";
for(let si=0;si<specs.length;si++){
 const spec=specs[si],key=spec.key,rootName=locale+" · "+key+" · "+spec[ru?"ru":"en"];
 if(page.children.some(n=>n.name===rootName))throw Error("Already exists "+rootName);
 const root=base.clone();page.appendChild(root);created.push(root.id);root.name=rootName;root.resize(1440,1200);root.x=18920+((36+si)%3)*1600;root.y=Math.floor((36+si)/3)*1560;
 const nav=root.children.find(n=>n.name==="Navigation"),main=root.children.find(n=>n.name==="Main");nav.resize(248,1200);main.resize(1192,1200);
 for(const g of nav.children.filter(n=>n.type==="INSTANCE"&&n.name.startsWith("Navigation group"))){g.setProperties({Open:g.name.includes("Management")?"Yes":"No"});mutated.push(g.id);}
 const ctx=main.children.find(n=>n.name==="Context"),crumb=main.children.find(n=>n.name==="Breadcrumb trail"),heading=main.children.find(n=>n.name==="Page heading");
 for(const n of [...main.children])if(![ctx,crumb,heading].includes(n)){removed.push(n.id);n.remove();}
 for(const t of ctx.children.filter(n=>n.type==="TEXT")){t.characters=T("ДИЗАЙН · ДЕМО · SHADOW-ADM-01","DESIGN · DEMO · SHADOW-ADM-01");mutated.push(t.id);}
 const avatar=ctx.findOne(n=>n.type==="INSTANCE"&&n.width===44);if(avatar){await avatar.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[{type:"NODE",destinationId:"2303:26697",navigation:"OVERLAY",transition:null}]}]);mutated.push(avatar.id);}
 crumb.setProperties({"Home#2211:0":T("Обзор","Overview"),"Section#2211:1":T("Маркетинг","Marketing"),"Current#2211:2":spec[ru?"ru":"en"]});crumb.visible=key!=="marketing-list";mutated.push(crumb.id);
 const ht=heading.children.filter(n=>n.type==="TEXT");ht[0].characters=spec[ru?"ru":"en"];for(const t of ht.slice(1))t.visible=false;mutated.push(...ht.map(n=>n.id));
 if(spec.type==="list"){
  const c=card(main,"");const fs=box(c,"Announcement filters","HORIZONTAL",1096);
  field(fs,T("Статус","Status"),key==="marketing-filtered"?T("Запланировано","Scheduled"):T("Все статусы","All statuses"),"",352,true);
  field(fs,T("Аудитория","Audience"),T("Все аудитории","All audiences"),"",352,true);
  field(fs,T("Период","Period"),"13–20 Oct 2026","UTC",352,true);
  actions(c,[["Новое объявление","New announcement","marketing-editor","primary"],["Запланированные","Scheduled","marketing-filtered"],["Сбросить","Reset","marketing-list"]]);
  const tab=box(main,"Announcement catalog","VERTICAL",1144,"color/bg/surface");tab.itemSpacing=0;bind(tab,"cornerRadius","radius/lg");
  const labels=ru?["Объявление / цель","Аудитория","Языки","Статус","Расписание","Автор / дата"]:["Announcement / purpose","Audience","Locales","Status","Schedule","Author / date"];const hp={};labels.forEach((x,i)=>hp["Column "+(i+1)]=x);comp(tab,headerMaster,hp,1144);
  const items=key==="marketing-filtered"?[1]:[0,1,2];
  for(const j of items){const r=comp(tab,rowMaster,{Title:j===2?T("Обзор новых профилей","Discover new profiles"):T(titleRU,titleEN),Detail:"ANN-DEMO-0"+(j+1)+" · Marketing",Audience:j===2?T("Не рассчитана","Not estimated"):T("100 клиентов","100 customers"),Locales:"RU / EN",Status:j===0?T("Активно","Active"):j===1?T("Запланировано","Scheduled"):T("Черновик","Draft"),Schedule:j===0?"13–20 Oct\n12:30 UTC":j===1?"14–20 Oct\n10:00 UTC":"—",Updated:T("Ирина Волкова","Irina Volkova")+"\n13 Oct · 12:15 UTC"},1144);pending.push({id:r.id,target:j===0?"marketing-active":j===1?"marketing-scheduled":"marketing-editor"});}
  notice(main,T("Только внутри приложения","In-app channel only"),T("Показатели основаны на подтверждённых событиях. Массовые email, Telegram и push появятся позже.","Metrics use confirmed events. Bulk email, Telegram and push are planned for later."));
 }else if(spec.type==="editor"){
  const valid=key==="marketing-validated",editOnly=["marketing-edit-only","marketing-edit-only-saved"].includes(key),revision=key==="marketing-revision";
  const c=card(main,T("Содержание объявления","Announcement content"));
  const row=box(c,"Purpose and placement","HORIZONTAL",1096);
  field(row,T("Цель сообщения","Message purpose"),T("Маркетинг","Marketing"),"",532,true);field(row,T("Размещение","Placement"),T("Объявления в приложении","In-app announcements"),"",532,true);
  field(c,T("Внутреннее название","Internal name"),T("Знакомство с каталогом","Catalog introduction"));
  const tr=box(c,"Translations","HORIZONTAL",1096);
  const left=box(tr,"RU translation","VERTICAL",532),right=box(tr,"EN translation","VERTICAL",532);
  field(left,"Русский · RU",titleRU,"",532);area(left,T("Текст RU","Body RU"),revision?oldRU:bodyRU,T("Без произвольного HTML","No arbitrary HTML"));
  field(right,"English · EN",titleEN,"",532);area(right,T("Текст EN","Body EN"),valid||editOnly?bodyEN:revision?oldEN:"",T("Обязательный перевод","Required translation"),key==="marketing-invalid");
  const settings=card(main,T("Аудитория и период","Audience and period"));const sr=box(settings,"Audience and timing","HORIZONTAL",1096);
  field(sr,T("Аудитория","Audience"),T("Разрешённые RU/EN клиенты","Eligible RU/EN customers"),"",532,true);field(sr,T("Период","Period"),"13–20 Oct 2026",T("Время: UTC","Time: UTC"),532);
  lines(settings,[[revision?"Новый черновик A-3 на основе A-1. Предыдущие версии и показы сохранены.":"ANN-DEMO-01 · черновик A-2 · автор Ирина Волкова",revision?"New A-3 draft based on A-1. Previous versions and impressions retained.":"ANN-DEMO-01 · draft A-2 · author Irina Volkova"]]);
  if(valid){notice(main,T("RU / EN проверены","RU / EN validated"),T("Содержание готово. Доступность аудитории проверяется отдельно перед запуском.","Content is ready. Audience eligibility is checked separately before launch."),"Success");actions(settings,[["Проверить аудиторию","Check audience","marketing-audience","primary"],["Предпросмотр","Preview","marketing-preview"]]);}
  else if(revision){actions(settings,[["Сохранить новый черновик","Save new draft","marketing-revision-saved","primary"]]);}
  else if(editOnly){notice(main,T("Доступно только редактирование","Editing only"),T("Черновик можно сохранить. Публикация и планирование недоступны для вашего набора прав.","You can save a draft. Your permissions do not allow publication or scheduling."),"Warning");actions(settings,[["Сохранить черновик","Save draft","marketing-edit-only-saved","primary"]]);}
  else if(key==="marketing-invalid"){notice(main,T("Перевод EN не заполнен","EN translation missing"),T("Заполните перевод перед предпросмотром и публикацией.","Complete the translation before preview and publication."),"Danger");actions(settings,[["Заполнить перевод","Complete translation","marketing-validated","primary"]]);}
  else actions(settings,[["Сохранить черновик","Save draft","marketing-draft-saved"],["Проверить","Validate",revision?"marketing-validated":"marketing-invalid","primary"]]);
  if(key==="marketing-edit-only-saved")notice(main,T("Черновик сохранён","Draft saved"),T("Публикация по-прежнему недоступна.","Publication remains unavailable."),"Success");
  if(key==="marketing-draft-saved")notice(main,T("Сохранено · A-2","Saved · A-2"),T("Черновик не показывается клиентам.","The draft is not shown to customers."),"Success");
  actions(main,[["К объявлениям","Back to announcements","marketing-list"]]);
 }else if(spec.type==="audience"){
  const blocked=key==="marketing-policy-blocked";
  stats(main,[[T("Подходят по сегменту","Match segment"),"124",T("RU / EN · вымышленные данные","RU / EN · synthetic data")],[T("Разрешено","Eligible"),blocked?"—":"100",T("После правил и ограничений","After eligibility checks")],[T("Исключено","Excluded"),blocked?"—":"24",T("Взаимоисключающие причины","Mutually exclusive reasons")]]);
  const c=card(main,T("Условия аудитории","Audience definition"));lines(c,[["Аудитория AU-DEMO-02 · RU / EN · обе площадки","Audience AU-DEMO-02 · RU / EN · both venues"],["Цель: Marketing · размещение: объявления внутри приложения","Purpose: Marketing · placement: in-app announcements"],["Согласия и ограничения проверяются снова перед каждой доставкой.","Consent and suppression are rechecked before every delivery."]]);
  if(blocked){notice(main,T("Отправка запрещена до настройки правила","Sending blocked until a rule is configured"),T("Правило согласия для этой цели неизвестно. Отсутствие отказа не считается разрешением.","Consent rule for this purpose is unknown. Lack of opt-out is not permission."),"Danger");actions(c,[["К редактору","Back to editor","marketing-editor"]]);}
  else{
   table(main,T("Причины исключения","Exclusion reasons"),[T("Причина","Reason"),T("Количество","Count"),T("Проверка","Evidence")],[[T("Отказ от маркетинга","Marketing opt-out"),"10",T("Предпочтения клиента","Customer preferences")],[T("Согласие неизвестно","Consent unknown"),"6",T("Не включаем по предположению","Never assumed eligible")],[T("Лимит частоты","Frequency limit"),"5",T("Правило демо FP-1","Demo rule FP-1")],[T("Ограничение аудитории","Audience restriction"),"3",T("Не соответствуют классу","Class not eligible")]]);
   notice(main,T("Аудитория проверена","Audience checked"),T("Снимок AS-DEMO-02: 100 клиентов. В интерфейсе доступны только агрегаты; контакты и финансовые данные не раскрываются.","Snapshot AS-DEMO-02: 100 customers. Only aggregates are shown; contacts and financial data are not exposed."),"Success");
   actions(main,[["Предпросмотр","Preview","marketing-preview","primary"],["К редактору","Back to editor","marketing-validated"]]);
  }
 }else if(spec.type==="preview"){
  const c=card(main,T(key==="marketing-test"?"Тестовый просмотр · не отправка":"Как увидит клиент",key==="marketing-test"?"Test view · no send":"Customer view"));
  const cols=box(c,"Localized previews","HORIZONTAL",1096);
  for(const language of ["RU","EN"]){const col=box(cols,language,"VERTICAL",532);text(col,language==="RU"?"Русский · RU":"English · EN","Body/Small medium",532);const pane=card(col,language==="RU"?titleRU:titleEN,532);text(pane,language==="RU"?bodyRU:bodyEN,"Body/Small",484);text(pane,language==="RU"?"13 октября · SHADOW":"13 October · SHADOW","Caption",484,"color/text/secondary");}
  lines(c,[["Текстовый формат. Произвольный HTML и платёжные действия отсутствуют.","Plain text format. No arbitrary HTML or payment actions."],[key==="marketing-test"?"Этот просмотр не ставит сообщение в очередь и не меняет счётчики клиентов.":"A-2 · AS-DEMO-02 · RU / EN · никаких внешних отправок",key==="marketing-test"?"This view does not enqueue a message or change customer counters.":"A-2 · AS-DEMO-02 · RU / EN · no external sends"]]);
  actions(c,[["Тестовый просмотр","Test view","marketing-test"],["Опубликовать сейчас","Publish now","marketing-publish-review","primary"],["Запланировать","Schedule","marketing-schedule"],["К редактору","Back to editor","marketing-validated"]]);
 }else if(spec.type==="schedule"){
  const c=card(main,T("Время показа","Availability window"));
  field(c,T("Начало","Start"),"14 Oct 2026 · 10:00 UTC",T("В интерфейсе явно указан часовой пояс","Timezone is explicit"));
  field(c,T("Завершение","End"),"20 Oct 2026 · 10:00 UTC");
  lines(c,[["ANN-DEMO-02 · отдельный пример расписания · содержание A-2","ANN-DEMO-02 · separate scheduling example · content A-2"],["В момент запуска повторно проверяются права сотрудника, ограничения проекта и доступность аудитории.","At launch, employee permissions, project controls and audience eligibility are rechecked."]]);
  actions(c,[["Проверить расписание","Review schedule","marketing-schedule-review","primary"],["К предпросмотру","Back to preview","marketing-preview"]]);
 }else if(spec.type==="review"){
  const scheduled=key==="marketing-schedule-review";
  const c=card(main,T(scheduled?"Запланировать ANN-DEMO-02":"Опубликовать ANN-DEMO-01",scheduled?"Schedule ANN-DEMO-02":"Publish ANN-DEMO-01"));
  lines(c,[["Версия содержания A-2 · языки RU / EN","Content version A-2 · RU / EN"],["Аудитория AU-DEMO-02 · снимок AS-DEMO-02 · 100 клиентов","Audience AU-DEMO-02 · snapshot AS-DEMO-02 · 100 customers"],[scheduled?"14 Oct · 10:00 → 20 Oct · 10:00 UTC":"13 Oct · 12:30 → 20 Oct · 12:30 UTC",scheduled?"14 Oct · 10:00 → 20 Oct · 10:00 UTC":"13 Oct · 12:30 → 20 Oct · 12:30 UTC"],["Цель Marketing · правило согласия CP-DEMO-2 · частота FP-1","Purpose Marketing · consent rule CP-DEMO-2 · frequency FP-1"],["Публикует Ирина Волкова · необходимые права доступны","Published by Irina Volkova · required permissions available"]]);
  notice(main,T("Проверка перед запуском","Launch preflight"),T("Поздние отказы исключаются повторно. Автор, время, версии и действие сохранятся в журнале.","Late opt-outs are excluded again. Actor, time, versions and action are logged."));
  actions(c,[[scheduled?"Подтвердить расписание":"Опубликовать",scheduled?"Confirm schedule":"Publish",scheduled?"marketing-scheduled":"marketing-publishing","primary"],["Назад","Back",scheduled?"marketing-schedule":"marketing-preview"]]);
 }else if(spec.type==="detail"){
  const paused=key==="marketing-paused",scheduled=key==="marketing-scheduled",ended=key==="marketing-ended",readonly=key==="marketing-readonly";
  const c=card(main,scheduled?"ANN-DEMO-02":"ANN-DEMO-01");
  const state=paused?T("Приостановлено","Paused"):scheduled?T("Запланировано","Scheduled"):ended?T("Завершено","Ended"):T("Активно","Active");
  lines(c,[[T(titleRU,titleEN),T(titleRU,titleEN)],["Версия A-2 · RU / EN · Marketing · Ирина Волкова","Version A-2 · RU / EN · Marketing · Irina Volkova"],[scheduled?"14–20 Oct · 10:00 UTC":"13–20 Oct · 12:30 UTC",scheduled?"14–20 Oct · 10:00 UTC":"13–20 Oct · 12:30 UTC"],["Аудитория: AS-DEMO-02 · 100 разрешено на проверке","Audience: AS-DEMO-02 · 100 eligible at preflight"]]);
  text(c,state,"Heading/Small",1096);
  if(scheduled){notice(main,T("Ожидает начала периода","Waiting for start time"),T("Публикация запланирована. До начала показов и прочтений нет.","Publication is scheduled. There are no impressions or reads before the start."));actions(c,[["Обновить статус","Refresh status","marketing-scheduler-blocked"]]);}
  else{
   stats(main,[[T("Доступно в приложении","Available in app"),"90",T("Уникальные клиенты","Unique customers")],[T("Подтверждён показ","Display confirmed"),"60",T("Не число загрузок","Not page-load count")],[T("Прочитали","Read"),"38",T("Отдельное подтверждение","Separate read evidence")]]);
   notice(main,paused?T("Будущая выдача остановлена","Future distribution paused"):ended?T("Период показа завершён","Availability window ended"):T("После повторной проверки: 98","After recheck: 98"),paused?T("Новые постановки и показы остановлены. Уже просмотренные объявления и история сохранены.","New enqueueing and impressions are stopped. Previously seen announcements and history remain."):ended?T("Новые показы не выполняются. Факты доставки и история сохранены.","No new impressions are served. Delivery facts and history remain."):T("Два клиента отозвали согласие после снимка и исключены до постановки в очередь.","Two customers withdrew consent after the snapshot and were excluded before enqueueing."),paused?"Warning":"Info");
   const a=[["Доставка и прочтение","Delivery and reading","marketing-delivery"],["История","History","marketing-history"]];
   if(!paused&&!ended&&!readonly)a.push(["Приостановить","Pause","marketing-pause-confirm"]);
   if(paused||ended)a.push(["Создать новую версию","Create new version","marketing-version"]);
   if(!readonly)actions(c,a);
   if(readonly)lines(c,[["Доступ: только просмотр. Публикация, пауза и изменение недоступны.","Access: view only. Publication, pause and editing are unavailable."]]);
  }
  actions(main,[["К объявлениям","Back to announcements","marketing-list"]]);
 }else if(spec.type==="delivery"){
  const unknown=key==="marketing-delivery-unknown",pausedDelivery=key==="marketing-delivery-paused";
  stats(main,[[T("Поставлено в очередь","Enqueued"),"98",T("100 − 2 поздних отказа","100 − 2 late opt-outs")],[pausedDelivery?T("Было доступно до паузы","Available before pause"):T("Доступно в приложении","Available in app"),"90",T("Не означает прочтение","Does not mean read")],[T("Прочитали","Read"),"38",T("Из 60 подтверждённых показов","Of 60 confirmed displays")]]);
  table(main,T("Подтверждённые состояния","Confirmed states"),[T("Состояние","State"),T("Уникальных клиентов","Unique customers"),T("Что известно","Evidence")],[[T("Доступно на экране","Available on surface"),"90",T("Объявление доступно клиенту","Announcement is available")],[T("Ошибка доставки","Delivery failed"),"4",T("Подтверждённая ошибка","Confirmed failure")],[T("Результат неизвестен","Unknown outcome"),"4",T("Нужна проверка событий","Event verification required"),pausedDelivery?null:"marketing-delivery-unknown"],[T("Подтверждён показ","Display acknowledged"),"60",T("Подмножество 90 доступных","Subset of 90 available")],[T("Подтверждено прочтение","Read acknowledged"),"38",T("Подмножество 60 показов","Subset of 60 displays")],[T("Исключены после снимка","Suppressed after snapshot"),"2",T("Не включены в очередь 98","Excluded from queue of 98")]]);
  notice(main,unknown?T("Четыре результата неизвестны","Four unknown outcomes"):T("Доступность, показ и прочтение различаются","Availability, display and reading differ"),unknown?T("Автоматический повтор недоступен до проверки. Обновление статуса не отправляет объявление повторно.","Automatic retry is unavailable until verification. Refreshing status does not resend the announcement."):T("90 + 4 + 4 = 98 поставленных в очередь. Показы и прочтения — вложенные метрики, их нельзя прибавлять к доставке.","90 + 4 + 4 = 98 enqueued. Displays and reads are nested metrics and must not be added to delivery totals."),unknown?"Warning":"Info");
  if(pausedDelivery)notice(main,T("История доставки · приостановлено","Delivery history · paused"),T("Эти показатели накоплены до паузы. Новые показы не выдаются.","These metrics were accumulated before pause. No new impressions are served."),"Warning");
  actions(main,pausedDelivery?[["К объявлению","Back to announcement","marketing-paused"],["История","History","marketing-history"]]:unknown?[["Проверить события","Check events","marketing-delivery"],["К объявлению","Back to announcement","marketing-active"]]:[["К объявлению","Back to announcement","marketing-active"],["Приостановить","Pause","marketing-pause-confirm"]]);
 }else if(spec.type==="pause"){
  const c=card(main,T("Остановить будущую выдачу ANN-DEMO-01","Stop future distribution of ANN-DEMO-01"));
  lines(c,[["Версия A-2 · обе площадки · объявления в приложении","Version A-2 · both venues · in-app announcements"],["Новые постановки в очередь и показы прекращаются после подтверждения применения.","New enqueueing and displays stop after application is confirmed."],["Уже увиденные объявления, 38 фактов прочтения и журнал не удаляются.","Previously seen announcements, 38 read acknowledgements and the audit log are retained."]]);
  field(c,T("Причина паузы","Pause reason"),T("Проверяем формулировку","Reviewing announcement wording"),T("Сохранится в журнале","Recorded in the audit log"));
  actions(c,[["Приостановить","Pause","marketing-pausing","danger"],["Отмена","Cancel","marketing-active"]]);
 }else if(spec.type==="history"){
  table(main,T("Версии и действия · ANN-DEMO-01","Versions and actions · ANN-DEMO-01"),[T("Событие / версия","Event / version"),T("Изменение","Change"),T("Автор / время","Actor / time")],[[T("Пауза A-2","Pause A-2"),T("Выдача остановлена, история сохранена","Distribution paused; history retained"),T("Ирина Волкова","Irina Volkova")+"\n13 Oct · 12:45 UTC","marketing-paused"],[T("Публикация A-2","Publish A-2"),T("Изменены тексты RU/EN · AS-DEMO-02","RU/EN text changed · AS-DEMO-02"),T("Ирина Волкова","Irina Volkova")+"\n13 Oct · 12:30 UTC","marketing-active"],[T("Сохранён черновик A-2","Saved draft A-2"),T("Предыдущие и новые значения сохранены","Before/after values retained"),T("Ирина Волкова","Irina Volkova")+"\n13 Oct · 12:15 UTC"],[T("Предыдущая версия A-1","Previous version A-1"),T("Архивная формулировка","Archived wording"),T("Ирина Волкова","Irina Volkova")+"\n12 Oct · 10:00 UTC","marketing-version"]]);
  actions(main,[["К объявлению","Back to announcement","marketing-paused"]]);
 }else if(spec.type==="version"){
  const c=card(main,T("A-1 · предыдущие значения","A-1 · previous values"));
  text(c,"RU: "+oldRU,"Body/Small",1096);text(c,"EN: "+oldEN,"Body/Small",1096);
  lines(c,[["Восстановление создаёт новый черновик. Для публикации снова нужны проверка текста и аудитории.","Restoration creates a new draft. Content and audience must be revalidated before publication."],["История A-1 / A-2 и прежние показы остаются. Повторная выдача не запускается автоматически.","A-1 / A-2 history and prior impressions remain. Distribution never restarts automatically."]]);
  actions(c,[["Создать черновик на основе A-1","Create draft from A-1","marketing-revision","primary"],["К истории","Back to history","marketing-history"]]);
 }else if(spec.type==="result"){
  const revisionSaved=key==="marketing-revision-saved";
  if(revisionSaved){const c=card(main,T("Новый черновик A-3 сохранён","New draft A-3 saved"));lines(c,[["Скопированы значения A-1. Публикация и повторные показы не запущены.","A-1 values copied. No publication or repeated distribution started."],["Дальше: новая проверка перевода, аудитории и периода перед публикацией.","Next: revalidate translations, audience and window before publishing."]]);actions(c,[["К истории","Back to history","marketing-history"]]);built.push({id:root.id,key,title:spec[ru?"ru":"en"],height:1200});continue;}
  const unknown=key==="marketing-unknown",failed=key==="marketing-publish-failed",blocked=key==="marketing-scheduler-blocked",pauseFailed=key==="marketing-pause-failed",pausing=key==="marketing-pausing";
  const c=card(main,T(blocked?"ANN-DEMO-02":"ANN-DEMO-01",blocked?"ANN-DEMO-02":"ANN-DEMO-01"));
  lines(c,[[blocked?"Плановый запуск не выполнен: право публикации отозвано.":pauseFailed?"Последний подтверждённый статус: активно.":unknown?"Текущий статус не подтверждён.":failed?"Подтверждено: версия A-2 не опубликована.":pausing?"Запрос паузы принят. Фактическое применение ещё не подтверждено.":"Запрос публикации принят. Активный статус ещё не подтверждён.",blocked?"Scheduled launch not performed: publication permission revoked.":pauseFailed?"Last confirmed status: active.":unknown?"Current status is not confirmed.":failed?"Confirmed: A-2 was not published.":pausing?"Pause request accepted. Actual application is not confirmed yet.":"Publication request accepted. Active state is not confirmed yet."],[unknown?"Повтор заблокирован. Проверка статуса не создаёт новую публикацию.":blocked?"Показы не начались. После исправления прав требуется новый запуск с актуальными проверками.":pauseFailed?"Нельзя считать новые показы остановленными. Обновите статус перед повторной попыткой.":"Автор и запрос сохранены в журнале.",unknown?"Retry blocked. Status verification does not create another publication.":blocked?"Displays have not started. After permissions are corrected, a new launch with fresh checks is required.":pauseFailed?"New displays cannot be assumed stopped. Refresh status before retrying.":"Actor and request are retained in the audit log."]]);
  if(unknown)actions(c,[["Проверить статус","Check status","marketing-active","primary"]]);
  else if(pausing)actions(c,[["Обновить статус","Refresh status","marketing-paused","primary"]]);
  else if(pauseFailed)actions(c,[["Обновить статус","Refresh status","marketing-active","primary"]]);
  else if(failed)actions(c,[["Вернуться к черновику","Back to draft","marketing-validated","primary"]]);
  else if(blocked)actions(c,[["К расписанию","Back to schedule","marketing-scheduled"]]);
  else actions(c,[["Обновить статус","Refresh status","marketing-active","primary"]]);
  actions(main,[["К объявлениям","Back to announcements","marketing-list"]]);
 }else{
  const c=card(main,"");text(c,key==="marketing-no-access"?T("Для этого раздела нужно право просмотра маркетинга.","This section requires marketing-view permission."):key==="marketing-load-error"?T("Данные не загружены. Статусы объявлений неизвестны.","Data was not loaded. Announcement statuses are unknown."):T("По выбранным фильтрам объявлений нет.","No announcements match these filters."),"Body/Small",1096);
  actions(c,key==="marketing-no-access"?[["К обзору","Back to overview","overview"]]:[["Сбросить фильтры","Reset filters","marketing-list"]]);
 }
 const height=Math.max(1200,...main.children.filter(n=>n.visible).map(n=>n.y+n.height+24));root.resize(1440,height);main.resize(1192,height);nav.resize(248,height);root.overflowDirection="VERTICAL";
 built.push({id:root.id,key,title:spec[ru?"ru":"en"],height});
}
return {createdNodeIds:created,mutatedNodeIds:mutated,removedNodeIds:removed,frames:built,links:pending};
