// Scoped prototype wiring; not a product router or complete Figma backup.
for(const s of CONFIG.specs)for(const a of s.actions)if(a.target!=='@back'&&!CONFIG.targets[a.target])throw Error('Preflight missing '+a.target);
const page=await figma.getNodeByIdAsync(CONFIG.pageId);await figma.setCurrentPageAsync(page);
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const ru=CONFIG.locale==='ru',T=CONFIG.targets,proof=[],changed=[],created=[];
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null});
const react=async(n,a)=>{await n.setReactionsAsync(a.length?[{trigger:{type:'ON_CLICK'},actions:a}]:[]);changed.push(n.id);};
const rootMain=root=>root.children.find(n=>/^Main/.test(n.name));
const button=await figma.getNodeByIdAsync('3051:63842');
const add=async(rootId,key,label,actions)=>{const root=await figma.getNodeByIdAsync(rootId),main=rootMain(root);let bar=main.children.find(n=>n.name==='List continuity actions');if(!bar){bar=figma.createAutoLayout('HORIZONTAL');main.appendChild(bar);bar.name='List continuity actions';bar.fills=[];bar.layoutSizingHorizontal='FILL';bar.setBoundVariable('itemSpacing',await figma.variables.getVariableByIdAsync('VariableID:2:56'));created.push(bar.id);}let b=bar.children.find(n=>n.name===key);if(!b){b=button.clone();bar.appendChild(b);b.name=key;created.push(b.id);}b.setProperties({'Label#113:1':label});await react(b,actions);main.layoutSizingVertical='HUG';root.resize(root.width,Math.max(root.height,main.y+main.height+32));return b;};
const collection=(await figma.variables.getLocalVariableCollectionsAsync()).find(c=>c.name==='Prototype demo state');
const vars=await figma.variables.getLocalVariablesAsync('STRING');const origin={};
for(const kind of ['sessions','reconciliation','support']){const name='Admin lists/'+CONFIG.locale.toUpperCase()+'/origin/'+kind;let v=vars.find(v=>v.name===name);if(!v){v=figma.variables.createVariable(name,collection,'STRING');v.setValueForMode(collection.defaultModeId,'');}origin[kind]=v;}
const setOrigin=(kind,key)=>({type:'SET_VARIABLE',variableId:origin[kind].id,variableValue:{type:'STRING',resolvedType:'STRING',value:key}});
const eq=(v,value)=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[{type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id:v.id}},{type:'STRING',resolvedType:'STRING',value}]}});
const returnOrigin=(kind,keys,fallback)=>[...keys.map(key=>({type:'CONDITIONAL',conditionalBlocks:[{condition:eq(origin[kind],key),actions:[nav(T[key])]},{actions:[]}]})),{type:'CONDITIONAL',conditionalBlocks:[{condition:eq(origin[kind],''),actions:[nav(T[fallback])]},{actions:[]}]}];
for(const item of CONFIG.roots){
 const spec=CONFIG.specs.find(s=>s.key===item.key),root=await figma.getNodeByIdAsync(item.id),main=rootMain(root),bar=main.children.find(n=>n.name==='Scenario actions');
 for(let i=0;i<spec.actions.length;i++){const a=spec.actions[i];if(!T[a.target]&&a.target!=='@back')throw Error('Missing '+a.target);bar.children[i].setProperties({'Label#113:1':a.label[CONFIG.locale]});await react(bar.children[i],[a.target==='@back'?{type:'BACK'}:nav(T[a.target])]);}
 const sectionTarget=spec.section==='ADM-03'?'sessions-page-1':spec.section==='ADM-05'?'reconciliation-selected':spec.section==='ADM-09'?'support-page2':spec.section==='ADM-04'?(item.key.includes('feed-closed')||item.key==='incident-feed-conflict'?'incident-feed-closed-queue':item.key.startsWith('incident-order')?'incident-reopened-queue':'ops-queue'):'users-filter-form';
 const crumb=main.children.find(n=>n.name==='Breadcrumb trail');const sectionKey=Object.keys(crumb.componentProperties).find(k=>k.startsWith('Section#'));const homeKey=Object.keys(crumb.componentProperties).find(k=>k.startsWith('Home#'));
 for(const text of crumb.findAllWithCriteria({types:['TEXT']})){
  if(text.characters===crumb.componentProperties[sectionKey].value)await react(text,T[sectionTarget]===root.id?[]:[nav(T[sectionTarget])]);
  else if(text.characters===crumb.componentProperties[homeKey].value)await react(text,[nav(T[spec.role==='ops'?'role-operations-overview':'overview'])]);
 }
 const rows=main.children.find(n=>n.name==='Scenario records').children.filter(n=>n.type==='INSTANCE').slice(1);
 if(item.key==='sessions-page-1'||item.key==='sessions-page-2'){const target=item.key==='sessions-page-1'?'session':'session-unknown';await react(rows[0],[setOrigin('sessions',item.key),nav(T[target])]);await react(bar.children[0],[setOrigin('sessions',item.key),nav(T[target])]);}
 if(item.key==='reconciliation-selected'){await react(rows[0],[setOrigin('reconciliation',item.key),nav(T['ops-case'])]);await react(bar.children[0],[setOrigin('reconciliation',item.key),nav(T['ops-case'])]);}
 // Role-specific navigation preserves the current closed feed snapshot.
 if(spec.role==='ops')for(const n of root.children[0].findAll(n=>'reactions'in n&&n.reactions.length)){
  const a=n.reactions.flatMap(r=>r.actions||[]);if(a.some(a=>a.type==='NODE'&&a.destinationId===T['ops-queue'])&&sectionTarget==='incident-feed-closed-queue')await react(n,T[sectionTarget]===root.id?[]:[nav(T[sectionTarget])]);
 }
 proof.push({key:item.key,id:root.id,role:spec.role,sectionTarget:T[sectionTarget],actions:bar.children.map(n=>({id:n.id,label:Object.values(n.componentProperties||{}).find(p=>p.type==='TEXT')?.value,reactions:n.reactions}))});
}
// Discoverable entries in the existing screens, no replacement pages.
await add(T.sessions,'Open paged session list',ru?'Страницы и актуальность':'Pages and freshness',[nav(T['sessions-page-1'])]);
await add(T['users-filter-result'],'Open stale user selection',ru?'Устаревший снимок · пример':'Stale snapshot · example',[nav(T['users-current-stale'])]);
await add(T['ops-cases'],'Open scoped reconciliation list',ru?'Отбор и актуальность':'Filters and freshness',[nav(T['reconciliation-selected'])]);
await add(T['incident-reopened'],'Closure blocker example',ru?'Проверить закрытие':'Check closure',[nav(T['incident-order-close-blocked'])]);
await add(T['incident-reopened'],'Closure conflict example',ru?'Конфликт закрытия · пример':'Closure conflict · example',[nav(T['incident-order-close-conflict'])]);
for(const key of ['session','session-unknown']){
 const r=await figma.getNodeByIdAsync(T[key]);await add(r.id,'Back to session selection',ru?'К исходной странице сессий':'Back to original session page',returnOrigin('sessions',['sessions-page-1','sessions-page-2'],'sessions'));
}
const caseRoot=await figma.getNodeByIdAsync(T['ops-case']);await add(caseRoot.id,'Back to reconciliation selection',ru?'К исходной выборке сверки':'Back to original reconciliation selection',returnOrigin('reconciliation',['reconciliation-selected'],'ops-cases'));
for(const n of rootMain(caseRoot).findAll(n=>'reactions'in n&&n.reactions.some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.destinationId===T['ops-cases']))))await react(n,returnOrigin('reconciliation',['reconciliation-selected'],'ops-cases'));
// Feed incident is a distinct case, not a connection details alias.
for(const key of ['ops-queue','ops-filtered']){const r=await figma.getNodeByIdAsync(T[key]);for(const n of rootMain(r).findAll(n=>'reactions'in n&&n.reactions.some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.destinationId===T['ops-connection-ll']))))await react(n,[nav(T['incident-feed-detail'])]);}
// Support refresh stays on its own selection; page 2 entries retain ticket identity.
for(const key of ['support','support-filtered','support-page2']){
 const r=await figma.getNodeByIdAsync(T[key]),main=rootMain(r);
 for(const n of main.findAll(n=>n.type==='INSTANCE'&&n.name==='Admin/Support ticket row')){
  const texts=n.findAllWithCriteria({types:['TEXT']}).map(t=>t.characters).join(' ');const destination=texts.includes('TKT-1060')?T['support-page2-1060']:texts.includes('TKT-1027')?T['support-page2-1027']:null;
  if(destination)await react(n,[setOrigin('support',key),nav(destination)]);
  else if(n.reactions.length)await react(n,[setOrigin('support',key),...n.reactions[0].actions]);
 }
 for(const n of main.findAll(n=>n.type==='INSTANCE'&&n.reactions.length)){
  const labels=Object.values(n.componentProperties||{}).filter(p=>p.type==='TEXT').map(p=>p.value);
  if(labels.includes(ru?'Обновить':'Refresh'))await react(n,[setOrigin('support',key),nav(T['support-refresh-loading'])]);
 }
}
const supportDetail=await figma.getNodeByIdAsync(T['support-ticket']);
if(supportDetail)for(const n of rootMain(supportDetail).findAll(n=>'reactions'in n&&n.reactions.some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.destinationId===T.support))))await react(n,returnOrigin('support',['support-filtered','support-page2','support'],'support'));
const loading=await figma.getNodeByIdAsync(T['support-refresh-loading']);await react(rootMain(loading).findOne(n=>n.name==='Scenario actions').children[0],returnOrigin('support',['support-filtered','support-page2','support'],'support'));
const err=await figma.getNodeByIdAsync(T['support-load-error']);for(const n of rootMain(err).findAll(n=>'reactions'in n&&n.reactions.some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.destinationId===T.support))))await react(n,returnOrigin('support',['support-filtered','support-page2','support'],'support'));
return {locale:CONFIG.locale,createdNodeIds:created,mutatedNodeIds:[...new Set(changed)],proof,originVariables:Object.fromEntries(Object.entries(origin).map(([k,v])=>[k,{id:v.id,name:v.name}]))};
