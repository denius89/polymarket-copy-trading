// Input CONFIG, ROOTS (one locale) and PAIRS. Existing roots; no server authorization.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const vars=await figma.variables.getLocalVariablesAsync(),origin=vars.find(v=>v.name==='Admin navigation/work origin'),has=vars.find(v=>v.name==='Admin navigation/has work origin');
if(!origin||!has)throw Error('Navigation context must exist first');
const created=[],mutated=[],proof=[],master=await figma.getNodeByIdAsync('2081:65');
for(const f of master.query('TEXT').values(['fontName']))if(f.fontName&&typeof f.fontName==='object')await figma.loadFontAsync(f.fontName);
const live=vars.find(v=>v.name==='Admin grant/limited/valid'),status=vars.find(v=>v.name==='Admin grant/limited/status');
const alias={type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id:origin.id}};
for(const role of CONFIG.roles){const root=await figma.getNodeByIdAsync(role.profile[LOCALE]),main=root.children.find(n=>/^Main/.test(n.name));const oldHas=vars.find(v=>v.name==='Admin role locale/role-profile-'+role.key+'/has origin');const row=main.query('INSTANCE').values(['id','componentProperties','boundVariables']).find(n=>oldHas&&n.boundVariables?.visible?.id===oldHas.id||Object.entries(n.componentProperties||{}).some(([k,p])=>k.startsWith('Label#')&&/Назад к рабочему экрану|Back to (work|workspace)|Return to work/.test(String(p.value))));let back=row?await figma.getNodeByIdAsync(row.id):null;
 if(!back){back=master.createInstance();main.appendChild(back);back.name='Return to exact work state';const k=Object.keys(back.componentProperties).find(k=>k.startsWith('Label#')),i=Object.keys(back.componentProperties).find(k=>k.startsWith('Show icon#'));back.setProperties({[k]:LOCALE==='ru'?'Назад к рабочему экрану':'Back to work screen',...(i?{[i]:false}:{})});back.primaryAxisSizingMode='AUTO';back.layoutSizingHorizontal='HUG';created.push(back.id);}
 back.setBoundVariable('visible',has);
 const ownerMenu=root.children.find(n=>n.name==='Navigation · owners');if(ownerMenu){for(const row of ownerMenu.children.filter(n=>n.type==='INSTANCE'&&n.name.startsWith('Navigation group'))){if(row.componentProperties.Open?.value!=='No'){for(const f of row.query('TEXT').values(['fontName']))if(f.fontName&&typeof f.fontName==='object')await figma.loadFontAsync(f.fontName);row.setProperties({Open:'No'});mutated.push(row.id);}}}
 const entries=PAIRS.filter(p=>role.key.startsWith('owner-')||ALLOWED[role.key].includes(p[LOCALE]));const actions=entries.map(p=>({type:'CONDITIONAL',conditionalBlocks:[{condition:{type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[alias,{type:'STRING',resolvedType:'STRING',value:p.key}]}},actions:[{type:'NODE',destinationId:p[LOCALE],navigation:'NAVIGATE',transition:null,preserveScrollPosition:false}]},{actions:[]}]}));
 await back.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions}]);mutated.push(back.id);proof.push({role:role.key,locale:LOCALE,root:root.id,back:back.id,origins:entries.length});
}
return {createdNodeIds:created,mutatedNodeIds:mutated,proof};
