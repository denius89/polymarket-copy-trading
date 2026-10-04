// Execute per page with PAGE, ROWS (from discovery) and RU.

const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);figma.skipInvisibleInstanceChildren=false;
const changed=new Set(),checks=[];const gap=await figma.variables.getVariableByIdAsync("VariableID:2:52");
for(const r of ROWS){const row=await figma.getNodeByIdAsync(r.id);const bs=await Promise.all(r.buttons.map(b=>figma.getNodeByIdAsync(b.id)));const fs=new Map();for(const b of bs)for(const t of b.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))fs.set(JSON.stringify(s.fontName),s.fontName);for(const f of fs.values())await figma.loadFontAsync(f);
 row.layoutMode="HORIZONTAL";row.primaryAxisSizingMode="FIXED";row.counterAxisSizingMode="AUTO";row.itemSpacing=8;row.setBoundVariable("itemSpacing",gap);row.clipsContent=false;row.overflowDirection="NONE";changed.add(row.id);
 const labels=RU?["24 ч","7 д","30 д","90 д"]:["24h","7d","30d","90d"];
 for(let i=0;i<bs.length;i++){const b=bs[i];b.minWidth=null;b.maxWidth=null;b.resize((row.width-24)/4,48);b.layoutSizingHorizontal="FILL";b.layoutSizingVertical="FIXED";b.primaryAxisAlignItems="CENTER";b.counterAxisAlignItems="CENTER";for(const k of ["paddingLeft","paddingRight"]){b[k]=8;b.setBoundVariable(k,gap);}for(const t of b.findAllWithCriteria({types:["TEXT"]})){t.characters=labels[i];t.textAlignHorizontal="CENTER";t.textAlignVertical="CENTER";t.textAutoResize="HEIGHT";t.layoutSizingHorizontal="FILL";changed.add(t.id);}changed.add(b.id);}
 checks.push({row:row.id,width:row.width,gap:row.itemSpacing,buttons:bs.map(b=>({id:b.id,w:b.width,h:b.height,reactions:b.reactions.length,labels:b.findAllWithCriteria({types:["TEXT"]}).map(t=>({text:t.characters,w:t.width,h:t.height}))})),overflow:bs.some(b=>b.x+b.width>row.width+1)});
}
return {page:PAGE,createdNodeIds:[],mutatedNodeIds:[...changed],checks};

