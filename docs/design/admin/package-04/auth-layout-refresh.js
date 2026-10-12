
const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);const styles=await figma.getLocalTextStylesAsync();for(const s of styles)await figma.loadFontAsync(s.fontName);const vars=await figma.variables.getLocalVariablesAsync(),vm=new Map(vars.map(v=>[v.name,v]));const mutated=[],removed=[];
for(const f of FRAMES){const main=await figma.getNodeByIdAsync(f.mainId);main.primaryAxisAlignItems='CENTER';main.counterAxisAlignItems='CENTER';main.setBoundVariable('paddingTop',vm.get('spacing/6'));
for(const child of main.children){child.resize(560,child.height);mutated.push(child.id);if(child.type==='TEXT'){child.textAutoResize='HEIGHT';continue;}if(child.type==='INSTANCE')continue;
if(child.name==='Workspace context'){const t=child.children.find(n=>n.type==='TEXT');t.resize(456,t.height);t.textAutoResize='HEIGHT';}
if(child.name==='Page heading')for(const t of child.children.filter(n=>n.type==='TEXT')){t.resize(560,t.height);t.textAutoResize='HEIGHT';mutated.push(t.id);}
if(child.name==='Form · static design values'){const fields=child.findAll(n=>n.type==='INSTANCE'&&n.name.includes('Form field'));const oldRows=[...child.children];for(const field of fields){child.appendChild(field);field.resize(560,field.height);mutated.push(field.id);}for(const row of oldRows){if(row.children.length===0){removed.push(row.id);row.remove();}}}
}
mutated.push(main.id);
}
return {mutatedNodeIds:mutated,removedNodeIds:removed};
