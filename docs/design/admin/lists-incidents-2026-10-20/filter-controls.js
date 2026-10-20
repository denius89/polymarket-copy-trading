// Native prototype-only state. CONFIG supplies locale, pageId and targets.
const page=await figma.getNodeByIdAsync(CONFIG.pageId);await figma.setCurrentPageAsync(page);
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const lang=CONFIG.locale,ru=lang==='ru',targets=CONFIG.targets;
const form=await figma.getNodeByIdAsync(targets['users-filter-form']);
const controls=form.findOne(n=>n.name==='Prepared form controls');
const fields=controls.children.flatMap(n=>n.children);
for(const row of controls.children)for(const field of row.children)field.layoutSizingHorizontal='FILL';
const collection=(await figma.variables.getLocalVariableCollectionsAsync()).find(c=>c.name==='Prototype demo state');
if(!collection)throw Error('Existing prototype collection missing');
const prefix='Admin lists/'+lang.toUpperCase()+'/';
const existing=(await figma.variables.getLocalVariablesAsync('STRING')).filter(v=>v.variableCollectionId===collection.id);
const choices=[['U-DEMO-002','Demo Noor','U-NOT-FOUND'],ru?['Все','Без VIP','С VIP']:['All','No VIP','VIP'],ru?['Все состояния','Требует внимания','Активен']:['All states','Needs attention','Active'],ru?['Все площадки','Polymarket','Limitless']:['All venues','Polymarket','Limitless'],ru?['За всё время','13–20.10.2026','20–13.10.2026 · ошибка']:['All time','13–20 Oct 2026','20–13 Oct 2026 · invalid']];
const defaults=[choices[0][0],choices[1][1],choices[2][1],choices[3][1],choices[4][0]],draft=[],applied=[];
for(const kind of ['draft','applied'])for(let i=0;i<5;i++){
 const name=prefix+kind+'/'+i;let v=existing.find(v=>v.name===name);if(!v){v=figma.variables.createVariable(name,collection,'STRING');v.setValueForMode(collection.defaultModeId,defaults[i]);}
 (kind==='draft'?draft:applied).push(v);
}
let prior=existing.find(v=>v.name===prefix+'prior selection');if(!prior){prior=figma.variables.createVariable(prefix+'prior selection',collection,'STRING');prior.setValueForMode(collection.defaultModeId,'users');}
const boolExisting=await figma.variables.getLocalVariablesAsync('BOOLEAN');let hasApplied=boolExisting.find(v=>v.name===prefix+'selection applied');if(!hasApplied){hasApplied=figma.variables.createVariable(prefix+'selection applied',collection,'BOOLEAN');hasApplied.setValueForMode(collection.defaultModeId,false);}
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null});
const set=(v,value)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type:'STRING',resolvedType:'STRING',value}});
const copy=(to,from)=>({type:'SET_VARIABLE',variableId:to.id,variableValue:{type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id:from.id}}});
const react=async(n,actions)=>{try{await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions}]);}catch(error){throw Error(n.id+' '+n.name+': '+error.message);}};
const templateOverlay=await figma.getNodeByIdAsync(ru?'2303:26697':'2305:53198');
const button=await figma.getNodeByIdAsync('3051:63842');
const menus=[],mutated=[];let x=Math.max(...page.children.map(n=>n.x+n.width))+200;
for(let i=0;i<5;i++){
 const name=lang.toUpperCase()+' · user-filter-menu-'+i;let overlay=page.children.find(n=>n.name===name);
 if(!overlay){overlay=templateOverlay.clone();page.appendChild(overlay);overlay.name=name;overlay.x=x;overlay.y=0;x+=1640;for(const c of [...overlay.children])c.remove();}
 overlay.resize(form.width,form.height);overlay.fills=[];
 if(!overlay.children.length){
  const dismiss=figma.createFrame();overlay.appendChild(dismiss);dismiss.name='Dismiss filter menu';dismiss.resize(overlay.width,overlay.height);dismiss.fills=[{type:'SOLID',color:{r:0,g:0,b:0},opacity:0.001}];await react(dismiss,[{type:'CLOSE'}]);
  const panel=figma.createAutoLayout('VERTICAL');overlay.appendChild(panel);panel.name='Filter options';panel.resize(fields[i].width,100);panel.layoutSizingVertical='HUG';panel.paddingTop=12;panel.paddingBottom=12;panel.paddingLeft=12;panel.paddingRight=12;panel.setBoundVariable('itemSpacing',await figma.variables.getVariableByIdAsync('VariableID:2:52'));
  const color=await figma.variables.getVariableByIdAsync('VariableID:2:29');panel.fills=[figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:0,g:0,b:0}},'color',color)];panel.cornerRadius=12;
  panel.x=Math.min(fields[i].absoluteTransform[0][2]-form.x,form.width-panel.width-32);panel.y=fields[i].absoluteTransform[1][2]-form.y+64;
  const label=fields[i].findOne(n=>n.type==='TEXT'&&n.name==='Label').clone();panel.appendChild(label);label.name='Menu title';
  for(const value of choices[i]){const b=button.clone();panel.appendChild(b);b.name='Select filter · '+i+' · '+value;b.setProperties({'Label#113:1':value});b.layoutSizingHorizontal='FILL';await react(b,[set(draft[i],value),{type:'CLOSE'}]);}
  const cancel=button.clone();panel.appendChild(cancel);cancel.name='Cancel filter choice';cancel.setProperties({'Label#113:1':ru?'Отмена':'Cancel'});cancel.layoutSizingHorizontal='FILL';await react(cancel,[{type:'CLOSE'}]);
 }
 const value=fields[i].findOne(n=>n.type==='TEXT'&&n.name==='Value');value.setBoundVariable('characters',draft[i]);
 await react(fields[i],[{type:'NODE',destinationId:overlay.id,navigation:'OVERLAY',transition:null}]);
 menus.push({id:overlay.id,key:'user-filter-menu-'+i,field:fields[i].id,options:choices[i],variableId:draft[i].id,appliedVariableId:applied[i].id});mutated.push(fields[i].id,value.id);
}
const eq=(v,value)=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[{type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id:v.id}},{type:'STRING',resolvedType:'STRING',value}]}});
const bools=await figma.variables.getLocalVariablesAsync('BOOLEAN'),B={};
for(const key of ['valid','query','vip','state','venue','period','m1','m2','m3','match','notMatch','success','empty','invalid']){const name=prefix+'computed/'+key;let v=bools.find(v=>v.name===name);if(!v){v=figma.variables.createVariable(name,collection,'BOOLEAN');v.setValueForMode(collection.defaultModeId,true);}B[key]=v;}
const aliasB=v=>({type:'VARIABLE_ALIAS',resolvedType:'BOOLEAN',value:{type:'VARIABLE_ALIAS',id:v.id}});
const setExpr=(v,fn,args)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:fn,expressionArguments:args}}});
const compare=(v,fn,value)=>setExpr(v,fn,[{type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id:value[0].id}},{type:'STRING',resolvedType:'STRING',value:value[1]}]);
const compute=values=>[
 compare(B.valid,'NOT_EQUAL',[values[4],choices[4][2]]),compare(B.query,'NOT_EQUAL',[values[0],choices[0][2]]),compare(B.vip,'NOT_EQUAL',[values[1],choices[1][2]]),compare(B.state,'NOT_EQUAL',[values[2],choices[2][2]]),compare(B.venue,'NOT_EQUAL',[values[3],choices[3][2]]),compare(B.period,'EQUALS',[values[4],choices[4][0]]),
 setExpr(B.m1,'AND',[aliasB(B.query),aliasB(B.vip)]),setExpr(B.m2,'AND',[aliasB(B.m1),aliasB(B.state)]),setExpr(B.m3,'AND',[aliasB(B.m2),aliasB(B.venue)]),setExpr(B.match,'AND',[aliasB(B.m3),aliasB(B.period)]),
 setExpr(B.notMatch,'EQUALS',[aliasB(B.match),{type:'BOOLEAN',resolvedType:'BOOLEAN',value:false}]),setExpr(B.success,'AND',[aliasB(B.valid),aliasB(B.match)]),setExpr(B.empty,'AND',[aliasB(B.valid),aliasB(B.notMatch)]),setExpr(B.invalid,'EQUALS',[aliasB(B.valid),{type:'BOOLEAN',resolvedType:'BOOLEAN',value:false}])];
const when=(variable,yes,no=[])=>({type:'CONDITIONAL',conditionalBlocks:[{condition:aliasB(variable),actions:yes},{actions:no}]});
const copies=applied.map((v,i)=>copy(v,draft[i]));const markApplied={type:'SET_VARIABLE',variableId:hasApplied.id,variableValue:{type:'BOOLEAN',resolvedType:'BOOLEAN',value:true}},clearApplied={type:'SET_VARIABLE',variableId:hasApplied.id,variableValue:{type:'BOOLEAN',resolvedType:'BOOLEAN',value:false}};
const applyActions=[...compute(draft),when(B.invalid,[nav(targets['users-period-invalid'])]),when(B.success,[...copies,markApplied,set(prior,'users-filter-result'),nav(targets['users-filter-result'])]),when(B.empty,[...copies,markApplied,set(prior,'users-current-empty'),nav(targets['users-current-empty'])])];
const previousActions=['users','users-filter-result','users-current-empty','users-current-stale','users-filter-loading','users-filter-error'].map(key=>({type:'CONDITIONAL',conditionalBlocks:[{condition:eq(prior,key),actions:[nav(targets[key])]},{actions:[]}]}));
const bar=form.findOne(n=>n.name==='Scenario actions');bar.children[0].setProperties({'Label#113:1':ru?'Применить отбор':'Apply filters'});await react(bar.children[0],applyActions);
let cancel=bar.children.find(n=>n.name==='Cancel draft filters');if(!cancel){cancel=button.clone();bar.appendChild(cancel);cancel.name='Cancel draft filters';}cancel.setProperties({'Label#113:1':ru?'Отмена изменений':'Cancel changes'});await react(cancel,[...draft.map((v,i)=>copy(v,applied[i])),...previousActions]);
const invalidRoot=await figma.getNodeByIdAsync(targets['users-period-invalid']);const invalidBar=invalidRoot.findOne(n=>n.name==='Scenario actions');await react(invalidBar.children[1],previousActions);await react(invalidBar.children[0],[set(draft[4],choices[4][2]),nav(targets['users-filter-form'])]);
await react(bar.children[1],[...draft.map((v,i)=>set(v,defaults[i])),...applied.map((v,i)=>set(v,defaults[i])),clearApplied,set(prior,'users'),nav(targets.users)]);
const ctx=form.findOne(n=>n.name==='Scenario context');ctx.setProperties({'Body#1981:4':ru?'Раскройте поле и выберите значение. Поиск предлагает три учебных запроса; произвольный текст не вводится. Выбранные параметры применяются вместе. Период относится к последней активности; неизвестная дата не считается попаданием в период.':'Open a field and choose a value. Search offers three synthetic queries; free text is not entered. Values are applied together. Period filters last activity; an unknown date does not match a bounded period.'});
for(const key of ['users-filter-result','users-current-empty','users-current-stale','users-filter-loading','users-filter-error']){
 const root=await figma.getNodeByIdAsync(targets[key]),main=root.children.find(n=>n.name==='Main');let display=main.children.find(n=>n.name==='Applied filter values');if(!display){display=controls.clone();display.name='Applied filter values';main.insertChild(main.children.findIndex(n=>n.name==='Scenario records'),display);display.layoutSizingHorizontal='FILL';}
 const fs=display.children.flatMap(n=>n.children);for(let i=0;i<fs.length;i++){await fs[i].setReactionsAsync([]);for(const icon of fs[i].findAllWithCriteria({types:['INSTANCE']})){const mc=await icon.getMainComponentAsync();if(mc&&/Icon|Search|Chevron/.test(mc.name+' '+(mc.parent?.name||'')))icon.visible=false;}fs[i].findOne(n=>n.type==='TEXT'&&n.name==='Value').setBoundVariable('characters',applied[i]);}
 const context=main.children.find(n=>n.name==='Scenario context');context.setProperties({'Body#1981:4':ru?(key==='users-current-stale'?'Прежний подтверждённый снимок. Значения ниже — применённый отбор. Обновление не очищает параметры.':key==='users-current-empty'?'Совпадений не найдено. Если отбор уже применён, его параметры сохранены. Измените отбор или сбросьте его.':'Значения ниже — применённый отбор; страница 1. Возврат из карточки и повторное чтение сохраняют эти параметры.'):(key==='users-current-stale'?'Prior confirmed snapshot. Applied filters are shown below. Refresh does not clear them.':key==='users-current-empty'?'No matches found. Applied values are retained when a selection exists. Edit or reset the filters.':'Applied values shown below; page 1. Card return and retries retain these values.')});
 if(key==='users-current-empty'){display.setBoundVariable('visible',hasApplied);}
 for(const b of main.findAll(n=>'reactions'in n&&n.reactions.some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.destinationId===targets['users-filter-form']))))await react(b,[set(prior,key),...draft.map((v,i)=>copy(v,applied[i])),nav(targets['users-filter-form'])]);
 main.layoutSizingVertical='HUG';root.resize(root.width,Math.max(1120,main.y+main.height+32));mutated.push(root.id);
}
const original=await figma.getNodeByIdAsync(targets.users);for(const n of original.findAll(n=>'reactions'in n&&n.reactions.some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.destinationId===targets['users-filter-form']))))await react(n,[clearApplied,set(prior,'users'),nav(targets['users-filter-form'])]);
return {priorSelection:{id:prior.id,name:prior.name},hasApplied:{id:hasApplied.id,name:hasApplied.name},previousActions,cancelReactions:bar.findOne(n=>n.name==='Cancel draft filters').reactions,locale:lang,menus,variables:{draft:draft.map(v=>({id:v.id,name:v.name})),applied:applied.map(v=>({id:v.id,name:v.name}))},mutatedNodeIds:mutated,formId:form.id,applyReactions:bar.children[0].reactions};
