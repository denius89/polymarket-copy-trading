// Inject SOURCES. Remap native mobile transitions only; reuse role/state variables.
const p=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(p);figma.skipInvisibleInstanceChildren=false;
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const inventory=SOURCES.map(s=>({...s,desktop:s.id,id:p.children.find(n=>n.name==='MOBILE / '+s.key)?.id}));
if(inventory.some(x=>!x.id))throw Error('Missing mobile root');
const map=Object.fromEntries(inventory.map(x=>[x.desktop,x.id]));const changed=[];let count=0;
function replace(v){if(typeof v==='string')return map[v]||v;if(Array.isArray(v))return v.map(replace);if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).map(([k,v])=>[k,replace(v)]));return v;}
for(const row of inventory){const root=await figma.getNodeByIdAsync(row.id);for(const node of [root,...root.findAll(n=>'reactions'in n&&n.reactions.length)]){
 if(!('reactions'in node)||!node.reactions.length)continue;
 const reactions=replace(JSON.parse(JSON.stringify(node.reactions)));
 if(node.name!=='Mobile menu toggle')for(const r of reactions)if(JSON.stringify(r).includes('NAVIGATE'))r.actions=[{type:'SET_VARIABLE',variableId:'VariableID:4159:416',variableValue:{type:'BOOLEAN',resolvedType:'BOOLEAN',value:false}},...(r.actions||[])];
 await node.setReactionsAsync(reactions);changed.push(node.id);count+=reactions.length;
 }
 if(row.key==='users'){
  const wrap=root.findOne(n=>n.name==='Mobile horizontal scroll / Table tools');if(wrap){const c=wrap.children[0],parent=wrap.parent,index=parent.children.indexOf(wrap);parent.insertChild(index,c);c.layoutMode='VERTICAL';c.resize(358,c.height);c.primaryAxisSizingMode='AUTO';wrap.remove();}
  const crumb=root.findOne(n=>n.name==='Breadcrumbs');if(crumb){crumb.layoutMode='HORIZONTAL';crumb.layoutWrap='WRAP';crumb.resize(358,18);crumb.primaryAxisSizingMode='AUTO';for(const t of crumb.children)if(t.type==='TEXT')t.textAutoResize='WIDTH_AND_HEIGHT';}
 }
 if(['feedbackOptions','feedbackLink'].includes(row.key)){row.kind='overlay';root.resize(390,Math.min(760,root.children.reduce((sum,c)=>sum+(c.visible?c.height+20:0),32)));}
 row.width=root.width;row.height=root.height;
}
return {inventory,reactions:count,changedNodeIds:changed};
