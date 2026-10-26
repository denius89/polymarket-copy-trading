// Run with START and END injected; current READY/MOBILE roots only. Retry-safe by named group.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
figma.skipInvisibleInstanceChildren=false;
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const col=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:3986:28');
const known={'navigation/clarity/restrictions':'VariableID:4361:2292','navigation/clarity/finance':'VariableID:4361:2293','navigation/clarity/finance-overview':'VariableID:4361:2294'};
const mutated=[],created=[],removed=[];
async function label(name,ru,en){const v=await figma.variables.getVariableByIdAsync(known[name]);v.setValueForMode('3986:1',ru);v.setValueForMode('3986:2',en);return v;}
const unified=await label('navigation/clarity/restrictions','Ограничения и восстановление','Restrictions and recovery');
const finTitle=await label('navigation/clarity/finance','Финансы','Finance');
const finOverview=await label('navigation/clarity/finance-overview','Обзор финансов','Finance overview');
const rec=await figma.variables.getVariableByIdAsync('VariableID:4101:409');rec.setValueForMode('3986:1','Сверка операций');rec.setValueForMode('3986:2','Operation reconciliation');mutated.push(rec.id);
function bind(n,v){for(const tx of n.query('TEXT')){tx.setBoundVariable('characters',v);tx.textAutoResize='HEIGHT';tx.resize(Math.max(100,n.width-32),tx.height);mutated.push(tx.id);}mutated.push(n.id);}
const roots=figma.currentPage.children.filter(n=>n.type==='FRAME'&&/^(READY|MOBILE) \/ /.test(n.name)).filter(r=>r.children.some(n=>['Persistent navigation','Mobile menu content'].includes(n.name)));
for(const root of roots.slice(START,END)){
 const side=root.children.find(n=>['Persistent navigation','Mobile menu content'].includes(n.name));const mobile=root.name.startsWith('MOBILE');
 let group=side.children.find(n=>n.name==='Finance navigation group');
 if(!group){
  const reco=side.children.find(n=>n.name==='Денежная сверка');
  const fin=side.children.find(n=>n.name==='Финансы'||n.name==='Финансы · availability');
  if(reco&&fin){const idx=Math.min(side.children.indexOf(reco),side.children.indexOf(fin));
   group=figma.createAutoLayout('VERTICAL',{name:'Finance navigation group',itemSpacing:8,fills:[]});side.insertChild(idx,group);group.resize(side.width-side.paddingLeft-side.paddingRight,100);group.layoutSizingHorizontal='FILL';group.primaryAxisSizingMode='AUTO';group.setBoundVariable('visible',await figma.variables.getVariableByIdAsync(reco.boundVariables.visible.id));created.push(group.id);
   const tx=figma.createText();tx.fontName={family:'Inter',style:'Medium'};tx.fontSize=12;tx.characters='Финансы';tx.setBoundVariable('characters',finTitle);tx.fills=[{type:'SOLID',color:{r:0.64,g:0.68,b:0.76}}];group.appendChild(tx);tx.textAutoResize='HEIGHT';tx.resize(group.width,20);tx.layoutSizingHorizontal='FILL';created.push(tx.id);
   group.appendChild(fin);group.appendChild(reco);bind(reco,rec);reco.name='Сверка операций';
   if(fin.type==='INSTANCE')bind(fin,finOverview);else for(const inst of fin.children.filter(n=>n.type==='INSTANCE'))bind(inst,finOverview);
   mutated.push(fin.id,reco.id,side.id);
  }
 }
 let target=side.children.find(n=>n.name==='Ограничения и восстановление');
 const tech=side.children.find(n=>n.name==='Технический режим');const old=side.children.find(n=>n.name==='Аварийное восстановление');
 if(!target){target=tech||old;if(target){target.name='Ограничения и восстановление';bind(target,unified);target.resize(target.width,64);if(root.id!==(mobile?'4311:2321':'4304:2295'))await target.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:mobile?'4311:2321':'4304:2295',navigation:'NAVIGATE',transition:null,resetScrollPosition:true}]}]);}}
 if(target){target.setBoundVariable('visible',await figma.variables.getVariableByIdAsync('VariableID:4143:375'));mutated.push(target.id);}
 if(old&&old!==target){removed.push(old.id);old.remove();}
 if(target&&/\/(?: |.*\/ )(?:emergency|technicalMode)/.test(root.name)){target.fills=[{type:'SOLID',color:{r:0.17,g:0.13,b:0.27}}];mutated.push(target.id);}
}
return {range:[START,END],sidebars:roots.length,createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],removedNodeIds:removed};
