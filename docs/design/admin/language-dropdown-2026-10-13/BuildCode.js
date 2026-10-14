
const page=await figma.getNodeByIdAsync("1981:2");await figma.setCurrentPageAsync(page);
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
const source=await figma.getNodeByIdAsync("2081:181"),section=await figma.getNodeByIdAsync("2097:5418");
const variants=[],data=[];
for(const locale of ["RU","EN"])for(const state of ["Closed","Open"]){
 const c=track(figma.createComponent());section.appendChild(c);c.name="Locale="+locale+", State="+state;c.layoutMode="VERTICAL";c.resize(516,96);c.primaryAxisSizingMode="AUTO";c.counterAxisSizingMode="FIXED";c.fills=[];bind(c,"itemSpacing","spacing/2");
 const f=track(source.createInstance());c.appendChild(f);f.setProperties({"Label#2019:0":locale==="RU"?"Язык интерфейса":"Interface language","Value#2019:3":locale==="RU"?"Русский · RU":"English · EN","Hint#2019:6":locale==="RU"?"Выбор сохраняется автоматически":"Your selection is saved automatically"});f.resize(516,96);
 for(const t of f.findAllWithCriteria({types:["TEXT"]})){t.resize(t.name==="Value"?450:516,t.height);mutated.push(t.id);}
 const ctrl=f.findOne(n=>n.name==="Control");ctrl.resize(516,48);mutated.push(ctrl.id);
 let menu=null,rows=[];
 if(state==="Open"){
 menu=box(c,"Language options","VERTICAL",516,"color/bg/surface");bind(menu,"itemSpacing","spacing/1");for(const k of ["paddingTop","paddingBottom","paddingLeft","paddingRight"])bind(menu,k,"spacing/2");bind(menu,"cornerRadius","radius/md");menu.strokes=[fill("color/border/default")];menu.strokeWeight=1;
 for(const [key,label] of [["RU","Русский"],["EN","English"]]){
 const row=box(menu,"Option · "+key,"HORIZONTAL",498,key===locale?"color/bg/canvas":undefined);row.resize(498,44);row.primaryAxisSizingMode="FIXED";row.counterAxisSizingMode="FIXED";row.counterAxisAlignItems="CENTER";bind(row,"cornerRadius","radius/md");bind(row,"paddingLeft","spacing/3");bind(row,"paddingRight","spacing/3");text(row,label,"Body/Small",398);text(row,key,"Caption",24,"color/text/secondary");text(row,key===locale?"✓":"","Body/Small",16);rows.push({key,id:row.id});
 }
 }
 variants.push(c);data.push({locale,state,id:c.id,field:f.id,rows});
}
const set=track(figma.combineAsVariants(variants,section));set.name="Admin/Language selector";set.x=24;set.y=7010;set.resize(1100,440);set.description="Employee account language. RU/EN enabled today; locale options come from an extensible enabled-language registry. Use native language names and codes. Auto-save on choice; preserve previous language on failure. Production uses a floating popover, closes on Escape/outside click, keyboard arrows and focus return. Add searchable, scrollable list when more than 8 enabled languages; max list height 320px. Account-only setting, separate from managed product content.";
variants.forEach((c,i)=>{c.x=(i%2)*548;c.y=Math.floor(i/2)*220;});
for(const v of data){const other=data.find(x=>x.locale===v.locale&&x.state!==v.state);const field=await figma.getNodeByIdAsync(v.field);await field.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[{type:"NODE",destinationId:other.id,navigation:"CHANGE_TO",transition:null}]}]);mutated.push(field.id);for(const row of v.rows){const n=await figma.getNodeByIdAsync(row.id);await n.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[row.key===v.locale?{type:"NODE",destinationId:other.id,navigation:"CHANGE_TO",transition:null}:{type:"URL",url:"https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id="+(row.key==="RU"?"2155-19891":"2155-79633")+"&starting-point-node-id="+(row.key==="RU"?"2155-19891":"2155-79633")+"&scaling=scale-down",openInNewTab:false}]}]);mutated.push(n.id);}}
section.resize(section.width,7480);mutated.push(section.id);
return {createdNodeIds:created,mutatedNodeIds:mutated,setId:set.id,variants:data,properties:set.componentPropertyDefinitions};