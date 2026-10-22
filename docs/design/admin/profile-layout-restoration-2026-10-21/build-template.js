
const page=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(page);figma.skipInvisibleInstanceChildren=false;
const created=[],mutated=[],proof=[];const src=await figma.getNodeByIdAsync('2236:25808');
const col=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:134:180');
const allVars=await figma.variables.getLocalVariablesAsync('BOOLEAN');
const knownFonts=new Map();for(const t of src.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))knownFonts.set(JSON.stringify(s.fontName),s.fontName);
const track=n=>{created.push(n.id);return n;};
function box(parent,name,width,dir='VERTICAL'){const n=track(figma.createAutoLayout(dir,{name,itemSpacing:24}));parent.appendChild(n);n.fills=[];n.resize(width,40);n.primaryAxisSizingMode='AUTO';n.counterAxisSizingMode='FIXED';n.layoutSizingVertical='HUG';return n;}
function props(n,values){const p={};for(const [key,value]of Object.entries(values)){const k=Object.keys(n.componentProperties).find(k=>k.split('#')[0]===key);if(k)p[k]=value;}n.setProperties(p);mutated.push(n.id);}
function navActions(flags,which){return flags.map((v,i)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type:'BOOLEAN',resolvedType:'BOOLEAN',value:i===which}}));}
async function go(n,flags,which){await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:navActions(flags,which)}]);mutated.push(n.id);}
for(const item of GROUP){
 const root=await figma.getNodeByIdAsync(item.id),main=root.children.find(c=>c.x===248&&'children'in c);if(main.children.some(c=>c.name==='Unified role account · 2 + 10')){proof.push({id:item.id,skipped:true});continue;}
 for(const t of main.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))knownFonts.set(JSON.stringify(s.fontName),s.fontName);
 for(const f of knownFonts.values())await figma.loadFontAsync(f);
 const en=item.en,existing=[...main.children],context=existing.find(c=>c.name==='Context'),heading=existing.find(c=>c.name==='Page heading'),records=existing.find(c=>c.name==='Operation records'),rights=existing.find(c=>c.name==='UX06 · My access'),language=existing.find(c=>c.name==='Role language dropdown'),intro=existing.find(c=>c.name==='Catalog and settings context');
 const headerText=context.findAllWithCriteria({types:['TEXT']})[0];
 const staff=records.children.filter(c=>c.type==='INSTANCE').find(c=>c.findAllWithCriteria({types:['TEXT']})[0]?.characters===(en?'Staff':'Сотрудник'));
 const rowTexts=staff.findAllWithCriteria({types:['TEXT']}).map(t=>t.characters),staffName=rowTexts[1],staffId=rowTexts[2];
 const roleRow=records.children.filter(c=>c.type==='INSTANCE').find(c=>c.findAllWithCriteria({types:['TEXT']})[0]?.characters===(en?'Access':'Права'));
 const roleLabel=roleRow.findAllWithCriteria({types:['TEXT']})[1].characters;
 const flags=[];for(let i=0;i<6;i++){const name='Admin account/'+item.key+'/section '+(i+1);let v=allVars.find(v=>v.name===name);if(!v){v=figma.variables.createVariable(name,col,'BOOLEAN');v.scopes=['ALL_SCOPES'];v.setValueForMode(col.defaultModeId,i===0);created.push(v.id);allVars.push(v);}flags.push(v);}
 const htexts=heading.findAllWithCriteria({types:['TEXT']});htexts[0].characters=en?'My account':'Мой аккаунт';for(const t of htexts.slice(1))t.visible=false;headerText.visible=false;mutated.push(headerText.id,...htexts.map(t=>t.id));
 for(const n of existing.filter(c=>c.name==='Breadcrumb trail'||c===intro||c===records)) {n.visible=false;mutated.push(n.id);}
 const section=track(src.clone());main.insertChild(main.children.indexOf(heading)+1,section);section.name='Unified role account · 2 + 10';section.layoutSizingHorizontal='FILL';section.layoutSizingVertical='HUG';
 const templateNav=section.children[0],content=section.children[1],identity=content.children[0],overview=content.children[1];
 section.counterAxisAlignItems='MIN';const menu=box(section,'Account section navigation',177.333);section.insertChild(0,menu);menu.itemSpacing=0;menu.appendChild(templateNav);
 const names=en?{1:'Overview',2:'Personal details',3:'Interface preferences',4:'Security',5:'Devices and sessions',6:'My permissions'}:{1:'Обзор',2:'Личные данные',3:'Настройки интерфейса',4:'Безопасность',5:'Устройства и сессии',6:'Мои права'};
 for(let active=1;active<=6;active++){const n=active===1?templateNav:track(templateNav.clone());if(active!==1)menu.appendChild(n);n.setProperties({Active:String(active)});n.name='Account navigation · section '+active;n.setBoundVariable('visible',flags[active-1]);n.resize(177.333,n.height);for(const row of n.children.filter(c=>c.type==='INSTANCE'&&c.name.startsWith('Section item'))){const number=Number(row.name.match(/\d+/)[0]);props(row,{Label:names[number]});await go(row,flags,number-1);}mutated.push(n.id);}
 const details=identity.children.find(c=>c.name==='Staff name and email'),dt=details.findAllWithCriteria({types:['TEXT']});dt[0].characters=staffName+' · '+roleLabel;dt[1].characters=staffId;
 identity.name='Current employee identity';const at=identity.children.find(c=>c.name==='Initials avatar').findAllWithCriteria({types:['TEXT']})[0];at.characters=staffName.split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase();mutated.push(...dt.map(t=>t.id),at.id);
 const rightsButton=identity.children.find(c=>c.type==='INSTANCE');props(rightsButton,{Label:en?'View my permissions':'Посмотреть мои права'});await go(rightsButton,flags,5);
 overview.name='Account panel · overview';overview.setBoundVariable('visible',flags[0]);mutated.push(overview.id);
 const panels={0:overview};for(const idx of [1,3,4,2,5]){panels[idx]=box(content,'Account panel · '+['overview','personal','interface','security','sessions','permissions'][idx],950.667);panels[idx].setBoundVariable('visible',flags[idx]);}
 function info(parent,title,body){const n=track(intro.clone());parent.appendChild(n);n.visible=true;n.name=title;props(n,{Title:title,Body:body});n.resize(950.667,n.height);n.layoutSizingHorizontal='FILL';n.layoutSizingVertical='HUG';return n;}
 info(panels[1],names[2],en?'Name: '+staffName+'\nStaff ID: '+staffId+'\nEmail and avatar details have no confirmed source in this demo. Only your own account is shown.':'Имя: '+staffName+'\nИдентификатор сотрудника: '+staffId+'\nEmail и сведения об аватаре не подтверждены в этом демо. Здесь только ваш собственный аккаунт.');
 info(panels[3],names[4],item.key==='owner-b'?(en?'Owners must use two different physical security keys. This employee’s registered-key state is not loaded. Personal settings do not change permissions or approve money actions.':'Для владельцев обязательны два разных физических ключа. Состояние зарегистрированных ключей этого сотрудника не загружено. Личные настройки не меняют полномочия и не подтверждают денежные действия.'):(en?'Account protection follows this assignment. The actual sign-in method and registered factors are not loaded in this demo. Secrets are never displayed; recovery does not restore old sessions or permissions.':'Защита аккаунта определяется назначением. Способ входа и зарегистрированные средства защиты не загружены в этом демо. Секреты не показываются; восстановление не возвращает старые сеансы и полномочия.'));
 info(panels[4],names[5],en?'Other sessions have not been loaded for '+staffId+'. This does not mean there are no active devices. Sign out on this device using the action below. Other employees’ sessions are outside this personal section.':'Другие сеансы '+staffId+' не загружены. Это не означает отсутствие активных устройств. Для выхода на текущем устройстве используйте действие ниже. Сеансы других сотрудников находятся вне этого личного раздела.');
 info(panels[2],names[3],en?'Your language preference applies to your account only. Changing language preserves your assignment and the saved work screen.':'Язык относится только к вашему аккаунту. Смена языка сохраняет назначение и исходный рабочий экран.');
 panels[2].appendChild(language);language.resize(520,language.height);mutated.push(language.id);
 panels[5].appendChild(rights);rights.resize(950.667,rights.height);rights.layoutSizingHorizontal='FILL';mutated.push(rights.id);
 const cards=overview.findAll(n=>n.name==='Overview card row').flatMap(row=>row.children.filter(c=>c.type==='FRAME'));const specs=en?[
 ['Personal details','Your name and account information','Open personal details',1],
 ['Security','Sign-in protection for your account','Open security',3],
 ['Interface preferences','Interface language: English','Open preferences',2],
 ['Devices and sessions','Your active devices and sign-out','View devices and sessions',4]
 ]:[
 ['Личные данные','Имя и сведения вашего аккаунта','Открыть личные данные',1],
 ['Безопасность','Защита входа в вашу учётную запись','Открыть безопасность',3],
 ['Настройки интерфейса','Язык интерфейса: Русский','Открыть настройки',2],
 ['Устройства и сессии','Ваши устройства и выход из аккаунта','Посмотреть устройства',4]
 ];
 if(cards.length!==4)throw Error('Expected four cards');
 for(let i=0;i<4;i++){const c=cards[i],texts=c.children.filter(c=>c.type==='TEXT');texts[0].characters=specs[i][0];texts[1].characters=specs[i][1];const b=c.children.find(c=>c.type==='INSTANCE');props(b,{Label:specs[i][2]});await go(b,flags,specs[i][3]);mutated.push(...texts.map(t=>t.id));}
 for(const n of existing.filter(c=>c.name==='Role work context'||c.name==='Permitted actions'||c.name==='Review disclaimer')){main.appendChild(n);mutated.push(n.id);}
 root.resize(1440,Math.max(root.height,1000));proof.push({id:root.id,key:item.key,locale:en?'en':'ru',section:section.id,staffName,staffId,roleLabel,flags:flags.map(v=>({id:v.id,name:v.name})),panels:Object.entries(panels).map(([idx,n])=>({section:Number(idx)+1,id:n.id})),language:language.id});
}
return {createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],proof};
