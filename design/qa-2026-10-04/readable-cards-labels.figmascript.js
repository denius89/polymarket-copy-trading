await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));figma.skipInvisibleInstanceChildren=false;
const ru=PAGE_ID==="33:2"||PAGE_ID==="205:2",changed=[];
for(const grid of figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>n.name==="Readable metric grid")){
 for(const m of grid.findAllWithCriteria({types:["INSTANCE"]}).filter(n=>n.name==="Shared/Data metric")){
 const label=m.componentProperties["Label#1216:0"]?.value;
 const next=({"Бюджет трейдера":"Бюджет копирования","Trader budget":"Copying budget","Давность сигнала":"Сигнал не старше","Signal age":"Max. signal age"})[label];
 if(next){m.setProperties({"Label#1216:0":next});changed.push(m.id);}
 }
}
for(const f of figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>n.name==="Risk level")){
 const t=f.children.find(c=>c.type==="TEXT"&&!c.boundVariables.characters);if(t){for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);t.characters=ru?"Профиль риска":"Risk preset";changed.push(t.id);}
}
return {changed};
