// One CONFIG and PATCH_RESULT literal per page; read-only evidence.
const c=CONFIG, patch=PATCH_RESULT;
const p=await figma.getNodeByIdAsync(c.page);await figma.setCurrentPageAsync(p);
const visible=(n,root)=>{while(n&&n!==root){if(n.visible===false)return false;n=n.parent;}return true;};
const roles={...patch.roles,emailBack:c.emailBack,confirmBack:c.confirmBack};
const welcome=await figma.getNodeByIdAsync(c.welcome);
roles.mainPrimary=c.mobile?c.mainPrimary:welcome.findAllWithCriteria({types:['INSTANCE']}).find(n=>visible(n,welcome)&&n.componentProperties.Style?.value==='Primary').id;
const actionIds=new Set(Object.values(roles));
const errorActions=[];
for(const id of c.errors){const f=await figma.getNodeByIdAsync(id);
  for(const n of f.findAll(n=>'reactions' in n&&n.reactions.length&&visible(n,f)&&/^Action/.test(n.name))){actionIds.add(n.id);errorActions.push({id:n.id,name:n.name});}}
const actions=await Promise.all([...actionIds].map(async id=>{
  const n=await figma.getNodeByIdAsync(id);return {id,name:n.name,actions:n.reactions.filter(r=>r.trigger.type==='ON_CLICK').flatMap(r=>r.actions||[r.action])};
}));
const frames=[];
for(const id of [c.review,c.percentReview,patch.resume]){
  const n=await figma.getNodeByIdAsync(id);
  frames.push({id,name:n.name,width:n.width,height:n.height,texts:n.findAllWithCriteria({types:['TEXT']}).filter(t=>visible(t,n)).map(t=>({id:t.id,text:t.characters}))});
}
const continuation=await figma.getNodeByIdAsync(patch.resume);
const types={};const images=[];
for(const n of continuation.findAll(()=>true)){
  types[n.type]=(types[n.type]||0)+1;
  if('fills' in n&&Array.isArray(n.fills)&&n.fills.some(f=>f.type==='IMAGE'))images.push({id:n.id,name:n.name,type:n.type,width:n.width,height:n.height});
}
const launch=await figma.getNodeByIdAsync(c.launch);
return {key:c.key,roles,resume:patch.resume,actions,frames,errorActions,launchReactions:launch.reactions,continuation:{types,images,nodeIds:[continuation.id,...continuation.findAll(()=>true).map(n=>n.id)]}};
