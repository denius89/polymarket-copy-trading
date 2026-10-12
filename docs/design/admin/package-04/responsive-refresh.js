
const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);const styles=await figma.getLocalTextStylesAsync();for(const s of styles)await figma.loadFontAsync(s.fontName);const mutated=[];
for(const f of FRAMES){const main=await figma.getNodeByIdAsync(f.mainId),context=main.children.find(n=>n.name==='Workspace context'),t=context.children.find(n=>n.type==='TEXT');t.resize(448,t.height);t.textAutoResize='HEIGHT';mutated.push(t.id);}
if(KIT){for(const id of ['2081:580','2081:581','2081:582','2081:583']){const n=await figma.getNodeByIdAsync(id);for(const t of n.children.filter(n=>n.type==='TEXT')){t.textAutoResize='HEIGHT';t.layoutSizingHorizontal='FILL';mutated.push(t.id);}n.primaryAxisSizingMode='AUTO';n.counterAxisSizingMode='FIXED';mutated.push(n.id);}}
return {mutatedNodeIds:mutated};
