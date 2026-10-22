// Prepared profile save must update the current employee header without changing identity or grants.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const vars=await figma.variables.getLocalVariablesAsync(),mutated=[],proof=[];
const alias=v=>({type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id:v.id}});
const str=value=>({type:'STRING',resolvedType:'STRING',value});
const add=(a,b)=>({type:'EXPRESSION',resolvedType:'STRING',value:{expressionFunction:'ADDITION',expressionArguments:[a,b]}});
const byName=new Map(vars.map(v=>[v.name,v])),headers=vars.filter(v=>v.name.startsWith('Admin navigation/header/'));
const headerIds=new Set(headers.map(v=>v.id));
const entries=PROFILES.flatMap(p=>p.views.filter(v=>['p1','pError'].includes(v.name)).map(v=>({key:p.key,locale:p.locale,staff:p.staffId,view:v.id})));
entries.push({key:'owner-a',locale:'ru',staff:'STAFF-201',button:'2155:19536'},{key:'owner-a',locale:'en',staff:'STAFF-201',button:'2155:79278'});
for(const p of entries){const r=CONFIG.roles.find(r=>r.key===p.key),draft={};for(const loc of ['ru','en']){draft[loc]=byName.get('Admin self-flow/'+p.key+'/draft name '+loc)||byName.get('Admin self/'+p.staff+'/draft name '+loc)||byName.get('Admin self/'+p.staff+'/draft '+loc);if(!draft[loc])throw Error('Missing name draft '+p.key+'/'+loc);}
 const updates=headers.map(v=>{const loc=v.name.endsWith('/ru')?'ru':'en',suffix=r[loc].slice(r[loc].split(' · ')[0].length);return {type:'SET_VARIABLE',variableId:v.id,variableValue:add(alias(draft[loc]),str(suffix))};});
 let button;if(p.button)button=await figma.getNodeByIdAsync(p.button);else{const view=await figma.getNodeByIdAsync(p.view);const row=view.query('INSTANCE').values(['id','componentProperties']).find(n=>Object.entries(n.componentProperties).some(([k,v])=>k.startsWith('Label#')&&/^(Сохранить|Save)( |$)/.test(v.value)));button=await figma.getNodeByIdAsync(row.id);}
 const reactions=button.reactions.map(r=>({trigger:r.trigger,actions:(r.actions||[]).map(a=>a.type==='CONDITIONAL'?{...a,conditionalBlocks:a.conditionalBlocks.map((b,i)=>({...b,actions:i===0?[...updates,...b.actions.filter(a=>!headerIds.has(a.variableId))]:b.actions}))}:a)}));await button.setReactionsAsync(reactions);mutated.push(button.id);proof.push({key:p.key,locale:p.locale,button:button.id,headers:headers.length});
}
return {createdNodeIds:[],mutatedNodeIds:mutated,proof};
