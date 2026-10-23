const p=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(p);
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const vars=new Map((await figma.variables.getLocalVariablesAsync()).map(v=>[v.id,v]));const changed=[],created=[];
const normal=await figma.getNodeByIdAsync('1978:1003'),active=await figma.getNodeByIdAsync('1978:1005');
for(const c of [normal,active])for(const t of c.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))await figma.loadFontAsync(s.fontName);
const states={overview:'3971:2',users:'3971:3',user:'3971:4',session:'3971:5',order:'3971:6',profile:'3990:109',denied:'3990:110'};
const results=[];
for(const [job,id]of Object.entries(states)){
 const root=await figma.getNodeByIdAsync(id);
 if(!root.name.startsWith('READY'))throw Error('Unfinished frame: '+id);
 for(const n of root.findAllWithCriteria({types:['FRAME']}))if(n.layoutMode==='HORIZONTAL'){n.counterAxisSizingMode='AUTO';changed.push(n.id);}
 const side=root.findOne(n=>n.type==='FRAME'&&n.name==='Persistent navigation');
 for(const old of [...side.children].filter(n=>n.type==='INSTANCE')){
  const label=old.findAllWithCriteria({types:['TEXT']})[0];const key=old.name;const chosen=job==='overview'?key==='Обзор':job==='profile'?key==='Личный профиль':key==='Пользователи';
  const n=(chosen?active:normal).createInstance();side.insertChild(side.children.indexOf(old),n);n.resize(200,44);n.name=key;const t=n.findAllWithCriteria({types:['TEXT']})[0];if(label.boundVariables.characters)t.setBoundVariable('characters',vars.get(label.boundVariables.characters.id));
  if(old.boundVariables.visible)n.setBoundVariable('visible',vars.get(old.boundVariables.visible.id));
  if(old.reactions.length)await n.setReactionsAsync(old.reactions);
  created.push(n.id,...n.findAll(()=>true).map(x=>x.id));old.remove();
 }
 const crumbs=root.findOne(n=>n.type==='FRAME'&&n.name==='Breadcrumbs');if(crumbs){for(const old of [...crumbs.children].filter(n=>n.type==='INSTANCE')){const label=old.findAllWithCriteria({types:['TEXT']})[0];const n=figma.createText();n.fontName={family:'Inter',style:'Regular'};n.fontSize=12;n.lineHeight={unit:'PIXELS',value:18};n.characters=label.characters;n.fills=label.fills;crumbs.insertChild(crumbs.children.indexOf(old),n);if(label.boundVariables.characters)n.setBoundVariable('characters',vars.get(label.boundVariables.characters.id));if(old.reactions.length)await n.setReactionsAsync(old.reactions);created.push(n.id);old.remove();}}
 for(const check of root.findAll(n=>n.type==='FRAME'&&n.name.startsWith('Selection '))){const old=check.children.find(n=>n.type==='RECTANGLE'&&n.boundVariables.visible);if(old){const v=vars.get(old.boundVariables.visible.id);const tick=figma.createNodeFromSvg('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><rect width="24" height="24" rx="5" fill="#7044e0"/><path d="m6 12 4 4 8-9" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>');check.appendChild(tick);tick.layoutPositioning='ABSOLUTE';tick.x=0;tick.y=0;tick.setBoundVariable('visible',v);created.push(tick.id,...tick.findAll(()=>true).map(n=>n.id));old.remove();}}
 const main=root.findOne(n=>n.type==='FRAME'&&n.name==='Main content');const h=Math.max(940,Math.ceil((main.height+40)/8)*8);root.resize(1440,h);side.resize(232,h);side.primaryAxisSizingMode='FIXED';changed.push(root.id,side.id);results.push({job,id,mainHeight:main.height,height:root.height});
}
for(const id of ['3990:108','3997:36','3990:116']){const root=await figma.getNodeByIdAsync(id);for(const n of root.findAllWithCriteria({types:['FRAME']}))if(n.layoutMode==='HORIZONTAL'){n.counterAxisSizingMode='AUTO';changed.push(n.id);}}
p.flowStartingPoints=[{nodeId:'3990:108',name:'Новая админка · роли и RU/EN'}];changed.push(p.id);
return {createdNodeIds:created,mutatedNodeIds:changed,results};
