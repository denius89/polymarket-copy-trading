// Figma-only entry wiring. Inputs: ROLE_VARS and RECORDS; each record is
// [root ID, source node ID, role index, qualified origin key, RU title, EN title].
const page=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(page);
const changed=[],proof=[];
const set=(id,type,value)=>({type:'SET_VARIABLE',variableId:id,variableValue:{type,resolvedType:type,value}});
for(const [root,nodeId,index,key,ruTitle,enTitle]of RECORDS){
 const role=ROLE_VARS[index],n=await figma.getNodeByIdAsync(nodeId),ids=new Set(Object.values(role.vars));
 const prefix=[set(role.vars.ru_origin,'STRING',key),set(role.vars.en_origin,'STRING',key),set(role.vars.ru_title,'STRING','Возврат: '+ruTitle),set(role.vars.en_title,'STRING','Return to: '+enTitle.replace(/^EN · [^·]+ · /,'')),set(role.vars.hasOrigin,'BOOLEAN',true)];
 let targets=0;
 function wire(as){return as.filter(a=>!(a.type==='SET_VARIABLE'&&ids.has(a.variableId))).flatMap(a=>a.type==='CONDITIONAL'?[{...a,conditionalBlocks:a.conditionalBlocks.map(b=>({...b,actions:wire(b.actions)}))}]:a.type==='NODE'&&a.navigation==='NAVIGATE'&&Object.values(role.profile).includes(a.destinationId)?(targets++,[...prefix,a]):[a]);}
 const reactions=n.reactions.map(r=>({trigger:r.trigger,actions:wire(r.actions||[r.action])}));
 if(targets!==1)throw Error('Ambiguous profile entry '+nodeId+': '+targets);
 await n.setReactionsAsync(reactions);changed.push(n.id);
 const flat=as=>as.flatMap(a=>a.type==='CONDITIONAL'?flat(a.conditionalBlocks.flatMap(b=>b.actions)):[a]);
 const actual=flat(n.reactions.flatMap(r=>r.actions||[r.action]));
 const setters=actual.filter(a=>a.type==='SET_VARIABLE'&&ids.has(a.variableId));
 const expected=JSON.stringify(prefix),observed=JSON.stringify(setters.map(a=>({type:a.type,variableId:a.variableId,variableValue:{type:a.variableValue.type,resolvedType:a.variableValue.resolvedType,value:a.variableValue.value}})));
 proof.push({root,node:nodeId,index,key,assignments:setters.length,prefixRetained:expected===observed,profileTarget:actual.find(a=>a.type==='NODE'&&Object.values(role.profile).includes(a.destinationId))?.destinationId});
}
return {mutatedNodeIds:changed,proof};
