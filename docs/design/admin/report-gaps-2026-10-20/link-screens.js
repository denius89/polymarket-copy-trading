// Supply CONFIG with the paired roots, specs, core targets and entry actions.
const page=await figma.getNodeByIdAsync(CONFIG.pageId);await figma.setCurrentPageAsync(page);
const changed=[],created=[],proof=[];
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const nodeAction=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null});
const resolve=key=>CONFIG.targets[key];
for(const item of CONFIG.roots){
 const spec=CONFIG.specs.find(s=>s.key===item.key);const root=await figma.getNodeByIdAsync(item.id);const main=root.children.find(n=>n.name==='Main');
 const bar=main.children.find(n=>n.name==='Scenario actions');
 for(let i=0;i<spec.actions.length;i++){
  const a=spec.actions[i],b=bar.children[i];if(!b)throw new Error('missing action '+item.key+' '+i);
  b.name='Gap action · '+a.target;b.setProperties({'Label#113:1':a.label[CONFIG.locale]});
  const action=a.target==='@back'?{type:'BACK'}:nodeAction(resolve(a.target));if(action.type==='NODE'&&!action.destinationId)throw new Error('unknown '+a.target);
  await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[action]}]);changed.push(b.id);
 }
 // Reapply changed domain copy after review; no detached instances.
 const rows=main.children.find(n=>n.name==='Scenario records').children.filter(n=>n.type==='INSTANCE').slice(1);
 for(let i=0;i<spec.rows[CONFIG.locale].length;i++){const v=spec.rows[CONFIG.locale][i];rows[i].setProperties({'Title#2137:0':v[0],'Detail#2137:1':v[1],'Meta#2137:2':v[2]});changed.push(rows[i].id);}
 const crumb=main.children.find(n=>n.name==='Breadcrumb trail');
 const sectionTarget=spec.section==='ADM-02'?(item.key==='users-filter-form'?'users':'users-filter-result'):spec.section==='ADM-03'?'session-inspection':spec.section==='ADM-04'?'incident-reopened-queue':spec.section==='ADM-09'?'support':spec.section==='ADM-14'?(item.key==='staff-invite-activated'||item.key==='staff-invited-list'?'staff-invited-list':'staff'):'connections';
 const sectionKey=Object.keys(crumb.componentProperties).find(k=>k.startsWith('Section#'));const homeKey=Object.keys(crumb.componentProperties).find(k=>k.startsWith('Home#'));
 const sectionText=crumb.componentProperties[sectionKey].value;const homeText=crumb.componentProperties[homeKey].value;
 for(const t of crumb.findAllWithCriteria({types:['TEXT']})){
  if(t.characters===sectionText){await t.setReactionsAsync(resolve(sectionTarget)===root.id?[]:[{trigger:{type:'ON_CLICK'},actions:[nodeAction(resolve(sectionTarget))]}]);changed.push(t.id);}
  else if(t.characters===homeText){await t.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[nodeAction(resolve(spec.role==='ops'?'role-operations-overview':'overview'))]}]);changed.push(t.id);}
 }
 // The operational actor never follows a cloned Owner A profile control.
 const actor=main.children.find(n=>n.name==='Context');
 for(const n of actor.findAll(n=>'reactions'in n&&/My account|open profile/i.test(n.name))){await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[nodeAction(resolve(spec.role==='ops'?'role-profile-ops':'my-profile'))]}]);changed.push(n.id);}
 if(spec.section==='ADM-04')for(const n of root.children[0].findAll(n=>'reactions'in n)){
  if((n.reactions||[]).some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.destinationId===resolve('ops-queue')))){await n.setReactionsAsync(resolve('incident-reopened-queue')===root.id?[]:[{trigger:{type:'ON_CLICK'},actions:[nodeAction(resolve('incident-reopened-queue'))]}]);changed.push(n.id);}
 }
 proof.push({key:item.key,id:root.id,actions:bar.children.map(n=>({id:n.id,name:n.name,reactions:n.reactions})),sectionTarget:resolve(sectionTarget),role:spec.role});
}
const sourceButton=await figma.getNodeByIdAsync('3051:63842');
for(const entry of CONFIG.entries){
 const root=await figma.getNodeByIdAsync(entry.root);if(!root)throw new Error('entry missing '+entry.root);
 const main=root.children.find(n=>/Main/.test(n.name));if(!main)throw new Error('entry main missing '+entry.root);
 let bar=main.children.find(n=>n.name==='Report follow-up navigation');
 if(!bar){bar=figma.createAutoLayout('HORIZONTAL');bar.name='Report follow-up navigation';bar.fills=[];bar.setBoundVariable('itemSpacing',await figma.variables.getVariableByIdAsync('VariableID:2:56'));main.appendChild(bar);bar.layoutSizingHorizontal='FILL';created.push(bar.id);}
 for(const a of entry.actions){
  let b=bar.children.find(n=>n.name==='Follow-up · '+a.target);
  if(!b){b=sourceButton.clone();bar.appendChild(b);b.name='Follow-up · '+a.target;created.push(b.id,...b.findAll(()=>true).map(n=>n.id));}
  b.setProperties({'Label#113:1':a.label[CONFIG.locale]});await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[nodeAction(resolve(a.target))]}]);changed.push(b.id);
 }
 main.layoutSizingVertical='HUG';root.resize(root.width,Math.max(root.height,main.y+main.height+32));changed.push(root.id,main.id);
}
// Original users page is an unfiltered fixture, not an ID search yielding two users.
const original=await figma.getNodeByIdAsync(CONFIG.locale==='ru'?'1982:37807':'1982:38630');
if(original&&original.type==='INSTANCE'&&Object.keys(original.componentProperties).includes('Body#1981:4')){original.setProperties({'Title#1981:3':CONFIG.locale==='ru'?'Все пользователи · учебный снимок':'All users · synthetic snapshot','Body#1981:4':CONFIG.locale==='ru'?'Два пользователя без отбора. Поиск по ID, VIP, состоянию, площадке и периоду — в форме «Поиск и отбор».':'Two unfiltered users. Search by ID, VIP, status, venue and period in Search and filters.'});changed.push(original.id);}
return {locale:CONFIG.locale,createdNodeIds:created,mutatedNodeIds:[...new Set(changed)],proof,entries:CONFIG.entries};
