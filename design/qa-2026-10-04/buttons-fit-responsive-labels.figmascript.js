await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));figma.skipInvisibleInstanceChildren=false;HELPER
const nodes=figma.currentPage.findAllWithCriteria({types:["FRAME","INSTANCE"]}).filter(n=>active(n)&&isButton(n));const before=nodes.reduce((s,n)=>s+n.reactions.length,0);const ids=new Set(),problems=[];
for(const n of nodes){const ts=n.findAllWithCriteria({types:["TEXT"]}).filter(active);for(const t of ts)for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);}for(const f of fonts.values())await figma.loadFontAsync(f);
for(const n of nodes){
const ts=n.findAllWithCriteria({types:["TEXT"]}).filter(active);let height=48;
for(const t of ts){if(!t.characters)continue;const p=t.parent;const direct=ts.length===1&&p===n;
if(direct){t.textAutoResize="HEIGHT";t.resize(Math.max(12,n.width-32),20);t.layoutSizingHorizontal="FILL";t.textAlignHorizontal="CENTER";height=Math.max(height,t.height+28);if(n.type==="FRAME"){t.x=16;t.y=14;}ids.add(t.id);}}
if(ts.some(t=>t.characters)){const fill=n.layoutSizingHorizontal;n.resize(n.width,height);if(fill==="FILL"&&n.parent.layoutMode!=="NONE")n.layoutSizingHorizontal="FILL";ids.add(n.id);if(n.parent.type==="FRAME"&&n.parent.layoutMode==="HORIZONTAL"&&n.parent.height<height){n.parent.counterAxisSizingMode="AUTO";n.parent.resize(n.parent.width,height);ids.add(n.parent.id);}}
}
for(const n of nodes)for(const t of n.findAllWithCriteria({types:["TEXT"]}).filter(t=>active(t)&&t.characters)){const tb=t.absoluteBoundingBox;for(let p=t.parent;p&&p!==n.parent;p=p.parent){const b=p.absoluteBoundingBox;if(tb&&b&&(tb.x<b.x-1||tb.x+tb.width>b.x+b.width+1||tb.y<b.y-1||tb.y+tb.height>b.y+b.height+1)){problems.push({button:n.id,label:t.id,text:t.characters});break;}}}
return {count:nodes.length,changed:[...ids],reactionsBefore:before,reactionsAfter:nodes.reduce((s,n)=>s+n.reactions.length,0),problems};