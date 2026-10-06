await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));figma.skipInvisibleInstanceChildren=false;
const labels=figma.currentPage.findAllWithCriteria({types:["TEXT"]}).filter(t=>/^(БУДУЩИЙ LIVE · ОБРАЗЕЦ|FUTURE LIVE · SPECIMEN)$/i.test(t.characters));
const spacing=await figma.variables.getVariableByIdAsync("VariableID:2:52");
const created=[],changed=[],groups=[],problems=[];
for(const badge of labels){
 const parent=badge.parent;if(parent.type!=="FRAME"||parent.name==="Account / intro")continue;
 const siblings=parent.children.filter(c=>c.type==="TEXT");
 const desc=siblings.find(t=>/^(Отдельный счёт площадки|Separate venue account)/.test(t.characters));
 if(!desc)continue;
 const at=siblings.indexOf(badge);const title=siblings[at+1];if(!title||title===desc)continue;
 const texts=[title,desc,badge];for(const t of texts)for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
 const index=Math.min(...texts.map(t=>parent.children.indexOf(t))),x=Math.min(...texts.map(t=>t.x)),y=Math.min(...texts.map(t=>t.y)),width=title.width;
 const g=figma.createAutoLayout("VERTICAL",{name:"Account / intro",itemSpacing:8,paddingLeft:0,paddingRight:0,paddingTop:0,paddingBottom:0});
 g.fills=[];g.strokes=[];parent.insertChild(index,g);g.resize(width,1);g.primaryAxisSizingMode="AUTO";g.counterAxisSizingMode="FIXED";g.primaryAxisAlignItems="MIN";g.counterAxisAlignItems="MIN";g.setBoundVariable("itemSpacing",spacing);
 if(parent.layoutMode==="NONE"){g.x=x;g.y=y;}else g.layoutSizingHorizontal="FILL";
 let cursor=0;
 for(const t of texts){g.appendChild(t);t.layoutPositioning="AUTO";t.textAutoResize="HEIGHT";t.textTruncation="DISABLED";t.maxLines=null;t.resize(width,t.height);t.layoutSizingHorizontal="FILL";t.textAlignHorizontal="LEFT";t.x=0;t.y=cursor;cursor+=t.height+8;changed.push(t.id);}
 g.resize(width,cursor-8);g.primaryAxisSizingMode="AUTO";if(parent.layoutMode!=="NONE")g.layoutSizingHorizontal="FILL";
 created.push(g.id);changed.push(parent.id);groups.push({id:g.id,parent:parent.id,width:g.width,height:g.height,texts:texts.map(t=>({id:t.id,text:t.characters,y:t.y,h:t.height}))});
 for(let i=0;i<texts.length-1;i++){const a=texts[i].absoluteBoundingBox,b=texts[i+1].absoluteBoundingBox;if(a&&b&&a.y+a.height>b.y-7)problems.push({group:g.id,a:texts[i].id,b:texts[i+1].id});}
}
// When the original heading was hidden by the shared header migration,
// anchor the visible specimen note below the current header.
for(const g of figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>n.name==="Account / intro")){
 const texts=g.children.filter(n=>n.type==="TEXT");
 if(!texts.some(t=>!t.visible))continue;
 const header=g.parent.children.find(n=>n.name==="Shared header / unified"&&n.visible);
 if(!header)continue;
 g.x=header.x;g.y=header.y+header.height+16;g.resize(header.width,16);g.primaryAxisSizingMode="AUTO";
 for(const t of texts){for(const segment of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(segment.fontName);t.resize(header.width,t.height);t.layoutSizingHorizontal="FILL";changed.push(t.id);}
 changed.push(g.id);
}
return {created,changed,groups,initialProblems:problems};