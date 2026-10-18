// Inputs PAGE, LOCALE, DATA, PAIRS. Editable native instances; no new components.
const page=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(page);
const L=LOCALE==='RU'?0:1,field=L===0?'ru':'en';
const ids=Object.fromEntries(PAIRS.map(p=>[p.key,p[field]]));
ids.sessions=L===0?'1982:38062':'1982:38885';ids['user-noor']=L===0?'2210:21620':'2210:82672';ids['order-history']=L===0?'3014:58072':'3016:58059';
const source=await figma.getNodeByIdAsync(L===0?'3014:58256':'3016:58243');
const sm=source.children.find(n=>n.name==='Main'),panelT=sm.children.find(n=>n.name==='Context panel'),tableT=sm.children.find(n=>n.name==='Operation evidence and amounts'),headerT=tableT.children[0],footerT=sm.children.at(-1);
const [pc,sc,rowC]=await Promise.all(['113:207','113:209','2137:26727'].map(id=>figma.getNodeByIdAsync(id)));
const fonts=new Map();for(const n of [sm,pc,sc,rowC])for(const t of n.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const created=[],changed=[],removed=[],screens=[],links=[],checks=[];
function prop(n,key,val){const k=Object.keys(n.componentProperties).find(k=>k.split('#')[0]===key);if(k)n.setProperties({[k]:val});}
function target(n,to,kind){if(to===CURRENT)throw Error('Self navigation');n.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:to,navigation:'NAVIGATE',transition:null,preserveScrollPosition:false}]}];links.push({from:CURRENT,node:n.id,to,kind});}
function text(n,s){n.characters='';n.characters=s;n.textAutoResize='HEIGHT';changed.push(n.id);}
function buttonRow(main,items,name,selected){const a=figma.createAutoLayout('HORIZONTAL');a.name=name;a.fills=[];main.appendChild(a);a.resize(1144,44);a.layoutSizingHorizontal='FILL';a.layoutWrap='WRAP';a.itemSpacing=12;a.counterAxisSpacing=12;a.layoutSizingVertical='HUG';created.push(a.id);for(const it of items){const b=(it[2]===selected?pc:sc).createInstance();a.appendChild(b);b.name=name+' · '+it[2];prop(b,'Label',it[L]);prop(b,'Show icon',false);b.primaryAxisSizingMode='AUTO';b.layoutSizingHorizontal='HUG';if(ids[it[2]]!==CURRENT)target(b,ids[it[2]],name);else b.reactions=[];created.push(b.id);}return a;}
const tabs=[['Сводка','Overview','session-inspection'],['Позиции','Positions','session-positions'],['Заявки','Orders','session-orders'],['Действия трейдера','Trader actions','session-trader-actions'],['Решения','Decisions','session-decisions']];
const selected={overview:'session-inspection',positions:'session-positions',orders:'session-orders',activity:'session-trader-actions',decisions:'session-decisions'};
let CURRENT;
for(const d of DATA){
 const root=await figma.getNodeByIdAsync(ids[d.key]);CURRENT=root.id;
 const main=root.children.find(n=>n.name==='Main');
 for(const n of [...main.children])if(!['Context','Breadcrumb trail','Page heading'].includes(n.name)){removed.push(n.id);n.remove();}
 const heading=main.children.find(n=>n.name==='Page heading').findAllWithCriteria({types:['TEXT']});text(heading[0],d.title[L]);text(heading[1],d.hideTabs?(L===0?'U-DEMO-002 · Limitless · альтернативный пример · Paper Alpha: комиссия 0%':'U-DEMO-002 · Limitless · alternative example · Paper Alpha: fee 0%'):(L===0?'S-DEMO-002 · U-DEMO-002 · Polymarket · снимок 42 · Paper Alpha: комиссия 0%':'S-DEMO-002 · U-DEMO-002 · Polymarket · snapshot 42 · Paper Alpha: fee 0%'));
 const crumb=main.children.find(n=>n.name==='Breadcrumb trail');prop(crumb,'Section',d.key==='session-inspection'?(L===0?'Сессии':'Sessions'):(L===0?'Сессия S-DEMO-002':'Session S-DEMO-002'));prop(crumb,'Current',d.title[L]);changed.push(crumb.id);
 const crumbSection=crumb.findAllWithCriteria({types:['TEXT']}).find(n=>n.name==='Section');if(crumbSection)target(crumbSection,d.key==='session-inspection'||d.hideTabs?ids.sessions:ids['session-inspection'],'Breadcrumb');
 if(d.hideTabs)prop(crumb,'Section',L===0?'Сессии':'Sessions');
 if(!d.hideTabs)buttonRow(main,tabs,'Session sections',selected[d.tab]);
 const panel=panelT.clone();main.appendChild(panel);panel.name='Session context';prop(panel,'Title',L===0?'Контекст и актуальность':'Context and freshness');prop(panel,'Body',d.body[L]);panel.resize(1144,panel.height);panel.layoutSizingHorizontal='FILL';panel.primaryAxisSizingMode='AUTO';panel.layoutSizingVertical='HUG';
 for(const t of panel.findAllWithCriteria({types:['TEXT']})){const value=t.characters;t.resize(1102,t.height);text(t,value);t.layoutSizingHorizontal='FILL';}created.push(panel.id);
 if(d.filters){const label=footerT.clone();main.appendChild(label);label.name='Filter scope';text(label,L===0?'Период решений: 11:59:50–12:01 UTC · снимок 42':'Decision period: 11:59:50–12:01 UTC · snapshot 42');label.resize(1144,label.height);created.push(label.id);buttonRow(main,d.filters,'Decision filters',d.filterSelected);}
 const table=figma.createAutoLayout('VERTICAL');table.name='Session records';table.fills=tableT.fills;table.strokes=tableT.strokes;table.strokeWeight=tableT.strokeWeight;table.cornerRadius=tableT.cornerRadius;table.clipsContent=true;main.appendChild(table);table.resize(1144,100);table.layoutSizingHorizontal='FILL';table.primaryAxisSizingMode='AUTO';table.counterAxisSizingMode='FIXED';table.layoutSizingVertical='HUG';table.itemSpacing=0;created.push(table.id);
 const h=headerT.clone();table.appendChild(h);d.headers.forEach((v,i)=>prop(h,'Column '+(i+1),v[L]));h.resize(1142,48);h.primaryAxisSizingMode='FIXED';h.counterAxisSizingMode='FIXED';h.layoutSizingHorizontal='FILL';h.layoutSizingVertical='FIXED';created.push(h.id);
 for(const v of d.rows){const row=rowC.createInstance();table.appendChild(row);row.name='Record · '+v[L];['Title','Detail','Meta'].forEach((key,i)=>prop(row,key,v[L+i*2]));row.resize(1142,64);row.primaryAxisSizingMode='FIXED';row.counterAxisSizingMode='AUTO';row.layoutSizingHorizontal='FILL';row.layoutSizingVertical='HUG';created.push(row.id);const link=Object.entries(d.rowLinks||{}).find(([id])=>v[L].includes(id));if(link){target(row,ids[link[1]],'Record detail');const label=row.children.find(n=>n.type==='TEXT');if(label){label.textDecoration='UNDERLINE';changed.push(label.id);}}}
 for(let i=0;i<table.children.length;i++){const r=table.children[i],ts=r.children.filter(n=>n.type==='TEXT'),w=(1142-r.paddingLeft-r.paddingRight-(ts.length-1)*r.itemSpacing)/ts.length;for(const t of ts){const value=t.characters;t.resize(w,t.height);text(t,value);t.layoutSizingHorizontal='FILL';}checks.push({root:root.id,row:i,columns:ts.length});}
 if(d.empty){const wrap=figma.createAutoLayout('VERTICAL');table.appendChild(wrap);wrap.name='List state';wrap.fills=[];wrap.resize(1142,80);wrap.layoutSizingHorizontal='FILL';wrap.paddingLeft=wrap.paddingRight=20;wrap.paddingTop=wrap.paddingBottom=20;wrap.layoutSizingVertical='HUG';const e=panel.findAllWithCriteria({types:['TEXT']})[1].clone();wrap.appendChild(e);e.name='List state message';text(e,d.empty[L]);e.resize(1102,e.height);e.layoutSizingHorizontal='FILL';created.push(wrap.id,e.id);}
 if(d.actions.length)buttonRow(main,d.actions,'Read-only actions');
 if(d.scenarios?.length){const lab=footerT.clone();main.appendChild(lab);lab.name='Prototype scenarios label';text(lab,L===0?'Сценарии прототипа · учебные исходы, не рабочие команды':'Prototype scenarios · synthetic outcomes, not product commands');lab.resize(1144,lab.height);created.push(lab.id);buttonRow(main,d.scenarios,'Prototype scenarios');}
 const footer=footerT.clone();main.appendChild(footer);footer.name='Review disclaimer';text(footer,L===0?'Макет для вычитки · данные вымышлены · реальные операции выключены':'Design review only · synthetic data · real operations disabled');footer.resize(1144,footer.height);created.push(footer.id);
 root.resize(1440,Math.max(1120,Math.ceil((main.y+footer.y+footer.height+24)/40)*40));root.children[0].layoutSizingVertical='FILL';root.placeholder=false;changed.push(root.id);
 screens.push({key:d.key,id:root.id,rows:d.rows.length,tab:d.tab,height:root.height,placeholder:root.placeholder,table:table.id});
}
return {createdNodeIds:created,mutatedNodeIds:changed,removedNodeIds:removed,screens,links,checks};
