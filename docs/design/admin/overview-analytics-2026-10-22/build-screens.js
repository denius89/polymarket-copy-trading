// Extend existing roots. Sidebar, role initializer, account return and routes survive.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const created=[],mutated=[],proof=[];
const vs=await figma.variables.getLocalVariablesAsync(),vm=new Map(vs.map(v=>[v.name,v])),vi=new Map(vs.map(v=>[v.id,v]));const cs=await figma.variables.getLocalVariableCollectionsAsync(),cm=new Map(cs.map(c=>[c.id,c]));
function value(v){const c=cm.get(v.variableCollectionId),x=v.valuesByMode[c.modes.find(m=>m.name==='Dark')?.modeId||c.defaultModeId];return x?.type==='VARIABLE_ALIAS'?value(vi.get(x.id)):x;}
function paint(name){const v=vm.get(name),c=value(v);return figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:c.r,g:c.g,b:c.b}},'color',v);}
const sm=new Map((await figma.getLocalTextStylesAsync()).map(s=>[s.name,s]));await Promise.all(['Caption','Label','Body/Small','Heading/Small','Numeric/Small'].map(n=>figma.loadFontAsync(sm.get(n).fontName)));
const tr=n=>(created.push(n.id),n);
function box(p,name,dir,w){const n=tr(figma.createAutoLayout(dir));p.appendChild(n);n.name=name;n.resize(w,80);n.primaryAxisSizingMode=dir==='VERTICAL'?'AUTO':'FIXED';n.counterAxisSizingMode=dir==='VERTICAL'?'FIXED':'AUTO';n.fills=[];n.setBoundVariable('itemSpacing',vm.get('spacing/4'));return n;}
function text(p,s,w=p.width,style='Body/Small',tone='color/text/primary'){const t=tr(figma.createText());p.appendChild(t);t.name=s.slice(0,65);t.textStyleId=sm.get(style).id;t.characters=s;t.textAutoResize='HEIGHT';t.resize(w,t.height);t.fills=[paint(tone)];return t;}
function surface(p,name,w){const n=box(p,name,'VERTICAL',w);n.fills=[paint('color/bg/surface')];n.setBoundVariable('cornerRadius',vm.get('radius/lg'));for(const k of ['paddingTop','paddingRight','paddingBottom','paddingLeft'])n.setBoundVariable(k,vm.get('spacing/4'));return n;}
function props(n,values){const p={};for(const[k,v]of Object.entries(values)){const key=Object.keys(n.componentProperties).find(x=>x.split('#')[0]===k);if(key)p[key]=v;}n.setProperties(p);}
const secondary=await figma.getNodeByIdAsync('2081:65'),primary=await figma.getNodeByIdAsync('2081:38'),detail=await figma.getNodeByIdAsync('3871:1524');
function button(p,label,active=false){const n=tr((active?primary:secondary).createInstance());p.appendChild(n);props(n,{Label:label,'Show icon':false});n.name=label;return n;}
const coll=cm.get('VariableCollectionId:134:180');function bool(name,d){const full='Admin overview/'+name;let v=vm.get(full);if(!v){v=figma.variables.createVariable(full,coll,'BOOLEAN');v.scopes=['ALL_SCOPES'];v.setValueForMode(coll.defaultModeId,d);created.push(v.id);vm.set(full,v);}return v;}
const six=bool('six hours',false),twelve=bool('twelve hours',true),data=bool('data expanded',false),closed=bool('data collapsed',true);
const set=(v,b)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type:'BOOLEAN',resolvedType:'BOOLEAN',value:b}});
for(const [rootId,locale,state]of ROOTS){const root=await figma.getNodeByIdAsync(rootId),m=root.children.find(n=>/^Main/.test(n.name));if(m.children.some(n=>n.name==='Overview analytics · v1')){proof.push({id:rootId,already:true});continue;}
 const ru=locale==='ru',t=(a,b)=>ru?a:b;
 const heading=m.children.find(n=>n.name==='Page heading');const original=[...m.children];const actions={};
 if(state==='ready'){const metrics=original.find(n=>n.name==='Metrics');for(let i=0;i<metrics.children.length;i++)actions[['sessions','users','review'][i]]=metrics.children[i].reactions;
 }else{const ready=await figma.getNodeByIdAsync(ru?'1982:37690':'1982:38513');const metrics=ready.children.find(n=>/^Main/.test(n.name)).findOne(n=>n.name==='Metrics');for(let i=0;i<metrics.children.length;i++)actions[['sessions','users','review'][i]]=metrics.children[i].reactions;}
 const body=box(m,'Overview analytics · v1','VERTICAL',1144);m.insertChild(m.children.indexOf(heading)+1,body);
 if(state==='ready'){
  text(body,t('Сейчас · учебный снимок 12 октября 2026, 12:00 UTC','Now · fictional snapshot 12 October 2026, 12:00 UTC'),1144,'Caption','color/text/secondary');
  const metrics=original.find(n=>n.name==='Metrics');body.appendChild(metrics);mutated.push(metrics.id);
  const row=box(body,'Analytics · 8 + 4 columns','HORIZONTAL',1144);row.counterAxisAlignItems='MIN';
  const chart=surface(row,'User activity',757.333333);const top=box(chart,'Activity heading and period','HORIZONTAL',725.333333);top.counterAxisAlignItems='CENTER';text(top,t('Активность пользователей','User activity'),450,'Heading/Small');const periods=box(top,'Period controls','HORIZONTAL',259.333333);periods.itemSpacing=8;
  for(const [hours,flag,other]of [[6,six,twelve],[12,twelve,six]])for(const active of [true,false]){const b=button(periods,t(hours+' часов',hours+' hours'),active);b.setBoundVariable('visible',active?flag:other);await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[set(six,hours===6),set(twelve,hours===12)]}]);}
  text(chart,t('Пользователи с действиями за каждый час · 12 октября · UTC','Users with activity in each hour · 12 October · UTC'),725.333333,'Caption','color/text/secondary');
  for(const [hours,flag]of [[12,twelve],[6,six]]){const i=tr((await figma.getNodeByIdAsync(KIT.variants[hours+'h'])).createInstance());chart.appendChild(i);i.setBoundVariable('visible',flag);i.name='Activity chart · '+hours+'h';}
  text(chart,t('Каждая точка — отдельный час. Одного пользователя нельзя суммировать между часами.','Each point is a separate hour. Do not add unique users across hours.'),725.333333,'Caption','color/text/secondary');
  const controls=box(chart,'Activity actions','HORIZONTAL',725.333333);for(const expanded of [false,true]){const b=button(controls,t(expanded?'Скрыть данные':'Показать данные',expanded?'Hide data':'Show data'));b.setBoundVariable('visible',expanded?data:closed);await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[set(data,!expanded),set(closed,expanded)]}]);}const users=button(controls,t('Открыть пользователей','Open users'));await users.setReactionsAsync(actions.users);
  const rows=box(chart,'Chart data alternative','VERTICAL',725.333333);rows.setBoundVariable('visible',data);rows.itemSpacing=8;
  text(rows,t('Час · UTC                       Пользователи с действиями','Hour · UTC                      Users with activity'),725.333333,'Label');
  for(const [hours,flag]of [[12,twelve],[6,six]]){const table=box(rows,'Data · '+hours+'h','VERTICAL',725.333333);table.itemSpacing=4;table.setBoundVariable('visible',flag);for(let i=12-hours;i<12;i++)text(table,String(FIXTURE.hoursUTC[i]).padStart(2,'0')+':00                                  '+FIXTURE.activeUsers[i],725.333333,'Caption');}
  const states=surface(row,'Current session states',370.666667);text(states,t('Сессии сейчас','Sessions now'),338.666667,'Heading/Small');text(states,t('2 сессии · по наличию замечаний','2 sessions · grouped by review need'),338.666667,'Caption','color/text/secondary');
  for(const [label,tone]of [[t('Без замечаний','No issues'),'color/accent/default'],[t('Нужна сверка','Needs reconciliation'),'color/warning/text']]){text(states,label+' · 1',338.666667,'Label');const track=tr(figma.createFrame());states.appendChild(track);track.name=label+' · 1 of 2';track.resize(338.666667,12);track.fills=[paint('color/bg/elevated')];track.cornerRadius=4;const bar=tr(figma.createRectangle());track.appendChild(bar);bar.resize(169.333333,12);bar.cornerRadius=4;bar.fills=[paint(tone)];}
  text(states,t('0                                         1                                         2','0                                         1                                         2'),338.666667,'Caption','color/text/secondary');const sb=button(states,t('Открыть все сессии','Open all sessions'));await sb.setReactionsAsync(actions.sessions);
  const attention=surface(body,'Needs attention · source and next step',1144);text(attention,t('Требует внимания · 1','Needs attention · 1'),1112,'Heading/Small');
  for(const [idx,values]of [t(['Пользователь / сессия','Проблема','Что делать'],['User / session','Issue','Next step']),[t('Demo Noor · U-DEMO-002\nS-DEMO-002 · Polymarket','Demo Noor · U-DEMO-002\nS-DEMO-002 · Polymarket'),t('Результат заявки неизвестен','Order result unknown'),t('Проверить результат до повторной отправки','Check the outcome before resubmission')]].entries()){
   const r=tr(detail.createInstance());attention.appendChild(r);r.resize(1112,r.height);props(r,{Title:values[0],Detail:values[1],Meta:values[2]});r.name=idx?'Attention · S-DEMO-002':'Attention table headings';if(idx)await r.setReactionsAsync(actions.review);
  }
  const review=button(attention,t('Открыть сессию для сверки','Open session for reconciliation'));await review.setReactionsAsync(actions.review);
  for(const n of original.filter(n=>['Grid row · 6 + 6','Actions','UX07 · Demo examples'].includes(n.name))){body.appendChild(n);mutated.push(n.id);}
 }else{
  const p=surface(body,state==='stale'?'Last known activity':'Activity unavailable',1144);text(p,t('Активность пользователей','User activity'),1112,'Heading/Small');text(p,state==='stale'?t('Прошлый учебный снимок · 12 октября, 12:00 UTC · свежесть не подтверждена','Past fictional snapshot · 12 October, 12:00 UTC · freshness not confirmed'):t('Нет подключённого источника. Значения и график пока недоступны.','No connected source. Values and chart are unavailable.'),1112,'Body/Small','color/text/secondary');const i=tr((await figma.getNodeByIdAsync(KIT.variants[state==='stale'?'Stale':'Empty'])).createInstance());p.appendChild(i);if(state==='empty')props(i,{Message:t('Нет источника данных','No data source')});for(const n of original.filter(n=>n.name==='Task column · 8 columns')){body.appendChild(n);mutated.push(n.id);}
 }
 root.resize(1440,state==='ready'?1800:1100);m.resize(1192,state==='ready'?1800:1100);mutated.push(root.id,m.id);proof.push({id:rootId,locale,state,rootPreserved:true,actorHeaderPreserved:true,body:body.id});
}
return {createdNodeIds:created,mutatedNodeIds:mutated,proof,variables:{six:six.id,twelve:twelve.id,data:data.id,closed:closed.id}};
