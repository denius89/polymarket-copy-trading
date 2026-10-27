// Inject PAGES, V. Final pages remain distinct locales; deep links encode prepared state.
const made=[],changed=[];figma.skipInvisibleInstanceChildren=false;
const lit=v=>({type:'STRING',resolvedType:'STRING',value:v});const ref=id=>({type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id}});const eq=(id,v)=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[ref(id),lit(v)]}});
const url=id=>({type:'URL',url:'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-')+'&starting-point-node-id='+id.replace(':','-')+'&scaling=scale-down',openInNewTab:false});
for(const data of PAGES){
 const p=figma.root.children.find(p=>p.id===data.page);await figma.setCurrentPageAsync(p);
 const profile=p.query('#'+data.aux.profile).first();const proto=p.query('#'+data.records.find(r=>r.key==='client-order-unknown').id).first().query('INSTANCE').filter(n=>n.name==='Read status only').first();
 const fonts=new Map();for(const r of [profile,proto])for(const t of r.query('TEXT'))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
 const shown=n=>{for(let c=n;c&&c!==profile;c=c.parent)if(c.type==='INSTANCE'||c.visible===false)return false;return true;};const host=profile.query('FRAME').filter(n=>shown(n)&&n.layoutMode==='VERTICAL'&&n.width>=340&&/content|settings/i.test(n.name)).first();
 let menu=p.children.find(n=>n.name==='FINAL / contextual locale / '+data.key);if(!menu){menu=figma.createFrame();p.appendChild(menu);menu.name='FINAL / contextual locale / '+data.key;menu.resize(data.mobile?350:460,160);menu.layoutMode='VERTICAL';menu.primaryAxisSizingMode='AUTO';menu.counterAxisSizingMode='FIXED';menu.paddingTop=menu.paddingBottom=menu.paddingLeft=menu.paddingRight=20;menu.itemSpacing=12;menu.fills=profile.fills;menu.cornerRadius=16;menu.x=profile.x;menu.y=profile.y+profile.height+200;made.push(menu.id);}
 for(const [label,target]of [['Русский',data.ru],['English',data.enTarget]]){
  const routes={...target.sources,...Object.fromEntries(target.records.map(r=>[r.key,r.id]))};routes.linked=target.home;
  const mapping=Object.entries({...data.sources,...Object.fromEntries(data.records.map(r=>[r.key,r.id])),linked:data.home});
  const blocks=mapping.map(([key])=>({condition:eq(V.returnKey,key),actions:[url(routes[key]||routes[key==='positions'?'positionsPaused':key==='activity'?'activityPaused':key]||target.sources.active)]}));blocks.push({actions:[url(target.sources.active)]});
  const b=proto.clone();menu.appendChild(b);b.resize(menu.width-40,44);b.name='Locale / '+label;const t=b.query('TEXT').first();t.setBoundVariable('characters',null);t.characters=label;await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'CONDITIONAL',conditionalBlocks:blocks}]}]);made.push(b.id,...b.query('*').map(n=>n.id));
 }
 const action=[{type:'NODE',destinationId:menu.id,navigation:'OVERLAY',transition:null,resetScrollPosition:true}];
 const b=proto.clone();host.appendChild(b);b.resize(Math.min(host.width,460),48);b.name='Contextual language / return to saved session';const t=b.query('TEXT').first();t.setBoundVariable('characters',null);t.characters=data.en?'Change language · return to session':'Сменить язык · вернуться к сессии';await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:action}]);made.push(b.id,...b.query('*').map(n=>n.id));changed.push(host.id);
 // Existing language row opens this exact state-aware menu as well.
 for(const t of profile.query('TEXT').filter(t=>/^(Язык|Language|Русский \/ English|Russian \/ English)$/.test(t.characters))){let n=t.parent;while(n!==profile&&!/Settings\/|setting|Row.*язык|Row.*language/i.test(n.name)&&n.parent!==profile)n=n.parent;if(n!==profile){await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:action}]);changed.push(n.id);}}
 data.language=menu.id;
}
return {createdNodeIds:made,mutatedNodeIds:changed,menus:PAGES.map(p=>({key:p.key,id:p.language})),scope:'Prepared state encoded in cross-page locale deep link; shared mutable scenarios use native joint client locale.'};
