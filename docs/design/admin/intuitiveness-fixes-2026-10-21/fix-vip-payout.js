await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const made=[], changed=[], checks=[];
const sample=await figma.getNodeByIdAsync('1982:37932');
async function fonts(n){const ts=n.type==='TEXT'?[n]:n.findAllWithCriteria({types:['TEXT']});const seen=new Set();for(const t of ts)for(const s of t.getStyledTextSegments(['fontName'])){const key=JSON.stringify(s.fontName);if(!seen.has(key)){await figma.loadFontAsync(s.fontName);seen.add(key);}}}
await fonts(sample);
async function setText(n,s){await fonts(n);n.characters=s;changed.push(n.id);}
async function panel(main,name,title,body,index){let p=main.children.find(c=>c.name===name);if(!p){p=sample.clone();p.name=name;main.insertChild(index,p);made.push(p.id,...p.findAll(()=>true).map(t=>t.id));}const ts=p.findAllWithCriteria({types:['TEXT']});for(const t of ts)await fonts(t);ts[0].setBoundVariable('characters',null);ts[1].setBoundVariable('characters',null);ts[0].characters=title;ts[1].characters=body;ts[1].textAutoResize='HEIGHT';ts[1].resize(p.width-42,ts[1].height);p.resize(main.width-48,Math.max(...ts.map(t=>t.y+t.height))+21);changed.push(p.id,...ts.map(t=>t.id));return p;}
function fit(n,main){const bottom=Math.max(...main.children.filter(c=>c.visible).map(c=>c.y+c.height))+32;main.resize(main.width,Math.max(n.height,bottom));n.resize(n.width,Math.max(n.height,main.height));const side=n.children.find(c=>c!==main&&c.x===0);if(side)side.resize(side.width,n.height);changed.push(n.id,main.id,...(side?[side.id]:[]));}
for(const id of ['1982:37913','1982:37945','1982:37972','1982:38001','1982:38026','1982:38736','1982:38768','1982:38795','1982:38824','1982:38849']){
const n=await figma.getNodeByIdAsync(id),main=n.children.find(c=>c.x===248),en=n.name.startsWith('EN');
const hi=main.children.findIndex(c=>c.name==='Page heading');
const p=await panel(main,'UX01 · VIP recipient',en?'Demo Atlas · U-DEMO-001 · User VIP':'Demo Atlas · U-DEMO-001 · Пользовательский VIP',en?'Recipient of user terms · Limitless. Paper Alpha: service fee 0%.\nPartner terms are unchanged. One owner applies user VIP.':'Получатель пользовательских условий · Limitless. Paper Alpha: комиссия сервиса 0%.\nПартнёрские условия не меняются. Пользовательский VIP назначает один владелец.',hi+1);
fit(n,main);checks.push({id,recipient:p.id,name:n.name});
}
for(const id of ['2003:713','2003:778','2004:806','2007:713','2007:778','2008:596']){
const n=await figma.getNodeByIdAsync(id),main=n.children.find(c=>c.x===248),en=n.name.startsWith('EN'),second=/second-review/.test(n.name),table=main.children.find(c=>c.name==='Money confirmation values');
if(!table)throw Error('No confirmation table '+id);
const rows=table.children.filter(c=>'findAllWithCriteria'in c).map(r=>({node:r,ts:r.findAllWithCriteria({types:['TEXT']})})).filter(r=>r.ts.length===3);
const find=(ru,english)=>rows.find(r=>r.ts[0].characters===ru||r.ts[0].characters===english);
const dataRows=rows.filter(r=>r.node.name!=='Table column headings');const src=dataRows[1];
const dst=dataRows[2];
const network=dataRows[3];
const money=dataRows[4];
if(!src||!dst||!network||!money)throw Error('Unexpected rows '+id+' '+rows.map(r=>r.ts[0].characters).join('|'));
const amount=money.ts[1].characters.match(/[\d.]+/g);if(!amount||amount.length<3)throw Error('Amounts absent '+id);
const sumBody=en?'Partner receives: '+amount[0]+' USDT\nTransfer fee: '+amount[1]+' USDT · '+money.ts[2].characters+'\nSource debit: '+amount[2]+' USDT':'Получит партнёр: '+amount[0]+' USDT\nКомиссия перевода: '+amount[1]+' USDT · '+money.ts[2].characters+'\nСпишется с источника: '+amount[2]+' USDT';
const route=(en?'Source: ':'Источник: ')+src.ts[2].characters+'\n'+src.ts[1].characters+'\n'+(en?'Recipient: ':'Получатель: ')+dst.ts[2].characters+'\n'+dst.ts[1].characters+'\n'+network.ts[1].characters+'\n'+network.ts[2].characters;
let idx=main.children.indexOf(table);await panel(main,'UX02 · Transfer amounts',en?'Full payout · amounts':'Полная выплата · суммы',sumBody,idx++);await panel(main,'UX02 · Full recipient details',en?'Verify complete transfer details':'Проверьте реквизиты целиком',route,idx++);
const sourceAddress=src.ts[1].characters,recipientAddress=dst.ts[1].characters;

for(const r of rows){if(/Снимок \/ срок действия|Snapshot \/ validity|Snapshot \/ expiry/.test(r.ts[0].characters)){await setText(r.ts[0],en?'Calculation snapshot':'Снимок расчёта');await setText(r.ts[2],en?'Approval expiry is not specified in this demo; it must be verified before sending. Parameter changes invalidate approval.':'Срок согласия в демо не задан; перед отправкой его необходимо проверить. Изменения отменяют согласие.');r.node.resize(r.node.width,96);}}
const action=main.findAllWithCriteria({types:['INSTANCE']}).find(c=>c.name===(second?'Action · second-approved':'Action · accepted'));
if(action){const t=action.findAllWithCriteria({types:['TEXT']})[0];await setText(t,second?(en?'Save second approval':'Сохранить второе согласие'):(en?'Confirm payout request':'Подтвердить заявку на выплату'));}
for(const r of [src,dst,network,money]){r.node.visible=false;changed.push(r.node.id);}table.resize(table.width,Math.max(100,table.children.filter(c=>c.visible).reduce((s,c)=>s+c.height,0)+16));fit(n,main);checks.push({id,source:sourceAddress,recipient:recipientAddress,amounts:amount.slice(0,3),second});
}
return {createdNodeIds:made,mutatedNodeIds:[...new Set(changed)],checks};
