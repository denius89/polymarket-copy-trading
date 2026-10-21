await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(CONFIG.pageId));
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const c=(await figma.variables.getLocalVariableCollectionsAsync()).find(c=>c.name==='Prototype demo state'),all=await figma.variables.getLocalVariablesAsync(),ru=CONFIG.locale==='ru';
function variable(name,type,value){let v=all.find(v=>v.name==='Feedback continuity/'+CONFIG.locale+'/'+name);if(!v){v=figma.variables.createVariable('Feedback continuity/'+CONFIG.locale+'/'+name,c,type);v.setValueForMode(c.defaultModeId,value);}return v;}
const state=variable('state','STRING','new'),status=variable('list status','STRING',ru?'Новое · не назначено':'New · unassigned'),link=variable('link','STRING',ru?'Связь с обращением не создавалась':'No ticket link has been created');
const set=(v,value)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type:'STRING',resolvedType:'STRING',value}});
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null});
const eq=value=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[{type:'VARIABLE_ALIAS',resolvedType:'STRING',value:{type:'VARIABLE_ALIAS',id:state.id}},{type:'STRING',resolvedType:'STRING',value}]}});
const keyFor={new:'feedback-detail',updated:'feedback-updated',linked:'feedback-linked',resolved:'feedback-resolved'};
const openCurrent=Object.entries(keyFor).map(([value,key])=>({type:'CONDITIONAL',conditionalBlocks:[{condition:eq(value),actions:[nav(CONFIG.targets[key])]},{actions:[]}]}));
const newSelection={type:'CONDITIONAL',conditionalBlocks:[{condition:eq('new'),actions:[nav(CONFIG.targets['feedback-filtered'])]},{actions:[nav(CONFIG.targets['feedback-empty'])]}]};
const nodes=[],proof=[];
for(const key of CONFIG.keys){const root=await figma.getNodeByIdAsync(CONFIG.targets[key]),main=root.children.find(n=>n.name==='Main');if(!main)throw Error(key);
 if(key==='feedback'){const row=main.findOne(n=>n.type==='TEXT'&&/^FB-DEMO-01 ·/.test(n.characters)).parent;const cell=row.findOne(n=>n.type==='TEXT'&&/^(Новое · не назначено|New · unassigned)$/.test(n.characters));cell.setBoundVariable('characters',status);nodes.push(cell.id);}
 if(key==='feedback-resolved'){const text=main.findOne(n=>n.type==='TEXT'&&/^(Связи сохраняются|Existing links retained)/.test(n.characters));text.setBoundVariable('characters',link);nodes.push(text.id);const outcome=main.findOne(n=>n.type==='TEXT'&&/^(Классифицировано и передано в поддержку|Classified and referred to support)/.test(n.characters));outcome.characters=ru?'Внутренний разбор завершён · Нора Азиз':'Internal processing completed · Nora Aziz';nodes.push(outcome.id);}
 for(const n of main.findAll(n=>'reactions'in n&&n.reactions.length>0)){let changed=false;const rs=[];
 for(const r of n.reactions){const actions=[];for(const a of r.actions||[]){if(a.type!=='NODE'){actions.push(a);continue;}
 const destination=a.destinationId;const targetKey=Object.keys(keyFor).find(value=>CONFIG.targets[keyFor[value]]===destination&&value!=='new');
 const sourceState=Object.keys(keyFor).find(value=>keyFor[value]===key&&value!=='new');const nextState=targetKey||sourceState;
 if(nextState){actions.push(set(state,nextState),set(status,ru?(nextState==='resolved'?'Разобрано · Нора Азиз':'В работе · Нора Азиз'):(nextState==='resolved'?'Reviewed · Nora Aziz':'In progress · Nora Aziz')));if(nextState==='linked')actions.push(set(link,'FB-DEMO-01 → TKT-1042 · '+(ru?'связь сохранена; статус обращения не изменён':'link retained; ticket status unchanged')));changed=true;}
 if(destination===CONFIG.targets['feedback-detail']&&key!=='feedback-readonly'&&key!=='feedback-no-access'){actions.push(...openCurrent);changed=true;}
 else if(destination===CONFIG.targets['feedback-filtered']){actions.push(newSelection);changed=true;}
 else actions.push(a);
 }rs.push({...r,actions});}
 if(changed){await n.setReactionsAsync(rs);nodes.push(n.id);}
 }
 proof.push({key,id:root.id,actor:main.findAllWithCriteria({types:['TEXT']}).find(t=>t.characters.includes('STAFF-203'))?.characters,originalText:main.findAllWithCriteria({types:['TEXT']}).filter(t=>t.characters.includes('В демо покупка')).map(t=>t.characters)});
}
return {locale:CONFIG.locale,mutatedNodeIds:nodes,variables:{state:state.id,status:status.id,link:link.id},proof,rootFrames:figma.currentPage.children.filter(n=>n.type==='FRAME').length};
