// Figma-only finishing and readback. Inputs: PAGE, LOCALE, ROWS, ALLOWED, EXTERNAL, EMERGENCY.
const page=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(page);
const L=LOCALE==='RU'?0:1,changed=[],created=[],removed=[],records=[];
async function fonts(n){for(const t of n.type==='TEXT'?[n]:n.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))await figma.loadFontAsync(s.fontName);}
function label(n,value){const k=Object.keys(n.componentProperties).find(x=>x.split('#')[0]==='Label');if(k)n.setProperties({[k]:value});changed.push(n.id);}
function nav(n,to){n.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:to,navigation:'NAVIGATE',transition:null,resetScrollPosition:true}]}];changed.push(n.id);}
const start=await figma.getNodeByIdAsync(EXTERNAL.feedback),sm=start.children.find(n=>n.name.startsWith('Main'));
const sh=sm.children.find(n=>n.name==='Context'),av=sh.children.find(n=>n.type==='INSTANCE');
const nora=av.reactions[0].actions[0].destinationId;
const own={...EXTERNAL.profiles,'nora-ops':nora};ALLOWED['nora-ops'].push(nora);
const limited=await figma.getNodeByIdAsync(own.limited),lm=limited.children.find(n=>n.name.startsWith('Main')),lc=lm.children.find(n=>n.name==='Context').children.find(n=>n.type==='TEXT');await fonts(lc);
lc.characters=L===0?'Нора Азиз · STAFF-203 · ASG-DEMO-41 · ограниченный учебный снимок':'Nora Aziz · STAFF-203 · ASG-DEMO-41 · limited assignment fixture';changed.push(lc.id);
for(const id of [...EXTERNAL.allProfiles,nora]){
 const r=await figma.getNodeByIdAsync(id),m=r.children.find(n=>n.name.startsWith('Main')),box=m.children.find(n=>n.name==='Permitted actions'),b=box.children[0];await fonts(b);label(b,L===0?'Назад к рабочему экрану':'Back to work screen');b.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'BACK'}]}];changed.push(b.id);
}
const ro=ROWS.find(x=>x.key==='ops-readonly'),rr=await figma.getNodeByIdAsync(ro.id),rm=rr.children.find(n=>n.name.startsWith('Main'));
const back=await figma.getNodeByIdAsync(L===0?'2414:120409':'2414:123829');await fonts(back);
const card=rm.children.find(n=>n.name.startsWith('INC-DEMO-03')&&'children'in n),box=card.children.find(n=>n.name==='Actions');box.appendChild(back);back.primaryAxisSizingMode='AUTO';back.layoutSizingHorizontal='HUG';label(back,L===0?'В рабочую область':'Back to workspace');nav(back,EXTERNAL.opsHome);
for(const n of [...rm.children])if(n.name==='Role handoff scenarios'&&!n.children.length){removed.push(n.id);n.remove();for(const t of [...rm.children])if(t.type==='TEXT'&&/^(Отдельные учебные примеры|Independent prototype fixtures)/.test(t.characters)){removed.push(t.id);t.remove();}}
const er=await figma.getNodeByIdAsync(EMERGENCY),em=er.children.find(n=>n.name.startsWith('Main')),targets=new Set([EXTERNAL.tech,EXTERNAL.deposits,EXTERNAL.withdrawals,EXTERNAL.payouts]);
let group=em.children.find(n=>n.name==='Prototype role handoffs · Nora operations');
if(!group){const t=em.children[0].children.find(n=>n.type==='TEXT').clone();await fonts(t);em.appendChild(t);t.name='Prototype role handoffs label';t.characters=L===0?'Учебные примеры Норы · отдельное операционное назначение; не переключение рабочего аккаунта':'Nora review fixtures · independent operations assignment; not a workspace account switch';t.resize(1144,t.height);t.textAutoResize='HEIGHT';t.layoutSizingHorizontal='FILL';t.layoutSizingVertical='HUG';created.push(t.id);group=figma.createAutoLayout('HORIZONTAL');em.appendChild(group);group.name='Prototype role handoffs · Nora operations';group.fills=[];group.resize(1144,44);group.layoutSizingHorizontal='FILL';group.layoutSizingVertical='HUG';group.layoutWrap='WRAP';group.itemSpacing=12;group.counterAxisSpacing=12;created.push(group.id);}
for(const n of em.query('INSTANCE, FRAME').toArray())if(n!==group&&n.reactions?.some(r=>(r.actions||[]).some(a=>targets.has(a.destinationId)))){group.appendChild(n);n.primaryAxisSizingMode='AUTO';n.layoutSizingHorizontal='HUG';changed.push(n.id);}
for(const d of [...ROWS,{id:nora,key:'role-profile-nora-operations',actor:'nora-ops'}]){
 const r=await figma.getNodeByIdAsync(d.id),m=r.children.find(n=>n.name.startsWith('Main'));
 for(const t of m.children.filter(n=>n.type==='TEXT'&&/^(Отдельные учебные примеры|Independent prototype fixtures)/.test(n.characters))){await fonts(t);t.textAutoResize='HEIGHT';t.layoutSizingHorizontal='FILL';t.layoutSizingVertical='HUG';changed.push(t.id);}
 const header=m.children.find(n=>n.name==='Context'||n.name==='Account header')||m.children[0],a=header.children.find(n=>n.type==='INSTANCE');
 const menu=r.children.find(n=>n.name==='Navigation'),allowed=new Set([...ALLOWED[d.actor],own[d.actor]]),cross=[],cases=[];
 const all=m.query('INSTANCE, FRAME, TEXT').toArray();
 for(const n of all)for(const re of n.reactions||[])for(const action of re.actions||[]){if(action.type!=='NODE'||action.navigation!=='NAVIGATE'||allowed.has(action.destinationId))continue;let p=n,example=false;while(p&&p!==m){if(/Prototype|Role handoff scenarios/.test(p.name)){example=true;break;}p=p.parent;}(example?cases:cross).push({id:n.id,name:n.name,to:action.destinationId});}
 const navTargets=menu.children.flatMap(n=>(n.reactions||[]).flatMap(re=>(re.actions||[]).filter(a=>a.type==='NODE').map(a=>a.destinationId)));
 const avatarTo=a?.reactions?.[0]?.actions?.[0]?.destinationId;
 const height=Math.max(1200,Math.ceil((m.y+Math.max(...m.children.filter(n=>n.visible).map(n=>n.y+n.height))+48)/40)*40);r.resize(1440,height);menu.layoutSizingVertical='FILL';changed.push(r.id);
 records.push({id:r.id,key:d.key,actor:d.actor,profile:own[d.actor],avatarTo,avatarHidden:a?!a.visible:true,navTargets,ordinaryCrosses:cross,prototypeExamples:cases.length});
}
er.resize(1440,Math.max(1200,Math.ceil((em.y+Math.max(...em.children.filter(n=>n.visible).map(n=>n.y+n.height))+48)/40)*40));changed.push(er.id);
return{locale:LOCALE,createdNodeIds:created,mutatedNodeIds:[...new Set(changed)],removedNodeIds:removed,noraProfile:nora,records,returnTarget:back.reactions[0].actions[0].destinationId};
