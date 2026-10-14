
const page=await figma.getNodeByIdAsync("1981:29");await figma.setCurrentPageAsync(page);
const created=[],mutated=[],frames=[],links=[];const track=n=>{created.push(n.id);return n;};
const styles=await figma.getLocalTextStylesAsync(),styleMap=new Map(styles.map(s=>[s.name,s]));for(const s of styles)await figma.loadFontAsync(s.fontName);
const vs=await figma.variables.getLocalVariablesAsync(),vm=new Map(vs.map(v=>[v.name,v])),vi=new Map(vs.map(v=>[v.id,v]));const cs=await figma.variables.getLocalVariableCollectionsAsync(),cm=new Map(cs.map(c=>[c.id,c]));
function resolve(v){const c=cm.get(v.variableCollectionId),x=v.valuesByMode[c.modes.find(m=>m.name==='Dark')?.modeId??c.defaultModeId];return x?.type==='VARIABLE_ALIAS'?resolve(vi.get(x.id)):x;}
function fill(name){const v=vm.get(name),rgb=resolve(v);return figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:rgb.r,g:rgb.g,b:rgb.b}},'color',v);}
function bind(n,k,name){n.setBoundVariable(k,vm.get(name));}
function box(parent,name,dir,w,color){const n=track(figma.createAutoLayout(dir));parent.appendChild(n);n.name=name;n.resize(w,80);n.fills=color?[fill(color)]:[];n.primaryAxisSizingMode=dir==='VERTICAL'?'AUTO':'FIXED';n.counterAxisSizingMode=dir==='VERTICAL'?'FIXED':'AUTO';bind(n,'itemSpacing','spacing/4');return n;}
function text(parent,label,style='Body/Small',w=parent.width,color='color/text/primary'){const t=track(figma.createText());parent.appendChild(t);t.name=label.slice(0,55);t.textStyleId=styleMap.get(style).id;t.characters=label;t.textAutoResize='HEIGHT';t.resize(w,t.height);t.fills=[fill(color)];return t;}
const masters={};for(const [key,id]of Object.entries({sidebar:'1981:16',nav:'2032:67',navSelected:'2032:74',primary:'2081:38',secondary:'2081:65',danger:'2081:119',field:'2081:150',fieldError:'2081:155',check:'2081:486',unchecked:'2081:483',disabledCheck:'2081:485',alertInfo:'2081:580',alertSuccess:'2081:581',alertWarning:'2081:582',alertDanger:'2081:583',status:'2081:356',metadata:'2137:26727'}))masters[key]=await figma.getNodeByIdAsync(id);
function inst(parent,key,props,width){const n=track(masters[key].createInstance());parent.appendChild(n);const vals={};for(const [name,value]of Object.entries(props)){const prop=Object.keys(n.componentProperties).find(p=>p.split('#')[0]===name);if(prop)vals[prop]=value;}n.setProperties(vals);if(width)n.resize(width,n.height);return n;}
const P=(a,b)=>[a,b];
const roots=["2210:21952","2210:22126","2223:25930"],records=[],removed=[];
const layouts=[];for(const id of roots){const root=await figma.getNodeByIdAsync(id);const row=root.findOne(n=>n.name==="User content · 6 + 4");const left=row.children.find(n=>n.name==="Profile main column"),right=row.children.find(n=>n.name==="Profile contextual column");const prefs=left.children.find(n=>n.name==="Client preferences"),snapshot=left.children.find(n=>n.name==="Client settings snapshot"),access=right.children.find(n=>n.name==="Client settings permissions"),terms=right.children.find(n=>n.name==="User terms and VIP"),history=right.children.find(n=>n.name==="User support and history");if(!prefs||!snapshot||!access||!terms||!history)throw Error("Unexpected user settings structure "+id);layouts.push({root,row,left,right,prefs,snapshot,access,terms,history});}
for(const l of layouts)for(const t of l.root.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
const titles=["Профиль и доступ клиента","Связанная сессия · снимок настроек","Тариф и VIP","Обращения и события"];
function title(card,label){const t=card.children.find(n=>n.type==="TEXT");t.characters=label;t.name=label;mutated.push(t.id);}
for(const l of layouts){
 l.left.insertChild(0,l.prefs);mutated.push(l.left.id,l.prefs.id);
 title(l.prefs,titles[0]);title(l.snapshot,titles[1]);title(l.terms,titles[2]);title(l.history,titles[3]);
 const oldHeading=l.access.children.find(n=>n.type==="TEXT");for(const n of [...l.access.children].filter(n=>n!==oldHeading)){l.prefs.appendChild(n);if(n.type==="TEXT"){n.textAutoResize="HEIGHT";n.resize(530,n.height);}mutated.push(n.id);}removed.push(oldHeading.id,l.access.id);l.access.remove();
 for(const t of l.prefs.children.filter(n=>n.type==="TEXT")){t.textAutoResize="HEIGHT";t.resize(530,t.height);mutated.push(t.id);}
 const actions=l.snapshot.children.filter(n=>n.type==="INSTANCE");const footer=box(l.snapshot,"Session actions","HORIZONTAL",530);bind(footer,"paddingTop","spacing/2");for(const a of actions){footer.appendChild(a);mutated.push(a.id);}
 for(const t of l.snapshot.children.filter(n=>n.type==="TEXT")){t.textAutoResize="HEIGHT";t.resize(530,t.height);mutated.push(t.id);}
 const note=l.terms.children.find(n=>n.type==="TEXT"&&/VIP.*(второго демо|second demo)/i.test(n.characters));if(note){removed.push(note.id);note.remove();}
 l.prefs.primaryAxisSizingMode="AUTO";l.snapshot.primaryAxisSizingMode="AUTO";l.left.primaryAxisSizingMode="AUTO";l.right.primaryAxisSizingMode="AUTO";l.row.counterAxisSizingMode="AUTO";mutated.push(l.snapshot.id,l.left.id,l.right.id,l.row.id,l.terms.id);
 records.push({rootId:l.root.id,prefsId:l.prefs.id,sessionId:l.snapshot.id,footerId:footer.id,columns:[l.left.children.map(n=>n.name),l.right.children.map(n=>n.name)],height:l.row.height});
}
return {locale:"RU",createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],removedNodeIds:removed,records};