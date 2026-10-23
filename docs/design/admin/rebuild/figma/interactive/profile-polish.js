// Repair native playback of multi-branch conditions, then check layout bounds.
const bounds=[];
for(const id of [PROFILE.profile,...Object.values(PROFILE.roots)]){const root=await figma.getNodeByIdAsync(id);for(const n of root.findAll(n=>'reactions'in n&&n.reactions.length)){let changed=false;const rr=JSON.parse(JSON.stringify(n.reactions));for(const r of rr)if(r.actions)r.actions=r.actions.flatMap(a=>{if(a.type==='CONDITIONAL'&&a.conditionalBlocks.length>1&&a.conditionalBlocks.every(b=>b.condition)){changed=true;return a.conditionalBlocks.map(b=>({type:'CONDITIONAL',conditionalBlocks:[b,{actions:[]}]}));}return[a];});if(changed){await n.setReactionsAsync(rr);mutated.push(n.id);}}
 bounds.push({id:root.id,name:root.name,width:root.width,height:root.height,children:root.children.map(n=>({name:n.name,width:n.width,height:n.height,y:n.y}))});}
const profile=await figma.getNodeByIdAsync(PROFILE.profile);profile.resize(1440,900);profile.children[0].resize(232,900);mutated.push(profile.id,profile.children[0].id);
return {createdNodeIds:[],mutatedNodeIds:mutated,bounds};
