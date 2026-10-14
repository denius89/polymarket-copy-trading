
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
const legacy=[];for(const id of ["113:207","113:209","113:211"]){const c=await figma.getNodeByIdAsync(id);for(const t of c.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);const key=Object.keys(c.componentPropertyDefinitions).find(k=>k.startsWith("Show icon#"));c.editComponentProperty(key,{defaultValue:false});c.description="Legacy admin button. Text-only by default; use explicit semantic icons per Admin UI kit action rules. Generic forward arrow is not an action icon.";mutated.push(c.id);legacy.push({id:c.id,properties:c.componentPropertyDefinitions});}
const section=await figma.getNodeByIdAsync("2097:5419");const review=box(section,"Action buttons · semantic icons","VERTICAL",1140,"color/bg/canvas");review.x=24;review.y=5290;for(const k of ["paddingTop","paddingBottom","paddingLeft","paddingRight"])bind(review,k,"spacing/4");text(review,"Кнопки · понятные действия","Heading/Small",1108);
const configs=[
 [["primary","Сохранить",null],["secondary","Отмена",null],["primary","Подтвердить","1978:718"],["danger","Остановить",null]],
 [["secondary","Назад","2032:47"],["secondary","Обновить","2032:50"],["secondary","Редактировать","2032:41"],["primary","Отправить ответ","2032:28"]],
 [["secondary","Пауза","2032:53"],["secondary","Возобновить","2032:56"],["secondary","Предпросмотр","2032:66"]]
];for(const list of configs){const row=box(review,"Actions","HORIZONTAL",1108);for(const[key,label,icon]of list)inst(row,key,{Label:label,"Show icon":!!icon,...(icon?{Icon:icon}:{})});}
text(review,"Иконка поясняет действие. Текст обязателен; стрелка назад означает возврат.","Caption",1108,"color/text/secondary");
section.resize(section.width,5660);mutated.push(section.id);await review.screenshot({scale:1});
return {createdNodeIds:created,mutatedNodeIds:mutated,reviewId:review.id,legacy,bounds:{w:review.width,h:review.height}};