
const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);const mutated=[],removed=[];
for(const s of await figma.getLocalTextStylesAsync())await figma.loadFontAsync(s.fontName);
function remove(n){removed.push(n.id,...('findAllWithCriteria'in n?n.findAllWithCriteria({types:['INSTANCE','FRAME','TEXT']}).map(c=>c.id):[]));n.remove();}
for(const key of KEYS){const root=await figma.getNodeByIdAsync(TARGETS[key]);if(!root)continue;
 const side=root.children.find(n=>n.width===248);if(side)remove(side);
 const main=root.children.find(n=>n.type==='FRAME');main.resize(1440,root.height);main.counterAxisAlignItems='CENTER';main.paddingTop=120;mutated.push(main.id);
 const header=main.children.find(n=>/Account header|context/i.test(n.name));if(header){for(const c of header.children.filter(n=>n.type==='INSTANCE'))remove(c);header.resize(560,header.height);const t=header.children.find(c=>c.type==='TEXT');if(t){t.resize(560,t.height);t.characters=LANG==='ru'?'ВОССТАНОВЛЕНИЕ · DEMO · SHADOW-ADM-01':'RECOVERY · DEMO · SHADOW-ADM-01';mutated.push(t.id);}mutated.push(header.id);}
 const heading=main.children.find(n=>n.name==='Page heading');if(heading){heading.resize(560,heading.height);for(const t of heading.children.filter(n=>n.type==='TEXT')){t.resize(560,t.height);mutated.push(t.id);}mutated.push(heading.id);}
 const columns=main.children.find(n=>/Profile layout/.test(n.name));if(!columns)continue;
 const right=columns.children.find(n=>/Identity/.test(n.name));if(right)remove(right);
 columns.resize(560,columns.height);const left=columns.children[0];left.resize(560,left.height);mutated.push(columns.id,left.id);
 for(const c of left.children){c.resize(560,c.height);mutated.push(c.id);for(const n of c.children){if(n.type==='TEXT'){n.resize(512,n.height);n.textAutoResize='HEIGHT';mutated.push(n.id);}else if(n.type==='INSTANCE'){n.resize(512,n.height);mutated.push(n.id);}else if(n.type==='FRAME'){n.resize(512,n.height);mutated.push(n.id);}}}
}
const recoveryCode=await figma.getNodeByIdAsync(TARGETS['mfa-recovery-code']);const actions=recoveryCode.findAllWithCriteria({types:['FRAME']}).find(n=>n.name==='Account actions');const verify=actions.children.find(n=>n.type==='INSTANCE'&&Object.values(n.componentProperties).some(v=>v.type==='TEXT'&&v.value===(LANG==='ru'?'Пример успешной проверки':'Successful example')));verify.name='Action · mfa-recovery-setup';await verify.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:TARGETS['mfa-recovery-setup'],navigation:'NAVIGATE',transition:null}]}]);mutated.push(verify.id);
for(const key of ['mfa-recovery-setup','mfa-recovery-complete']){const r=await figma.getNodeByIdAsync(TARGETS[key]);for(const n of r.findAllWithCriteria({types:['INSTANCE']})){if(!n.name.startsWith('Action · '))continue;const target=n.name.slice('Action · '.length);await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:TARGETS[target],navigation:'NAVIGATE',transition:null}]}]);mutated.push(n.id);}}
return {mutatedNodeIds:mutated,removedNodeIds:removed,authRecoveryKeys:KEYS,recoveryVerifyId:verify.id};
