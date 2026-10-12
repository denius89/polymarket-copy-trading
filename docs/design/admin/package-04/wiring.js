
const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);const mutated=[],invalid=[];let edges=0;
for(const l of LINKS){const n=await figma.getNodeByIdAsync(l.sourceId);if(!n){invalid.push(l.sourceId);continue;}let action;
if(l.kind==='url')action={type:'URL',url:l.url};
else if(l.kind==='locale'){const id=OPPOSITE[l.target];if(!id){invalid.push(l.target);continue;}action={type:'URL',url:'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id='+id.replace(':','-')+'&starting-point-node-id='+id.replace(':','-')+'&scaling=scale-down'};}
else{const id=TARGETS[l.target];if(!id){invalid.push(l.target);continue;}let root=n;while(root.parent&&root.parent.id!==p.id)root=root.parent;if(root.id===id){await n.setReactionsAsync([]);mutated.push(n.id);continue;}action={type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,preserveScrollPosition:false};}
await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[action]}]);mutated.push(n.id);edges++;}
if(FINAL){const keys=['demo-review','admin-login','monitor-normal','emergency','audit'];p.flowStartingPoints=[...p.flowStartingPoints.filter(f=>!f.name.includes('Package 04')&&!keys.some(k=>TARGETS[k]===f.nodeId)),...keys.map(k=>({nodeId:TARGETS[k],name:LANG.toUpperCase()+' · Package 04 · '+k}))];mutated.push(p.id);}
return {mutatedNodeIds:mutated,invalid,edgeCount:edges};