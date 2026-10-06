
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync("2:79"));const changed=new Set(),created=[];const gap=await figma.variables.getVariableByIdAsync("VariableID:2:52");
const mobile=await figma.getNodeByIdAsync("1187:49"),long=await figma.getNodeByIdAsync("1194:11546"),balance=await figma.getNodeByIdAsync("819:318");
for(const n of [mobile,long,balance])for(const t of n.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
for(const n of [mobile,long,balance]){
 for(const t of n.findAllWithCriteria({types:["TEXT"]})){if(/context/i.test(t.name)){t.visible=false;changed.add(t.id);}else if(/value|balance|arrow/i.test(t.name)){t.textAutoResize="WIDTH_AND_HEIGHT";t.layoutSizingHorizontal="HUG";t.layoutSizingVertical="HUG";changed.add(t.id);}}
 n.layoutMode="HORIZONTAL";n.primaryAxisAlignItems="CENTER";n.counterAxisAlignItems="CENTER";n.resize(n.width,44);n.primaryAxisSizingMode="AUTO";n.counterAxisSizingMode="FIXED";n.layoutSizingHorizontal="HUG";n.layoutSizingVertical="FIXED";n.minWidth=null;n.maxWidth=null;n.paddingLeft=12;n.paddingRight=12;n.paddingTop=0;n.paddingBottom=0;n.itemSpacing=8;n.setBoundVariable("itemSpacing",gap);changed.add(n.id);
}
const row=await figma.getNodeByIdAsync("1194:11550");row.primaryAxisSizingMode="AUTO";row.layoutSizingHorizontal="HUG";row.itemSpacing=8;row.setBoundVariable("itemSpacing",gap);changed.add(row.id);
let arrow=balance.children.find(n=>n.name==="Open funds arrow");if(!arrow){arrow=(await figma.getNodeByIdAsync("1187:50")).clone();balance.appendChild(arrow);created.push(arrow.id);}arrow.layoutSizingHorizontal="HUG";arrow.layoutSizingVertical="HUG";changed.add(arrow.id);
return {createdNodeIds:created,mutatedNodeIds:[...changed],bounds:[mobile,long,balance].map(n=>({id:n.id,w:n.width,h:n.height,layout:n.layoutMode,visibleTexts:n.findAllWithCriteria({types:["TEXT"]}).filter(t=>t.visible).map(t=>({id:t.id,text:t.characters,w:t.width,h:t.height}))}))};

// Instance pass: execute separately on each page with PAGE

await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE));figma.skipInvisibleInstanceChildren=false;
function active(n){for(let q=n;q&&q.type!=="PAGE";q=q.parent)if(q.visible===false)return false;return true;}
const blocks=figma.currentPage.findAll(n=>(n.type==="FRAME"||n.type==="INSTANCE")&&active(n)&&(/Shared funds entry/.test(n.name)||n.name==="Button/Balance → Wallets"));
const changed=new Set(),fonts=new Map();for(const b of blocks)for(const t of b.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))fonts.set(JSON.stringify(s.fontName),s.fontName);for(const f of fonts.values())await figma.loadFontAsync(f);
const values=[],checks=[];
for(const b of blocks){
 b.layoutMode="HORIZONTAL";
 for(const t of b.findAllWithCriteria({types:["TEXT"]})){if(/context/i.test(t.name)){t.setBoundVariable("visible",null);t.visible=false;changed.add(t.id);}else if(/value|balance|arrow/i.test(t.name)){t.textAutoResize="WIDTH_AND_HEIGHT";t.layoutSizingHorizontal=t.parent.layoutMode&&t.parent.layoutMode!=="NONE"?"HUG":"FIXED";t.layoutSizingVertical=t.parent.layoutMode&&t.parent.layoutMode!=="NONE"?"HUG":"FIXED";changed.add(t.id);if(!/arrow/i.test(t.name)&&["Демо и реальные счета","Demo and real accounts","Нет данных","No data"].includes(t.characters)&&!t.boundVariables.characters)t.characters="—";if(!/arrow/i.test(t.name))values.push({id:t.id,text:t.characters,bound:t.boundVariables.characters?.id});}}
 b.layoutMode="HORIZONTAL";b.resize(b.width,44);b.layoutSizingHorizontal="HUG";b.layoutSizingVertical="FIXED";b.primaryAxisSizingMode="AUTO";b.counterAxisSizingMode="FIXED";b.primaryAxisAlignItems="CENTER";b.counterAxisAlignItems="CENTER";changed.add(b.id);
 checks.push({id:b.id,w:b.width,h:b.height,reactions:b.reactions.length,contextVisible:b.findAllWithCriteria({types:["TEXT"]}).some(t=>/context/i.test(t.name)&&t.visible),textOverflow:b.findAllWithCriteria({types:["TEXT"]}).some(t=>t.visible&&(t.absoluteBoundingBox.x<b.absoluteBoundingBox.x-1||t.absoluteBoundingBox.x+t.width>b.absoluteBoundingBox.x+b.width+1))});
}
return {page:PAGE,createdNodeIds:[],mutatedNodeIds:[...changed],count:blocks.length,values:[...new Set(values.map(v=>v.text))],boundVariableIds:[...new Set(values.map(v=>v.bound).filter(Boolean))],issues:checks.filter(x=>x.contextVisible||x.textOverflow),widths:[...new Set(checks.map(x=>x.w))],heights:[...new Set(checks.map(x=>x.h))],linked:checks.filter(x=>x.reactions>0).length};

// Desktop spacing pass: execute separately with PAGE
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE));function active(n){for(let q=n;q&&q.type!=="PAGE";q=q.parent)if(q.visible===false)return false;return true;}const changed=[],gap=await figma.variables.getVariableByIdAsync("VariableID:2:52"),pad=await figma.variables.getVariableByIdAsync("VariableID:2:53");const ns=figma.currentPage.findAll(n=>n.type==="FRAME"&&n.name==="Button/Balance → Wallets"&&active(n));for(const n of ns){for(const t of n.findAllWithCriteria({types:["TEXT"]}))for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);n.itemSpacing=8;n.setBoundVariable("itemSpacing",gap);for(const k of ["paddingLeft","paddingRight"]){n[k]=12;n.setBoundVariable(k,pad);}changed.push(n.id);}return {createdNodeIds:[],mutatedNodeIds:changed,bounds:ns.map(n=>({id:n.id,w:n.width,h:n.height,gap:n.itemSpacing}))};
