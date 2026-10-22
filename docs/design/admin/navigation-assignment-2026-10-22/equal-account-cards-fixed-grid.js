// Fixed 1440px design grid: 1144 - 177.333 internal navigation - 16 gap.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const mutated=[],proof=[],W=1144-177.333-16,GAP=16,CARD=(W-GAP)/2;
for(const item of PANELS){const panel=await figma.getNodeByIdAsync(item.panel);let rows=panel.children.filter(n=>n.type==='FRAME'&&n.name==='Overview card row');if(!rows.length)rows=panel.children.flatMap(n=>'children'in n?[...n.children]:[]).filter(n=>n.type==='FRAME'&&n.name==='Overview card row');if(rows.length!==2)throw Error('Expected two known overview rows '+item.id);
 for(const row of rows){const cards=row.children.filter(n=>n.type==='FRAME');if(cards.length!==2)throw Error('Expected two overview cards');const texts=cards.flatMap(c=>c.children.filter(n=>n.type==='TEXT'));const fonts=new Map();for(const t of texts)for(const f of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(f.fontName),f.fontName);await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
  row.layoutMode='HORIZONTAL';row.primaryAxisSizingMode='FIXED';row.counterAxisSizingMode='FIXED';row.layoutSizingHorizontal='FIXED';row.layoutSizingVertical='FIXED';row.itemSpacing=GAP;row.resize(W,180);
  for(const c of cards){c.layoutMode='VERTICAL';c.primaryAxisSizingMode='FIXED';c.counterAxisSizingMode='FIXED';c.layoutSizingHorizontal='FIXED';c.layoutSizingVertical='FIXED';c.minWidth=null;c.maxWidth=null;c.minHeight=180;c.resize(CARD,180);const iw=CARD-c.paddingLeft-c.paddingRight-2*c.strokeWeight;for(const t of c.children.filter(n=>n.type==='TEXT')){t.layoutSizingHorizontal='FIXED';t.textAutoResize='HEIGHT';t.resize(iw,t.height);mutated.push(t.id);}mutated.push(c.id);}
  mutated.push(row.id);proof.push({root:item.id,row:row.id,widths:cards.map(c=>c.width),modes:cards.map(c=>c.layoutMode),expected:CARD});
 }
}
return {createdNodeIds:[],mutatedNodeIds:mutated,proof};
