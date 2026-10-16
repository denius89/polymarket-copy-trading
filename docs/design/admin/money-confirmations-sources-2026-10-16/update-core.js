
const page=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(page);figma.skipInvisibleInstanceChildren=false;
const ids=[TEMPLATE,"2867:45501","2867:45844","2867:45762","2867:45783","2203:25356","2137:26727","2010:1133","2010:1134","2019:5","113:207","113:209"];
const deps=await Promise.all(ids.map(id=>figma.getNodeByIdAsync(id)));const [template,panelT,tableT,actionsT,footT,headerT,rowC,fieldsT,fieldrowT,fieldC,primaryC,secondaryC]=deps;
const fonts=new Map();for(const d of deps){if(!d)throw Error("missing dependency");const ts=d.type==="TEXT"?[d]:d.findAllWithCriteria({types:["TEXT"]});for(const t of ts)for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);}
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const created=[],mutated=[],removed=[],out=[],map={};const L=LOCALE==="RU"?0:1;
for(const n of page.children)if(n.type==="FRAME"&&n.name.startsWith(LOCALE+" · ")){const key=n.name.split(" · ")[1];if(!map[key])map[key]=n;}
function prop(n,k,val){const key=Object.keys(n.componentProperties).find(x=>x.split("#")[0]===k);if(key)n.setProperties({[key]:val});}
function wraptexts(n){for(const t of n.findAllWithCriteria({types:["TEXT"]})){if(!t.visible)continue;t.textAutoResize="HEIGHT";const parent=t.parent;const width=parent.layoutMode==="HORIZONTAL"?t.width:parent.width-(parent.paddingLeft||0)-(parent.paddingRight||0);t.resize(Math.max(width,1),t.height);t.textAutoResize="HEIGHT";}}
function clear(n){for(const c of [...n.children]){removed.push(c.id);c.remove();}}
const nextY=Math.max(...page.children.filter(n=>"height" in n).map(n=>n.y+n.height))+200;
for(let i=0;i<DATA.length;i++){
 const d=DATA[i];
 const root=await figma.getNodeByIdAsync(d.ids[L]);root.name=LOCALE+" · "+d.key+" · "+d.title[L];root.resize(1440,1120);mutated.push(root.id);map[d.key]=root;
 const main=root.children.find(n=>n.name==="Main");const preserve=["Context","Breadcrumb trail","Page heading"];for(const n of [...main.children])if(!preserve.includes(n.name)){removed.push(n.id);n.remove();}
 const ctx=main.children.find(n=>n.name==="Context");const actor=ctx.children.find(n=>n.type==="TEXT");actor.characters=L===0?"Рабочее пространство · Владелец "+(d.role||"A"):"Workspace · Owner "+(d.role||"A");mutated.push(actor.id);
 const crumb=main.children.find(n=>n.name==="Breadcrumb trail");prop(crumb,"Current",d.title[L]);prop(crumb,"Section",L===0?"Финансы":"Finance");mutated.push(crumb.id);
 const h=main.children.find(n=>n.name==="Page heading");const ht=h.findAllWithCriteria({types:["TEXT"]});ht[0].characters=d.title[L];ht[1].characters=L===0?"Учебные данные · Paper Alpha: комиссия 0% · реальные отправки выключены":"Synthetic data · Paper Alpha: service fee 0% · real sending disabled";mutated.push(...ht.map(t=>t.id));
 const panel=panelT.clone();main.appendChild(panel);prop(panel,"Title",L===0?"Контекст":"Context");prop(panel,"Body",d.body[L]);panel.resize(1144,panel.height);panel.layoutSizingHorizontal="FILL";wraptexts(panel);panel.primaryAxisSizingMode="AUTO";panel.layoutSizingVertical="HUG";created.push(panel.id);
 if(d.fields?.length){
  const fs=fieldsT.clone();clear(fs);fs.name="Source configuration fields";main.appendChild(fs);fs.resize(1144,100);fs.layoutSizingHorizontal="FILL";fs.primaryAxisSizingMode="AUTO";fs.layoutSizingVertical="HUG";created.push(fs.id);
  for(let j=0;j<d.fields.length;j+=3){
   const fr=fieldrowT.clone();clear(fr);fs.appendChild(fr);fr.resize(1144,96);fr.layoutSizingHorizontal="FILL";fr.primaryAxisSizingMode="FIXED";fr.counterAxisSizingMode="AUTO";fr.layoutSizingVertical="HUG";created.push(fr.id);
   for(const f of d.fields.slice(j,j+3)){
    const fi=fieldC.createInstance();fr.appendChild(fi);fi.setProperties({Kind:f.kind,State:"Filled"});prop(fi,"Label",f.label[L]);prop(fi,"Value",f.value[L]);prop(fi,"Hint",f.hint?.[L]||"");
    if(d.notice&&(f.label[0]===d.notice.field)){fi.setProperties({State:"Error"});prop(fi,"Value",d.notice.value);prop(fi,"Hint",d.notice.hint[L]);}
    fi.name="Field · "+f.label[L];fi.resize((1144-32)/3,96);fi.layoutSizingHorizontal="FIXED";fi.layoutSizingVertical="HUG";wraptexts(fi);created.push(fi.id);
   }
  }
 }
 if(d.rows?.length){
  const table=tableT.clone();clear(table);table.name="Money confirmation values";main.appendChild(table);table.resize(1144,100);table.layoutSizingHorizontal="FILL";table.itemSpacing=0;table.primaryAxisSizingMode="AUTO";table.layoutSizingVertical="HUG";created.push(table.id);
  const th=headerT.clone();table.appendChild(th);["Parameter","Value / state","Note / context"].forEach((v,i)=>prop(th,"Column "+(i+1),L===0?["Параметр","Значение / состояние","Примечание / контекст"][i]:v));th.resize(1144,48);created.push(th.id);
  const sp=await figma.variables.getVariableByIdAsync("VariableID:2:52");
  for(const r of d.rows){
   const rr=rowC.createInstance();table.appendChild(rr);prop(rr,"Title",r[L]);prop(rr,"Detail",r[2+L]);prop(rr,"Meta",r[4+L]);rr.setBoundVariable("paddingTop",sp);rr.setBoundVariable("paddingBottom",sp);rr.resize(1144,48);wraptexts(rr);rr.primaryAxisSizingMode="AUTO";rr.counterAxisSizingMode="AUTO";rr.layoutSizingVertical="HUG";created.push(rr.id);
  }
  table.primaryAxisSizingMode="AUTO";table.layoutSizingVertical="HUG";
 }
 const actions=actionsT.clone();clear(actions);main.appendChild(actions);actions.resize(1144,44);actions.layoutSizingHorizontal="FILL";actions.layoutWrap="WRAP";actions.counterAxisSpacing=12;actions.counterAxisSizingMode="AUTO";actions.layoutSizingVertical="HUG";actions.name="Actions";created.push(actions.id);
 for(let j=0;j<d.actions.length;j++){const a=d.actions[j],b=(j===0?primaryC:secondaryC).createInstance();actions.appendChild(b);prop(b,"Label",a[L]);prop(b,"Show icon",false);b.name="Action · "+a[2];b.primaryAxisSizingMode="AUTO";b.layoutSizingHorizontal="HUG";created.push(b.id);}
 const ft=footT.clone();main.appendChild(ft);ft.characters=L===0?"Дизайн-прототип · вымышленные адреса и суммы · операции не выполняются":"Design prototype · synthetic addresses and amounts · no operations are executed";created.push(ft.id);
 const bottom=ft.y+ft.height+24;if(bottom>1120)root.resize(1440,Math.ceil(bottom/40)*40);
 out.push({key:d.key,id:root.id,name:root.name,width:root.width,height:root.height,fields:d.fields?.length||0,rows:d.rows?.length||0});
}
const links=[];for(const d of DATA){const root=map[d.key];for(const a of d.actions){const b=root.findAllWithCriteria({types:["INSTANCE"]}).find(n=>n.name==="Action · "+a[2]);const dest=map[a[2]];if(!dest)throw Error("missing destination "+a[2]);b.reactions=[{trigger:{type:"ON_CLICK"},actions:[{type:"NODE",destinationId:dest.id,navigation:"NAVIGATE",transition:null,preserveScrollPosition:false}]}];mutated.push(b.id);links.push([root.id,b.id,dest.id]);}}
const types={},imageNodes=[],family=new Set();for(const s of out){const r=map[s.key];for(const n of r.findAll(()=>true)){types[n.type]=(types[n.type]||0)+1;if(Array.isArray(n.fills)&&n.fills.some(f=>f.type==="IMAGE"))imageNodes.push(n.id);if(n.type==="TEXT")for(const x of n.getStyledTextSegments(["fontName"]))family.add(x.fontName.family);}}
return {page:PAGE,locale:LOCALE,createdNodeIds:created,mutatedNodeIds:mutated,removedNodeIds:removed,screens:out,links,types,imageNodes,fontFamilies:[...family],totalRoots:page.children.filter(x=>x.type==="FRAME").length};
