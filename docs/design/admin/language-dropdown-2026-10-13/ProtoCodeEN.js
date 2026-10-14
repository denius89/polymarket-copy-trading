
const page=await figma.getNodeByIdAsync("1981:30");await figma.setCurrentPageAsync(page);
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
const root=await figma.getNodeByIdAsync("2155:79510");
for(const t of root.findAllWithCriteria({types:["TEXT"]}))for(const seg of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(seg.fontName);
const open=root.clone();page.appendChild(open);created.push(open.id,...open.findAll(()=>true).map(n=>n.id));open.name=root.name+" · language-dropdown-open";open.x=Math.max(...page.children.map(n=>n.x+n.width))+160;open.y=root.y;
const openSelector=open.findOne(n=>n.type==="INSTANCE"&&n.name==="Account language dropdown");openSelector.swapComponent(await figma.getNodeByIdAsync("2254:1096"));
function url(id){return {type:"URL",url:"https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id="+id.replace(":","-")+"&starting-point-node-id="+id.replace(":","-")+"&scaling=scale-down",openInNewTab:false};}
async function wire(n,id){await n.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[url(id)]}]);mutated.push(n.id);}
const closed=root.findOne(n=>n.type==="INSTANCE"&&n.name==="Account language dropdown");
await wire(closed.children[0],open.id);await wire(openSelector.children[0],root.id);
const same=openSelector.findOne(n=>n.name==="Option · EN");await wire(same,root.id);
return {locale:"EN",openRootId:open.id,closedRootId:root.id,createdNodeIds:created,mutatedNodeIds:mutated};
