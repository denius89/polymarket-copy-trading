const page=await figma.getNodeByIdAsync(PAGE_ID);await figma.setCurrentPageAsync(page);figma.skipInvisibleInstanceChildren=false;
const changed=new Set(),created=[],fundRows=[],groupRows=[];
const vars=await figma.variables.getLocalVariablesAsync(),by=n=>vars.find(v=>v.name===n);
const labelStyle=(await figma.getLocalTextStylesAsync()).find(s=>s.name==='Controls/Button label');
function visible(n){for(let a=n;a&&a.type!=='PAGE';a=a.parent)if(a.visible===false)return false;return true;}
function isButton(n){return /^(Action\s*\/|Button\s*\/|GuestButton|buttonPrimary|buttonSecondary|buttonQuiet|Unavailable\s*\/)/i.test(n.name)&&!/Content group|Header help icon|notifications|Profile|Balance|Button\/Help|button\/view all|button\/all events/i.test(n.name);}
const nodes=page.findAllWithCriteria({types:['FRAME','INSTANCE']}).filter(n=>visible(n)&&isButton(n)).filter(n=>n.findAllWithCriteria({types:['TEXT']}).some(t=>visible(t)));
const texts=nodes.flatMap(n=>n.findAllWithCriteria({types:['TEXT']}).filter(visible));
const fonts=new Map();for(const t of texts)for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);for(const f of fonts.values())await figma.loadFontAsync(f);await figma.loadFontAsync(labelStyle.fontName);
const mobile=PAGE_ID==='29:2'||PAGE_ID==='33:2';
function color(n,role){const paint=(name,fallback)=>{const v=by(name);return v?figma.variables.setBoundVariableForPaint({type:'SOLID',color:fallback},'color',v):{type:'SOLID',color:fallback};};
 if(role==='primary'){n.fills=[paint('color/accent/default',{r:.45,g:.25,b:.9})];n.strokes=[];}
 else{n.fills=[paint('color/bg/surface',{r:.08,g:.09,b:.14})];n.strokes=[paint('color/border/default',{r:.17,g:.19,b:.25})];n.strokeWeight=1;}
 changed.add(n.id);
}
for(const n of nodes){
 const labels=n.findAllWithCriteria({types:['TEXT']}).filter(visible);if(!labels.length)continue;
 const oldW=n.width;
 n.layoutMode='HORIZONTAL';n.primaryAxisAlignItems='CENTER';n.counterAxisAlignItems='CENTER';n.primaryAxisSizingMode='FIXED';n.counterAxisSizingMode='FIXED';
 n.paddingLeft=16;n.paddingRight=16;n.paddingTop=0;n.paddingBottom=0;n.itemSpacing=8;n.cornerRadius=10;
 n.setBoundVariable('paddingLeft',by('spacing/4'));n.setBoundVariable('paddingRight',by('spacing/4'));n.setBoundVariable('itemSpacing',by('spacing/2'));n.setBoundVariable('cornerRadius',by('radius/md'));
 let natural=0;
 for(const t of labels){await t.setTextStyleIdAsync(labelStyle.id);t.textAlignHorizontal='CENTER';t.textAlignVertical='CENTER';t.textAutoResize='WIDTH_AND_HEIGHT';natural+=t.width;changed.add(t.id);}
 const icons=n.findAllWithCriteria({types:['FRAME','INSTANCE','VECTOR']}).filter(c=>/icon/i.test(c.name)&&c.width<=24&&c.height<=24);
 const required=natural+36+(icons.length?28:0);
 const maxW=n.parent.type==='FRAME'?Math.max(96,n.parent.width-(n.parent.paddingLeft||0)-(n.parent.paddingRight||0)):oldW;
 const width=Math.min(maxW,Math.max(96,oldW,required));
 for(const t of labels){t.textAutoResize='HEIGHT';t.resize(Math.max(32,width-32-(icons.length?28:0)),20);if(t.parent.layoutMode&&t.parent.layoutMode!=='NONE')t.layoutSizingHorizontal='FILL';}
 const height=Math.max(48,...labels.map(t=>t.height+24));
 n.resize(width,height);
 for(const group of n.children.filter(c=>c.type==='FRAME'&&/Content group/.test(c.name))){group.layoutMode='HORIZONTAL';group.primaryAxisAlignItems='CENTER';group.counterAxisAlignItems='CENTER';group.paddingLeft=0;group.paddingRight=0;group.paddingTop=0;group.paddingBottom=0;group.itemSpacing=8;group.resize(width-32,height);group.layoutSizingHorizontal='FILL';changed.add(group.id);}
 // Direct text labels fill the available content box; one line stays centered.
 for(const t of labels.filter(t=>t.parent===n))t.layoutSizingHorizontal='FILL';
 changed.add(n.id);
}
const funded=new Set();
for(const dep of nodes.filter(n=>n.findAllWithCriteria({types:['TEXT']}).some(t=>/^(Пополнить|Deposit)$/.test(t.characters)))){
 const parent=dep.parent;if(funded.has(parent.id))continue;
 const siblings=parent.children.filter(c=>c.type==='FRAME'||c.type==='INSTANCE');
 const withdraw=siblings.find(c=>c!==dep&&c.findAllWithCriteria({types:['TEXT']}).some(t=>/^(Вывести|Withdraw)$/.test(t.characters)));
 if(!withdraw)continue;funded.add(parent.id);
 let row=parent.layoutMode==='NONE'?parent.children.find(c=>c.name==='Actions/Funding'):parent;
 if(parent.layoutMode==='NONE'&&!row){row=figma.createAutoLayout('HORIZONTAL');row.name='Actions/Funding';parent.appendChild(row);created.push(row.id);row.fills=[];row.x=20;row.y=Math.min(dep.y,parent.height-68);row.resize(parent.width-40,48);}
 row.layoutMode='HORIZONTAL';row.primaryAxisAlignItems='MIN';row.counterAxisAlignItems='CENTER';row.itemSpacing=12;row.paddingLeft=0;row.paddingRight=0;row.paddingTop=0;row.paddingBottom=0;row.counterAxisSizingMode='AUTO';
 row.insertChild(0,dep);row.insertChild(1,withdraw);
 const width=mobile?(row.width-12)/2:Math.min(160,(row.width-12)/2);
 dep.resize(width,48);withdraw.resize(width,48);
 if(mobile){dep.layoutSizingHorizontal='FILL';withdraw.layoutSizingHorizontal='FILL';}else{dep.layoutSizingHorizontal='FIXED';withdraw.layoutSizingHorizontal='FIXED';}
 if(!/Unavailable|unavailable/.test(dep.name+parent.name)){color(dep,'primary');color(withdraw,'secondary');}
 for(const b of [dep,withdraw])for(const t of b.findAllWithCriteria({types:['TEXT']})){t.resize(Math.max(32,width-32),20);changed.add(t.id);}
 changed.add(row.id);changed.add(dep.id);changed.add(withdraw.id);
 fundRows.push({row:row.id,parent:parent.id,deposit:dep.id,withdraw:withdraw.id,width});
}
const parentGroups=[...new Set(nodes.map(n=>n.parent))].filter(p=>p.type==='FRAME'&&/^(Actions|Action area|Footer actions|Button group|Session actions)/i.test(p.name)&&p.name!=='Actions/Funding');
for(const row of parentGroups){
 const btns=row.children.filter(c=>nodes.includes(c));if(btns.length<2||btns.length>4||row.children.some(c=>visible(c)&&!btns.includes(c)))continue;
 if(funded.has(row.id))continue;
 const cancel=n=>n.findAllWithCriteria({types:['TEXT']}).some(t=>/^(Cancel|Back|Keep |Отмен|Назад|Оставить|Сохранить позицию)/i.test(t.characters));
 const sorted=[...btns].sort((a,b)=>Number(cancel(b))-Number(cancel(a)));
 row.layoutMode=mobile?'VERTICAL':'HORIZONTAL';row.itemSpacing=12;row.primaryAxisAlignItems='MIN';row.counterAxisAlignItems=mobile?'CENTER':'CENTER';row.primaryAxisSizingMode='AUTO';row.counterAxisSizingMode='FIXED';
 for(let i=0;i<sorted.length;i++){row.insertChild(i,sorted[i]);if(mobile){sorted[i].resize(Math.max(96,row.width),sorted[i].height);sorted[i].layoutSizingHorizontal='FILL';}}
 changed.add(row.id);groupRows.push(row.id);
}

return {page:PAGE_ID,changed:[...changed].join('|'),created,count:nodes.length,fundRows,groupRows,qa:{small:nodes.filter(n=>n.width<96||n.height<48).map(n=>n.id),labelsClipped:nodes.flatMap(n=>n.findAllWithCriteria({types:['TEXT']}).filter(visible).filter(t=>t.width>n.width-24||t.height>n.height-12).map(t=>t.id)).slice(0,20),reactionCount:nodes.reduce((s,n)=>s+n.reactions.length,0)}};
