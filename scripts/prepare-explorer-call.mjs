import fs from 'node:fs';
const cfg=JSON.parse(process.argv[2]);
const all=JSON.parse(fs.readFileSync('design/interactive-fixtures-2026-10-02.json','utf8'));
let data={synthetic:true,fixtureId:all.fixtureId,contexts:all.contexts};
for(const k of ['traders','positions','orders','events','ledger','notifications','tickets','faq','messages','markets'])data[k]=all[k].map(o=>({id:o.id}));
const fields={traders:['id','name','venue','historyDays','minimumBudgetCents','publicPnlCents','activityBand','address','periods'],positions:['id','marketId','status','quantity','costBasisCents','markValueCents','realizedPnlCents','unrealizedPnlCents','outcomeId'],orders:['id','marketId','side','status','timestamp','quantity','filledQuantity','remainingQuantity','reservedCents','limitPriceCents','signalId','positionId'],events:['id','kind','status','timestamp','marketId','requiresAttention','reason','relatedOrderId','relatedPositionId'],ledger:['id','kind','marketId','timestamp','quantity','priceCents','feeCents','orderId','positionId'],notifications:['id','eventId','read'],tickets:['id','subject','status','eventId','conversationId'],faq:['id','question','answer','questionRu','answerRu','category'],messages:['id','author','timestamp','text','textRu'],markets:['id','label','labelRu','questionRu','questionEn','outcomes','synthetic']};
function full(k){data[k]=all[k].map(o=>Object.fromEntries(fields[k].filter(f=>o[f]!==undefined).map(f=>[f,o[f]])));if(k==='traders')for(const t of data[k])if(t.periods)t.periods=Object.fromEntries(Object.entries(t.periods).map(([p,v])=>[p,Object.fromEntries(['available','publicPnlCents','turnoverCents','closedTrades','successBasisPoints','drawdownBasisPoints','chartPoints'].map(f=>[f,v[f]]))]));}
full('markets');
if(cfg.phase==='catalog')full('traders');
if(cfg.phase==='positions-orders'){full('positions');full('orders');}
if(cfg.phase==='events')full('events');
if(cfg.phase==='funds-notifications'){full('ledger');full('events');full('notifications');data.events=data.events.filter(e=>data.notifications.some(n=>n.eventId===e.id));}
if(cfg.phase==='help-details'){
 if(cfg.part==='lists'){full('tickets');full('faq');}
 if(cfg.part==='profiles')full('traders');
 if(cfg.part==='conversation')full('messages');
 for(const k of cfg.detailKinds||[]){full({position:'positions',order:'orders',event:'events',operation:'ledger',ticket:'tickets',faq:'faq'}[k]);if(['order','event','operation'].includes(k))full('positions');if(['event','operation'].includes(k))full('orders');if(k==='ticket')full('events');}
}
if(cfg.phase==='help-details' && cfg.detailKinds?.length){
 const kinds=cfg.detailKinds;
 function roots(k,keys){data[k]=data[k].map((o,i)=>i===0?o:Object.fromEntries(keys.filter(f=>o[f]!==undefined).map(f=>[f,o[f]])));}
 if(kinds.includes('event'))roots('events',['id','relatedOrderId','relatedPositionId']);
 if(kinds.includes('operation'))roots('ledger',['id','orderId','positionId']);
 if(kinds.includes('order')&&!kinds.includes('event')&&!kinds.includes('operation'))roots('orders',['id','positionId']);
 if(kinds.includes('ticket'))data.events=data.events.filter(e=>data.tickets.some(t=>t.eventId===e.id));
 if(kinds.includes('faq'))roots('faq',['id']);
}
if(cfg.phase==='home-wire')full('orders');
const src=fs.readFileSync('design/qa-2026-10-02/build-interactive-data.js','utf8');
const markers=[...src.matchAll(/\nif\(CONFIG.phase==='([^']+)'\)\{/g)];
const start=markers.findIndex(m=>m[1]===cfg.phase);if(start<0)throw Error('Unknown phase');
const common=src.slice(0,markers[0].index);
const ret=src.slice(src.lastIndexOf('\nreturn {phase:'));
const block=src.slice(markers[start].index,start+1<markers.length?markers[start+1].index:src.lastIndexOf('\nreturn {phase:'));
let code=(common+block+ret).replace(/const CONFIG = .*?;\n/,'const CONFIG = '+JSON.stringify(cfg)+';\n').replace('const DATA = null;','const DATA = '+JSON.stringify(data)+';');
if(cfg.phase!=='catalog'){const a=code.indexOf("if(kind==='trader'){for(");const b=code.indexOf("if(kind==='ticket')actions.push",a);if(a>=0&&b>a)code=code.slice(0,a)+code.slice(b);}
let needed=new Set();
if(cfg.phase==='catalog')needed.add('trader');
if(cfg.phase==='positions-orders')needed=new Set(['position','order']);
if(cfg.phase==='events')needed.add('event');
if(cfg.phase==='funds-notifications')needed=new Set(['operation','event']);
if(cfg.phase==='home-wire')needed.add('order');
if(cfg.phase==='help-details'){needed=new Set(cfg.detailKinds||[]);if(cfg.part==='lists')needed.add('ticket');if(needed.has('event')||needed.has('operation')){needed.add('order');needed.add('position');}if(needed.has('order'))needed.add('position');if(needed.has('ticket'))needed.add('event');}
const a=code.indexOf('function item('),b=code.indexOf('const labels=',a);let itemCode=code.slice(a,b);
const branches=['trader','position','order','event','operation','ticket'];
for(let i=branches.length-1;i>=0;i--){const k=branches[i];if(needed.has(k))continue;const from=itemCode.indexOf("if(kind==='"+k+"')");if(from<0)continue;let to=itemCode.indexOf("\nif(kind==='",from+1);if(to<0)to=itemCode.indexOf('\nreturn {title:o.question',from);if(to>from)itemCode=itemCode.slice(0,from)+itemCode.slice(to);}
code=code.slice(0,a)+itemCode+code.slice(b);
new Function('return async function(){'+code+'}')();
if(code.length>50000)throw Error('Code exceeds provider cap: '+code.length);
process.stdout.write(JSON.stringify({code,length:code.length}));
