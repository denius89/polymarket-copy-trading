
const p=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(p);figma.skipInvisibleInstanceChildren=false;
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const changed=[];function remap(v){if(typeof v==='string')return MAP[v]||v;if(Array.isArray(v))return v.map(remap);if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).map(([k,v])=>[k,remap(v)]));return v;}
for(const row of JOB){const desktop=await figma.getNodeByIdAsync(row.desktop),mobile=await figma.getNodeByIdAsync(row.id);
if(!row.key.startsWith('finance')){
const ds=desktop.findOne(n=>n.name==='Persistent navigation'),ms=mobile.findOne(n=>n.name==='Mobile menu content');
if(ds&&ms){const b=ds.findOne(n=>n.name==='Финансы');if(b&&!ms.findOne(n=>n.name==='Финансы')){const c=b.clone();ms.appendChild(c);c.resize(358,44);changed.push(c.id,...c.findAll(()=>true).map(n=>n.id));}}
if(row.key==='entry'){for(const b of desktop.children.filter(n=>'reactions'in n&&n.reactions.length&&n.name.includes('STAFF-'))){const target=mobile.findOne(n=>n.name===b.name);if(target){await target.setReactionsAsync(remap(JSON.parse(JSON.stringify(b.reactions))));changed.push(target.id);}}}
if(row.key==='profile'){const b=desktop.findOne(n=>n.name==='Вернуться к работе'),target=mobile.findOne(n=>n.name==='Вернуться к работе');if(b&&target){await target.setReactionsAsync(remap(JSON.parse(JSON.stringify(b.reactions))));changed.push(target.id);}}
if(row.key==='user'){const b=desktop.findOne(n=>n.name==='Условия VIP выбранного пользователя');if(b&&!mobile.findOne(n=>n.name===b.name)){const main=mobile.children.find(n=>n.name==='Main content')||mobile,c=b.clone();main.appendChild(c);c.resize(358,80);for(const t of c.findAllWithCriteria({types:['TEXT']})){t.textAutoResize='HEIGHT';t.resize(326,t.height);}changed.push(c.id);}}
}
const targets=row.key.startsWith('finance')?mobile.findAll(n=>'reactions'in n&&n.reactions.length):mobile.findAll(n=>'reactions'in n&&n.reactions.length&&['Финансы','Условия VIP выбранного пользователя'].includes(n.name));
for(const n of targets){const rx=remap(JSON.parse(JSON.stringify(n.reactions)));for(const r of rx){delete r.action;if(n.name!=='Mobile menu toggle'&&JSON.stringify(r).includes('NAVIGATE'))r.actions=[{type:'SET_VARIABLE',variableId:'VariableID:4159:416',variableValue:{type:'BOOLEAN',resolvedType:'BOOLEAN',value:false}},...(r.actions||[])];}await n.setReactionsAsync(rx);changed.push(n.id);}
}
return{mutatedNodeIds:changed,count:changed.length};
