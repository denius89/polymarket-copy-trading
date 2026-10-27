// Inject CONFIG, STATES. Scoped editable examples, not an execution engine.
const p=await figma.getNodeByIdAsync(CONFIG.page);await figma.setCurrentPageAsync(p);
if(p.findOne(n=>n.name==="BI FIXES / "+CONFIG.key+" / budget"))throw new Error("Already built: inspect existing IDs before retry");
const template=await figma.getNodeByIdAsync(CONFIG.template);
const fonts=new Map();for(const t of template.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);
for(const style of ["Regular","Medium","Semi Bold","Bold"])fonts.set(style,{family:"Inter",style});
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const comps={};for(const [k,id]of Object.entries({primary:"113:240",secondary:"113:242",field:"987:49",errorField:"987:69",Info:"1980:103",Warning:"1980:106",Danger:"1980:109",Success:"1980:112"})){comps[k]=await figma.getNodeByIdAsync(id);if(!comps[k]||comps[k].type!=="COMPONENT")throw new Error("Component missing "+id);}
const tokenIds={primary:"VariableID:2:34",secondary:"VariableID:2:35",surface:"VariableID:2:29",border:"VariableID:2:32",gap8:"VariableID:2:52",gap12:"VariableID:2:53",gap16:"VariableID:2:54",gap24:"VariableID:2:56",radius:"VariableID:2:63"};
const vars={};await Promise.all(Object.entries(tokenIds).map(async([k,id])=>{vars[k]=await figma.variables.getVariableByIdAsync(id);if(!vars[k])throw new Error("Token missing "+id);}));
const styleIds={title:"S:b405e33d1cb9a52dcc1fcd0aa7688dea6eb2dd89,",heading:"S:91e4e6f77407c842a145f672d90065d16fbfcf28,",body:"S:bc557184905d0960b434ff365a67efddde9a111f,",caption:"S:3383453afee1e6a118c6d49295501d664091bd8a,"};
const loc=CONFIG.en?1:0,tx=a=>Array.isArray(a)?a[loc]:a;
const names={},roots={},buttons={},made=[],changed=[],bindings=[],patches=[];
const width=CONFIG.mobile?390:1440,height=CONFIG.mobile?844:1024;
const startX=Math.max(...p.children.map(n=>n.x+n.width))+200;
const section=figma.createSection();section.name=CONFIG.en?"27 Oct · Budget and session completion":"27 окт · Бюджет и завершение сессии";p.appendChild(section);section.x=startX;section.y=60;
// Every state below is a NEW clone. Existing screens are never cleared.
for(const [i,s]of STATES.entries()){
 const n=template.clone();
 if(!n)throw new Error("Missing root "+s.key);
 section.appendChild(n);n.name="BI FIXES / "+CONFIG.key+" / "+s.key;n.visible=true;n.setBoundVariable("visible",null);n.layoutMode="NONE";n.resize(width,height);n.overflowDirection="NONE";n.numberOfFixedChildren=0;
 n.x=40+(i%7)*(width+60);n.y=80+Math.floor(i/7)*(height+100);roots[s.key]=n.id;names[s.key]=n;made.push(n.id);
}
section.resizeWithoutConstraints(80+7*(width+60)-60,160+2*(height+100));
function paint(k){return figma.variables.setBoundVariableForPaint({type:"SOLID",color:{r:0,g:0,b:0}},"color",vars[k]);}
function stack(parent,name,w,gap=16){const n=figma.createAutoLayout("VERTICAL");parent.appendChild(n);n.name=name;n.fills=[];n.resize(w,40);n.primaryAxisSizingMode="AUTO";n.counterAxisSizingMode="FIXED";n.itemSpacing=gap;n.setBoundVariable("itemSpacing",vars["gap"+gap]);return n;}
async function text(parent,name,value,style="body",color="primary"){const t=figma.createText();parent.appendChild(t);t.name=name;t.fontName={family:"Inter",style:style==="title"?"Bold":style==="heading"?"Semi Bold":style==="caption"?"Medium":"Regular"};await t.setTextStyleIdAsync(styleIds[style]);t.characters=value;t.fills=[paint(color)];t.textAutoResize="HEIGHT";t.resize(parent.width,t.height);t.layoutSizingHorizontal="FILL";return t;}
async function props(i,o){for(const [key,value]of Object.entries(o)){const pk=Object.keys(i.componentProperties).find(k=>k.split("#")[0]===key);if(pk)i.setProperties({[pk]:value});}}
async function button(parent,label,key,style="secondary"){const i=comps[style].createInstance();parent.appendChild(i);i.name="BI action / "+key;await props(i,{Label:label});i.resize(parent.width,48);i.layoutSizingHorizontal="FILL";return i;}
const collection=figma.variables.createVariableCollection("BI financial context / "+CONFIG.key);
function contextVar(name,type,value,scope){const v=figma.variables.createVariable(name,collection,type);v.scopes=[scope];v.setValueForMode(collection.defaultModeId,value);return v;}
const cv={title:contextVar("Title","STRING",tx(["Сессия","Session"]),"TEXT_CONTENT"),body:contextVar("Body","STRING","","TEXT_CONTENT"),key:contextVar("Origin","STRING","budget","TEXT_CONTENT"),language:contextVar("Language controls","BOOLEAN",false,"ALL_SCOPES")};
const utility=figma.createAutoLayout("VERTICAL");section.appendChild(utility);utility.name="BI utility / "+CONFIG.key;utility.resize(CONFIG.mobile?350:480,200);utility.primaryAxisSizingMode="AUTO";utility.counterAxisSizingMode="FIXED";utility.paddingTop=24;utility.paddingBottom=24;utility.paddingLeft=24;utility.paddingRight=24;for(const k of ["paddingTop","paddingBottom","paddingLeft","paddingRight"])utility.setBoundVariable(k,vars.gap24);utility.itemSpacing=16;utility.setBoundVariable("itemSpacing",vars.gap16);utility.fills=[paint("surface")];utility.strokes=[paint("border")];utility.strokeWeight=1;utility.cornerRadius=14;for(const k of ["topLeftRadius","topRightRadius","bottomLeftRadius","bottomRightRadius"])utility.setBoundVariable(k,vars.radius);utility.x=40;utility.y=80+2*(height+100);
const ut=await text(utility,"Context title",tx(["Сессия","Session"]),"heading");ut.setBoundVariable("characters",cv.title);
const ub=await text(utility,"Context body"," ");ub.setBoundVariable("characters",cv.body);
const lang=await button(utility,CONFIG.en?"Русский":"English","language");lang.setBoundVariable("visible",cv.language);
const close=await button(utility,tx(["Назад","Back"]),"close","primary");await close.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[{type:"CLOSE"}]}]);

made.push(utility.id);section.resizeWithoutConstraints(section.width,utility.y+utility.height+60);
const set=(v,value)=>({type:"SET_VARIABLE",variableId:v.id,variableValue:{type:typeof value==="boolean"?"BOOLEAN":"STRING",resolvedType:typeof value==="boolean"?"BOOLEAN":"STRING",value}});
const nav=id=>({type:"NODE",destinationId:id,navigation:"NAVIGATE",transition:null,resetScrollPosition:true});
function utilityActions(s,key){
 const titles={help:["Помощь","Help"],notifications:["Уведомления","Notifications"],profile:["Профиль","Profile"],home:["Сессия","Session"],session:["Сессия","Session"],catalogue:["Трейдеры","Traders"],positions:["Позиции","Positions"],events:["Активность","Activity"],report:["Отчёт сессии","Session report"],operations:["Операции сессии","Session operations"],settings:["Настройки копирования","Copy settings"]};
 let body=tx(s.snapshot);
 if(key==="help")body+="\n\n"+tx(["Изменение бюджета не продаёт позиции. Неизвестный итог не разрешает повтор. Новая сессия и сброс требуют строгого завершения.","Changing the budget does not sell positions. An unknown outcome does not permit resending. A new session and reset require strict completion."]);
 if(key==="notifications")body+="\n\n"+tx(["Событие сессии: ","Session event: "])+tx(s.title);
 if(key==="profile")body=tx(["Демо-аккаунт · текущая сессия\n","Demo account · current session\n"])+body+"\n\n"+tx(["Просмотр профиля и смена языка не меняют торговое состояние.","Viewing the profile or changing language does not change trading state."]);
 if(key==="catalogue")body+="\n\n"+tx(["Momentum Fox · Polymarket. Новый запуск доступен только после полного завершения текущей сессии.","Momentum Fox · Polymarket. A new launch is available only after strict completion of the current session."]);
 if(key==="report")body+="\n\n"+tx(["Баланс изменён. Движение бюджета ","Balance changed. Budget flow "])+(s.key==="increased"?"+100 $":"−50 $")+tx([" отделено от торгового результата. Старые позиции и заявки не пересчитаны. Отметка сохранится и после возврата к исходному B."," is separate from trading results. Existing orders and positions were not recalculated. The marker remains even if B returns to its initial value."]);
 if(key==="operations")body+="\n\n"+tx(["Неизвестная BUY-заявка удерживает резерв 20 $ до сверки. Просмотр не отключает сокращения и не закрывает позиции.","The unknown BUY retains its $20 reserve until reconciliation. Reviewing it does not turn exit-only copying off or close positions."]);
 if(key==="settings")body+="\n\n"+tx(["Фиксированная копия 20 $. Позиция 15 $ (10%), покупки 22,50 $/день (15%). Старое F сохранено с предупреждением; новый ввод проверяется отдельно. BUY не уменьшается до остатка.","Fixed copy $20. Position $15 (10%), daily buys $22.50 (15%). Existing F is kept with a warning; new input is validated separately. BUY is not reduced to the remaining allowance."]);
 return [set(cv.title,tx(titles[key]||titles.home)),set(cv.body,body),set(cv.key,s.key),set(cv.language,key==="profile"),{type:"NODE",destinationId:utility.id,navigation:"OVERLAY",transition:null,resetScrollPosition:true}];
}
for(const s of STATES){
 const n=names[s.key];
 const header=n.findAllWithCriteria({types:["INSTANCE"]}).find(x=>/Recovery\/Header|Shared header \/ unified/.test(x.name));
 const navSource=n.findAllWithCriteria({types:["FRAME"]}).find(x=>x.visible&&(CONFIG.mobile?x.name==="App shell / Bottom navigation":x.name==="App shell / Sidebar"));
 if(!header||!navSource)throw new Error("Shell missing "+s.key);
 const h=header.clone(),bar=navSource.clone();
 n.appendChild(h);n.appendChild(bar);
 for(const child of [...n.children])if(child!==h&&child!==bar)child.remove();
 bar.visible=true;bar.setBoundVariable("visible",null);h.x=CONFIG.mobile?20:256;h.y=CONFIG.mobile?20:24;bar.x=CONFIG.mobile?20:0;bar.y=CONFIG.mobile?748:0;
 if(!CONFIG.mobile)bar.resize(232,height);
 for(const x of [h,bar,...h.findAll(),...bar.findAll()])if("reactions"in x&&x.reactions.length)await x.setReactionsAsync([]);
 for(const t of h.findAllWithCriteria({types:["TEXT"]}))if(t.boundVariables?.characters)t.setBoundVariable("characters",null);
 await props(h,{"Text 1":tx(s.title),"Balance context":tx(["Демо-сессия · Polymarket","Demo session · Polymarket"]),"Balance context 3":tx(["Демо · виртуальные средства","Demo · virtual funds"]),"Balance value":s.key==="increased"?"160,00 $":s.key==="decreased"?"10,00 $":s.key==="reset-done"?"200,00 $":"60,00 $"});
 const vp=figma.createAutoLayout("VERTICAL");n.appendChild(vp);vp.name="BI scroll viewport";vp.fills=[];vp.resize(CONFIG.mobile?350:1152,CONFIG.mobile?656:888);vp.x=CONFIG.mobile?20:256;vp.y=CONFIG.mobile?84:112;vp.primaryAxisSizingMode="FIXED";vp.counterAxisSizingMode="FIXED";vp.clipsContent=true;vp.overflowDirection="VERTICAL";
 const content=stack(vp,"BI content",vp.width,24);content.layoutSizingHorizontal="FILL";
 const columns=CONFIG.mobile?content:figma.createAutoLayout("HORIZONTAL");if(!CONFIG.mobile){content.appendChild(columns);columns.name="BI desktop columns";columns.fills=[];columns.resize(1152,100);columns.primaryAxisSizingMode="FIXED";columns.counterAxisSizingMode="AUTO";columns.itemSpacing=24;columns.setBoundVariable("itemSpacing",vars.gap24);}
 const main=CONFIG.mobile?content:stack(columns,"BI main column",720,24);
 if(CONFIG.mobile)await text(main,"Screen title",tx(s.title),"title");
 await text(main,"Session context",tx(["Демо · виртуальные средства · Polymarket","Demo · virtual funds · Polymarket"]),"caption","secondary");
 const alert=comps[s.tone].createInstance();main.appendChild(alert);alert.name="BI status";await props(alert,{Body:tx(s.body)});const at=alert.findAllWithCriteria({types:["TEXT"]}).find(t=>t.name==="prop:Title");if(at){at.characters=tx(s.alert);changed.push(at.id);}alert.resize(main.width,alert.height);alert.layoutSizingHorizontal="FILL";for(const t of alert.findAllWithCriteria({types:["TEXT"]})){t.textAutoResize="HEIGHT";t.resize(main.width-alert.paddingLeft-alert.paddingRight,t.height);}alert.primaryAxisSizingMode="AUTO";
 if(s.rows){const rows=stack(main,"BI budget facts",main.width,8);for(const [label,value]of s.rows){const sides=label.split(" · ");const printed=CONFIG.en?(label.includes("Free")?"Free after reserves":label.includes("Reserved")?"Reserved":label.includes("Positions")?"Positions · cost basis":"Current budget"):label.includes("Free")?"Свободно после резервов":label.includes("Reserved")?"В резерве":label.includes("Positions")?"Позиции · учётная стоимость":"Текущий бюджет";await text(rows,printed,printed+" · "+value);}}
 if(s.field){const f=comps[s.key==="insufficient"?"errorField":"field"].createInstance();main.appendChild(f);f.name="BI budget input";await props(f,{Label:tx(s.field.slice(0,2)),Value:s.field[2],Hint:tx(["100–1 000 $ · шаг 10 $","$100–$1,000 · $10 step"])});f.resize(main.width,f.height);f.layoutSizingHorizontal="FILL";
 for(const t of f.query("TEXT")){const name=t.name.toLowerCase();const val=name==="value"?(loc===1?"$"+s.field[2].replace(/[^0-9.]/g,""):s.field[2]):name==="hint"?(s.key==="insufficient"?tx(["Для изъятия 100 $ доступно только 60 $.","Need to withdraw $100; only $60 is free."]):tx(["100–1 000 $ · шаг 10 $","$100–$1,000 · $10 step"])):null;if(val!==null){const common=Object.keys(f.componentProperties).find(k=>k.split("#")[0].toLowerCase()===name);if(common)f.setProperties({[common]:val});const ref=t.componentPropertyReferences.characters;if(ref)f.setProperties({[ref]:val});else t.characters=val;}t.textAutoResize="HEIGHT";t.resize(t.parent===f?f.width:f.width-(t.parent.paddingLeft||0)-(t.parent.paddingRight||0),t.height);t.layoutSizingHorizontal="FILL";}
 for(const box of f.children.filter(c=>c.type==="FRAME")){box.resize(f.width,box.height);box.layoutSizingHorizontal="FILL";}f.primaryAxisSizingMode="AUTO";
 if(s.key!=="budget")await f.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[nav(roots.budget)]}]);}
 if(s.details)await text(main,"Rule explanation",tx(s.details),"body","secondary");
 const actions=stack(main,"BI actions",main.width,12);buttons[s.key]=[];
 for(const a of s.actions){const b=await button(actions,tx(a.slice(0,2)),a[2],a[3]||"secondary");let aa;
 if(roots[a[2]])aa=[nav(roots[a[2]])];
 else if(a[2]==="catalog")aa=[set({id:CONFIG.accountState},"new"),set({id:CONFIG.stage},"before"),set({id:CONFIG.draft},false),set({id:CONFIG.draftMode},"none"),nav(CONFIG.catalog)];
 else aa=utilityActions(s,a[2]);
 await b.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:aa}]);buttons[s.key].push({id:b.id,target:a[2]});}
 if(!CONFIG.mobile){const aside=stack(columns,"BI session context",408,16);await text(aside,"Current state heading",tx(["Текущее состояние","Current state"]),"heading");await text(aside,"Current state snapshot",tx(s.snapshot),"body","secondary");await text(aside,"Reset gate",tx(["Сброс не удаляет позиции или резерв. История сохраняется.","Reset does not erase positions or reserves. History is retained."]),"body","secondary");}
 for(const b of h.query("FRAME,INSTANCE")){if(b.width<40||b.height<40)continue;const key=/Help/.test(b.name)?"help":/Notifications/.test(b.name)?"notifications":/Profile|avatar/i.test(b.name)?"profile":null;if(key)await b.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:utilityActions(s,key)}]);}
 for(const b of bar.children){const key=/home|главная/i.test(b.name)?"home":/catalog|trader/i.test(b.name)?"catalogue":/position/i.test(b.name)?"positions":/event|activity/i.test(b.name)?"events":null;if(key)await b.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:utilityActions(s,key)}]);}
}
for(const n of [...Object.values(names),utility])made.push(...n.findAll().map(x=>x.id));
made.push(section.id,...Object.values(cv).map(v=>v.id),collection.id);
return {createdNodeIds:[...new Set(made)],mutatedNodeIds:[...new Set(changed)],section:section.id,roots,utility:utility.id,languageButton:lang.id,variables:Object.fromEntries(Object.entries(cv).map(([k,v])=>[k,v.id])),buttons,counts:{states:STATES.length,desktop:!CONFIG.mobile}};
