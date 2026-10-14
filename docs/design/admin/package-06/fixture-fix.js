
const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);for(const s of await figma.getLocalTextStylesAsync())await figma.loadFontAsync(s.fontName);
const mutated=[],removed=[],newLinks=[],disabled=[];
const fields=DATA;
for(const f of FRAMES){const d=fields.find(d=>d.key===f.key),root=await figma.getNodeByIdAsync(f.id);const composer=root.findAllWithCriteria({types:['FRAME']}).find(n=>n.name==='Composer · explicit visibility');if(composer){
const mode=composer.children.find(n=>n.name==='Public reply / private note'),actions=composer.children.find(n=>n.name==='Composer actions');
for(const n of mode.children.filter(n=>n.type==='INSTANCE')){const label=Object.entries(n.componentProperties).find(([k])=>k.split('#')[0]==='Label')?.[1]?.value;
if(d.general||d.limitless){if(label===(LANG==='ru'?'Внутренняя заметка':'Internal note')){removed.push(n.id);n.remove();continue;}const target=d.general?'support-general-draft':'support-limitless-draft';n.name='Action · '+target;newLinks.push({sourceId:n.id,target,kind:'action',screen:f.key});mutated.push(n.id);}
if(d.unknown||d.sending){n.setProperties({State:'Disabled'});await n.setReactionsAsync([]);disabled.push(n.id);mutated.push(n.id);}}
for(const n of actions.children.filter(n=>n.type==='INSTANCE')){const label=Object.entries(n.componentProperties).find(([k])=>k.split('#')[0]==='Label')?.[1]?.value;if(!d.filled&&label===(LANG==='ru'?'Отправить ответ':'Send reply')){n.setProperties({State:'Disabled'});await n.setReactionsAsync([]);disabled.push(n.id);mutated.push(n.id);}}
}
if(d.general||d.limitless){const summary=root.findAllWithCriteria({types:['FRAME']}).find(n=>n.name==='Ticket context');for(const n of summary.children.filter(n=>n.type==='INSTANCE'))if(['Action · support-assignment','Action · support-status','Action · support-audit'].includes(n.name)){removed.push(n.id);n.remove();}}
}
const filtered=await figma.getNodeByIdAsync(TARGETS['support-filtered']);const table=filtered.findAllWithCriteria({types:['FRAME']}).find(n=>n.name==='Ticket queue');for(const row of table.children.filter(n=>n.type==='INSTANCE')){const title=Object.entries(row.componentProperties).find(([k])=>k.split('#')[0]==='Title')?.[1]?.value;if(title?.startsWith('TKT-1046')){removed.push(row.id);row.remove();}}
for(const t of filtered.findAllWithCriteria({types:['TEXT']}))if(t.characters===(LANG==='ru'?'1–4 из 6 · учебная очередь':'1–4 of 6 · sample queue')){t.characters=LANG==='ru'?'1 из 1 · учебный фильтр':'1 of 1 · sample filter';mutated.push(t.id);}
const pagination=filtered.findAllWithCriteria({types:['FRAME']}).find(n=>n.name==='Queue pagination');for(const n of pagination.children.filter(n=>n.type==='INSTANCE'))if(n.name==='Action · support-page2'){n.setProperties({State:'Disabled'});await n.setReactionsAsync([]);disabled.push(n.id);mutated.push(n.id);}
return {mutatedNodeIds:mutated,removedNodeIds:removed,newLinks,disabledSourceIds:disabled};
