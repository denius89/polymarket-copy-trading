await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(CFG.page));
function shown(n){while(n&&n.type!=="PAGE"){if(!n.visible)return false;n=n.parent;}return true;}
const vs=await figma.variables.getLocalVariablesAsync(),coll=(await figma.variables.getLocalVariableCollectionsAsync()).find(c=>c.name===CFG.ns);
let flag=vs.find(v=>v.name===CFG.ns+"/focusTopics");const created=[];if(!flag){flag=figma.variables.createVariable(CFG.ns+"/focusTopics",coll,"BOOLEAN");flag.scopes=["ALL_SCOPES"];flag.setVariableCodeSyntax("WEB","var(--focus-topics)");flag.setValueForMode(coll.defaultModeId,false);created.push(flag.id);}
flag.setValueForMode(coll.defaultModeId,false);const changed=[flag.id];const set=value=>({type:"SET_VARIABLE",variableId:flag.id,variableValue:{type:"BOOLEAN",resolvedType:"BOOLEAN",value}});
const themes=figma.currentPage.findAll(n=>n.type==="TEXT"&&n.name==="Theme"&&shown(n));
for(const text of themes){let root=text;while(root.parent&&root.parent.type!=="PAGE"&&root.parent.type!=="SECTION")root=root.parent;
const condition={type:"VARIABLE_ALIAS",resolvedType:"BOOLEAN",value:{type:"VARIABLE_ALIAS",id:flag.id}};
const branch={type:"CONDITIONAL",conditionalBlocks:[{condition,actions:[{type:"NODE",destinationId:text.parent.id,navigation:"SCROLL_TO",transition:null,resetScrollPosition:false},set(false)]},{actions:[]}]};
const rs=root.reactions.filter(r=>r.trigger?.type!=="AFTER_TIMEOUT"||r.trigger.timeout!==0.01);
rs.push({trigger:{type:"AFTER_TIMEOUT",timeout:0.01},actions:[branch]});await root.setReactionsAsync(rs);changed.push(root.id);}
const cards=figma.currentPage.findAll(n=>n.type==="INSTANCE"&&/Trader\/trader-/.test(n.name));
for(const card of cards){const rs=card.reactions.map(r=>({ ...r,actions:[set(false),...(r.actions||[r.action]).filter(Boolean).filter(a=>a.variableId!==flag.id)]}));await card.setReactionsAsync(rs);changed.push(card.id);
const more=card.findOne(n=>n.name==="Topic more / open profile");if(more&&more.reactions.length){const ms=more.reactions.map(r=>({...r,actions:[set(true),...(r.actions||[]).filter(a=>a.navigation!=="SCROLL_TO"&&a.variableId!==flag.id)]}));await more.setReactionsAsync(ms);changed.push(more.id);}}
return {page:CFG.page,createdNodeIds:created,mutatedNodeIds:changed,focusVariable:flag.id,profiles:themes.length};
