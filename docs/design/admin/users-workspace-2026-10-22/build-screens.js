// Inputs: KIT (returned component IDs), SCREENS (explicit existing roots).
// Reuses each root, sidebar, actor header, breadcrumb and prototype initializer.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const created=[],mutated=[],removed=[],proof=[];
const vars=await figma.variables.getLocalVariablesAsync(),vm=new Map(vars.map(v=>[v.name,v])),vi=new Map(vars.map(v=>[v.id,v]));
const collections=await figma.variables.getLocalVariableCollectionsAsync(),cm=new Map(collections.map(c=>[c.id,c]));
function value(v){const c=cm.get(v.variableCollectionId),x=v.valuesByMode[c.modes.find(m=>m.name==='Dark')?.modeId||c.defaultModeId];return x?.type==='VARIABLE_ALIAS'?value(vi.get(x.id)):x;}
function fill(name){const v=vm.get(name),c=value(v);return figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:c.r,g:c.g,b:c.b}},'color',v);}
const styles=await figma.getLocalTextStylesAsync(),sm=new Map(styles.map(s=>[s.name,s]));
await Promise.all(['Body/Small','Body/Small medium','Label','Caption','Heading/Small','Heading/Medium','Numeric/Small'].map(name=>figma.loadFontAsync(sm.get(name).fontName)));
const masters={};for(const [k,id]of Object.entries({button:'2081:65',primary:'2081:38',field:'2081:150',nav:'2032:67',selectedNav:'2032:74',metadata:'3871:1524',notice:'2081:582',header:KIT.header,userRow:KIT.defaultRow}))masters[k]=await figma.getNodeByIdAsync(id);
const track=n=>(created.push(n.id),n);
function box(parent,name,dir,w){const n=track(figma.createAutoLayout(dir));parent.appendChild(n);n.name=name;n.resize(w,80);n.primaryAxisSizingMode=dir==='VERTICAL'?'AUTO':'FIXED';n.counterAxisSizingMode=dir==='VERTICAL'?'FIXED':'AUTO';n.fills=[];n.setBoundVariable('itemSpacing',vm.get('spacing/4'));return n;}
function text(parent,s,w=parent.width,style='Body/Small',color='color/text/primary'){const t=track(figma.createText());parent.appendChild(t);t.name=s.slice(0,65);t.textStyleId=sm.get(style).id;t.characters=s;t.textAutoResize='HEIGHT';t.resize(w,t.height);t.fills=[fill(color)];return t;}
function props(n,values){const p={};for(const[k,v]of Object.entries(values)){const key=Object.keys(n.componentProperties).find(x=>x.split('#')[0]===k);if(key)p[key]=v;}n.setProperties(p);}
function inst(parent,key,p,w){const n=track(masters[key].createInstance());parent.appendChild(n);props(n,p);if(w)n.resize(w,n.height);return n;}
const node=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,preserveScrollPosition:true});
async function link(n,id){await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[node(id)]}]);}
async function button(parent,label,id,primary=false){const n=inst(parent,primary?'primary':'button',{Label:label,'Show icon':false});n.name='User action · '+label;if(id)await link(n,id);return n;}
function surface(parent,name,w){const n=box(parent,name,'VERTICAL',w);n.fills=[fill('color/bg/surface')];n.setBoundVariable('cornerRadius',vm.get('radius/lg'));for(const k of ['paddingTop','paddingRight','paddingBottom','paddingLeft'])n.setBoundVariable(k,vm.get('spacing/4'));return n;}
function record(parent,values,head=false){const n=inst(parent,'metadata',{Title:values[0],Detail:values[1],Meta:values[2]},parent.width);for(const t of n.children.filter(x=>x.type==='TEXT')){t.textAutoResize='HEIGHT';t.resize((parent.width-72)/3,t.height);}n.counterAxisSizingMode='AUTO';n.name=head?'User table headings':'User table record';if(head)n.fills=[fill('color/bg/elevated')];return n;}
const coll=cm.get('VariableCollectionId:134:180');
function bool(name,def){const full='Admin customer/'+name;let v=vm.get(full);if(!v){v=figma.variables.createVariable(full,coll,'BOOLEAN');v.scopes=['ALL_SCOPES'];v.setValueForMode(coll.defaultModeId,def);vm.set(full,v);created.push(v.id);}return v;}
const views=['overview','connections','sessions','operations','support'];
const flags={};for(const who of ['atlas','noor']){flags[who]={};for(const v of views)flags[who][v]={yes:bool(who+'/'+v,true&&v==='overview'),no:bool(who+'/'+v+'/inactive',v!=='overview')};}
const set=(v,b)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type:'BOOLEAN',resolvedType:'BOOLEAN',value:b}});
function tabActions(who,key){return views.flatMap(v=>[set(flags[who][v].yes,key===v),set(flags[who][v].no,key!==v)]);}
for(const d of SCREENS){
 const root=await figma.getNodeByIdAsync(d.id),m=root.children.find(n=>/^Main/.test(n.name));
 if(m.children.some(n=>n.name==='Customer workspace · v1')){proof.push({id:d.id,already:true});continue;}
 const L=d.locale==='ru',tr=(a,b)=>L?a:b,filtered=!!d.filtered,noor=!!d.noor,who=noor?'noor':'atlas',name=noor?'Demo Noor':'Demo Atlas',uid=noor?'U-DEMO-002':'U-DEMO-001',venue=noor?'Polymarket':'Limitless';
 const ids=L?{list:'1982:37788',filtered:'3445:70297',atlas:'1982:37844',noor:'2210:21620',filterCard:'3445:202900',settings:noor?'2210:22126':'2210:21952',session:noor?'1982:38392':'1982:38090',search:'3445:70055',support:'3445:203115',history:'3445:203322'}:{list:'1982:38611',filtered:'3445:202693',atlas:'1982:38667',noor:'2210:82672',filterCard:'3445:204036',settings:noor?'2210:83020':'2210:82846',session:noor?'1982:39215':'1982:38913',search:'3445:202451',support:'3445:204251',history:'3445:204458'};
 if(d.ops){ids.session=noor?(L?'2414:119294':'2414:122714'):(L?'1984:398':'1984:38802');}
 const originalBack=m.query('INSTANCE').filter(x=>x.name==='К инциденту'||x.name==='Back to incident').first()?.reactions;
 const header=m.children.find(n=>/context|account header/i.test(n.name)&&n.type==='FRAME'&&n.height<=50);
 const crumb=m.children.find(n=>n.name==='Breadcrumb trail'),heading=m.children.find(n=>n.name==='Page heading');
 const keep=new Set([header?.id,crumb?.id,heading?.id]);
 for(const n of [...m.children])if(!keep.has(n.id)){removed.push(n.id);n.remove();}
 const headingTexts=heading.query('TEXT').toArray();for(const t of headingTexts){for(const seg of t.getStyledTextSegments(['fontName']))await figma.loadFontAsync(seg.fontName);}
 headingTexts[0].characters=d.list?tr('Пользователи','Users'):name+' · '+uid;
 if(headingTexts[1])headingTexts[1].characters=tr('Paper Alpha · учебные средства · комиссия Shadow 0%','Paper Alpha · fictional funds · Shadow fee 0%');
 mutated.push(root.id,m.id,...headingTexts.map(n=>n.id));
 const body=box(m,'Customer workspace · v1','VERTICAL',1144);
 if(d.list){
  const tools=box(body,'User search and filters','HORIZONTAL',1144);tools.counterAxisAlignItems='CENTER';
  const f=inst(tools,'field',{Kind:'Search',State:'Default',Label:tr('Поиск по имени или ID','Search by name or ID'),Value:filtered?'U-DEMO-002':tr('Найти пользователя','Find a user'),Hint:tr('Открыть поиск и отбор','Open search and filters')},470);await link(f,ids.search);
  const venueFilter=inst(tools,'field',{Kind:'Select',State:'Filled',Label:tr('Площадка','Venue'),Value:filtered?'Polymarket':tr('Все площадки','All venues'),Hint:''},250);await link(venueFilter,ids.search);
  await button(tools,tr('Все фильтры','All filters'),ids.search);
  if(filtered)await button(tools,tr('Сбросить','Reset'),ids.list);
  text(body,filtered?tr('1 пользователь · без VIP · требует внимания · всё время · страница 1','1 user · no VIP · needs attention · all time · page 1'):tr('2 пользователя · все площадки · страница 1','2 users · all venues · page 1'),1144,'Body/Small medium','color/text/secondary');
  const table=box(body,'Users table','VERTICAL',1144);table.itemSpacing=0;table.setBoundVariable('itemSpacing',vm.get('spacing/0'));table.setBoundVariable('cornerRadius',vm.get('radius/lg'));table.clipsContent=true;
  const labels=tr(['Пользователь','Площадка','Баланс, $','Доступно, $','Сессии','VIP','Статус','Активность · UTC'],['User','Venue','Cash balance, $','Available, $','Sessions','VIP','Status','Activity · UTC']);inst(table,'header',Object.fromEntries(labels.map((v,i)=>['Column '+(i+1),v])));
  const data=filtered?[true]:[false,true];for(const isNoor of data){const vals=[isNoor?'Demo Noor\nU-DEMO-002':'Demo Atlas\nU-DEMO-001',isNoor?'Polymarket':'Limitless',isNoor?tr('180,00','180.00'):tr('1 000,00','1 000.00'),isNoor?tr('160,00','160.00'):tr('1 000,00','1 000.00'),'1',tr('Нет','None'),isNoor?tr('Активен\nНужна сверка','Active\nNeeds review'):tr('Активен','Active'),'12 Oct 2026\n12:00'];const row=inst(table,'userRow',Object.fromEntries(vals.map((v,i)=>['Column '+(i+1),v])));row.name='Open customer · '+(isNoor?'U-DEMO-002':'U-DEMO-001');await row.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[...tabActions(isNoor?'noor':'atlas','overview'),node(filtered?ids.filterCard:isNoor?ids.noor:ids.atlas)]}]);}
  text(body,tr('Учебный снимок · 12 Oct 2026, 12:00 UTC. Баланс — денежные средства без оценки позиций. Доступно — после резервов. Бюджет сессии не прибавляется к балансу.','Fictional snapshot · 12 Oct 2026, 12:00 UTC. Cash balance excludes positions. Available is after reserves. Session budgets are not added to cash.'),1144,'Caption','color/text/secondary');
 }else{
  const identity=box(body,'Customer identity and conditions','HORIZONTAL',1144);identity.counterAxisAlignItems='CENTER';
  const detail=box(identity,'Identity metadata','VERTICAL',850);detail.itemSpacing=8;text(detail,tr('Аккаунт активен · VIP не назначен','Account active · No VIP'),850,'Label');text(detail,venue+tr(' · Зарегистрирован: нет данных · Активность: 12 Oct 2026, 12:00 UTC',' · Registered: no data · Activity: 12 Oct 2026, 12:00 UTC'),850,'Caption','color/text/secondary');
  const back=await button(identity,d.ops?tr('В рабочую область','Back to workspace'):tr('К выборке','Back to results'),d.ops?(L?'3189:230621':'3189:230753'):filtered?ids.filtered:ids.list);if(d.ops&&noor&&originalBack)await back.setReactionsAsync(originalBack);
  const layout=box(body,'Customer sections','HORIZONTAL',1144);layout.counterAxisAlignItems='MIN';
  const nav=box(layout,'Customer section navigation','VERTICAL',177.333333);nav.itemSpacing=4;
  const content=box(layout,'Customer section content','VERTICAL',950.666667);
  const tabs=tr(['Обзор','Подключения','Сессии','Операции','Обращения'],['Overview','Connections','Sessions','Operations','Support']);
  for(let i=0;i<views.length;i++){const key=views[i];for(const active of [true,false]){const item=inst(nav,active?'selectedNav':'nav',{Label:tabs[i],Icon:['2032:10','2032:59','2032:17','2032:25','2032:14'][i]},177.333333);item.name='Customer tab · '+key+(active?' selected':'');item.setBoundVariable('visible',flags[who][key][active?'yes':'no']);await item.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:tabActions(who,key)}]);}}
  const settings=inst(nav,'nav',{Label:tr('Настройки','Settings'),Icon:'2032:41'},177.333333);if(d.ops&&noor){settings.opacity=0.45;text(nav,tr('Только контекст инцидента','Incident context only'),177.333333,'Caption','color/text/secondary');}else await link(settings,d.ops?(L?'2223:25930':'2223:52047'):ids.settings);
  for(const view of views){const panel=box(content,'Customer view · '+view,'VERTICAL',950.666667);panel.setBoundVariable('visible',flags[who][view].yes);text(panel,tabs[views.indexOf(view)],950.666667,'Heading/Small');
   if(view==='overview'){
    if(noor){const a=inst(panel,'notice',{Title:tr('Результат заявки неизвестен','Order result unknown'),Body:tr('S-DEMO-002 · повторная отправка запрещена до сверки. Аккаунт не заблокирован.','S-DEMO-002 · resubmission blocked until reconciliation. The account itself is active.')},950.666667);await link(a,ids.session);}
    if(!d.ops){const sum=surface(panel,'Read-only customer funds',950.666667),metrics=box(sum,'Cash and positions','HORIZONTAL',918.666667);metrics.itemSpacing=16;for(const[label,val]of [[tr('Баланс средств, $','Cash balance, $'),noor?tr('180,00','180.00'):tr('1 000,00','1 000.00')],[tr('Доступно, $','Available, $'),noor?tr('160,00','160.00'):tr('1 000,00','1 000.00')],[tr('В резерве, $','Reserved, $'),noor?tr('20,00','20.00'):tr('0,00','0.00')],[tr('Оценка позиций, $','Position value, $'),noor?tr('Нет данных','No data'):tr('0,00','0.00')]]){const c=box(metrics,label,'VERTICAL',217.666667);c.itemSpacing=8;text(c,label,217.666667,'Caption','color/text/secondary');text(c,val,217.666667,noor&&val===tr('Нет данных','No data')?'Label':'Numeric/Small');}text(sum,tr('Учебные суммы · 12 Oct 2026, 12:00 UTC. Средства и оценка позиций показаны отдельно.','Fictional amounts · 12 Oct 2026, 12:00 UTC. Cash and position value are shown separately.'),918.666667,'Caption','color/text/secondary');}
    else text(panel,tr('Денежная сводка кошелька не входит в этот разрешённый просмотр.','Wallet summary is outside this permitted view.'),950.666667,'Body/Small','color/text/secondary');
    const venueTable=box(panel,'Venue summary table','VERTICAL',950.666667);venueTable.itemSpacing=0;record(venueTable,tr(['Площадка / режим','Подключение','Обновлено · UTC'],['Venue / mode','Connection','Updated · UTC']),true);record(venueTable,[venue+' · Paper',tr('Учебный источник','Fictional source'),'12 Oct 2026 · 12:00']);
    text(panel,tr('Сессии пользователя','User sessions'),950.666667,'Heading/Small');const st=box(panel,'User sessions overview','VERTICAL',950.666667);st.itemSpacing=0;record(st,tr(['Сессия / площадка','Бюджет / позиции / заявки','Состояние'],['Session / venue','Budget / positions / orders','State']),true);const row=record(st,[noor?'S-DEMO-002 · Polymarket':'S-DEMO-001 · Limitless',noor?tr('$200 · стоимость исполнения $20','$200 · executed cost $20'):tr('$200 · 0 позиций · 0 заявок','$200 · 0 positions · 0 orders'),noor?tr('Результат неизвестен','Result unknown'):tr('Активна','Active')]);await link(row,ids.session);
    text(panel,tr('Бюджет — лимит сессии, а не отдельные деньги. Он не вычитается из баланса повторно.','Budget is a session limit, not separate funds. It is not deducted from cash a second time.'),950.666667,'Caption','color/text/secondary');
    if(!d.ops&&!noor){const a=box(panel,'Customer conditions actions','HORIZONTAL',950.666667);const vip=await button(a,tr('Управлять VIP','Manage VIP'),L?'2936:169255':'2936:175131');vip.setBoundVariable('visible',vm.get('Admin navigation/owners or unset'));text(panel,tr('Paper Alpha: комиссия 0%. VIP не меняет прошлые комиссии; 1% — лишь пример будущей платной версии.','Paper Alpha fee: 0%. VIP does not rewrite past fees; 1% is only a future paid-plan example.'),950.666667,'Caption','color/text/secondary');}
   }else if(view==='connections'){
    const t=box(panel,'Customer connections table','VERTICAL',950.666667);t.itemSpacing=0;record(t,tr(['Площадка','Состояние / режим','Проверено · UTC'],['Venue','State / mode','Checked · UTC']),true);record(t,[venue,tr('Учебное подключение · Paper','Fictional connection · Paper'),'12 Oct 2026 · 12:00']);record(t,[noor?'Limitless':'Polymarket',tr('Нет данных о подключении','No connection data'),tr('Нет данных','No data')]);text(panel,tr('Секреты не отображаются. Отсутствие данных не означает нулевой баланс или отключённый аккаунт.','Secrets are hidden. Missing data does not mean zero balance or a disconnected account.'),950.666667,'Body/Small','color/text/secondary');
   }else if(view==='sessions'){
    const t=box(panel,'Customer sessions table','VERTICAL',950.666667);t.itemSpacing=0;record(t,tr(['Сессия / площадка','Бюджет / резерв','Состояние / действие'],['Session / venue','Budget / reserve','State / action']),true);const r=record(t,[noor?'S-DEMO-002 · Polymarket':'S-DEMO-001 · Limitless',noor?'$200 / $20':'$200 / $0',noor?tr('Результат неизвестен · открыть','Result unknown · open'):tr('Активна · открыть','Active · open')]);await link(r,ids.session);await button(panel,tr('Открыть сессию','Open session'),ids.session);
   }else if(view==='operations'){
    if(noor){const t=box(panel,'Customer operation context','VERTICAL',950.666667);t.itemSpacing=0;record(t,tr(['Операция','Подтверждённый факт','Что остаётся неизвестным'],['Operation','Confirmed fact','What remains unknown']),true);record(t,['S-DEMO-002',tr('Стоимость исполнения $20; резерв $20','Executed cost $20; reserve $20'),tr('Результат заявки; оценка позиций','Order result; position valuation')]);await button(panel,tr('Открыть заявку и сверку','Open order and reconciliation'),ids.session);if(!d.ops)await button(panel,tr('История пользователя','User history'),ids.history);}else text(panel,tr('Подтверждённая история денежных операций не загружена. Здесь появятся операции с источником, временем и результатом.','Confirmed monetary history is not loaded. Operations will include source, time and outcome.'),950.666667,'Body/Small','color/text/secondary');
   }else{
    text(panel,noor?tr('Обращения, связанные только с U-DEMO-002. Внутренние заметки видят сотрудники с соответствующим правом.','Tickets linked only to U-DEMO-002. Internal notes require the appropriate permission.'):tr('Связанные обращения не загружены. Это не означает, что пользователь никогда не обращался.','Linked tickets are not loaded. This does not mean the user has never contacted support.'),950.666667,'Body/Small','color/text/secondary');if(noor&&!d.ops)await button(panel,tr('Открыть обращения пользователя','Open user tickets'),ids.support);
   }
  }
 }
 if(!d.list){root.resize(1440,1200);m.resize(1192,1200);}
 proof.push({id:root.id,list:!!d.list,noor,filtered,financialView:!d.ops,actorHeader:header?.id,sections:d.list?null:views,rootPreserved:true});
}
return {createdNodeIds:created,mutatedNodeIds:mutated,removedNodeIds:removed,proof,variables:Object.fromEntries(Object.entries(flags).map(([k,x])=>[k,Object.fromEntries(Object.entries(x).map(([v,p])=>[v,{yes:p.yes.id,no:p.no.id}]))]))};
