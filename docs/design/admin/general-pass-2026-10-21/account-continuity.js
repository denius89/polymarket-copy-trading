await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(CONFIG.pageId));
const roots=[];for(const entry of CONFIG.roots){roots.push({entry,node:await figma.getNodeByIdAsync(entry.id)});}
const fontMap=new Map();for(const {node} of roots)for(const t of node.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fontMap.set(s.fontName.family+'|'+s.fontName.style,s.fontName);await Promise.all([...fontMap.values()].map(f=>figma.loadFontAsync(f)));
const collection=(await figma.variables.getLocalVariableCollectionsAsync()).find(c=>c.name==='Prototype demo state');if(!collection)throw Error('Missing prototype state collection');
const existing=await figma.variables.getLocalVariablesAsync(),prefix='Admin account continuity/'+CONFIG.locale.toUpperCase()+'/';
async function variable(key,type,value){let v=existing.find(v=>v.name===prefix+key);if(!v){v=figma.variables.createVariable(prefix+key,collection,type);v.setValueForMode(collection.defaultModeId,value);}return v;}
const email=await variable('email','STRING','elena.owner@demo.example'),emailVerified=await variable('verified email','STRING','elena.owner@demo.example · '+(CONFIG.locale==='ru'?'Подтверждён':'Verified')),ended=await variable('other sessions ended','BOOLEAN',false);
const set=(v,type,value)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type,resolvedType:type,value}});
const changedEmail=[set(email,'STRING','elena.new@demo.example'),set(emailVerified,'STRING','elena.new@demo.example · '+(CONFIG.locale==='ru'?'Подтверждён':'Verified')),set(ended,'BOOLEAN',true)];
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null});
const sessionChoice={type:'CONDITIONAL',conditionalBlocks:[{condition:{type:'VARIABLE_ALIAS',resolvedType:'BOOLEAN',value:{type:'VARIABLE_ALIAS',id:ended.id}},actions:[nav(CONFIG.targets['sessions-other-revoked'])]},{actions:[nav(CONFIG.targets['my-sessions'])]}]};
let modifiedRoots=[],linkCount=0,boundCount=0,translatedCount=0,proof=[];
for(const {entry,node}of roots){let edits=0;
 for(const t of node.findAllWithCriteria({types:['TEXT']})){
  if(CONFIG.locale==='ru'&&t.characters==='Елена Морозова · Owner'){t.characters='Елена Морозова · владелец';translatedCount++;edits++;}
  if(t.characters==='elena.owner@demo.example'&&entry.key!=='email-saved'){t.setBoundVariable('characters',email);boundCount++;edits++;}
  else if(t.characters==='elena.owner@demo.example'&&entry.key==='email-saved'){t.characters='elena.new@demo.example';edits++;}
  else if(/^elena.owner@demo.example · (Подтверждён|Verified)$/.test(t.characters)){t.setBoundVariable('characters',emailVerified);boundCount++;edits++;}
 }
 for(const n of node.findAll(n=>'reactions'in n&&n.reactions.length)){
  let touched=false;const reactions=[];
  for(const r of n.reactions){const acts=[];for(const a of r.actions||[]){
   let next=a;
   if(a.type==='URL'&&a.url.includes('figma.com/proto/'+CONFIG.fileKey)){const match=a.url.match(/[?&]node-id=(\d+)-(\d+)/);if(match){const id=match[1]+':'+match[2];if(id===node.id){touched=true;continue;}const target=await figma.getNodeByIdAsync(id);if(target&&target.type==='FRAME'&&target.parent.id===CONFIG.pageId){next=nav(id);linkCount++;touched=true;}}}
   if(next.type==='NODE'&&next.destinationId===CONFIG.targets['my-sessions']){next=sessionChoice;touched=true;}
   const emailDone=next.type==='NODE'&&next.destinationId===CONFIG.targets['email-saved'];
   const pwdDone=next.type==='NODE'&&next.destinationId===CONFIG.targets['password-saved'];
   if(emailDone||entry.key==='email-saved'){if(!acts.some(a=>a.variableId===email.id))acts.push(...changedEmail);touched=true;}
   else if(pwdDone||entry.key==='password-saved'||entry.key==='sessions-other-revoked'){if(!acts.some(a=>a.variableId===ended.id))acts.push(set(ended,'BOOLEAN',true));touched=true;}
   acts.push(next);
  }reactions.push({...r,actions:acts});}
  if(touched){await n.setReactionsAsync(reactions);edits++;}
 }
 if(edits)modifiedRoots.push({key:entry.key,id:node.id,edits});
 if(['email-pending','email-saved','password-saved','account-security','my-sessions','sessions-other-revoked'].includes(entry.key))proof.push({key:entry.key,id:node.id,text:node.findAllWithCriteria({types:['TEXT']}).filter(t=>t.visible&&(/elena\.|владелец|Owner|сессии|sessions/.test(t.characters))).map(t=>({id:t.id,text:t.characters,bound:t.boundVariables})),actions:node.findAll(n=>'reactions'in n&&(n.name.startsWith('Action ·')||n.name.startsWith('Section item'))).map(n=>({id:n.id,name:n.name,reactions:n.reactions}))});
}
return {locale:CONFIG.locale,modifiedRoots,linkCount,boundCount,translatedCount,variables:{email:email.id,verifiedEmail:emailVerified.id,otherSessionsEnded:ended.id},proof};
