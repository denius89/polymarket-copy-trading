await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));const changed=[];
for(const frame of figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>n.name==="Risk level")){
 const label=frame.children.find(c=>c.type==="TEXT"&&!c.boundVariables.characters);if(label){for(const s of label.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);label.textAutoResize="WIDTH_AND_HEIGHT";label.layoutSizingHorizontal="HUG";changed.push(label.id);}
}
for(const card of figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>n.name.startsWith("State /")&&n.layoutMode==="VERTICAL")){
 for(const action of card.children.filter(c=>c.type==="FRAME"&&c.name.startsWith("Actions/"))){
 for(const t of action.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
 card.appendChild(action);action.layoutSizingHorizontal="FILL";changed.push(card.id,action.id);
 }
}return {changed};
