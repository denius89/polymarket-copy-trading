// Inject DATA, COPY and V. Scoped extension of existing client instances, not a backup.
const p=figma.root.children.find(p=>p.id===DATA.page);await figma.setCurrentPageAsync(p);
figma.skipInvisibleInstanceChildren=false;
const changed=new Set(),created=new Set(),removed=new Set();
const lit=v=>({type:typeof v==='boolean'?'BOOLEAN':'STRING',resolvedType:typeof v==='boolean'?'BOOLEAN':'STRING',value:v});
const ref=(id,type='STRING')=>({type:'VARIABLE_ALIAS',resolvedType:type,value:{type:'VARIABLE_ALIAS',id}});
const ex=(fn,...args)=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:fn,expressionArguments:args}});
const eq=(id,value)=>ex('EQUALS',ref(id),lit(value));
const set=(name,value)=>({type:'SET_VARIABLE',variableId:V[name],variableValue:typeof value==='object'?value:lit(value)});
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,resetScrollPosition:true});
const when=(condition,yes,no=[])=>({type:'CONDITIONAL',conditionalBlocks:[{condition,actions:yes},{actions:no}]});
function flatten(actions,guard=null){const out=[];for(const a of actions){if(a.type!=='CONDITIONAL'){out.push(guard?when(guard,[a]):a);continue;}let seen=null;for(const b of a.conditionalBlocks){const test=b.condition?(seen?ex('AND',ex('NOT',seen),b.condition):b.condition):seen?ex('NOT',seen):lit(true);out.push(...flatten(b.actions,guard?ex('AND',guard,test):test));if(b.condition)seen=seen?ex('OR',seen,b.condition):b.condition;}}return out;}
async function reactions(node,rx){for(const r of rx)if(r.actions)r.actions=flatten(r.actions);await node.setReactionsAsync(rx);changed.add(node.id);}
const locked=ex('OR',eq('VariableID:4305:2295','pending'),ex('OR',eq('VariableID:4305:2295','partial'),ex('OR',eq('VariableID:4305:2295','unknown'),eq('VariableID:4305:2295','active'))));
const ids=[...DATA.records.map(x=>x.id),...Object.values(DATA.aux),...Object.values(DATA.sources),DATA.index];
const roots=new Map(p.query(ids.map(id=>'#'+id).join(',')).map(n=>[n.id,n]));
const byKey=Object.fromEntries(DATA.records.map(x=>[x.key,roots.get(x.id)]));
const fonts=new Map();for(const root of roots.values())for(const t of root.query('TEXT'))for(const seg of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(seg.fontName),seg.fontName);
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
function remember(n){created.add(n.id);for(const c of n.query('*'))created.add(c.id);}
function txt(t,value){t.setBoundVariable('characters',null);t.characters=value;changed.add(t.id);}
function bind(t,id){t.setBoundVariable('characters',{type:'VARIABLE_ALIAS',id});changed.add(t.id);}
function host(root){const shown=n=>{for(let c=n;c&&c!==root;c=c.parent)if(c.type==='INSTANCE'||('visible'in c&&c.visible===false))return false;return true;};return root.query('FRAME').filter(n=>shown(n)&&n.visible&&n.layoutMode==='VERTICAL'&&n.width>=340&&n.width<=1160&&/content|stack/i.test(n.name)).first()||root.query('FRAME').filter(n=>shown(n)&&n.visible&&n.layoutMode==='VERTICAL'&&n.width>=340&&n.width<=1160).first();}
const template=byKey['client-order-unknown'].query('INSTANCE').filter(n=>n.name==='Read status only').first();
async function button(parent,label,actions,width){const found=parent.query('INSTANCE').filter(n=>n.name==='Linked client / '+label).first();if(found){await reactions(found,[{trigger:{type:'ON_CLICK'},actions}]);return found;}const b=template.clone();parent.appendChild(b);remember(b);b.name='Linked client / '+label;b.resize(width||Math.min(parent.width,400),48);const t=b.query('TEXT').first();txt(t,label);await reactions(b,[{trigger:{type:'ON_CLICK'},actions}]);changed.add(parent.id);return b;}
function fundActions(kind){
 const robin=kind==='partial'||kind==='late';
 const late=kind==='late';
 return [set('previewKind',kind),set('original',false),set('linked',true),set('clientLabel',robin?'Demo Robin · U-DEMO-005':'Demo Noor · U-DEMO-002'),set('meta',robin?'S-DEMO-005 · ORD-005 · T-102 · Limitless':'S-DEMO-002 · ORD-002 · T-101 · Polymarket'),set('messageMeta',robin?'T-102-M1 · S-DEMO-005 · Limitless':'T-101-M1 · S-DEMO-002 · Polymarket'),
 set('statusRu',robin?(late?'Позднее исполнение':'Частичное исполнение'):'Проверяем результат заявки'),set('statusEn',robin?(late?'Late fill':'Partial fill'):'Checking the order outcome'),
 set('fundsRu',robin?(late?'Бюджет 200 $. Доступно 160 $. Исполнено 12 $ из 20 $: сначала 8 $, затем 4 $. В резерве 8 $. Учётная стоимость позиций 32 $.':'Бюджет 200 $. Доступно 160 $. Исполнено 8 $ из 20 $. В резерве 12 $. Учётная стоимость позиций 28 $.'):'Бюджет 200 $. Доступно 160 $. В резерве 20 $. Учётная стоимость позиций 20 $. Исполнение заявки 20 $ пока не подтверждено.'),
 set('fundsEn',robin?(late?'Budget $200. Available $160. $12 of $20 filled: first $8, then $4. Reserved $8. Position cost basis $32.':'Budget $200. Available $160. $8 of $20 filled. Reserved $12. Position cost basis $28.'):'Budget $200. Available $160. Reserved $20. Position cost basis $20. The $20 order fill is not confirmed yet.')];
}
const isRobin=ex('OR',eq(V.previewKind,'partial'),eq(V.previewKind,'late'));
const prepare=key=>[set('returnKey',key),when(isRobin,[set('replySent',ref('VariableID:4059:215','BOOLEAN')),set('noReply',ex('NOT',ref('VariableID:4059:215','BOOLEAN'))),when(eq('VariableID:4182:1048','published'),[set('robinVipPublished',true),set('robinVipRu',ref('VariableID:4182:1053')),set('robinVipEn',ref('VariableID:4182:1054'))]),set('vipRu',ref(V.robinVipRu)),set('vipEn',ref(V.robinVipEn))],[set('replySent',ref('VariableID:4059:179','BOOLEAN')),set('noReply',ex('NOT',ref('VariableID:4059:179','BOOLEAN'))),when(eq('VariableID:4182:1026','published'),[set('vipPublished',true),set('noorVipRu',ref('VariableID:4182:1031')),set('noorVipEn',ref('VariableID:4182:1032'))]),set('vipRu',ref(V.noorVipRu)),set('vipEn',ref(V.noorVipEn))])];
const orderDest=[when(isRobin,[...prepare('client-order-late'),nav(byKey['client-order-late'].id)],[...fundActions('unknown'),...prepare('client-order-unknown'),nav(byKey['client-order-unknown'].id)])];

for(const row of DATA.records){
 const root=roots.get(row.id),copy=COPY.find(x=>x.key===row.key),index=DATA.en?1:0;
 for(const t of root.query('TEXT')){
  if(t.name==='Page title')txt(t,copy.title[index]);
  else if(t.name==='prop:Body')txt(t,copy.body[index]);
  else if(t.name==='prop:Value')txt(t,copy.details[1][index]);
  else if(t.name==='prop:Hint')txt(t,copy.identity[index]);
 }
 root.name=DATA.locale+' · '+row.key+' · '+copy.title[index];changed.add(root.id);
}
const homeName=DATA.locale+' · linked-client-home';
let home=p.children.find(n=>n.name===homeName);
if(!home){home=byKey['client-order-unknown'].clone();p.appendChild(home);remember(home);home.name=homeName;home.x=byKey['client-order-unknown'].x;home.y=Math.max(...p.children.filter(n=>n.id!==home.id).map(n=>n.y+n.height))+160;}
const homeHost=host(home);if(!homeHost)throw Error('Missing client home content host');
for(const t of home.query('TEXT')){if(t.name==='Page title')txt(t,DATA.en?'Home':'Главная');else if(t.name==='prop:Body')bind(t,V[DATA.en?'statusEn':'statusRu']);else if(t.name==='Page title')bind(t,V[DATA.en?'statusEn':'statusRu']);else if(t.name==='prop:Value')bind(t,V[DATA.en?'fundsEn':'fundsRu']);else if(t.name==='prop:Hint')bind(t,V.meta);}
const routes={...DATA.sources,linked:home.id};
for(const row of DATA.records)routes[row.key]=row.id;
const back=[{type:'CONDITIONAL',conditionalBlocks:[...Object.entries(routes).map(([key,id])=>({condition:eq(V.returnKey,key),actions:[nav(id)]})),{actions:[nav(DATA.sources.active)]}]}];
const homeActions=[when(ref(V.original,'BOOLEAN'),[when(eq(V.previewKind,'original-paused'),[nav(DATA.sources.paused)],[when(eq(V.previewKind,'original-resumed'),[nav(DATA.sources.resumed)],[nav(DATA.sources.active)])])],[nav(home.id)])];
for(const [key,id]of Object.entries(DATA.aux)){
 const root=roots.get(id),h=host(root);if(!h)throw Error('Missing auxiliary host '+id);for(const b of root.query('INSTANCE').filter(n=>n.name.startsWith('Linked client / '))){if(b.parent!==h){h.appendChild(b);changed.add(b.id);changed.add(h.id);}}
 if(!root.query('INSTANCE').filter(n=>n.name==='Linked client / '+(DATA.en?'Back to session':'Вернуться к сессии')).length){const b=await button(h,DATA.en?'Back to session':'Вернуться к сессии',back);h.insertChild(0,b);}
 for(const t of root.query('TEXT'))if(t.name==='Identity explanation')bind(t,V.clientLabel);
 for(const n of root.query('FRAME,INSTANCE'))if(/Nav\/home|Bottom.*home/i.test(n.name)&&'setReactionsAsync'in n){await reactions(n,[{trigger:{type:'ON_CLICK'},actions:homeActions}]);changed.add(n.id);}
 if(key==='notifications'){
  for(const n of root.query('INSTANCE'))if(/Item \/ notification/.test(n.name)){n.setBoundVariable('visible',{type:'VARIABLE_ALIAS',id:V.original});changed.add(n.id);}
  for(const [label,dest]of [[DATA.en?'Original order':'Исходная заявка',byKey['client-order-unknown'].id],[DATA.en?'Support · T-101':'Поддержка · T-101',byKey['client-support-reply'].id]])if(!root.query('INSTANCE').filter(n=>n.name==='Linked client / '+label).length){const b=await button(h,label,dest===byKey['client-order-unknown'].id?orderDest:[...prepare('client-support-reply'),nav(dest)]);b.setBoundVariable('visible',{type:'VARIABLE_ALIAS',id:V.linked});h.insertChild(1,b);}
 }
 if(key==='help')for(const t of root.query('TEXT'))if(t.characters===(DATA.en?'My conversations':'Мои обращения')){const n=t.parent;if('setReactionsAsync'in n){await reactions(n,[{trigger:{type:'ON_CLICK'},actions:[...prepare('client-support-reply'),nav(byKey['client-support-reply'].id)]}]);changed.add(n.id);}}
}
// Preserve original authentication decisions; only record the caller before opening shared utilities.
for(const [key,id]of Object.entries(DATA.sources)){
 const root=roots.get(id);if(!root)continue;
 for(const n of root.query('FRAME,INSTANCE'))if(/^(Button\/Help|Button\/Notifications|Button\/Profile avatar|Profile \/ Open account)$/.test(n.name)){
  const target=/Help$/.test(n.name)?DATA.aux.help:/Notifications$/.test(n.name)?DATA.aux.notifications:DATA.aux.profile;
  await reactions(n,[{trigger:{type:'ON_CLICK'},actions:[set('returnKey',key),set('original',true),set('linked',false),set('clientLabel',DATA.en?'Current demo session':'Текущая демо-сессия'),...(['active','paused','resumed'].includes(key)?[set('previewKind','original-'+key)]:[]),nav(target)]}]);changed.add(n.id);
 }
 if(['active','paused','resumed'].includes(key)){const h=host(root);if(h)for(const b of root.query('INSTANCE').filter(n=>n.name==='Linked client / '+(DATA.en?'Open shared Noor example':'Открыть связанный пример Noor'))){if(b.parent!==h){h.appendChild(b);changed.add(b.id);changed.add(h.id);}}if(h&&!root.query('INSTANCE').filter(n=>n.name==='Linked client / '+(DATA.en?'Open shared Noor example':'Открыть связанный пример Noor')).length)await button(h,DATA.en?'Open shared Noor example':'Открыть связанный пример Noor',[...prepare('linked'),...fundActions('unknown'),nav(home.id)]);}
}
const contextual=[home,...DATA.records.filter(x=>x.key!=='client-tech-down').map(x=>roots.get(x.id))];
for(const root of contextual){
 const h=host(root);if(!h)throw Error('Missing projection content host');
 const key=root.id===home.id?'linked':DATA.records.find(x=>x.id===root.id).key;
 if(root.id!==home.id&&!root.query('INSTANCE').filter(n=>n.name==='Linked client / '+(DATA.en?'Back to session':'К сессии')).length)await button(h,DATA.en?'Back to session':'К сессии',[nav(home.id)]);
 for(const [kind,label]of [['help',DATA.en?'Help':'Помощь'],['notifications',DATA.en?'Notifications':'Уведомления'],['profile',DATA.en?'Profile':'Профиль']])if(!root.query('INSTANCE').filter(n=>n.name==='Linked client / '+label).length)await button(h,label,[...prepare(key),...(key==='client-order-late'?[when(eq(V.previewKind,'partial'),fundActions('partial'),fundActions('late'))]:key==='linked'?[]:fundActions('unknown')),nav(DATA.aux[kind])]);
 const rx=JSON.parse(JSON.stringify(root.reactions||[])).filter(r=>r.trigger?.type!=='AFTER_TIMEOUT');
 rx.push({trigger:{type:'AFTER_TIMEOUT',timeout:0.1},actions:[...(key==='client-order-unknown'?fundActions('unknown'):['linked','client-support-reply','client-vip-terms'].includes(key)?[when(ex('NOT',isRobin),fundActions('unknown'))]:key==='client-order-late'?[when(eq(V.previewKind,'partial'),fundActions('partial'),fundActions('late'))]:[]),...prepare(key),when(locked,[nav(byKey['client-tech-down'].id)])]});await reactions(root,rx);changed.add(root.id);root.overflowDirection='VERTICAL';root.clipsContent=true;
}
for(const [label,dest]of [[DATA.en?'Order · ORD-002':'Заявка · ORD-002',byKey['client-order-unknown'].id],[DATA.en?'My terms':'Мои условия',byKey['client-vip-terms'].id],[DATA.en?'Support · T-101':'Поддержка · T-101',byKey['client-support-reply'].id]])if(!home.query('INSTANCE').filter(n=>n.name==='Linked client / '+label).length)await button(homeHost,label,dest===byKey['client-order-unknown'].id?orderDest:[...prepare('linked'),nav(dest)]);
const late=byKey['client-order-late'];for(const t of late.query('TEXT'))if(t.name==='Page title')bind(t,V[DATA.en?'statusEn':'statusRu']);else if(t.name==='prop:Value')bind(t,V[DATA.en?'fundsEn':'fundsRu']);else if(t.name==='prop:Hint')bind(t,V.meta);
const support=byKey['client-support-reply'],detail=support.query('INSTANCE').filter(n=>n.name==='Permitted client detail').first();detail.setBoundVariable('visible',{type:'VARIABLE_ALIAS',id:V.replySent});changed.add(detail.id);
for(const t of support.query('TEXT'))if(t.name==='Page title')txt(t,DATA.en?'Support':'Поддержка');else if(t.name==='prop:Body')bind(t,V.clientLabel);else if(t.name==='prop:Hint')bind(t,V.messageMeta);
const sh=host(support);if(!support.query('INSTANCE').filter(n=>n.name==='Linked client / '+(DATA.en?'No reply received yet · refresh':'Ответ пока не получен · обновить')).length){const b=await button(sh,DATA.en?'No reply received yet · refresh':'Ответ пока не получен · обновить',[...prepare('client-support-reply')]);b.setBoundVariable('visible',{type:'VARIABLE_ALIAS',id:V.noReply});}
const vip=byKey['client-vip-terms'];for(const t of vip.query('TEXT'))if(t.name==='prop:Value')bind(t,V[DATA.en?'vipEn':'vipRu']);
const tech=byKey['client-tech-down'];const refresh=tech.query('INSTANCE').filter(n=>n.name==='Read status only').first();await reactions(refresh,[{trigger:{type:'ON_CLICK'},actions:[when(ex('NOT',locked),[...prepare('linked'),nav(home.id)])]}]);changed.add(refresh.id);
const index=roots.get(DATA.index);
if(index){const buttons=index.query('INSTANCE').toArray();for(let i=0;i<DATA.records.length;i++){const b=buttons[i],row=DATA.records[i];if(!b)continue;const t=b.query('TEXT').first();if(t)txt(t,COPY.find(c=>c.key===row.key).title[DATA.en?1:0]);await reactions(b,[{trigger:{type:'ON_CLICK'},actions:[...fundActions(row.key==='client-order-late'?'late':'unknown'),...prepare(row.key),nav(row.id)]}]);changed.add(b.id);}}
// Refresh our existing controls as well as newly created controls on a safe retry.
for(const root of contextual){
 const key=root.id===home.id?'linked':DATA.records.find(x=>x.id===root.id).key;
 const h=host(root);
 for(const b of root.query('INSTANCE').filter(n=>n.name.startsWith('Linked client / '))){
  const name=b.name.slice('Linked client / '.length);
  let a=null;
  if(name===(DATA.en?'Help':'Помощь')||name===(DATA.en?'Notifications':'Уведомления')||name===(DATA.en?'Profile':'Профиль')){
   const dest=name===(DATA.en?'Help':'Помощь')?'help':name===(DATA.en?'Profile':'Профиль')?'profile':'notifications';
   const subject=key==='client-order-unknown'?fundActions('unknown'):key==='client-order-late'?[when(eq(V.previewKind,'partial'),fundActions('partial'),fundActions('late'))]:[];
   a=[...subject,...prepare(key),nav(DATA.aux[dest])];
  }
  if(name===(DATA.en?'Back to session':'К сессии'))a=[nav(home.id)];
  if(name===(DATA.en?'No reply received yet · refresh':'Ответ пока не получен · обновить'))a=prepare(key);
  if(a)await reactions(b,[{trigger:{type:'ON_CLICK'},actions:a}]);
  if(root.id===home.id&&['Order · ORD-002','Заявка · ORD-002','My terms','Мои условия','Support · T-101','Поддержка · T-101'].includes(name)){for(const x of [b,...b.query('*')])removed.add(x.id);b.remove();}
 }
 if(root.id===home.id)for(const [name,a]of [[DATA.en?'Original order':'Исходная заявка',orderDest],[DATA.en?'Your terms':'Ваши условия',[...prepare('linked'),nav(byKey['client-vip-terms'].id)]],[DATA.en?'Conversation':'Переписка',[...prepare('linked'),nav(byKey['client-support-reply'].id)]]])await button(h,name,a);
}
for(const [key,id]of Object.entries(DATA.aux)){
 const root=roots.get(id),h=host(root);
 for(const b of root.query('INSTANCE').filter(n=>n.name.startsWith('Linked client / '))){
  const name=b.name.slice('Linked client / '.length);
  if(name===(DATA.en?'Back to session':'Вернуться к сессии'))await reactions(b,[{trigger:{type:'ON_CLICK'},actions:back}]);
  else if(name===(DATA.en?'Original order':'Исходная заявка'))await reactions(b,[{trigger:{type:'ON_CLICK'},actions:orderDest}]);
  else if(['Support · T-101','Поддержка · T-101','Conversation','Переписка'].includes(name)){b.name='Linked client / '+(DATA.en?'Conversation':'Переписка');txt(b.query('TEXT').first(),DATA.en?'Conversation':'Переписка');await reactions(b,[{trigger:{type:'ON_CLICK'},actions:[...prepare('client-support-reply'),nav(byKey['client-support-reply'].id)]}]);}
 }
 if(key==='profile'&&!root.query('INSTANCE').filter(n=>n.name==='Linked client / '+(DATA.en?'Your terms':'Ваши условия')).length)await button(h,DATA.en?'Your terms':'Ваши условия',[...prepare('client-vip-terms'),nav(byKey['client-vip-terms'].id)]);
}
return {createdNodeIds:[...created].filter(id=>!removed.has(id)),mutatedNodeIds:[...changed],removedNodeIds:[...removed],page:DATA.page,home:home.id,routes,aux:DATA.aux};
