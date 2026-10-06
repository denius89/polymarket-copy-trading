// Execute once per page with C, V, ORD and POS from the paired ledger/data files.

const p=await figma.getNodeByIdAsync(C.page);await figma.setCurrentPageAsync(p);
const created=new Set(),mutated=new Set(), summaries=[];
const allVars=await figma.variables.getLocalVariablesAsync();const vv=new Map(allVars.map(v=>[v.id,v]));
const get=k=>vv.get(V.find(v=>v.lang===C.lang&&v.key===k).id);const L=(ru,en)=>C.lang==="RU"?ru:en;
const fonts=new Map();for(const t of p.findAll(n=>n.type==="TEXT"))for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);
for(const f of fonts.values())await figma.loadFontAsync(f);
await figma.loadFontAsync({family:"Inter",style:"Medium"});await figma.loadFontAsync({family:"Inter",style:"Semi Bold"});
const ts={title:"S:91e4e6f77407c842a145f672d90065d16fbfcf28,",body:"S:bc557184905d0960b434ff365a67efddde9a111f,",caption:"S:3383453afee1e6a118c6d49295501d664091bd8a,",num:"S:331bd2fdb6d259752ba88f1a4d9fcc9642da9656,"};
function paint(id){return figma.variables.setBoundVariableForPaint({type:"SOLID",color:{r:1,g:1,b:1}}, "color", vv.get("VariableID:"+id));}
function record(n){created.add(n.id);if("children"in n)for(const x of n.children)record(x);}
function frame(name,parent,h=false,card=false){const n=figma.createFrame();n.name=name;n.layoutMode=h?"HORIZONTAL":"VERTICAL";n.primaryAxisSizingMode="AUTO";n.counterAxisSizingMode="FIXED";n.resize(Math.max(100,parent.width),100);n.fills=card?[paint("2:29")]:[];n.itemSpacing=12;n.setBoundVariable("itemSpacing",vv.get("VariableID:2:53"));if(card){for(const k of ["paddingLeft","paddingRight","paddingTop","paddingBottom"]){n[k]=16;n.setBoundVariable(k,vv.get("VariableID:2:54"));}n.cornerRadius=14;n.setBoundVariable("cornerRadius",vv.get("VariableID:2:63"));}parent.appendChild(n);n.layoutSizingHorizontal="FILL";n.layoutSizingVertical="HUG";created.add(n.id);return n;}
async function txt(name,value,parent,style="body",key=null,muted=false){const t=figma.createText();t.name=name;t.fontName={family:"Inter",style:"Regular"};await t.setTextStyleIdAsync(ts[style]);t.characters=value;t.fills=[paint(muted?"2:35":"2:34")];t.textAutoResize="HEIGHT";parent.appendChild(t);t.layoutSizingHorizontal="FILL";t.layoutSizingVertical="HUG";if(key)t.setBoundVariable("characters",get(key));created.add(t.id);return t;}
async function row(parent,label,key){const r=frame("Detail / "+label,parent,true);r.counterAxisAlignItems="MIN";await txt("Label",label,r,"body",null,true);const t=await txt("Value","—",r,"body",key);t.textAlignHorizontal="RIGHT";return r;}
const metricMaster=await figma.getNodeByIdAsync("1216:49"),disclosureMaster=await figma.getNodeByIdAsync("1216:55");
async function metric(parent,label,key){const n=metricMaster.createInstance();parent.appendChild(n);n.layoutSizingHorizontal="FILL";n.layoutSizingVertical="HUG";n.setProperties({"Label#1216:0":label,"Value#1216:3":{type:"VARIABLE_ALIAS",id:get(key).id}});record(n);return n;}
async function disclosure(parent){const n=disclosureMaster.createInstance();parent.appendChild(n);n.layoutSizingHorizontal="FILL";n.layoutSizingVertical="HUG";n.setProperties({"Title#1216:6":L("Подробности заявки","Order details"),"Body#1216:9":{type:"VARIABLE_ALIAS",id:get("details").id}});record(n);return n;}
const set=(v,value)=>({type:"SET_VARIABLE",variableId:v.id,variableValue:{type:v.resolvedType,resolvedType:v.resolvedType,value}});
const condition=v=>({type:"VARIABLE_ALIAS",resolvedType:"BOOLEAN",value:{type:"VARIABLE_ALIAS",id:v.id}});
const keys=["order-cancel","order-change","order-requested","position-manual","position-close","position-requested"];
for(let i=0;i<keys.length;i++){
 const root=await figma.getNodeByIdAsync(C.roots[i]),content=await figma.getNodeByIdAsync(C.contents[i]),key=keys[i];
 const old=content.children.slice();for(const n of old){if((n.type==="TEXT"&&!/Page.?title|Heading/i.test(n.name))||/^Fix \/ card|^Page summary/.test(n.name)){n.visible=false;mutated.add(n.id);}}
 const area=frame("Shared/Management content",content);const firstOldAction=old.find(n=>/Recovery\/Actions|Action \/|SettingsRow/.test(n.name));
 let idx=firstOldAction?content.children.indexOf(firstOldAction):content.children.length-1;content.insertChild(idx,area);
 const banner=frame("Shared/Action explanation",area,false,true);banner.fills=[paint("2:31")];
 let title="",body="",titleKey=null,bodyKey=null;
 if(key==="order-change"){title=L("Сначала подтвердим остаток","Confirm the remaining order first");bodyKey="note";}
 if(key==="order-cancel"){title=L("Отменяется только остаток","Only the remaining order is cancelled");body=L("Исполненные доли останутся в позиции. Резерв освобождается после подтверждения отмены, а не после нажатия кнопки.","Filled shares remain in the position. Reserved funds are released after cancellation is confirmed, not when the button is pressed.");}
 if(key==="order-requested"){title=L("Отмена проверяется","Cancellation pending");body=L("Запрос отправлен. Это ещё не подтверждение отмены. Резерв сохраняется, баланс пока не меняется. Не отправляйте повторный запрос.","The request was sent. Cancellation has not been confirmed. Funds remain reserved and the balance is unchanged. Do not send the request again.");}
 if(key==="position-manual"){title=L("Что изменится","What changes");body=L("После подтверждения эта позиция перейдёт под ваше управление: дальнейшие действия трейдера по ней не копируются. Позиция не продаётся. Остальные копии продолжают работать.","After confirmation, you manage this position: the trader’s future actions on it are no longer copied. The position is not sold. Other copies continue.");}
 if(key==="position-close"){title=L("Продажа после подтверждения","Sell after confirmation");body=L("Будет отправлена заявка на продажу этой позиции. Цена и итоговая сумма зависят от исполнения. До подтверждения позиция остаётся открытой.","A sell order will be submitted for this position. The price and final proceeds depend on execution. The position stays open until confirmation.");}
 if(key==="position-requested"){titleKey="pendingTitle";bodyKey="pendingText";}
 await txt("Action explanation title",title||"—",banner,"title",titleKey);await txt("Action explanation body",body||"—",banner,"body",bodyKey,true);
 if(key==="order-cancel"){const b=await txt("Blocked reason","—",banner,"body","note",true);b.setBoundVariable("visible",get("blocked"));}
 if(i<3){
  const card=frame("Shared/Order action summary",area,false,true);
  const top=frame("Order side and status",card,true);await txt("Order side","—",top,"caption","side",true);const st=await txt("Execution status","—",top,"caption","status");st.textAlignHorizontal="RIGHT";
  await txt("Market question","—",card,"title","market");await row(card,L("Выбранный исход","Selected outcome"),"outcome");
  await txt("Copied trader and venue","—",card,"body","identity",true);
  const mr=frame("Order metrics",card,true);await metric(mr,L("Цена за долю","Limit price / share"),"price");await metric(mr,L("Осталось купить","Remaining shares"),"remaining");
  await row(card,L("Исполнено","Filled"),"filled");await row(card,L("В резерве","Reserved funds"),"reserve");await disclosure(card);summaries.push({root:root.id,key,card:card.id,area:area.id});
 }else{
  const source=await figma.getNodeByIdAsync(C.source);const card=source.clone();area.appendChild(card);card.name="Shared/Position action summary";card.layoutSizingHorizontal="FILL";card.layoutSizingVertical="HUG";record(card);summaries.push({root:root.id,key,card:card.id,area:area.id});
 }
 const actionParent=C.actions?await figma.getNodeByIdAsync(C.actions[i]):content;
 const primary=actionParent.findOne(n=>n.type==="INSTANCE"&&/^Action \/ /.test(n.name)&&/Подтвердить|Confirm|Отменить остаток|Cancel remaining|Перейти к отмене|Cancel first/.test(n.name));
 if(primary&&[0,1,3,4].includes(i)){
   const gate=get(i<2?"allow":i===3?"canManual":"canClose");primary.setBoundVariable("visible",gate);mutated.add(primary.id);
   const rr=primary.reactions.map(r=>{let as=JSON.parse(JSON.stringify(r.actions||[r.action]));
    if(i===3||i===4){const manual=i===3;as=[set(get("pendingTitle"),manual?L("Передача управления проверяется","Management transfer pending"):L("Закрытие позиции проверяется","Position close pending")),set(get("pendingText"),manual?L("Передача ещё не подтверждена. Продажи нет; позиция сохраняется. Копирование изменится после подтверждения.","The transfer is not confirmed yet. No sale occurs; the position remains. Copying changes after confirmation."):L("Заявка на закрытие проверяется. Позиция и результат изменятся после исполнения; окончательная сумма пока неизвестна.","The close request is being checked. The position and result change after execution; final proceeds are not yet known.")),...as];}
    return {trigger:r.trigger,actions:[{type:"CONDITIONAL",conditionalBlocks:[{condition:condition(gate),actions:as},{actions:[]}]}]};});
   await primary.setReactionsAsync(rr);
 }
}
let selectors=0;
const orderSelector=C.lang==="RU"?"VariableID:882:22":"VariableID:882:57",positionSelector=C.lang==="RU"?"VariableID:882:17":"VariableID:882:52";
function rewrite(as){let out=[];for(const a of as){if(a.type==="CONDITIONAL"){out.push({...a,conditionalBlocks:a.conditionalBlocks.map(b=>({...b,actions:rewrite(b.actions)}))});continue;}out.push(a);if(a.type==="SET_VARIABLE"&&a.variableId===orderSelector){const data=ORD[a.variableValue?.value];if(data){for(const [k,v]of Object.entries(data))out.push(set(get(k),v));selectors++;}}if(a.type==="SET_VARIABLE"&&a.variableId===positionSelector){const data=POS.find(x=>x.id===a.variableValue?.value);if(data){out.push(set(get("canManual"),data.status==="open"&&data.management!=="manual"&&data.quantity>0),set(get("canClose"),["open","manual"].includes(data.status)&&data.quantity>0));selectors++;}}}return out;}
for(const n of p.findAll(n=>"reactions"in n&&n.reactions.length)){let changed=false;const reactions=n.reactions.map(r=>{const as=r.actions||[r.action];const before=selectors;const next=rewrite(as);if(selectors>before)changed=true;return {trigger:r.trigger,actions:next};});if(changed){await n.setReactionsAsync(reactions);mutated.add(n.id);}}
return {page:C.page,createdNodeIds:[...created],mutatedNodeIds:[...mutated],summaries,selectorUpdates:selectors};
