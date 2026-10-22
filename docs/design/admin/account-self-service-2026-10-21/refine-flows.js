await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));figma.skipInvisibleInstanceChildren=false;
const created=[],mutated=[],removed=[],proof=[];const col=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:134:180');const variables=await figma.variables.getLocalVariablesAsync();
const lit=(type,value)=>({type,resolvedType:type,value});const set=(id,type,value)=>({type:'SET_VARIABLE',variableId:id,variableValue:lit(type,value)});
const track=n=>{created.push(n.id);return n;};
function prop(n,values){const p={};for(const [key,value]of Object.entries(values)){const k=Object.keys(n.componentProperties).find(k=>k.split('#')[0]===key);if(k)p[k]=value;}n.setProperties(p);mutated.push(n.id);}
function makeRow(parent,name){const n=track(figma.createAutoLayout('HORIZONTAL',{name,itemSpacing:12}));parent.appendChild(n);n.fills=[];n.resize(parent.width,44);n.primaryAxisSizingMode='FIXED';n.counterAxisSizingMode='AUTO';n.layoutWrap='WRAP';n.counterAxisSpacing=12;return n;}
function actionButton(n){return n.type==='INSTANCE'&&Object.keys(n.componentProperties).some(k=>k.split('#')[0]==='Show icon');}
function label(n){return n.type==='INSTANCE'?Object.entries(n.componentProperties).find(([k])=>k.split('#')[0]==='Label')?.[1].value:'';}
for(const item of GROUP){
 const root=await figma.getNodeByIdAsync(item.id);const fs=new Map();for(const t of root.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fs.set(JSON.stringify(s.fontName),s.fontName);for(const f of fs.values())await figma.loadFontAsync(f);
 const en=item.locale==='en',V=item.variables,can={};for(const k of ['can end all','can end 1','can end 2']){const name='Admin self/'+item.staffId+'/'+k;let v=variables.find(v=>v.name===name);if(!v){v=figma.variables.createVariable(name,col,'BOOLEAN');v.scopes=['ALL_SCOPES'];v.setValueForMode(col.defaultModeId,true);variables.push(v);created.push(v.id);}can[k]=v;}
 for(const v of item.views){const p=await figma.getNodeByIdAsync(v.id);if(p.children.some(n=>n.name==='Account action row'))continue;
  if(v.name==='t0'){
   let fields=p.children.filter(c=>c.type==='INSTANCE'&&c.name==='Admin/Form field/v0.1');
   if(fields.length===4){for(let i=0;i<2;i++){const metadata=fields[i*2],status=fields[i*2+1];prop(status,{Label:item.staffId+'-SELF-0'+(i+2)+' · '+(i===0?'Chrome / Windows':'Safari / iOS'),Hint:en?'Last active: today, 11:42 UTC · demo data':'Последняя активность: сегодня, 11:42 UTC · учебные данные'});removed.push(metadata.id);metadata.remove();}}
   fields=p.children.filter(c=>c.type==='INSTANCE'&&c.name==='Admin/Form field/v0.1');const buttons=p.children.filter(actionButton);
   for(let i=0;i<2;i++){const b=buttons[i];b.setBoundVariable('visible',can['can end '+(i+1)]);mutated.push(b.id);const row=makeRow(p,'Own session row '+(i+1));p.insertChild(p.children.indexOf(fields[i]),row);row.appendChild(fields[i]);row.appendChild(b);mutated.push(fields[i].id,b.id);}
   buttons[2].setBoundVariable('visible',can['can end all']);mutated.push(buttons[2].id);
  }else{let buttons=p.children.filter(actionButton);if(buttons.length){if(['p1','pError'].includes(v.name)){const helpers=makeRow(p,'Account form helpers');for(const b of buttons.slice(0,2)){helpers.appendChild(b);mutated.push(b.id);}buttons=buttons.slice(2);}const row=makeRow(p,'Account action row');for(const b of buttons){row.appendChild(b);mutated.push(b.id);}}}
  if(['tOne','tTwo','tAll'].includes(v.name)){
   const which=v.name==='tOne'?1:v.name==='tTwo'?2:0,items=which?[which]:[1,2];
   const bs=p.findAllWithCriteria({types:['INSTANCE']}).filter(actionButton);
   const confirm=bs.find(b=>label(b)===(en?'End selected sessions':'Завершить выбранные сессии'));
   const unknown=bs.find(b=>label(b)===(en?'No confirmation · example':'Нет подтверждения · пример'));
   const old=confirm.reactions.find(r=>r.trigger?.type==='ON_CLICK').actions;
   await confirm.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[...items.map(i=>set(can['can end '+i].id,'BOOLEAN',false)),...(which?[]:[set(can['can end all'].id,'BOOLEAN',false)]),...old]}]);
   const changes=[set(can['can end all'].id,'BOOLEAN',false),...items.flatMap(i=>[set(can['can end '+i].id,'BOOLEAN',false),set(V['session '+i+' ru'],'STRING','Результат неизвестен'),set(V['session '+i+' en'],'STRING','Result unknown')])];
   await unknown.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[...changes,...unknown.reactions.find(r=>r.trigger?.type==='ON_CLICK').actions]}]);mutated.push(confirm.id,unknown.id);
  }
  // A confirmed security/email mutation also disables termination of already-ended sessions.
  for(const b of p.findAllWithCriteria({types:['INSTANCE']}).filter(actionButton)){
   const r=b.reactions.find(r=>r.trigger?.type==='ON_CLICK');if(!r?.actions)continue;
   function hasEnd(actions){return actions.some(a=>a.type==='SET_VARIABLE'&&a.variableId===V['session 1 active']&&a.variableValue?.value===false||a.type==='CONDITIONAL'&&a.conditionalBlocks.some(c=>hasEnd(c.actions)));}
   if(hasEnd(r.actions)&&!['tOne','tTwo'].includes(v.name)){function add(actions){return actions.flatMap(a=>a.type==='CONDITIONAL'?[{...a,conditionalBlocks:a.conditionalBlocks.map(c=>({...c,actions:add(c.actions)}))}]:a.type==='SET_VARIABLE'&&a.variableId===V['session 1 active']&&a.variableValue?.value===false?[set(can['can end all'].id,'BOOLEAN',false),set(can['can end 1'].id,'BOOLEAN',false),set(can['can end 2'].id,'BOOLEAN',false),a]:[a]);}await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:add(r.actions)}]);mutated.push(b.id);}
  }
 }
 proof.push({id:item.id,can:Object.fromEntries(Object.entries(can).map(([k,v])=>[k,v.id])),views:item.views.length});
}
return {createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],removedNodeIds:removed,proof};
