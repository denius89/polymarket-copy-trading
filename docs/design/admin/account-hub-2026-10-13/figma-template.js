
const page=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(page);
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

const routeMap=ROUTES, roots=ROOTS, removed=[],records=[];
function url(id){return {type:"URL",url:"https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id="+id.replace(":","-")+"&starting-point-node-id="+id.replace(":","-")+"&scaling=scale-down",openInNewTab:false};}
async function go(n,key){await n.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[url(routeMap[key])]}]);mutated.push(n.id);}
function card(p,name,w){const n=box(p,name,"VERTICAL",w,"color/bg/surface");for(const k of ["paddingTop","paddingBottom","paddingLeft","paddingRight"])bind(n,k,"spacing/4");bind(n,"cornerRadius","radius/lg");n.strokes=[fill("color/border/default")];n.strokeWeight=1;return n;}
function relabel(n,label){const p=Object.keys(n.componentProperties).find(k=>k.startsWith("Label#"));n.setProperties({[p]:label});mutated.push(n.id);}
function safeFlow(n){const w=n.width,h=n.height,mode=n.layoutMode,ps=n.primaryAxisSizingMode,cs=n.counterAxisSizingMode,wrap=n.layoutWrap;n.layoutMode=mode==="VERTICAL"?"HORIZONTAL":"VERTICAL";n.layoutMode=mode;n.resize(w,h);n.primaryAxisSizingMode=ps;n.counterAxisSizingMode=cs;if(wrap)n.layoutWrap=wrap;mutated.push(n.id);}
let menuId=MENU;
if(!menuId){
 const overlay=track(figma.createFrame());page.appendChild(overlay);overlay.name="LOCALE · account-menu · Avatar menu";overlay.resize(1440,1200);overlay.fills=[];overlay.x=Math.max(...page.children.filter(n=>n!==overlay).map(n=>n.x+n.width))+160;overlay.y=0;
 const backdrop=track(figma.createRectangle());overlay.appendChild(backdrop);backdrop.name="Close on outside click";backdrop.resize(1440,1200);backdrop.fills=[{...fill("color/bg/canvas"),opacity:.001}];await backdrop.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[{type:"CLOSE"}]}]);
 const popup=card(overlay,"Account menu",264);popup.x=1152;popup.y=76;text(popup,LANG==="RU"?"Елена Морозова":"Elena Morozova","Body/Small medium",230);text(popup,"Owner","Caption",230,"color/text/secondary");
 const account=inst(popup,"secondary",{Label:LANG==="RU"?"Мой аккаунт":"My account","Show icon":false});await go(account,"my-profile");
 const home=await figma.getNodeByIdAsync(routeMap["my-profile"]),logout=home.findOne(n=>n.type==="INSTANCE"&&n.name==="Action · admin-login");popup.appendChild(logout);relabel(logout,LANG==="RU"?"Выйти":"Sign out");menuId=overlay.id;
}
const names=LANG==="RU"?{1:"Обзор",2:"Личные данные",3:"Настройки интерфейса",4:"Безопасность",5:"Устройства и сессии",6:"Мои права"}:{1:"Overview",2:"Personal details",3:"Interface preferences",4:"Security",5:"Devices and sessions",6:"My permissions"};
for(const item of roots){
 const root=await figma.getNodeByIdAsync(item.id),section=root.findOne(n=>n.name==="Section layout · 2 + 10");if(!section){records.push({id:item.id,key:item.key,skipped:true});continue;}
 const fonts=new Map();for(const t of root.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);for(const f of fonts.values())await figma.loadFontAsync(f);
 const menu=section.children.find(n=>n.type==="INSTANCE"),content=section.children.find(n=>n.name==="Section content · 10 columns"),old=content.findOne(n=>n.name==="Account content · 6 + 4 columns"),left=old.children.find(n=>n.name==="Personal settings · 8 columns"),right=old.children.find(n=>n.name==="Identity · 4 columns");
 for(const n of menu.children.filter(n=>n.type==="INSTANCE"&&n.name.startsWith("Section item"))){const idx=+n.name.match(/\d+/)[0];relabel(n,names[idx]);n.layoutSizingVertical="HUG";}
 const identity=box(content,"Account identity · compact","HORIZONTAL",950.667);for(const k of ["paddingTop","paddingBottom"])bind(identity,k,"spacing/2");
 const avatar=box(identity,"Initials avatar","HORIZONTAL",48,"color/bg/surface");avatar.resize(48,48);avatar.primaryAxisSizingMode="FIXED";avatar.counterAxisSizingMode="FIXED";avatar.primaryAxisAlignItems="CENTER";avatar.counterAxisAlignItems="CENTER";avatar.cornerRadius=24;const initials=text(avatar,"EM","Heading/Small",36);initials.textAlignHorizontal="CENTER";
 const details=box(identity,"Staff name and email","VERTICAL",666.667);bind(details,"itemSpacing","spacing/1");text(details,LANG==="RU"?"Елена Морозова · Owner":"Elena Morozova · Owner","Heading/Small",666.667);text(details,"elena.owner@demo.example","Body/Small",666.667,"color/text/secondary");const rights=inst(identity,"secondary",{Label:LANG==="RU"?"Посмотреть мои права":"View my permissions","Show icon":false},204);await go(rights,"profile-access");content.insertChild(0,identity);
 removed.push(right.id);right.remove();old.name="Account content · full width";left.name="Account page content";left.resize(950.667,left.height);left.primaryAxisSizingMode="AUTO";left.counterAxisSizingMode="FIXED";mutated.push(old.id,left.id,content.id);
 if(item.key==="my-profile"){
  for(const child of [...left.children]){removed.push(child.id);child.remove();}
  const specs=LANG==="RU"?[["Личные данные","Email и сведения профиля","Редактировать профиль","profile-edit"],["Безопасность","MFA включена · резервные коды настроены","Настроить безопасность","account-security"],["Настройки интерфейса","Язык интерфейса: Русский","Открыть настройки","profile-language"],["Устройства и сессии","2 активные сессии · текущее устройство Safari","Управлять сессиями","my-sessions"]]:[["Personal details","Email and profile information","Edit profile","profile-edit"],["Security","MFA enabled · recovery codes configured","Manage security","account-security"],["Interface preferences","Interface language: English","Open preferences","profile-language"],["Devices and sessions","2 active sessions · current device: Safari","Manage sessions","my-sessions"]];
  for(let i=0;i<4;i+=2){const row=box(left,"Overview card row","HORIZONTAL",950.667);for(const s of specs.slice(i,i+2)){const c=card(row,s[0],467.333);c.minHeight=180;text(c,s[0],"Heading/Small",433.333);text(c,s[1],"Body/Small",433.333,"color/text/secondary");const b=inst(c,"secondary",{Label:s[2],"Show icon":false});await go(b,s[3]);}}
 }else{
  for(const c of left.children.filter(n=>n.type==="FRAME")){c.resize(950.667,c.height);c.primaryAxisSizingMode="AUTO";c.counterAxisSizingMode="FIXED";mutated.push(c.id);const iw=950.667-c.paddingLeft-c.paddingRight-2;for(const n of c.children){if(n.type==="TEXT"){n.textAutoResize="HEIGHT";n.resize(iw,n.height);mutated.push(n.id);}else if(n.type==="FRAME"&&n.name==="Account actions"){n.resize(iw,n.height);n.counterAxisSizingMode="AUTO";mutated.push(n.id);}}}
  if(item.key==="my-sessions"){
   const c=left.children[0],action=c.children.find(n=>n.name==="Account actions"),end=action.children.find(n=>n.name==="Action · session-own-revoke-confirm"),all=action.children.find(n=>n.name==="Action · sessions-other-confirm"),exit=action.children.find(n=>n.name==="Action · admin-login");
   for(const t of [...c.children].filter(n=>n.type==="TEXT"&&n!==c.children[0])){removed.push(t.id);t.remove();}if(exit){removed.push(exit.id);exit.remove();}
   const toolbar=box(c,"Session list actions","HORIZONTAL",900.667);toolbar.appendChild(all);mutated.push(all.id);
   const widths=[280,220,160,192.667],headers=LANG==="RU"?["Устройство","Последняя активность","Статус","Действие"]:["Device","Last activity","Status","Action"];
   const table=box(c,"Active own sessions","VERTICAL",900.667);bind(table,"itemSpacing","spacing/2");const head=box(table,"Table column headings","HORIZONTAL",900.667);head.resize(900.667,44);head.counterAxisSizingMode="FIXED";for(let i=0;i<4;i++)text(head,headers[i],"Body/Small medium",widths[i]);
   const data=LANG==="RU"?[["Safari · macOS","12:00 UTC · Warsaw","Текущая"],["Chrome · Windows","11:42 UTC · Warsaw","Активна"]]:[["Safari · macOS","12:00 UTC · Warsaw","Current"],["Chrome · Windows","11:42 UTC · Warsaw","Active"]];
   for(let j=0;j<2;j++){const row=box(table,"Session "+(j+1),"HORIZONTAL",900.667);row.resize(900.667,64);row.counterAxisSizingMode="FIXED";row.counterAxisAlignItems="CENTER";for(let i=0;i<3;i++)text(row,data[j][i],"Body/Small",widths[i]);const ac=box(row,"Row action","HORIZONTAL",widths[3]);if(j===1){ac.appendChild(end);relabel(end,LANG==="RU"?"Завершить":"End session");}else text(ac,LANG==="RU"?"Это устройство":"This device","Caption",widths[3],"color/text/secondary");}
   c.appendChild(action);mutated.push(action.id);safeFlow(c);
  }
  if(item.key==="account-security"){
   const c=left.children[0],texts=c.children.filter(n=>n.type==="TEXT"),action=c.children.find(n=>n.name==="Account actions");
   const targets=["password-change","mfa-replace","email-change","recovery-codes"];
   for(let i=0;i<4;i++){const row=box(c,"Security setting "+targets[i],"HORIZONTAL",900.667);row.counterAxisAlignItems="CENTER";const words=box(row,"Setting description","VERTICAL",610);bind(words,"itemSpacing","spacing/1");words.appendChild(texts[1+i*2]);words.appendChild(texts[2+i*2]);for(const t of words.children){t.resize(610,t.height);mutated.push(t.id);}const b=action.children.find(n=>n.name==="Action · "+targets[i]);if(b){const control=box(row,"Setting action","HORIZONTAL",274.667);control.appendChild(b);mutated.push(b.id);}c.insertChild(i+1,row);}
   c.appendChild(action);safeFlow(c);
  }
 }
 for(const n of root.findAllWithCriteria({types:["INSTANCE"]}).filter(n=>n.name==="Action · my-profile"))relabel(n,LANG==="RU"?"К обзору аккаунта":"Back to account overview");
 const titleMap={"my-profile":LANG==="RU"?"Мой аккаунт":"My account","profile-language":names[3],"profile-language-open":names[3],"my-sessions":names[5],"profile-access":names[6]};if(titleMap[item.key]){const heading=root.findOne(n=>n.name==="Page heading");const t=heading.children.find(n=>n.type==="TEXT");t.characters=titleMap[item.key];mutated.push(t.id);}
 const account=root.findOne(n=>n.type==="INSTANCE"&&n.name==="My account · open profile");await account.setReactionsAsync([{trigger:{type:"ON_CLICK"},actions:[{type:"NODE",destinationId:menuId,navigation:"OVERLAY",transition:null}]}]);mutated.push(account.id);
 safeFlow(left);safeFlow(content);records.push({id:root.id,key:item.key,contentId:content.id,leftId:left.id,headerId:identity.id});
}
return {createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],removedNodeIds:removed,menuId,records};
