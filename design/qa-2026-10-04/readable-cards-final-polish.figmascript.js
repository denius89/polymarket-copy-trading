await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));
figma.skipInvisibleInstanceChildren=false;const map=VALUE_MAP,created=[],changed=[],cards=[];
function active(n){for(let p=n;p&&p.type!=="PAGE";p=p.parent)if(p.visible===false)return false;return true;}
function patch(actions){let touched=false;const out=[];for(const a of actions||[]){
 let x={...a};if(a.type==="CONDITIONAL"){x.conditionalBlocks=a.conditionalBlocks.map(b=>{const p=patch(b.actions);if(p.touched)touched=true;return {...b,actions:p.out};});}
 out.push(x);
 if(a.type==="SET_VARIABLE"&&map[a.variableId]&&a.variableValue?.type==="VARIABLE_ALIAS"&&map[a.variableValue.value?.id]&&!actions.some(b=>b.variableId===map[a.variableId])){
 out.push({...a,variableId:map[a.variableId],variableValue:{...a.variableValue,value:{type:"VARIABLE_ALIAS",id:map[a.variableValue.value.id]}}});touched=true;
 }
 }return {out,touched};}
for(const n of figma.currentPage.findAllWithCriteria({types:["FRAME","INSTANCE"]}).filter(n=>active(n)&&n.reactions.length)){
 let touched=false;const rs=n.reactions.map(r=>{const p=patch(r.actions);if(p.touched)touched=true;return {...r,actions:p.out};});
 if(touched){await n.setReactionsAsync(rs);changed.push(n.id);}
}
for(const t of figma.currentPage.findAllWithCriteria({types:["TEXT"]}).filter(t=>active(t)&&t.parent.name==="Field control"&&t.characters.includes(":")&&/\d/.test(t.characters))){
 const source=t.boundVariables.characters; if(source&&!map[source.id])continue;
 for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
 if(source)t.setBoundVariable("characters",await figma.variables.getVariableByIdAsync(map[source.id]));else t.characters=t.characters.slice(t.characters.indexOf(":")+1).trim();
 await t.setTextStyleIdAsync("S:331bd2fdb6d259752ba88f1a4d9fcc9642da9656,");changed.push(t.id);
}
for(const card of figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>active(n)&&n.name.startsWith("State /")&&n.layoutMode==="NONE")){
 const ts=card.children.filter(c=>c.type==="TEXT"&&c.visible);
 if(ts.length<5||ts.length%2!==1)continue;
 for(const t of ts)for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
 const buttons=card.children.filter(c=>c.type==="INSTANCE"&&c.visible);
 card.layoutMode="VERTICAL";card.primaryAxisSizingMode="AUTO";card.counterAxisSizingMode="FIXED";card.itemSpacing=16;card.paddingTop=16;card.paddingBottom=16;card.paddingLeft=16;card.paddingRight=16;
 for(let i=0;i<ts.length-1;i+=2){
 const row=figma.createAutoLayout("HORIZONTAL",{name:"Account detail row",itemSpacing:12,fills:[],counterAxisAlignItems:"CENTER"});
 card.insertChild(i/2,row);row.layoutSizingHorizontal="FILL";row.appendChild(ts[i]);row.appendChild(ts[i+1]);created.push(row.id);
 ts[i].textAutoResize="HEIGHT";ts[i].layoutSizingHorizontal="FILL";await ts[i].setTextStyleIdAsync("S:bc557184905d0960b434ff365a67efddde9a111f,");
 ts[i+1].textAutoResize="WIDTH_AND_HEIGHT";ts[i+1].layoutSizingHorizontal="HUG";await ts[i+1].setTextStyleIdAsync("S:331bd2fdb6d259752ba88f1a4d9fcc9642da9656,");changed.push(ts[i].id,ts[i+1].id);
 }
 const note=ts[ts.length-1];note.textAutoResize="HEIGHT";note.layoutSizingHorizontal="FILL";card.appendChild(note);changed.push(note.id);
 if(buttons.length){const actions=figma.createAutoLayout("HORIZONTAL",{name:"Account actions",itemSpacing:12,fills:[]});card.appendChild(actions);actions.layoutSizingHorizontal="FILL";created.push(actions.id);for(const b of buttons){actions.appendChild(b);b.resize(100,48);b.layoutSizingHorizontal="FILL";changed.push(b.id);}}
 changed.push(card.id);cards.push(card.id);
}
return {changed,created,cards};
