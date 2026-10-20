// Reuse one stale/loading/error view while preserving its original session page.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(CONFIG.pageId));await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const ru=CONFIG.locale==='ru',T=CONFIG.targets,collection=(await figma.variables.getLocalVariableCollectionsAsync()).find(c=>c.name==='Prototype demo state'),all=await figma.variables.getLocalVariablesAsync('STRING');
const origin=all.find(v=>v.name==='Admin lists/'+CONFIG.locale.toUpperCase()+'/origin/sessions');
const base=['S-DEMO-002 · U-DEMO-002','Polymarket',ru?'Последний снимок · результат заявки неизвестен · резерв $20':'Last snapshot · order result unknown · $20 reserved',ru?'Все площадки · Alpha / Paper · ID ↑ · страница 2 из 2. Новый результат ещё не получен.':'All venues · Alpha / Paper · ID ascending · page 2 of 2. New results have not arrived.'];
const V=[];for(let i=0;i<4;i++){const name='Admin lists/'+CONFIG.locale.toUpperCase()+'/session snapshot/'+i;let v=all.find(v=>v.name===name);if(!v){v=figma.variables.createVariable(name,collection,'STRING');v.setValueForMode(collection.defaultModeId,base[i]);}V.push(v);}
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null});const set=(v,value)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type:'STRING',resolvedType:'STRING',value}});const eq=value=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[{type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id:origin.id}},{type:'STRING',resolvedType:'STRING',value}]}});
const react=async(n,actions)=>n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions}]);
const returnActions=['sessions-page-1','sessions-page-2',''].map(key=>({type:'CONDITIONAL',conditionalBlocks:[{condition:eq(key),actions:[nav(T[key||'sessions-page-2'])]},{actions:[]}]}));const changed=[];
for(const [i,key] of ['sessions-page-1','sessions-page-2'].entries()){
 const root=await figma.getNodeByIdAsync(T[key]),main=root.children.find(n=>n.name==='Main'),bar=main.findOne(n=>n.name==='Scenario actions');const values=i===0?['S-DEMO-001 · U-DEMO-001','Limitless',ru?'Последний снимок · активна · нет позиций и заявок':'Last snapshot · active · no positions or orders',ru?'Все площадки · Alpha / Paper · ID ↑ · страница 1 из 2. Новый результат ещё не получен.':'All venues · Alpha / Paper · ID ascending · page 1 of 2. New results have not arrived.']:base;
 await react(bar.children[2],[set(origin,key),...V.map((v,i)=>set(v,values[i])),nav(T['sessions-stale'])]);changed.push(bar.children[2].id);
 await react(bar.children[1],[set(origin,i===0?'sessions-page-2':'sessions-page-1'),nav(T[i===0?'sessions-page-2':'sessions-page-1'])]);changed.push(bar.children[1].id);
}
for(const key of ['sessions-stale','sessions-loading','sessions-error','sessions-empty']){
 const root=await figma.getNodeByIdAsync(T[key]),main=root.children.find(n=>n.name==='Main'),bar=main.findOne(n=>n.name==='Scenario actions');await react(bar.children[0],returnActions);changed.push(bar.children[0].id);
 if(key!=='sessions-empty'){const context=main.findOne(n=>n.name==='Scenario context');const body=context.componentProperties['Body#1981:4'].value;context.findOne(n=>n.type==='TEXT'&&n.characters===body).setBoundVariable('characters',V[3]);changed.push(context.id);}
 if(key==='sessions-stale'){const row=main.findOne(n=>n.name==='Scenario records').children.filter(n=>n.type==='INSTANCE')[1];for(const [i,k]of ['Title#2137:0','Detail#2137:1','Meta#2137:2'].entries()){const value=row.componentProperties[k].value;row.findOne(n=>n.type==='TEXT'&&n.characters===value).setBoundVariable('characters',V[i]);}changed.push(row.id);}
}
// Baseline list entry clears a previous paged origin; it does not inherit it accidentally.
const legacy=await figma.getNodeByIdAsync(T.sessions),main=legacy.children.find(n=>/^Main/.test(n.name))||legacy;
for(const n of main.findAll(n=>'reactions'in n&&n.reactions.length)){const a=n.reactions.flatMap(r=>r.actions||[]);const target=a.find(a=>a.type==='NODE'&&[T.session,T['session-unknown']].includes(a.destinationId));if(target){await react(n,[set(origin,''),nav(target.destinationId)]);changed.push(n.id);}}
return {locale:CONFIG.locale,mutatedNodeIds:changed,projectionVariables:V.map(v=>({id:v.id,name:v.name})),origin:origin.id,returnActions};
