await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const changed=[],removed=[];function scan(n,out=[]){if(n.type==='INSTANCE'||n.type==='TEXT'){out.push(n);return out;}if('children'in n)for(const c of n.children)scan(c,out);return out;}
for(const id of ['2003:153','2003:313','2003:367','2003:520','3363:69201','2007:153','2007:313','2007:367','2007:520','3363:138351','2003:213','2003:574','2003:627','2003:713','2003:838','2003:876','2003:976','2003:916','2007:213','2007:574','2007:627','2007:713','2007:838','2007:876','2007:976','2007:916']){
const root=await figma.getNodeByIdAsync(id),main=root.children.find(n=>n.name==='Main');
for(const n of scan(main)){if(n.type==='TEXT'){const before=n.characters,after=before.replace('списание $121,20','расчётное списание $121,20').replace('source debit $121.20','calculated source debit $121.20');if(after!==before){await Promise.all(n.getStyledTextSegments(['fontName']).map(s=>figma.loadFontAsync(s.fontName)));n.characters=after;changed.push(n.id);}}
else{const patch={};for(const[k,p]of Object.entries(n.componentProperties))if(p.type==='TEXT'){const v=String(p.value).replace('Списание источника','Расчётное списание').replace('Source debit','Calculated debit').replace('прежний attempt','прежнюю попытку отправки');if(v!==p.value)patch[k]=v;}if(Object.keys(patch).length){n.setProperties(patch);changed.push(n.id);}}}
}
return{mutatedNodeIds:changed,removedNodeIds:removed};
