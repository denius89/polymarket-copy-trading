// Align existing settings navigation; preserve its right-hand content.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
await Promise.all(['Regular','Medium','Semi Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const created=[],mutated=[],removed=[],proof=[];
const vars=await figma.variables.getLocalVariablesAsync(),vm=new Map(vars.map(v=>[v.name,v]));
const col=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:134:180');
let origin=vm.get('Admin customer/noor/filtered origin');if(!origin){origin=figma.variables.createVariable('Admin customer/noor/filtered origin',col,'BOOLEAN');origin.scopes=['ALL_SCOPES'];origin.setValueForMode(col.defaultModeId,false);created.push(origin.id);}
const set=(v,value)=>({type:'SET_VARIABLE',variableId:v.id,variableValue:{type:'BOOLEAN',resolvedType:'BOOLEAN',value}});
const node=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,preserveScrollPosition:true});
const condition={type:'VARIABLE_ALIAS',resolvedType:'BOOLEAN',value:{type:'VARIABLE_ALIAS',id:origin.id}};
function route(yes,no){return {type:'CONDITIONAL',conditionalBlocks:[{condition,actions:[node(yes)]},{actions:[node(no)]}]};}
const keys=['overview','connections','sessions','operations','support'];
const normal=await figma.getNodeByIdAsync('2032:67'),selected=await figma.getNodeByIdAsync('2032:74');
function props(n,vals){const p={};for(const[k,v]of Object.entries(vals)){const a=Object.keys(n.componentProperties).find(x=>x.split('#')[0]===k);if(a)p[a]=v;}n.setProperties(p);}
for(const [id,loc,who,ops]of SETTINGS){const r=await figma.getNodeByIdAsync(id),en=loc==='en',noor=who==='noor';const nav=r.query('FRAME[name^="Section navigation"]').first();if(!nav)throw Error('Missing nav '+id);const width=nav.width;for(const c of [...nav.children]){removed.push(c.id);c.remove();}nav.itemSpacing=4;
 const labels=en?['Overview','Connections','Sessions','Operations','Support','Settings']:['Обзор','Подключения','Сессии','Операции','Обращения','Настройки'];
 const dest=ops?(en?'1982:38700':'1982:37877'):noor?(en?'2210:82672':'2210:21620'):(en?'1982:38667':'1982:37844');
 for(let i=0;i<6;i++){const n=(i===5?selected:normal).createInstance();nav.appendChild(n);created.push(n.id);n.resize(width,n.height);n.name='Customer settings tab · '+(keys[i]||'settings');props(n,{Label:labels[i],Icon:['2032:10','2032:59','2032:17','2032:25','2032:14','2032:41'][i]});if(i<5){const actions=keys.flatMap(k=>[set(vm.get('Admin customer/'+who+'/'+k),k===keys[i]),set(vm.get('Admin customer/'+who+'/'+k+'/inactive'),k!==keys[i])]);actions.push(noor?route(en?'3445:204036':'3445:202900',dest):node(dest));await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions}]);}}
 mutated.push(nav.id);proof.push({id,nav:nav.id,client:who,ops,settingsContentPreserved:true});}
for(const [id,filtered]of [['1982:37788',false],['1982:38611',false],['3445:70297',true],['3445:202693',true]]){const r=await figma.getNodeByIdAsync(id);for(const row of r.query('INSTANCE[name="Open customer · U-DEMO-002"]')){await row.setReactionsAsync(row.reactions.map(x=>({...x,actions:[set(origin,filtered),...(x.actions||[])]})));mutated.push(row.id);}}
for(const [id,en,filtered]of [['2210:21620',false,false],['2210:82672',true,false],['3445:202900',false,true],['3445:204036',true,true]]){const r=await figma.getNodeByIdAsync(id);const settings=r.query('FRAME[name="Customer section navigation"] INSTANCE').filter(x=>Object.values(x.componentProperties).some(p=>p.value===(en?'Settings':'Настройки'))).first();if(settings){await settings.setReactionsAsync(settings.reactions.map(x=>({...x,actions:[set(origin,filtered),...(x.actions||[])]})));mutated.push(settings.id);}const back=r.query('INSTANCE').filter(n=>n.name==='User action · '+(en?'Back to results':'К выборке')).first();if(back){await back.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[filtered?node(en?'3445:202693':'3445:70297'):route(en?'3445:202693':'3445:70297',en?'1982:38611':'1982:37788')]}]);mutated.push(back.id);}}
return {createdNodeIds:created,mutatedNodeIds:mutated,removedNodeIds:removed,origin:origin.id,proof};
