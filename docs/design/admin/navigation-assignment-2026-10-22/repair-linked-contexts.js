// Repairs the remaining legacy personal entry points and shared linked context.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const vars=await figma.variables.getLocalVariablesAsync(),V=new Map(vars.map(v=>[v.name.replace('Admin navigation/',''),v])),created=[],mutated=[],proof=[],unresolved=[];
const active=V.get('active role'),origin=V.get('work origin'),has=V.get('has work origin');
const lit=(type,value)=>({type,resolvedType:type,value}),alias=v=>({type:'VARIABLE_ALIAS',resolvedType:v.resolvedType,value:{type:'VARIABLE_ALIAS',id:v.id}});
const set=(v,x)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:lit(v.resolvedType,x)}),eq=(v,x)=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[alias(v),lit(v.resolvedType,x)]}});
const node=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,preserveScrollPosition:false}),cond=(c,actions)=>({type:'CONDITIONAL',conditionalBlocks:[{condition:c,actions},{actions:[]}]});
function targets(aa){return aa.flatMap(a=>a.type==='NODE'&&a.navigation==='NAVIGATE'&&a.destinationId?[a.destinationId]:a.type==='CONDITIONAL'?a.conditionalBlocks.flatMap(b=>targets(b.actions)):[]);}
function label(n){return n.type==='TEXT'?n.characters:n.type==='INSTANCE'?Object.entries(n.componentProperties).find(([k])=>k.startsWith('Label#'))?.[1].value||n.name:n.name;}
const allKeys=CONFIG.roles.map(r=>r.key),sources={};
for(const loc of ['ru','en']){const r=await figma.getNodeByIdAsync(CONFIG.roles.find(r=>r.key==='nora-operations').home[loc]);sources[loc]=r.children.find(n=>n.name==='Navigation · nora-operations');}
for(const item of ROOTS){
 const root=await figma.getNodeByIdAsync(item.id),main=root.children.find(n=>/^Main/.test(n.name));let menu=root.children.find(n=>n.name==='Navigation · nora-operations');
 if(!menu){const s=sources[item.locale];for(const f of s.query('TEXT').values(['fontName']))if(f.fontName&&typeof f.fontName==='object')await figma.loadFontAsync(f.fontName);menu=s.clone();root.insertChild(0,menu);menu.resize(248,root.height);menu.layoutSizingVertical='FILL';menu.setBoundVariable('visible',V.get('active/nora-operations'));created.push(menu.id);}
 for(const n of menu.children.filter(n=>n.type==='INSTANCE'&&n.componentProperties.State)){for(const f of n.query('TEXT').values(['fontName']))if(f.fontName&&typeof f.fontName==='object')await figma.loadFontAsync(f.fontName);n.setProperties({State:n.name.endsWith('ADM-09/support')?'Selected':'Default'});mutated.push(n.id);}
 const controls=main.query('INSTANCE, TEXT, FRAME').values(['id','name','reactions']).filter(n=>n.reactions?.length&&n.name!=='My account · open profile'&&n.name!=='Admin/Account button');let guarded=0;
 for(const row of controls){const dest=row.reactions.flatMap(r=>targets(r.actions||[]));if(!dest.length)continue;const n=await figma.getNodeByIdAsync(row.id),text=label(n);if(/пример|sample|scenario|учеб/i.test(text)&&/владелец|owner|Нора|Nora|роль|role/i.test(text))continue;
  if(dest.every(id=>id===CONFIG.roles[0].home.ru||id===CONFIG.roles[0].home.en)){await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:CONFIG.roles.map(r=>cond(eq(active,r.key),[node(r.home[item.locale])]))}]);mutated.push(n.id);continue;}
  const keys=allKeys.filter(k=>k.startsWith('owner-')||dest.every(id=>ALLOWED[k].includes(id)||CONFIG.neutral.includes(id)));if(keys.length===allKeys.length)continue;
  const v=V.get('mask/'+keys.join('|')+'@ops');if(!v){unresolved.push({id:n.id,keys});continue;}
  if(n.boundVariables.visible?.id===v.id||n.parent.name==='Navigation permission guard'&&n.parent.boundVariables.visible?.id===v.id)continue;
  if(n.boundVariables.visible){if(n.parent.type==='INSTANCE'){unresolved.push({id:n.id,reason:'immutable existing visibility'});continue;}const parent=n.parent,index=parent.children.indexOf(n),w=figma.createAutoLayout('VERTICAL');parent.insertChild(index,w);w.name='Navigation permission guard';w.fills=[];w.resize(n.width,n.height);w.primaryAxisSizingMode='AUTO';w.counterAxisSizingMode='AUTO';w.appendChild(n);w.setBoundVariable('visible',v);created.push(w.id);}else n.setBoundVariable('visible',v);
  mutated.push(n.id);guarded++;
 }
 proof.push({root:root.id,locale:item.locale,noraMenu:menu.id,guarded});
}
for(const b of LEGACY){const n=await figma.getNodeByIdAsync(b.button);n.name='My account · open profile';await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:CONFIG.roles.map(r=>cond(eq(active,r.key),[set(origin,b.key),set(has,true),node(r.profile[b.locale])]))}]);mutated.push(n.id);proof.push({root:b.root,button:n.id,locale:b.locale,branches:n.reactions[0].actions.length});}
return {createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],proof,unresolved};
