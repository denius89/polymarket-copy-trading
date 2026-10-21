// Figma-only construction. Input ROLES: existing profiles, origin domains, variable IDs.
// Keeps existing main frames and component instances; not an exact Figma backup.
const page=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(page);
const templates={},created=[],changed=[],removed=[],proof=[];
const fontMap=new Map();
for(const lang of ['ru','en']){
 const closedRoot=await figma.getNodeByIdAsync(lang==='ru'?'2155:19768':'2155:79510');
 const closed=closedRoot.findAll(n=>n.name==='Account language dropdown')[0];
 const open=await figma.getNodeByIdAsync(lang==='ru'?'2258:92796':'2258:92966');
 const source=await figma.getNodeByIdAsync(lang==='ru'?'I2258:92796;2254:1083':'I2258:92966;2254:1106');
 const actions=JSON.parse(JSON.stringify(source.reactions[0].actions));
 if(actions.filter(a=>a.type==='SET_VARIABLE').length!==33||actions.at(-1).type!=='NODE')throw Error('Unexpected state transfer contract');
 templates[lang]={closed,open,actions};
 for(const n of [closed,open])for(const t of n.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fontMap.set(s.fontName.family+'|'+s.fontName.style,{family:s.fontName.family,style:s.fontName.style});
}
const profiles=[];for(const r of ROLES)for(const lang of ['ru','en'])profiles.push(await figma.getNodeByIdAsync(r.profile[lang]));
for(const n of profiles)for(const t of n.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fontMap.set(s.fontName.family+'|'+s.fontName.style,{family:s.fontName.family,style:s.fontName.style});
for(const font of fontMap.values())await figma.loadFontAsync(font);
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,resetScrollPosition:false});
const react=async(n,actions)=>{await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions}]);changed.push(n.id);};
const remember=n=>{created.push(n.id,...n.findAll(()=>true).map(c=>c.id));};
const eq=(id,value)=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[{type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id}},{type:'STRING',resolvedType:'STRING',value}]}});
let x=Math.max(...page.children.map(n=>n.x+n.width))+1600;
for(const role of ROLES){
 const visible=await figma.variables.getVariableByIdAsync(role.vars.hasOrigin);
 for(const lang of ['ru','en']){
  const other=lang==='ru'?'en':'ru',root=await figma.getNodeByIdAsync(role.profile[lang]);
  const main=root.children.find(n=>n.name==='Main'),records=main.children.find(n=>n.name==='Operation records'),bar=main.children.find(n=>n.name==='Permitted actions');
  const old=records.children.find(n=>n.type==='INSTANCE'&&Object.entries(n.componentProperties).some(([k,v])=>k.startsWith('Title#')&&['Язык интерфейса','Interface language'].includes(v.value)));
  if(old){removed.push(old.id);old.remove();records.layoutSizingVertical='HUG';changed.push(records.id);}
  let picker=main.children.find(n=>n.name==='Role language dropdown');
  if(!picker){picker=templates[lang].closed.clone();main.insertChild(main.children.indexOf(bar),picker);picker.name='Role language dropdown';picker.resize(Math.min(520,main.width),picker.height);picker.layoutSizingHorizontal='FIXED';remember(picker);}
  for(const n of [picker,...picker.findAll(n=>'reactions'in n&&n.reactions.length)])if('reactions'in n&&n.reactions.length){await n.setReactionsAsync([]);changed.push(n.id);}
  let hint=main.children.find(n=>n.name==='Role work context');
  if(!hint){hint=main.children.find(n=>n.name==='Review disclaimer').clone();main.insertChild(main.children.indexOf(bar),hint);hint.name='Role work context';hint.textAutoResize='HEIGHT';hint.resize(main.width,hint.height);hint.layoutSizingHorizontal='FILL';created.push(hint.id);}
  hint.setBoundVariable('characters',await figma.variables.getVariableByIdAsync(role.vars[lang+'_title']));changed.push(hint.id);
  const back=bar.children[0];back.setBoundVariable('visible',visible);changed.push(back.id);
  const returns=role.origins.map(o=>({type:'CONDITIONAL',conditionalBlocks:[{condition:eq(role.vars[lang+'_origin'],o.key),actions:[nav(o[lang])]},{actions:[]}]}));
  await react(back,returns);
  const height=Math.max(root.height,Math.ceil((main.y+Math.max(...main.children.filter(n=>n.visible).map(n=>n.y+n.height))+48)/40)*40);root.resize(root.width,height);changed.push(root.id);
  const name=lang.toUpperCase()+' · role-language-menu · '+role.key;
  let overlay=page.children.find(n=>n.type==='FRAME'&&n.name===name);
  if(!overlay){overlay=figma.createFrame();page.appendChild(overlay);overlay.name=name;overlay.resize(root.width,root.height);overlay.fills=[];overlay.clipsContent=false;overlay.x=x;overlay.y=0;x+=root.width+200;created.push(overlay.id);
   const dismiss=figma.createFrame();overlay.appendChild(dismiss);dismiss.name='Dismiss role language menu';dismiss.resize(overlay.width,overlay.height);dismiss.fills=root.fills.map(p=>({...p,opacity:0.001}));created.push(dismiss.id);await react(dismiss,[{type:'CLOSE'}]);
   const open=templates[lang].open.clone();overlay.appendChild(open);open.name='Role language options';open.resize(picker.width,open.height);open.x=picker.absoluteTransform[0][2]-root.absoluteTransform[0][2];open.y=picker.absoluteTransform[1][2]-root.absoluteTransform[1][2];remember(open);
   for(const n of [open,...open.findAll(n=>'reactions'in n&&n.reactions.length)])if('reactions'in n&&n.reactions.length){await n.setReactionsAsync([]);changed.push(n.id);}
  }
  const panel=overlay.children.find(n=>n.name==='Role language options');
  const field=panel.children.find(n=>n.type==='INSTANCE');await react(field,[{type:'CLOSE'}]);
  const options=panel.findAll(n=>/^Option · (RU|EN)$/.test(n.name));if(options.length!==2)throw Error('Option inventory '+role.key+' '+lang);
  for(const option of options){const optionLang=option.name.endsWith('RU')?'ru':'en';await react(option,optionLang===lang?[{type:'CLOSE'}]:[...templates[lang].actions.slice(0,-1),{...nav(role.profile[other]),resetInteractiveComponents:true}]);}
  const trigger=picker.children.find(n=>n.type==='INSTANCE');await react(trigger,[{type:'NODE',destinationId:overlay.id,navigation:'OVERLAY',transition:null}]);
  proof.push({role:role.key,locale:lang,profile:root.id,overlay:overlay.id,picker:picker.id,trigger:trigger.id,back:back.id,hint:hint.id,returnCount:returns.length,profileHeight:root.height,panelBounds:{x:panel.x,y:panel.y,width:panel.width,height:panel.height},options:options.map(n=>({id:n.id,name:n.name,actionCount:n.reactions[0].actions.length,destination:n.reactions[0].actions.at(-1).destinationId||null})),identity:records.children.filter(n=>n.type==='INSTANCE').map(n=>({name:n.name,props:n.componentProperties})),fonts:[...new Set(root.findAllWithCriteria({types:['TEXT']}).flatMap(t=>t.getStyledTextSegments(['fontName']).map(s=>s.fontName.family)))]});
 }
}
return {createdNodeIds:[...new Set(created)],mutatedNodeIds:[...new Set(changed)],removedNodeIds:removed,variableIds:ROLES.map(r=>r.vars.hasOrigin),proof};
