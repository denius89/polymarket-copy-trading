await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));
figma.skipInvisibleInstanceChildren=false;
const map=VALUE_MAP,changed=[],created=[],cards=[],linked=[];
function active(n){for(let p=n;p&&p.type!=="PAGE";p=p.parent)if(p.visible===false)return false;return true;}
function patch(actions){return (actions||[]).flatMap(a=>{
 const x=JSON.parse(JSON.stringify(a));if(x.type==="CONDITIONAL")for(const b of x.conditionalBlocks||[])b.actions=patch(b.actions);
 if(x.type==="SET_VARIABLE"&&map[x.variableId]&&x.variableValue?.type==="VARIABLE_ALIAS"&&map[x.variableValue.value?.id]&&!actions.some(q=>q.variableId===map[x.variableId]))return [x,{...x,variableId:map[x.variableId],variableValue:{...x.variableValue,value:{type:"VARIABLE_ALIAS",id:map[x.variableValue.value.id]}}}];
 return [x];
});}
for(const n of figma.currentPage.findAll(n=>("reactions"in n)&&n.reactions.length)){
 if(!JSON.stringify(n.reactions).includes('"type":"VARIABLE_ALIAS"'))continue;
 const rs=n.reactions.map(r=>({...r,actions:patch(r.actions||[])}));
 if(JSON.stringify(rs)!==JSON.stringify(n.reactions)){await n.setReactionsAsync(rs);changed.push(n.id);linked.push(n.id);}
}
const small=await figma.getNodeByIdAsync("1216:49"),disclosure=await figma.getNodeByIdAsync("1216:55");
for(const master of [small,disclosure])for(const t of master.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
const ru=PAGE_ID==="33:2"||PAGE_ID==="205:2";
const frames=figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>active(n)&&n.layoutMode==="VERTICAL"&&/card|summary|session|Notification|Program terms|Risk limits|Settings/i.test(n.name)&&!n.name.includes("Header"));
for(const card of frames){
 let touched=false;
 for(const t of card.children.filter(c=>c.type==="TEXT"&&c.visible)){
  let style;
  if(/^(Card title|Heading|Object title|Selected trader|Market question|Performance title)$/.test(t.name))style="S:91e4e6f77407c842a145f672d90065d16fbfcf28,";
  else if(/^(Object value|Result)$/.test(t.name)&&t.fontSize<18)style="S:331bd2fdb6d259752ba88f1a4d9fcc9642da9656,";
  else if(/^(Object metadata|Object ID|Context|Topic period and coverage)$/.test(t.name))style="S:3383453afee1e6a118c6d49295501d664091bd8a,";
  else if(/^(Card body|Message|Selected account)$/.test(t.name))style="S:bc557184905d0960b434ff365a67efddde9a111f,";
  if(style&&t.textStyleId!==style){for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);await t.setTextStyleIdAsync(style);changed.push(t.id);touched=true;}
  if(t.name==="Object body"&&t.boundVariables.characters&&!card.children.some(c=>c.name==="Record details disclosure")){
   const details=disclosure.createInstance();details.name="Record details disclosure";card.insertChild(card.children.indexOf(t),details);details.layoutSizingHorizontal="FILL";
   details.setProperties({"Title#1216:6":ru?"Подробности записи":"Record details","Body#1216:9":t.boundVariables.characters});
   t.visible=false;created.push(details.id);changed.push(t.id);touched=true;
  }
  if(t.name==="Card body"&&!t.boundVariables.characters&&t.characters.split("\n").filter(s=>s.includes(":")).length>=4){
   const lines=t.characters.split("\n"),values=lines.filter(s=>s.includes(":"));
   const grid=figma.createAutoLayout("VERTICAL",{name:"Readable account metrics",itemSpacing:16,fills:[]});card.insertChild(card.children.indexOf(t),grid);grid.layoutSizingHorizontal="FILL";created.push(grid.id);
   let row;for(let i=0;i<values.length;i++){if(i%2===0){row=figma.createAutoLayout("HORIZONTAL",{name:"Readable metrics row",itemSpacing:12,fills:[]});grid.appendChild(row);row.layoutSizingHorizontal="FILL";created.push(row.id);}
    const s=values[i],metric=small.createInstance();row.appendChild(metric);metric.layoutSizingHorizontal="FILL";metric.setProperties({"Label#1216:0":s.slice(0,s.indexOf(":")),"Value#1216:3":"—"});created.push(metric.id);
   }
   for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
   t.characters=(ru?"Счёт не подключён: данные недоступны. ":"Account disconnected: data unavailable. ")+lines.filter(s=>!s.includes(":")).join(" ");changed.push(t.id);touched=true;
  }
 }
 if(touched){card.itemSpacing=16;changed.push(card.id);cards.push(card.id);}
}
const vars=await figma.variables.getLocalVariablesAsync();
for(const frame of figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>/Readable metric|Budget highlight|Risk level/.test(n.name))){
 if(frame.itemSpacing===16)frame.setBoundVariable("itemSpacing",vars.find(v=>v.id==="VariableID:2:54"));
 if(frame.itemSpacing===12)frame.setBoundVariable("itemSpacing",vars.find(v=>v.id==="VariableID:2:53"));
 if(frame.itemSpacing===8)frame.setBoundVariable("itemSpacing",vars.find(v=>v.id==="VariableID:2:52"));
 changed.push(frame.id);
}
return {changed,created,cards,linked};
