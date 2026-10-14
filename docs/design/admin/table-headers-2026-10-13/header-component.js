const p=await figma.getNodeByIdAsync('1981:2');await figma.setCurrentPageAsync(p);
const created=[],mutated=[],track=n=>{created.push(n.id);return n;};
const styles=await figma.getLocalTextStylesAsync();const style=styles.find(s=>s.name==='Body/Small medium');await figma.loadFontAsync(style.fontName);
const vars=await figma.variables.getLocalVariablesAsync(),vm=new Map(vars.map(v=>[v.name,v]));const collections=await figma.variables.getLocalVariableCollectionsAsync(),cm=new Map(collections.map(c=>[c.id,c])),vi=new Map(vars.map(v=>[v.id,v]));
function resolve(v){const c=cm.get(v.variableCollectionId),x=v.valuesByMode[c.modes.find(m=>m.name==='Dark')?.modeId||c.defaultModeId];return x?.type==='VARIABLE_ALIAS'?resolve(vi.get(x.id)):x;}
function fill(name){const v=vm.get(name),rgb=resolve(v);return figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:rgb.r,g:rgb.g,b:rgb.b}},'color',v);}
const host=await figma.getNodeByIdAsync('2097:5418'),reviewHost=await figma.getNodeByIdAsync('2097:5419');
if(p.findAllWithCriteria({types:['COMPONENT_SET']}).some(n=>n.name==='Admin/Table header'))throw new Error('Existing header; inspect');
const variants=[];
for(const cfg of [{name:'Metadata',padding:20,widths:[357.333333,357.333333,357.333333],labels:['Параметр','Значение','Примечание']},{name:'Support',padding:16,widths:[660,244,176],labels:['Обращение / клиент и контекст','Статус / ответственный','Обновлено (UTC)']}]){
 const c=track(figma.createComponent());host.appendChild(c);c.name='Layout='+cfg.name;c.layoutMode='HORIZONTAL';c.resize(1144,48);c.primaryAxisSizingMode='FIXED';c.counterAxisSizingMode='FIXED';c.counterAxisAlignItems='CENTER';c.paddingLeft=cfg.padding;c.paddingRight=cfg.padding;c.paddingTop=8;c.paddingBottom=8;c.itemSpacing=16;c.fills=[fill('color/bg/surface')];c.strokes=[fill('color/border/default')];c.strokeBottomWeight=1;c.strokeTopWeight=0;c.strokeLeftWeight=0;c.strokeRightWeight=0;c.setBoundVariable('itemSpacing',vm.get('spacing/4'));
 for(let j=0;j<3;j++){const t=track(figma.createText());c.appendChild(t);t.name='Column '+(j+1);t.textStyleId=style.id;t.characters=cfg.labels[j];t.textAutoResize='HEIGHT';t.resize(cfg.widths[j],t.height);t.fills=[fill('color/text/primary')];const prop=c.addComponentProperty('Column '+(j+1),'TEXT',cfg.labels[j]);t.componentPropertyReferences={characters:prop};}
 c.description='Шапка таблицы. Колонки и отступы совпадают с Admin/Metadata row либо Admin/Support ticket row. Метки задаются по смыслу данных; не обозначает сортировку.';variants.push(c);
}
const set=track(figma.combineAsVariants(variants,host));set.name='Admin/Table header';set.x=24;set.y=5230;set.resize(1208,156);for(let i=0;i<variants.length;i++){variants[i].x=24;variants[i].y=18+i*66;}
const review=track(figma.createAutoLayout('VERTICAL'));reviewHost.appendChild(review);review.name='Table headers · aligned columns';review.x=24;review.y=3650;review.resize(1172,200);review.primaryAxisSizingMode='AUTO';review.counterAxisSizingMode='FIXED';review.itemSpacing=16;review.fills=[];review.setBoundVariable('itemSpacing',vm.get('spacing/4'));
for(const v of variants){const i=track(v.createInstance());review.appendChild(i);i.name='Header example · '+v.name;for(const ch of i.findAllWithCriteria({types:['TEXT']}))created.push(ch.id);}
reviewHost.resizeWithoutConstraints(reviewHost.width,review.y+review.height+40);mutated.push(reviewHost.id,host.id);
return {createdNodeIds:created,mutatedNodeIds:mutated,setId:set.id,metadata:variants[0].id,support:variants[1].id,review:review.id,width:1144,height:48};