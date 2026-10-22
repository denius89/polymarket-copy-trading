// OPACITY variable values use percentages; keep normal menus readable.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const v=await figma.variables.getVariableByIdAsync('VariableID:3805:227999'),mutated=[v.id],proof=[];
v.setValueForMode('134:0',100);
function actions(aa){return aa.map(a=>a.type==='SET_VARIABLE'&&a.variableId===v.id?{...a,variableValue:{type:'FLOAT',resolvedType:'FLOAT',value:45}}:a.type==='CONDITIONAL'?{...a,conditionalBlocks:a.conditionalBlocks.map(b=>({...b,actions:actions(b.actions)}))}:a);}
for(const id of ['3069:64274','3069:192733','3069:64302','3069:192761']){const n=await figma.getNodeByIdAsync(id);await n.setReactionsAsync(n.reactions.map(r=>({trigger:r.trigger,actions:actions(r.actions||[])})));mutated.push(id);proof.push({id,disabledOpacityPercent:45});}
return {createdNodeIds:[],mutatedNodeIds:mutated,defaultOpacityPercent:v.valuesByMode['134:0'],proof};
