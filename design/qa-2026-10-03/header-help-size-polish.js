const page=await figma.getNodeByIdAsync('2:79');await figma.setCurrentPageAsync(page);
const ids=['1058:34','1058:39','1058:44'];const mutated=[];
for(const id of ids){const n=await figma.getNodeByIdAsync(id);n.primaryAxisSizingMode='FIXED';n.counterAxisSizingMode='FIXED';n.resize(44,44);n.layoutSizingHorizontal='FIXED';n.layoutSizingVertical='FIXED';mutated.push(id);}
const t=await figma.getNodeByIdAsync('819:282');for(const seg of t.getStyledTextSegments(['fontName']))await figma.loadFontAsync(seg.fontName);t.fontSize=16;t.lineHeight={unit:'PIXELS',value:24};t.textAutoResize='HEIGHT';t.resize(66,24);t.layoutSizingHorizontal='FILL';t.minWidth=null;mutated.push(t.id);return{mutatedNodeIds:mutated};
