await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));
figma.skipInvisibleInstanceChildren=false;
const map=VALUE_MAP;const changed=[],created=[],unhandled=[];
function transform(actions){if(!Array.isArray(actions))return actions;const out=[];
for(const a of actions){const copy=JSON.parse(JSON.stringify(a));if(copy.type==="CONDITIONAL")for(const block of copy.conditionalBlocks||[])block.actions=transform(block.actions);
out.push(copy);
if(copy.type==="SET_VARIABLE"&&map[copy.variableId]){
 if(copy.variableValue?.type==="STRING"&&typeof copy.variableValue.value==="string"){
 const val=copy.variableValue.value,trimmed=val.includes(":")?val.slice(val.indexOf(":")+1).trim():val;
 if(!actions.some(b=>b.type==="SET_VARIABLE"&&b.variableId===map[copy.variableId]))out.push({...copy,variableId:map[copy.variableId],variableValue:{...copy.variableValue,value:trimmed}});
 }else unhandled.push(copy);
}
}return out;}
for(const n of figma.currentPage.findAll(n=>("reactions"in n)&&n.reactions.length)){
 const rs=n.reactions.map(r=>({...r,actions:transform(r.actions|| (r.action?[r.action]:[]))}));
 if(JSON.stringify(rs)!==JSON.stringify(n.reactions)){await n.setReactionsAsync(rs);changed.push(n.id);}
}
for(const grid of figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>n.name==="Readable metric grid")){
 const card=grid.parent;
 if(card.name==="Recovery/Content"){
 card.paddingTop=0;card.paddingBottom=0;card.paddingLeft=0;card.paddingRight=0;changed.push(card.id);
 grid.paddingTop=16;grid.paddingBottom=16;grid.paddingLeft=16;grid.paddingRight=16;
 grid.fills=[figma.variables.setBoundVariableForPaint({type:"SOLID",color:{r:0.07,g:0.08,b:0.12}}, "color",await figma.variables.getVariableByIdAsync("VariableID:2:31"))];grid.cornerRadius=12;
 }
 const metrics=grid.children.flatMap(r=>r.children).filter(m=>m.type==="INSTANCE");
 const budget=metrics.find(m=>m.componentProperties?.["Label#1216:0"]?.value=== "Бюджет трейдера"||m.componentProperties?.["Label#1216:0"]?.value==="Trader budget");
 if(budget){
 const old=budget.parent;const row=figma.createAutoLayout("HORIZONTAL",{name:"Budget highlight",fills:[]});grid.insertChild(0,row);row.layoutSizingHorizontal="FILL";row.appendChild(budget);budget.layoutSizingHorizontal="FILL";created.push(row.id);changed.push(budget.id);
 if(!old.children.length){changed.push(old.id);old.remove();}
 const others=metrics.filter(m=>m!==budget);const rest=grid.children.filter(r=>r!==row);
 for(const m of others)row.appendChild(m);
 for(const r of rest){changed.push(r.id);r.remove();}
 const cols=card.width<500?2:4;
 let secondary;
 for(let i=0;i<others.length;i++){
 if(i%cols===0){secondary=figma.createAutoLayout("HORIZONTAL",{name:"Readable metrics row",itemSpacing:12,fills:[]});grid.appendChild(secondary);secondary.layoutSizingHorizontal="FILL";created.push(secondary.id);}
 secondary.appendChild(others[i]);others[i].layoutSizingHorizontal="FILL";changed.push(others[i].id);
 }
 }
 changed.push(grid.id);
}
return {changed,created,unhandled,actionNodes:changed.length};
