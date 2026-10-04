await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));figma.skipInvisibleInstanceChildren=false;
const ids=ROOT_IDS,errors=[],values=[];function active(n){for(let p=n;p&&p.type!=="PAGE";p=p.parent)if(p.visible===false)return false;return true;}
for(const id of ids){const n=await figma.getNodeByIdAsync(id);if(!n||!active(n))continue;
 for(const t of n.findAllWithCriteria({types:["TEXT"]}).filter(active)){
 if(t.name==="Value"&&t.parent.name==="Shared/Data metric"){values.push(t.id);if(t.lineHeight.unit==="PIXELS"&&t.height>t.lineHeight.value+1)errors.push({id:t.id,type:"wrapped-value",text:t.characters});if(t.width>t.parent.width+1)errors.push({id:t.id,type:"wide-value"});}
 if(t.x+t.width>t.parent.width+1)errors.push({id:t.id,type:"right-bound",text:t.characters,w:t.width,p:t.parent.width});
 }
}
const map=VALUE_MAP;let linked=0,missing=0;
function scan(actions){for(const a of actions||[]){if(a.type==="CONDITIONAL")for(const b of a.conditionalBlocks||[])scan(b.actions);if(a.type==="SET_VARIABLE"&&map[a.variableId]){linked++;if(!actions.some(x=>x.type==="SET_VARIABLE"&&x.variableId===map[a.variableId]))missing++;}}}
for(const n of figma.currentPage.findAllWithCriteria({types:["FRAME","INSTANCE"]}).filter(n=>active(n)&&n.reactions.length))for(const r of n.reactions)scan(r.actions);
return {cards:ids.length,values:[...new Set(values)].length,errors,sourceActions:linked,missingDerivedActions:missing};
