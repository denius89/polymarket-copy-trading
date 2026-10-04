// Reference-only clone. One inspected page/source/width per use_figma invocation.
// Originals are never resized or rewired. Reactions are stripped from the clone.
const CONFIG = { pageId:'33:2', sourceFrameId:null, width:320, sectionName:'Reference · Rich data · mobile RU', index:0, sampleFaq:null };
const page=await figma.getNodeByIdAsync(CONFIG.pageId);
if(!page || page.type!=='PAGE') throw new Error('Missing verified page');
await figma.setCurrentPageAsync(page);
const source=CONFIG.sourceFrameId && await figma.getNodeByIdAsync(CONFIG.sourceFrameId);
if(!source || source.type!=='FRAME') throw new Error('Supply a verified rich source frame');
let owner=source;while(owner && owner.type!=='PAGE')owner=owner.parent;
if(owner!==page)throw new Error('Source belongs to a different page');
if(!Number.isFinite(CONFIG.width) || CONFIG.width<300 || !Number.isInteger(CONFIG.index) || CONFIG.index<0)throw new Error('Invalid reference width/index');
let section=page.children.find(n=>n.type==='SECTION' && n.name===CONFIG.sectionName);
const title='Reference only · '+source.name+' · '+CONFIG.width+' px';
if(section){const prior=section.children.find(n=>n.type==='FRAME' && n.name===title);if(prior)return{existing:true,referenceId:prior.id,sectionId:section.id,createdNodeIds:[],mutatedNodeIds:[],diagnostics:['Reference exists; no overwrite or duplication.']};}
const fonts=new Map();for(const t of source.findAllWithCriteria({types:['TEXT']}))for(const seg of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(seg.fontName),seg.fontName);
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const created=[],mutated=[],diagnostics=[];
if(!section){section=figma.createSection();page.appendChild(section);section.name=CONFIG.sectionName;section.x=Math.max(0,...page.children.filter(n=>n!==section).map(n=>n.x+n.width))+240;section.y=100;created.push(section.id);}
const clone=source.clone();section.appendChild(clone);clone.name=title;
const nodes=[clone,...clone.findAll(()=>true)];created.push(...nodes.map(n=>n.id));
if(CONFIG.sampleFaq){
  const replacements={'Object title':CONFIG.sampleFaq.question,'Object body':CONFIG.sampleFaq.answer};
  for(const t of nodes.filter(n=>n.type==='TEXT' && Object.prototype.hasOwnProperty.call(replacements,n.name))){t.setBoundVariable('characters',null);t.characters=String(replacements[t.name]||'');t.textAutoResize='HEIGHT';if(t.parent?.type==='FRAME' && t.parent.layoutMode!=='NONE')t.layoutSizingVertical='HUG';}
}
for(const n of nodes.filter(n=>['FRAME','INSTANCE'].includes(n.type) && n.name.startsWith('Action / '))){
  if('minHeight'in n)n.minHeight=48;
  if(n.layoutMode==='HORIZONTAL')n.counterAxisSizingMode='AUTO';
  else if(n.layoutMode==='VERTICAL')n.primaryAxisSizingMode='AUTO';
  if(n.parent?.type==='FRAME' && n.parent.layoutMode!=='NONE' && n.layoutPositioning!=='ABSOLUTE')n.layoutSizingVertical='HUG';
}
const oldWidths=new Map(nodes.filter(n=>'width'in n).map(n=>[n.id,n.width]));
const clickOwners=nodes.filter(n=>'reactions'in n && n.reactions.some(r=>['ON_CLICK','ON_PRESS','ON_DRAG'].includes(r.trigger?.type)));
for(const n of nodes.filter(n=>'reactions'in n && n.reactions.length))await n.setReactionsAsync([]);
if('flowStartingPoints'in page && page.flowStartingPoints.some(p=>p.nodeId===clone.id))page.flowStartingPoints=page.flowStartingPoints.filter(p=>p.nodeId!==clone.id);
function widthOf(n,w,fill=false){
  if(!['FRAME','INSTANCE','TEXT'].includes(n.type))return;
  w=Math.max(1,w);const vh=n.type==='FRAME'&&n.layoutMode==='VERTICAL'&&n.primaryAxisSizingMode==='AUTO',hh=n.type==='FRAME'&&n.layoutMode==='HORIZONTAL'&&n.counterAxisSizingMode==='AUTO';
  if('minWidth'in n && n.minWidth>w){let a=n.parent,inside=false;while(a&&a!==clone){if(a.type==='INSTANCE'){inside=true;break;}a=a.parent;}if(inside)w=n.minWidth;else n.minWidth=w;}
  n.resize(w,n.height);if(vh)n.primaryAxisSizingMode='AUTO';if(hh)n.counterAxisSizingMode='AUTO';
  if(n.type==='TEXT'){n.textAutoResize='HEIGHT';if(n.parent && n.parent.type==='FRAME' && ['VERTICAL','HORIZONTAL'].includes(n.parent.layoutMode) && n.layoutPositioning!=='ABSOLUTE'){n.layoutSizingVertical='HUG';if(fill)n.layoutSizingHorizontal='FILL';}}
  else if(fill && n.parent && n.parent.type==='FRAME' && ['VERTICAL','HORIZONTAL'].includes(n.parent.layoutMode) && n.layoutPositioning!=='ABSOLUTE')n.layoutSizingHorizontal='FILL';
}
function reflow(n){
  if(!('children'in n))return;
  const flow=n.children.filter(c=>c.visible && c.layoutPositioning!=='ABSOLUTE'),inner=Math.max(1,n.width-(n.paddingLeft||0)-(n.paddingRight||0));
  if(n.layoutMode==='VERTICAL'){
    const oldInner=Math.max(1,(oldWidths.get(n.id)||n.width)-(n.paddingLeft||0)-(n.paddingRight||0));
    for(const c of flow)if(c.width>inner || (oldWidths.get(c.id)||c.width)>=oldInner*.8)widthOf(c,inner,true);
  }else if(n.layoutMode==='HORIZONTAL'){
    const available=Math.max(1,inner-Math.max(0,flow.length-1)*(n.itemSpacing||0));
    const total=flow.reduce((s,c)=>s+c.width,0);
    if(total>available+.5){
      const fixed=flow.filter(c=>!['FRAME','INSTANCE','TEXT'].includes(c.type) || c.width<=44 || (c.type==='TEXT' && /Amount|P[n&]L|Value/i.test(c.name)));
      const flexible=flow.filter(c=>!fixed.includes(c));const room=available-fixed.reduce((s,c)=>s+c.width,0),weight=flexible.reduce((s,c)=>s+c.width,0);
      if(room>=flexible.length*44 && weight>0)for(const c of flexible)widthOf(c,Math.max(44,room*c.width/weight),false);
      else diagnostics.push({id:n.id,name:n.name,issue:'Horizontal row needs explicit compact/wrap design',available,total});
    }
  }else if(n.type==='FRAME' && n.layoutMode==='NONE'){
    for(const c of n.children.filter(c=>c.visible)){
      const oldW=oldWidths.get(c.id)||c.width,oldParent=oldWidths.get(n.id)||n.width;
      if(c.x<=1 && oldW>=oldParent*.8)widthOf(c,n.width-c.x,false);
      else if(c.x+c.width>n.width+.5 && ['FRAME','INSTANCE','TEXT'].includes(c.type)){
        if(c.x>=n.width-44){diagnostics.push({id:c.id,issue:'Absolute child requires explicit repositioning',x:c.x,parentWidth:n.width});}
        else widthOf(c,n.width-c.x,false);
      }
    }
  }
  for(const c of n.children)reflow(c);
}
const compactCandidate=clone.findOne(n=>n.name==='Shared header / explorer');if(CONFIG.width===320 && CONFIG.compactHeaderId && compactCandidate)compactCandidate.swapComponent(await figma.getNodeByIdAsync(CONFIG.compactHeaderId));
clone.resize(CONFIG.width,source.height);reflow(clone);
const header=clone.findOne(n=>n.name==='Shared header / explorer');

if(header && CONFIG.width<600){header.primaryAxisSizingMode='FIXED';header.resize(CONFIG.width-40,44);header.itemSpacing=8;header.primaryAxisAlignItems='MIN';const brand=header.children.find(n=>n.type==='TEXT'),balance=header.children.find(n=>/Balance/.test(n.name));if(brand){brand.layoutSizingHorizontal='FIXED';brand.resize(70,brand.height);}if(balance){balance.layoutSizingHorizontal='FIXED';balance.resize(Math.min(120,header.width-70-88-24),44);for(const t of balance.findAllWithCriteria({types:['TEXT']})){t.resize(balance.width-16,t.height);if(CONFIG.width===320 && /Демо|Demo/.test(t.characters))t.characters=source.name.includes(' / RU / ')?'Демо':'Demo';}}}

for(const n of clickOwners)if('resize'in n && (n.width<44 || n.height<44)){
  n.resize(Math.max(44,n.width),Math.max(44,n.height));
  if(n.type==='TEXT'){n.textAutoResize='HEIGHT';if(n.parent?.type==='FRAME' && n.parent.layoutMode!=='NONE' && n.layoutPositioning!=='ABSOLUTE')n.layoutSizingVertical='HUG';}
  diagnostics.push({id:n.id,name:n.name,issue:'Original hit geometry expanded to at least 44px in reference; inspect neighbours'});
}
// Stack references in canvas order. A single existing reference is not moved.
clone.x=40;clone.y=40+CONFIG.index*(source.height+80);
const right=Math.max(0,...section.children.map(n=>n.x+n.width)),bottom=Math.max(0,...section.children.map(n=>n.y+n.height));section.resizeWithoutConstraints(right+40,bottom+40);mutated.push(section.id);
const remainingReactions=nodes.filter(n=>'reactions'in n && n.reactions.length).map(n=>n.id);
const actionTextOverflows=[];
for(const t of nodes.filter(n=>n.type==='TEXT' && n.characters.trim())){let a=t.parent;while(a && a!==clone && !a.name.startsWith('Action / '))a=a.parent;if(!a || a===clone || !a.absoluteBoundingBox || !t.absoluteBoundingBox)continue;const b=a.absoluteBoundingBox,p=t.absoluteBoundingBox;if(p.x<b.x-.5 || p.y<b.y-.5 || p.x+p.width>b.x+b.width+.5 || p.y+p.height>b.y+b.height+.5)actionTextOverflows.push({id:t.id,actionId:a.id,text:t.characters.slice(0,80)});}
return{pageId:page.id,sectionId:section.id,sourceId:source.id,referenceId:clone.id,width:clone.width,height:clone.height,createdNodeIds:created,mutatedNodeIds:mutated.filter(id=>!created.includes(id)),clonedDescendantCount:nodes.length-1,remainingReactions,sampleFaqApplied:!!CONFIG.sampleFaq,actionTextOverflows,diagnostics:diagnostics.slice(0,30),diagnosticCount:diagnostics.length,referenceOnly:true,limitations:['Responsive reference is a static full-frame composition, not a new product flow or runtime proof.','Original source IDs and reactions are untouched; clone reactions are cleared.','FAQ sample overrides title/body character bindings only in reference clone.','Inspect full screenshot, wrapping, absolute children and last row under fixed navigation before accepting.']};
