
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));figma.skipInvisibleInstanceChildren=false;
HELPER
const nodes=figma.currentPage.findAllWithCriteria({types:["FRAME","INSTANCE"]}).filter(n=>active(n)&&isButton(n)).filter(n=>n.findAllWithCriteria({types:["TEXT"]}).some(active));
for(const n of nodes)for(const t of n.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);
fonts.set(JSON.stringify(style.fontName),style.fontName);for(const f of fonts.values())await figma.loadFontAsync(f);
const before=nodes.reduce((s,n)=>s+n.reactions.length,0);
for(const n of nodes)await fix(n);
const groups=[...new Set(nodes.map(n=>n.parent))].filter(p=>p.type==="FRAME"&&p.layoutMode!=="NONE");
const rearranged=[];
for(const row of groups){
 const buttons=row.children.filter(n=>nodes.includes(n));
 if(buttons.length<2||buttons.length>4||row.children.some(n=>active(n)&&!buttons.includes(n)))continue;
 const capacity=row.width-row.paddingLeft-row.paddingRight;
 const need=buttons.reduce((s,n)=>s+Math.min(required.get(n.id)||n.width,320),0)+(buttons.length-1)*12;
 const funding=row.name==="Actions/Funding";
 if(row.layoutMode==="HORIZONTAL"&&need>capacity&&!/Period|Tab|Preset|Chip/i.test(row.name)){
 row.layoutMode="VERTICAL";row.primaryAxisSizingMode="AUTO";row.counterAxisSizingMode="FIXED";row.itemSpacing=12;rearranged.push(row.id);
 }
 if(row.layoutMode==="VERTICAL"){row.primaryAxisSizingMode="AUTO";for(const n of buttons){n.resize(capacity,n.height);n.layoutSizingHorizontal="FILL";await fix(n);}}
 else{row.counterAxisSizingMode="AUTO";const each=(capacity-row.itemSpacing*(buttons.length-1))/buttons.length;
 if(funding){for(const n of buttons){n.resize(PAGE_ID==="33:2"||PAGE_ID==="29:2"?each:Math.min(160,each),n.height);if(PAGE_ID==="33:2"||PAGE_ID==="29:2")n.layoutSizingHorizontal="FILL";await fix(n);}}
 }
 changed.add(row.id);
}
const problems=[];
for(const n of nodes){
 const box=n.absoluteBoundingBox;if(!box)continue;
 for(const t of n.findAllWithCriteria({types:["TEXT"]}).filter(active)){
 const tb=t.absoluteBoundingBox;for(let p=t.parent;p&&p!==n.parent;p=p.parent){const b=p.absoluteBoundingBox;if(b&&tb&&(tb.x<b.x-1||tb.x+tb.width>b.x+b.width+1||tb.y<b.y-1||tb.y+tb.height>b.y+b.height+1)){problems.push({button:n.id,label:t.id,parent:p.id,text:t.characters});break;}}
 }
}
return {count:nodes.length,changed:[...changed],rearranged,reactionsBefore:before,reactionsAfter:nodes.reduce((s,n)=>s+n.reactions.length,0),problems};
