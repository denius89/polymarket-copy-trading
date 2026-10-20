// Figma-only scoped corrections. Inputs: PAGE, LOCALE, ROWS, ALLOWED, EXTERNAL.
const page = await figma.getNodeByIdAsync(PAGE); await figma.setCurrentPageAsync(page);
const L = LOCALE === 'RU' ? 0 : 1, created = [], changed = [], removed = [], records = [], moved = [];
const navMaster = await figma.getNodeByIdAsync('2032:67');
const buttonMaster = await figma.getNodeByIdAsync('113:209');
const loaded = new Set();
async function load(n) { for (const t of n.type==='TEXT'?[n]:n.findAllWithCriteria({types:['TEXT']})) for (const s of t.getStyledTextSegments(['fontName'])) { const k=JSON.stringify(s.fontName); if (!loaded.has(k)) { await figma.loadFontAsync(s.fontName); loaded.add(k); } } }
await load(navMaster); await load(buttonMaster);
function prop(n,k,v) { const key=Object.keys(n.componentProperties).find(x=>x.split('#')[0]===k); if (key) n.setProperties({[key]:v}); changed.push(n.id); }
function link(n,to) { n.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:to,navigation:'NAVIGATE',transition:null,resetScrollPosition:true}]}]; changed.push(n.id); }
const profile = {...EXTERNAL.profiles};
let nora = page.children.find(n=>n.name.startsWith(LOCALE+' · role-profile-nora-operations · '));
if (!nora) { const source=await figma.getNodeByIdAsync(profile.ops); nora=source.clone(); page.appendChild(nora); nora.x=4680; nora.y=Math.max(...page.children.filter(x=>x!==nora&&'height'in x).map(x=>x.y+x.height))+240; nora.name=LOCALE+' · role-profile-nora-operations · '+(L===0?'Личный профиль Норы · операционная роль':'Nora profile · operations assignment'); created.push(nora.id); }
const nm=nora.children.find(n=>n.name.startsWith('Main')); await load(nm);
for (const t of nm.findAllWithCriteria({types:['TEXT']})) { const v=t.characters.replaceAll(L===0?'Олег Смирнов':'Oleg Smirnov',L===0?'Нора Азиз':'Nora Aziz').replaceAll('STAFF-206','STAFF-203'); if(v!==t.characters){t.characters=v;changed.push(t.id);} }
const staffRow=nm.children.find(n=>n.name==='Operation records').children[1];
prop(staffRow,'Detail',L===0?'Нора Азиз':'Nora Aziz');prop(staffRow,'Meta','STAFF-203');
const nctx=nm.children.find(n=>n.name==='Context'); const nct=nctx.children.find(n=>n.type==='TEXT'); nct.characters=L===0?'Нора Азиз · STAFF-203 · учебный снимок операционного назначения':'Nora Aziz · STAFF-203 · operations assignment fixture'; changed.push(nct.id);
profile['nora-ops']=nora.id; ALLOWED['nora-ops'].push(nora.id);
const nback=nm.children.find(n=>n.name==='Permitted actions')?.children[0];if(nback){prop(nback,'Label',L===0?'Назад к рабочему экрану':'Back to work screen');nback.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'BACK'}]}];changed.push(nback.id);}
const rows=[...ROWS,{id:nora.id,key:'role-profile-nora-operations',actor:'nora-ops'}];
const defs={
 'owner-b':[['Мой профиль','My profile',profile['owner-b']]],
 'nora-ops':[['Отзывы','Feedback',EXTERNAL.feedback],['Технический режим','Technical mode',EXTERNAL.tech],['Ограничения пополнений','Deposit restrictions',EXTERNAL.deposits],['Ограничения выводов','Withdrawal restrictions',EXTERNAL.withdrawals],['Ограничения выплат','Payout restrictions',EXTERNAL.payouts],['Мой профиль','My profile',profile['nora-ops']]],
 ops:[['Рабочая область','Workspace',EXTERNAL.opsHome],['Инциденты','Incidents',EXTERNAL.opsQueue],['Сверка','Reconciliation',EXTERNAL.opsCases],['Поддержка','Support',EXTERNAL.support],['Диагностика','Diagnostics',EXTERNAL.opsConnection],['Мой профиль','My profile',profile.ops]]
};
for (const d of rows) {
 const root=await figma.getNodeByIdAsync(d.id), main=root.children.find(n=>n.name.startsWith('Main'));
 const header=main.children.find(n=>n.name==='Context'||n.name==='Account header')||main.children[0]; await load(header);
 const actorText=header.children.find(n=>n.type==='TEXT');
 if(actorText){actorText.characters=d.actor==='owner-b'?(L===0?'Максим Орлов · STAFF-202 · владелец B':'Maxim Orlov · STAFF-202 · Owner B'):d.actor==='nora-ops'?(L===0?'Нора Азиз · STAFF-203 · операционное назначение · учебный снимок':'Nora Aziz · STAFF-203 · operations assignment fixture'):(L===0?'Олег Смирнов · STAFF-206 · операции и поддержка':'Oleg Smirnov · STAFF-206 · operations and support'); changed.push(actorText.id);}
 const avatar=header.children.find(n=>n.type==='INSTANCE');
 if(avatar){if(root.id===profile[d.actor]){avatar.visible=false;avatar.reactions=[];changed.push(avatar.id);}else link(avatar,profile[d.actor]);}
 const old=root.children.find(n=>n!==main&&n.width<=280);
 const nav=figma.createAutoLayout('VERTICAL'); nav.name='Navigation'; root.insertChild(0,nav); nav.resize(248,root.height); nav.fills=old.fills; nav.paddingLeft=nav.paddingRight=20;nav.paddingTop=nav.paddingBottom=24;nav.itemSpacing=8;nav.layoutSizingVertical='FILL';created.push(nav.id);
 const brand=old.children.find(n=>n.type==='TEXT'); if(brand){await load(brand);const b=brand.clone();nav.appendChild(b);b.resize(208,b.height);created.push(b.id);}
 for(const a of defs[d.actor]){const b=navMaster.createInstance();nav.appendChild(b);b.name='Role menu · '+a[2];prop(b,'Label',a[L]);b.resize(208,44);b.layoutSizingHorizontal='FILL';b.counterAxisSizingMode='AUTO';b.layoutSizingVertical='HUG';if(a[2]===root.id)prop(b,'State','Selected');else link(b,a[2]);created.push(b.id);}
 removed.push(old.id);old.remove();
 const crumb=main.children.find(n=>n.name==='Breadcrumb trail');if(crumb){crumb.reactions=[];for(const t of crumb.findAllWithCriteria({types:['TEXT']})){t.reactions=[];changed.push(t.id);}changed.push(crumb.id);}
 if(d.key==='user-ops-settings'){
  for(const n of main.query('INSTANCE, FRAME').toArray())if(n.reactions.some(r=>(r.actions||[]).some(a=>a.destinationId===EXTERNAL.users||a.url?.includes('node-id='+EXTERNAL.users.replace(':','-'))))){if(n.type==='INSTANCE')prop(n,'Label',L===0?'В рабочую область':'Back to workspace');link(n,EXTERNAL.opsHome);}
 }
 if(d.key==='ops-readonly'){
  const b=main.query('INSTANCE[name="Data action · ops-queue"]').first();if(b)link(b,EXTERNAL.opsHome);
 }
 const allowed=new Set(ALLOWED[d.actor]);allowed.add(profile[d.actor]);
 const nodes=main.query('INSTANCE, FRAME, TEXT').toArray();
 for(const n of nodes){const a=n.reactions?.[0]?.actions?.[0];const match=a?.type==='URL'&&a.url?.includes('figma.com/proto/lxPP2um7FvIbt02K8eeH4T')?a.url.match(/[?&]node-id=(\d+)-(\d+)/):null;if(match)link(n,match[1]+':'+match[2]);}
 const all=nodes.filter(n=>n.reactions?.some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.navigation==='NAVIGATE'&&!allowed.has(a.destinationId))));
 let cases=main.children.find(n=>n.name==='Role handoff scenarios');
 for(const n of all){
  let p=n,already=false;while(p&&p!==main){if(/Prototype|Role handoff scenarios|Сценарии прототипа/.test(p.name)){already=true;break;}p=p.parent;}if(already)continue;
  if(n.name.startsWith('My account')||n===avatar)continue;
  if(!cases){const base=header.children.find(n=>n.type==='TEXT');const t=base.clone();main.appendChild(t);t.characters=L===0?'Отдельные учебные примеры · могут менять сотрудника; не рабочие переходы':'Independent prototype fixtures · may switch staff; not product navigation';t.resize(main.width-main.paddingLeft-main.paddingRight,t.height);t.textAutoResize='HEIGHT';created.push(t.id);cases=figma.createAutoLayout('HORIZONTAL');main.appendChild(cases);cases.name='Role handoff scenarios';cases.fills=[];cases.resize(t.width,44);cases.layoutSizingHorizontal='FILL';cases.layoutSizingVertical='HUG';cases.layoutWrap='WRAP';cases.itemSpacing=12;cases.counterAxisSpacing=12;created.push(cases.id);}
  const actions=n.reactions;
  if(n.type==='INSTANCE'&&/^(Action|Data action|Permitted actions|Открыть|Open|Review only)/.test(n.name)){cases.appendChild(n);n.primaryAxisSizingMode='AUTO';n.layoutSizingHorizontal='HUG';changed.push(n.id);}
  else {const b=buttonMaster.createInstance();cases.appendChild(b);prop(b,'Label',L===0?'Отдельный пример связанного экрана':'Separate related-screen fixture');prop(b,'Show icon',false);b.reactions=actions;b.name='Prototype actor handoff · '+n.id;n.reactions=[];created.push(b.id);changed.push(n.id);}
  moved.push({root:root.id,node:n.id,reason:'Explicit independent fixture instead of an implicit actor switch'});
 }
 root.resize(1440,Math.max(root.height,Math.ceil((main.y+Math.max(...main.children.filter(n=>n.visible).map(n=>n.y+n.height))+48)/40)*40));nav.layoutSizingVertical='FILL';changed.push(root.id);
 records.push({id:root.id,key:d.key,actor:d.actor,profile:profile[d.actor],avatar:avatar?.id,menu:nav.id});
}
for(const id of EXTERNAL.allProfiles){const root=await figma.getNodeByIdAsync(id);const main=root.children.find(n=>n.name.startsWith('Main'));const box=main.children.find(n=>n.name==='Permitted actions');if(box?.children[0]){const b=box.children[0];await load(b);prop(b,'Label',L===0?'Назад к рабочему экрану':'Back to work screen');b.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'BACK'}]}];changed.push(b.id);}}
const nb=nm.children.find(n=>n.name==='Permitted actions')?.children[0];if(nb){prop(nb,'Label',L===0?'Назад к рабочему экрану':'Back to work screen');nb.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'BACK'}]}];changed.push(nb.id);}
return{locale:LOCALE,createdNodeIds:created,mutatedNodeIds:[...new Set(changed)],removedNodeIds:removed,records,moved,noraProfile:nora.id};
