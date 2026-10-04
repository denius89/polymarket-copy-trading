await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(C.page));
function vis(n){while(n&&n.type!=='PAGE'){if(n.visible===false)return false;n=n.parent;}return true;}
const mutated=new Set(),created=new Set();
function mark(n){mutated.add(n.id);}
async function fonts(n){const fs=n.findAllWithCriteria({types:['TEXT']}).flatMap(t=>t.getStyledTextSegments(['fontName']).map(s=>s.fontName));await Promise.all([...new Map(fs.map(f=>[JSON.stringify(f),f])).values()].map(f=>figma.loadFontAsync(f)));}
async function txt(t,s){await Promise.all(t.getStyledTextSegments(['fontName']).map(v=>figma.loadFontAsync(v.fontName)));t.characters=s;mark(t);}
const pos=await figma.getNodeByIdAsync(C.pos),order=await figma.getNodeByIdAsync(C.order),fresh=await figma.getNodeByIdAsync(C.fresh);
await fonts(fresh);
const emptyName='Current / fresh-orders / '+C.lang+' / '+(C.mobile?'mobile':'desktop');
let empty=fresh.parent.children.find(n=>n.name===emptyName);
if(!empty){empty=fresh.clone();empty.name=emptyName;empty.x=fresh.x;empty.y=Math.max(...fresh.parent.children.filter(n=>n.id!==empty.id&&'height'in n).map(n=>n.y+n.height))+80;for(const n of [empty,...empty.findAll(()=>true)])created.add(n.id);if(fresh.parent.type==='SECTION'){fresh.parent.resizeWithoutConstraints(fresh.parent.width,Math.max(fresh.parent.height,empty.y+empty.height+80));mark(fresh.parent);}}
const pword=C.lang==='RU'?'Позиции':'Positions',oword=C.lang==='RU'?'Заявки':'Orders';
for(const t of empty.findAllWithCriteria({types:['TEXT']}).filter(vis)){
 if(/Nav|Navigation/.test(t.parent.name))continue;
 if(t.characters===pword)await txt(t,oword);
 else if(t.characters.includes('Позиции появятся'))await txt(t,'Заявки появятся после запуска копирования и отправки первого заказа.');
 else if(/Positions will appear|Positions appear/.test(t.characters))await txt(t,'Orders will appear after copying starts and the first order is submitted.');
}
function content(n){return n.findAll(x=>x.type==='FRAME'&&/^(Recovery\/(Content|Page content)|Page content)$/.test(x.name)&&vis(x)).at(-1);}
function nav(n,kind){return n.findAll(x=>x.name.endsWith('Nav/'+kind)&&vis(x)).at(-1);}
function clonePaint(src,dst){if('fills'in dst&&Array.isArray(src.fills)){dst.fills=JSON.parse(JSON.stringify(src.fills));mark(dst);}if('strokes'in dst&&Array.isArray(src.strokes)){dst.strokes=JSON.parse(JSON.stringify(src.strokes));mark(dst);}}
function styleNav(src,dst){if(!src||!dst)return;clonePaint(src,dst);const st=src.findAllWithCriteria({types:['TEXT']})[0],dt=dst.findAllWithCriteria({types:['TEXT']})[0];if(st&&dt)clonePaint(st,dt);const sv=src.findAllWithCriteria({types:['VECTOR','LINE']}).find(v=>Array.isArray(v.strokes)&&v.strokes.length);for(const d of dst.findAllWithCriteria({types:['VECTOR','LINE']}))if(sv)clonePaint(sv,d);}
const pnav=nav(pos,'positions'),neutral=nav(pos,'events');
for(const n of [order,empty]){styleNav(pnav,nav(n,'positions'));styleNav(neutral,nav(n,'events'));}
const sourceRow=await figma.getNodeByIdAsync('1037:23145');await fonts(sourceRow);
function go(id){return [{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,resetScrollPosition:false}],action:{type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,resetScrollPosition:false}}];}
async function tabs(n,isOrder,isFresh){const p=content(n);if(!p)throw Error('No visible content '+n.id);
let row=p.children.find(x=>x.name==='Position and order navigation');
if(!row){row=sourceRow.clone();p.insertChild(C.mobile?2:0,row);for(const x of [row,...row.findAll(()=>true)])created.add(x.id);mark(p);}
row.resize(C.mobile?350:1152,48);row.layoutSizingHorizontal='FILL';mark(row);
const btns=row.children.filter(x=>x.type==='INSTANCE');for(let i=0;i<btns.length;i++){const b=btns[i],selected=(i===1)===isOrder;const master=await figma.getNodeByIdAsync(selected?'113:240':'113:242');if(b.mainComponent.id!==master.id){b.swapComponent(master);mark(b);}const t=b.findAllWithCriteria({types:['TEXT']})[0];await txt(t,i===0?pword:oword);b.name='Button/'+(i===0?pword:oword);b.resize(C.mobile?171:160,48);b.layoutSizingHorizontal=C.mobile?'FILL':'FIXED';await b.setReactionsAsync((i===1)===isOrder?[]:go(isFresh?(i===0?fresh.id:empty.id):(i===0?pos.id:order.id)));for(const x of [b,...b.findAll(()=>true)])mark(x);}
return {screen:n.id,row:row.id,targets:[isFresh?fresh.id:pos.id,isFresh?empty.id:order.id],w:row.width,h:row.height};}
const rows=[];for(const n of [pos,order,fresh,empty])rows.push(await tabs(n,n===order||n===empty,n===fresh||n===empty));
const notif=await figma.getNodeByIdAsync(C.notif),profile=await figma.getNodeByIdAsync(C.profile);
for(const t of notif.findAllWithCriteria({types:['TEXT']}).filter(vis))if(t.characters===(C.lang==='RU'?'Уведомления':'Notifications'))await txt(t,C.lang==='RU'?'Журнал уведомлений':'Notification history');
for(const t of profile.findAllWithCriteria({types:['TEXT']}).filter(vis)){
const s=t.characters;
if(s==='Уведомления'||s==='Notifications'){
 const ancestor=t.parent.name==='Description'?t.parent.parent:t.parent;
 const raw=JSON.stringify(ancestor.reactions||[]);
 const isJournal=raw.includes(C.notif);
 await txt(t,C.lang==='RU'?(isJournal?'Журнал уведомлений':'Настройки уведомлений'):(isJournal?'Notification history':'Notification settings'));
}else if(s==='Сводки и уведомления'||s==='Summaries and notifications'||s==='Сводки')await txt(t,C.lang==='RU'?'Настройки уведомлений':'Notification settings');
}
for(const t of figma.currentPage.findAllWithCriteria({types:['TEXT']}).filter(vis)){if(t.characters==='Сводки и уведомления'||t.characters==='Summaries and notifications'){
let root=t;while(root.parent&&root.parent.type!=='SECTION'&&root.parent.type!=='PAGE')root=root.parent;
if(/notifications-(weekly|daily)/.test(root.name))await txt(t,C.lang==='RU'?'Настройки уведомлений':'Notification settings');
}}
if(C.lang==='EN'&&!C.mobile){
 const template=JSON.parse(JSON.stringify((await figma.getNodeByIdAsync('1037:23087')).reactions));
 function replace(o){if(!o||typeof o!=='object')return;for(const [k,v] of Object.entries(o)){if(k==='destinationId'&&v==='905:9162')o[k]=C.pos;else if(k==='destinationId'&&v==='955:3698')o[k]=C.fresh;else replace(v);}}
 replace(template);for(const n of figma.currentPage.findAllWithCriteria({types:['INSTANCE']}).filter(x=>vis(x)&&x.name.endsWith('Nav/positions'))){await n.setReactionsAsync(template);mark(n);}
}
return {page:C.page,createdNodeIds:[...created],mutatedNodeIds:[...mutated],empty:{id:empty.id,x:empty.x,y:empty.y,w:empty.width,h:empty.height},rows};
