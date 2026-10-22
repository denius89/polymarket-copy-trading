// Inputs are bounded ROOTS, CONFIG and ALLOWED. Prototype-only context, not authorization code.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
figma.skipInvisibleInstanceChildren=false;
const created=[],mutated=[],removed=[],proof=[],unresolved=[];
const col=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:134:180'),vars=await figma.variables.getLocalVariablesAsync(),V={};
const byName=new Map(vars.map(v=>[v.name,v]));
function variable(k,type,value){let v=byName.get('Admin navigation/'+k);if(!v){v=figma.variables.createVariable('Admin navigation/'+k,col,type);v.scopes=type==='STRING'?['TEXT_CONTENT']:['ALL_SCOPES'];v.setValueForMode(col.defaultModeId,value);created.push(v.id);vars.push(v);byName.set(v.name,v);}V[k]=v;return v;}
variable('work origin','STRING','');variable('has work origin','BOOLEAN',false);variable('active role','STRING','');variable('owners active','BOOLEAN',false);variable('owners or unset','BOOLEAN',true);
for(const r of CONFIG.roles){variable('default/'+r.key,'BOOLEAN',true);variable('active/'+r.key,'BOOLEAN',false);for(const loc of ['ru','en'])variable('header/'+r.key+'/'+loc,'STRING',r[loc]);}
const ownerKeys=['owner-a','owner-b'],allKeys=CONFIG.roles.map(r=>r.key),maskSets=new Set([ownerKeys.join('|'),allKeys.join('|'),'owner-b']);
for(const id of new Set(Object.values(ALLOWED).flat()))maskSets.add(allKeys.filter(r=>r.startsWith('owner-')||ALLOWED[r]?.includes(id)||CONFIG.neutral.includes(id)).join('|'));
let grew=true;while(grew){grew=false;const rows=[...maskSets];for(const a of rows)for(const b of rows){const x=a.split('|').filter(k=>b.split('|').includes(k)).join('|');if(x&&!maskSets.has(x)){maskSets.add(x);grew=true;}}}
for(const m of maskSets)for(const r of allKeys)variable('mask/'+m+'@'+r,'BOOLEAN',m.split('|').includes(r));
const literal=(type,value)=>({type,resolvedType:type,value});
const alias=v=>({type:'VARIABLE_ALIAS',resolvedType:v.resolvedType,value:{type:'VARIABLE_ALIAS',id:v.id}});
const set=(v,value)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:typeof value==='object'?value:literal(v.resolvedType,value)});
const eq=(v,value)=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[alias(v),literal(v.resolvedType,value)]}});
const cond=(condition,yes,no=[])=>({type:'CONDITIONAL',conditionalBlocks:[{condition,actions:yes},{actions:no}]});
const node=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,preserveScrollPosition:false});
const label=n=>n.type==='INSTANCE'?Object.entries(n.componentProperties).find(([k])=>k.startsWith('Label#'))?.[1].value||n.name:n.name;
function prop(n,p){const q={};for(const[k,v]of Object.entries(p)){const key=Object.keys(n.componentProperties).find(x=>x.split('#')[0]===k);if(key&&n.componentProperties[key].value!==v)q[key]=v;}if(Object.keys(q).length){n.setProperties(q);mutated.push(n.id);}}
async function fonts(n){const map=new Map();for(const row of n.query('TEXT').values(['fontName'])){const f=row.fontName;if(f&&typeof f==='object'&&f.family)map.set(JSON.stringify(f),f);}await Promise.all([...map.values()].map(f=>figma.loadFontAsync(f)));}
const maskVars=vars.filter(v=>v.name.startsWith('Admin navigation/mask/')),contextCache=new Map();
function contextActions(key){if(contextCache.has(key))return contextCache.get(key);const r=CONFIG.roles.find(r=>r.key===key),owner=key.startsWith('owner-'),a=[set(V['work origin'],''),set(V['has work origin'],false),...vars.filter(v=>v.name.startsWith('Admin role locale/')&&v.name.endsWith('/has origin')).map(v=>set(v,false)),set(V['active role'],key),set(V['owners active'],owner),set(V['owners or unset'],owner)];for(const q of CONFIG.roles){a.push(set(V['default/'+q.key],q.key===key),set(V['active/'+q.key],q.key===key));for(const loc of ['ru','en'])a.push(set(V['header/'+q.key+'/'+loc],r[loc]));}for(const v of maskVars){const mask=v.name.split('/').at(-1).split('@')[0].split('|');a.push(set(v,mask.includes(key)));}contextCache.set(key,a);return a;}
function targets(aa){return aa.flatMap(a=>a.type==='NODE'&&a.navigation==='NAVIGATE'&&a.destinationId?[a.destinationId]:a.type==='CONDITIONAL'?a.conditionalBlocks.flatMap(b=>targets(b.actions)):[]);}
function permitted(role,id){return role.startsWith('owner-')||ALLOWED[role].includes(id)||CONFIG.neutral.includes(id);}

const profileIds=new Set(CONFIG.roles.map(r=>r.profile[LOCALE]));
const ownerRoot=await figma.getNodeByIdAsync(CONFIG.ownerMenu[LOCALE]),ownerTemplate=ownerRoot.children.find(n=>n.name==='Navigation · owners'||n.name==='Admin navigation');await fonts(ownerTemplate);
for(const d of ROOTS){const root=await figma.getNodeByIdAsync(d.id),main=root.children.find(n=>/^Main/.test(n.name));let nav=root.children.find(n=>/^(Navigation|Admin navigation)$/.test(n.name)||n.name==='Navigation · owners')||root.children.find(n=>n!==main&&n.width>=200&&n.width<=280&&'children'in n);if(!main||!nav){proof.push({id:d.id,skip:'no work shell'});continue;}const already=nav.name==='Navigation · owners',role=d.role;
if(nav.type==='FRAME'&&!d.key.endsWith('/demo-review')){const old=nav;nav=ownerTemplate.clone();root.insertChild(0,nav);nav.resize(248,root.height);nav.layoutSizingVertical='FILL';old.remove();created.push(nav.id);const overview=nav.children.find(n=>n.name==='Overview');if(overview){prop(overview,{State:'Default'});await overview.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[node(CONFIG.roles[0].home[LOCALE])]}]);mutated.push(overview.id);}for(const group of nav.children.filter(n=>n.type==='INSTANCE'&&n.name.startsWith('Navigation group'))){const g=CONFIG.accountRoots?.includes(root.id)?null:/^(ADM-02|ADM-03|ADM-09)/.test(d.key)?'Clients':/^(ADM-06|ADM-07|ADM-08|ADM-13)/.test(d.key)?'Finance':'Management';prop(group,{Open:group.componentProperties.Group.value===g?'Yes':'No'});}}
nav.name='Navigation · owners';nav.setBoundVariable('visible',V['owners or unset']);mutated.push(nav.id);
 const ctx=main.children.find(n=>(/context/i.test(n.name)||/account header|topbar|header bar/i.test(n.name))&&'children'in n),actor=ctx?.children.find(n=>n.type==='TEXT');if(actor){for(const f of actor.getStyledTextSegments(['fontName']))await figma.loadFontAsync(f.fontName);actor.setBoundVariable('characters',V['header/'+role+'/'+LOCALE]);if(CONFIG.accountRoots?.includes(root.id))actor.visible=false;mutated.push(actor.id);}
 const isProfile=profileIds.has(root.id);
 const openProfile=ctx?.children.find(n=>n.type==='INSTANCE'&&['My account · open profile','Admin/Account button'].includes(n.name));
 if(openProfile&&!isProfile){const aa=CONFIG.roles.map(r=>cond(eq(V['active role'],r.key),[...(CONFIG.accountRoots?.includes(root.id)?[]:[set(V['work origin'],d.key),set(V['has work origin'],true)]),node(r.profile[LOCALE])]));await openProfile.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[cond(eq(V['active role'],''),contextActions(role)),...aa]}]);mutated.push(openProfile.id);}
 const rr=root.reactions,init=cond(eq(V['active role'],''),contextActions(role));
 let initAdded=false;const rootReactions=rr.map(r=>{if(r.trigger?.type==='AFTER_TIMEOUT'&&!initAdded){initAdded=true;return {trigger:r.trigger,actions:[init,...(already?[]:(r.actions||[]))]};}return {trigger:r.trigger,actions:r.actions||[]};});
 if(!initAdded)rootReactions.push({trigger:{type:'AFTER_TIMEOUT',timeout:0.01},actions:[init]});await root.setReactionsAsync(rootReactions);mutated.push(root.id);

proof.push({id:root.id,defaultRole:role,rootActions:root.reactions.length,actor:actor?.id,profile:openProfile?.id});}
return {createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],proof};
