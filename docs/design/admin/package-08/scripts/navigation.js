
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
const set=await figma.getNodeByIdAsync("2207:1223"),records=[];
for(const v of set.children.filter(n=>n.name.includes("Management"))){
const items=v.children.find(n=>n.name==="Group items"),ru=v.name.includes("Locale=RU");if(items.findOne(n=>n.name==="Nav · marketing"))throw Error("Already exists");
const n=inst(items,"nav",{Label:ru?"Маркетинг":"Marketing",Icon:"2032:62"},items.width-items.paddingLeft-items.paddingRight);n.name="Nav · marketing";
const ci=items.children.findIndex(n=>n.name==="Nav · content");items.insertChild(ci+1,n);
const target={"RU":"2376:29545","EN":"2378:102168"}[ru?"RU":"EN"];await n.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[{type:"URL",url:"https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id="+target.replace(":","-")+"&starting-point-node-id="+target.replace(":","-")+"&scaling=scale-down",openInNewTab:false}]}]);
mutated.push(items.id,v.id);records.push({id:n.id,locale:ru?"RU":"EN",variant:v.id});}
set.resize(set.width,Math.max(...set.children.map(n=>n.y+n.height))+24);mutated.push(set.id);
const rowSet=await figma.getNodeByIdAsync("2375:1260");const review=await figma.getNodeByIdAsync("2375:1268");await review.screenshot({scale:.75});
return {createdNodeIds:created,mutatedNodeIds:mutated,records,properties:rowSet.componentPropertyDefinitions,kitSets:page.findAllWithCriteria({types:["COMPONENT_SET"]}).length,variants:page.findAllWithCriteria({types:["COMPONENT_SET"]}).reduce((a,s)=>a+s.children.filter(n=>n.type==="COMPONENT").length,0)};
