figma.skipInvisibleInstanceChildren=false;
const p=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(p);
const vs=await figma.variables.getLocalVariablesAsync(),v=n=>vs.find(x=>x.name===n&&x.variableCollectionId==='VariableCollectionId:3986:27')||vs.find(x=>x.name===n);
const val=x=>({type:typeof x==='boolean'?'BOOLEAN':'STRING',resolvedType:typeof x==='boolean'?'BOOLEAN':'STRING',value:x});
const set=(n,x)=>({type:'SET_VARIABLE',variableId:v(n).id,variableValue:val(x)});
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,resetScrollPosition:true});
const changed=[];for(const[id,btn]of[['4127:346','4127:393'],['4127:348','4127:510']]){const n=await figma.getNodeByIdAsync(btn);await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[set('reconciliation/profileReturn',id),nav('3990:109')]}]);changed.push(btn);}
const note=await figma.getNodeByIdAsync('4127:454');note.setBoundVariable('visible',v('trading/robin/shown'));changed.push(note.id);
const names=['Обзор','Пользователи','Сессии','Поддержка','Денежная сверка','Инциденты'];
for(const root of p.children.filter(n=>n.name.startsWith('READY /'))){for(const n of root.findAll(n=>'reactions'in n&&n.reactions.length&&names.includes(n.name))){const rr=JSON.parse(JSON.stringify(n.reactions));for(const r of rr){const a=r.actions||[r.action];delete r.action;r.actions=[set('trading/fromOrder',false),...a];}await n.setReactionsAsync(rr);changed.push(n.id);}}
return {changedNodeIds:changed,noteVisibleBinding:note.boundVariables.visible,rootCount:p.children.filter(x=>x.name.startsWith('READY /')).length};