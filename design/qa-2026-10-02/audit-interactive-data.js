// Read-only structural QA for the rich-data section. One verified page per invocation.
// Supply actual section/start/frame IDs from creation evidence; defaults do not claim coverage.
const CONFIG = { pageId: '33:2', sectionId: null, startFrameIds: [], expectedFrameIds: [], viewportHeightByFrameId: {}, minHit: 44, requireScrollFrameIds: [] };
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing verified page');
await figma.setCurrentPageAsync(page);
const section = CONFIG.sectionId && await figma.getNodeByIdAsync(CONFIG.sectionId);
if (!section || section.type !== 'SECTION' || section.parent !== page) throw new Error('Supply the actual rich-data section ID on this page');
const visible = n => { for (let x=n; x && x.type !== 'PAGE'; x=x.parent) if ('visible' in x && !x.visible) return false; return true; };
const screen = n => { let root=null; for (let x=n; x && x.type !== 'PAGE'; x=x.parent) if (x.type === 'FRAME') root=x; return root; };
function* actions(list) { for (const a of list || []) { yield a; if (a.type === 'CONDITIONAL') for (const b of a.conditionalBlocks || []) yield* actions(b.actions); } }
const scopeNodes = section.findAll(() => true), scopeIds = new Set(scopeNodes.map(n=>n.id));
const frames = section.children.filter(n=>n.type === 'FRAME');
const expected = CONFIG.expectedFrameIds.length ? CONFIG.expectedFrameIds : frames.map(n=>n.id);
const shortHits=[], missingLinks=[], edges=[], cache=new Map();
for (const n of page.findAll(n=>'reactions' in n && n.reactions.length)) {
  for (const r of n.reactions) {
    if (scopeIds.has(n.id) && visible(n) && ['ON_CLICK','ON_PRESS','ON_DRAG'].includes(r.trigger?.type) && (n.width < CONFIG.minHit || n.height < CONFIG.minHit)) if (!shortHits.some(x=>x.id===n.id)) shortHits.push({id:n.id,name:n.name,width:n.width,height:n.height});
    for (const a of actions(r.actions || (r.action ? [r.action] : []))) {
      if (a.type !== 'NODE' || !a.destinationId) continue;
      if (!cache.has(a.destinationId)) cache.set(a.destinationId,await figma.getNodeByIdAsync(a.destinationId));
      const target=cache.get(a.destinationId), source=screen(n), dest=target && screen(target);
      if (scopeIds.has(n.id) && !target) missingLinks.push({sourceId:n.id,destinationId:a.destinationId});
      if (source && dest) edges.push({from:source.id,to:dest.id});
    }
  }
}
const adjacency=new Map(); for (const e of edges) { if (!adjacency.has(e.from)) adjacency.set(e.from,new Set()); adjacency.get(e.from).add(e.to); }
const reachable=new Set(CONFIG.startFrameIds), queue=[...reachable];
while(queue.length) for(const id of adjacency.get(queue.shift()) || []) if(!reachable.has(id)) {reachable.add(id);queue.push(id);}
const missingFrames=[]; for(const id of expected) if(!scopeIds.has(id)) missingFrames.push(id);
const unreachable=CONFIG.startFrameIds.length ? expected.filter(id=>!reachable.has(id)) : [];
const viewports=[], viewportIssues=[], scrollIssues=[];
for(const f of frames) {
  const intended=CONFIG.viewportHeightByFrameId[f.id];
  const info={id:f.id,name:f.name,width:f.width,height:f.height,clipsContent:f.clipsContent,expectedHeight:intended ?? null}; viewports.push(info);
  if(Number.isFinite(intended) && Math.abs(f.height-intended) > .5) viewportIssues.push({...info,issue:'Root frame height differs from fixed review viewport'});
  const candidates=[f,...f.findAll(n=>n.type==='FRAME')].filter(n=>visible(n) && ['VERTICAL','BOTH'].includes(n.overflowDirection));
  const bounds=candidates.map(n=>{
    const children=n.children.filter(c=>visible(c));
    const bottom=Math.max(0,...children.map(c=>c.y+c.height));
    const right=Math.max(0,...children.map(c=>c.x+c.width));
    return {id:n.id,name:n.name,height:n.height,width:n.width,contentBottom:bottom,contentRight:right,overflowHeight:bottom-n.height,clipsContent:n.clipsContent,overflowDirection:n.overflowDirection};
  });
  info.scrollContainers=bounds;
  if(CONFIG.requireScrollFrameIds.includes(f.id) && !bounds.some(b=>b.overflowHeight > .5 && b.clipsContent)) scrollIssues.push({frameId:f.id,issue:'Required long-list frame has no clipped vertical viewport with content taller than viewport'});
  for(const b of bounds) { if(!b.clipsContent) scrollIssues.push({frameId:f.id,...b,issue:'Scrollable frame does not clip viewport'}); if(b.contentRight > b.width+.5 && b.overflowDirection==='VERTICAL') scrollIssues.push({frameId:f.id,...b,issue:'Unexpected horizontal content overflow'}); }
}
const overlaps=[];
for(let i=0;i<frames.length;i++) for(let j=i+1;j<frames.length;j++) {const a=frames[i],b=frames[j],w=Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x),h=Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y);if(w>.5 && h>.5)overlaps.push({a:a.id,b:b.id,width:w,height:h});}
const sectionOverlaps=[];
for(const other of page.children.filter(n=>n.type==='SECTION' && n.id!==section.id && visible(n))) {const w=Math.min(section.x+section.width,other.x+other.width)-Math.max(section.x,other.x),h=Math.min(section.y+section.height,other.y+other.height)-Math.max(section.y,other.y);if(w>.5 && h>.5)sectionOverlaps.push({a:section.id,b:other.id,width:w,height:h});}
const actionTextOverflows=[];
for(const t of scopeNodes.filter(n=>n.type==='TEXT' && visible(n) && n.characters.trim())){let a=t.parent;while(a && a.type!=='PAGE' && !a.name.startsWith('Action / '))a=a.parent;if(!a || a.type==='PAGE' || !a.absoluteBoundingBox || !t.absoluteBoundingBox)continue;const b=a.absoluteBoundingBox,p=t.absoluteBoundingBox;if(p.x<b.x-.5 || p.y<b.y-.5 || p.x+p.width>b.x+b.width+.5 || p.y+p.height>b.y+b.height+.5)actionTextOverflows.push({id:t.id,actionId:a.id,text:t.characters.slice(0,80)});}
return {pageId:page.id,sectionId:section.id,counts:{frames:frames.length,expectedFrames:expected.length,missingFrames:missingFrames.length,reachableExpected:expected.filter(id=>reachable.has(id)).length,unreachable:unreachable.length,shortHits:shortHits.length,missingLinks:missingLinks.length,viewportIssues:viewportIssues.length,actionTextOverflows:actionTextOverflows.length,scrollIssues:scrollIssues.length,frameOverlaps:overlaps.length,sectionOverlaps:sectionOverlaps.length},startFrameIds:CONFIG.startFrameIds,missingFrames,unreachable,shortHits,missingLinks,viewportIssues,actionTextOverflows,scrollIssues,frameOverlaps:overlaps,sectionOverlaps,viewports,createdNodeIds:[],mutatedNodeIds:[],limitations:['Reachability traverses every conditional branch; it does not prove variable-state consistency or runtime execution.','Bounds use direct scrolling children and structural clip settings; screenshots and Presentation gestures must confirm actual scroll and fixed-panel obstruction.','Return-to-list position, filter semantics, prepared search, keyboard and runtime accessibility require manual review.','An absent start or viewport/long-list configuration is missing coverage, not a passing test.'],coverage:{hasStarts:CONFIG.startFrameIds.length>0,hasExplicitExpectedFrames:CONFIG.expectedFrameIds.length>0,configuredViewportCount:Object.keys(CONFIG.viewportHeightByFrameId).length,requiredLongListCount:CONFIG.requireScrollFrameIds.length}};
