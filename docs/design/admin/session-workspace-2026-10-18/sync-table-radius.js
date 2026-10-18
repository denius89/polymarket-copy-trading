// Inputs PAGE, IDS. Use the already verified shared radius/lg; do not create a token.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE));
const v=await figma.variables.getVariableByIdAsync('VariableID:2:63');
if(v.name!=='radius/lg')throw Error('Unexpected token');
const changed=[],values=[];
for(const id of IDS){
 const root=await figma.getNodeByIdAsync(id);
 const table=root.children.find(n=>n.name==='Main').children.find(n=>n.name==='Session records');
 const before=table.cornerRadius;
 for(const field of ['topLeftRadius','topRightRadius','bottomLeftRadius','bottomRightRadius'])table.setBoundVariable(field,v);
 changed.push(table.id);values.push({root:id,table:table.id,before,after:table.cornerRadius});
}
return {mutatedNodeIds:changed,variableId:v.id,variableName:v.name,derivedFrom:'Approved RU table source bindings',values};
