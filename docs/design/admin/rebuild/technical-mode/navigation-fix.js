// Inject common helpers, the clarity variable helper and ROOTS. Bounded sidebar update.
figma.skipInvisibleInstanceChildren=false;
const normal=vars['technical/normal'],locked=vars['technical/locked'];
const desktopSource=await figma.getNodeByIdAsync('4010:95');
const mobileRoot=await figma.getNodeByIdAsync('4162:707');
const mobileSource=mobileRoot.children.find(n=>n.name==='Mobile menu content');
const mobileHeader=mobileRoot.children.find(n=>n.name==='Mobile navigation header');
const order=['Обзор','Пользователи','Личный профиль','Поддержка','Денежная сверка','Финансы','Площадки и данные','Контент и маркетинг','Incident management heading','Сотрудники и права','Технический режим','Инциденты','Аварийное восстановление'];
const blockedNames=['Обзор','Пользователи','Поддержка','Финансы','Площадки и данные','Контент и маркетинг','Сотрудники и права'];
const mobileDest={'3971:2':'4162:707','3971:3':'4159:420','3990:109':'4160:684','4083:241':'4161:64265','4100:294':'4161:64832','4143:371':'4161:65427','4304:2295':'4311:2321'};
const done=[];
for(const [id,mobile,active] of ROOTS){
 const root=await figma.getNodeByIdAsync(id);
 let side=root.children.find(n=>n.name===(mobile?'Mobile menu content':'Persistent navigation'));
 if(side?.children.some(n=>n.name==='Technical mode navigation status')){done.push({id,alreadyApplied:true});continue;}
 if(id==='4304:2295'||id==='4304:2296'||!side){
  const old=side;side=(mobile?mobileSource:desktopSource).clone();root.insertChild(0,side);created.push(side.id,...side.findAll(()=>true).map(n=>n.id));if(old)old.remove();
  if(mobile&&!root.children.some(n=>n.name==='Mobile navigation header')){const h=mobileHeader.clone();root.insertChild(0,h);created.push(h.id,...h.findAll(()=>true).map(n=>n.id));}
 }
 side.itemSpacing=8;side.primaryAxisSizingMode='AUTO';side.paddingTop=side.paddingBottom=16;side.paddingLeft=side.paddingRight=mobile?0:16;
 const width=mobile?358:200;
 let tech=side.children.find(n=>n.name==='Технический режим');
 if(!tech){tech=button(side,'Технический режим','Technical mode',null,width);tech.setBoundVariable('visible',vars['support/read']||await figma.variables.getVariableByIdAsync('VariableID:4059:143'));if(id!==(mobile?'4311:2321':'4304:2295'))await tech.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[nav(mobile?'4311:2321':'4304:2295')]}]);}
 for(const c of [...side.children])if(c.type==='TEXT'&&['Первый рабочий маршрут','Демо-торговля Paper Alpha · комиссия 0%'].includes(c.name)){c.remove();}
 let idx=2;
 for(const name of order){const c=side.children.find(n=>n.name===name);if(!c)continue;side.insertChild(idx++,c);if(c.type!=='INSTANCE')continue;
  if(name==='Обзор'&&id!==(mobile?'4162:707':'3971:2'))await c.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[nav(mobile?'4162:707':'3971:2')]}]);
  c.fills=[paint(name===active?'selected':'surface')];c.resize(width,['Аварийное восстановление','Контент и маркетинг','Сотрудники и права'].includes(name)?64:44);
  for(const tx of c.findAllWithCriteria({types:['TEXT']})){tx.textAutoResize='HEIGHT';tx.resize(width-32,tx.height);tx.layoutSizingHorizontal='FILL';tx.fills=[paint(name===active?'text':'muted')];}
  if(blockedNames.includes(name)){
   const role=c.boundVariables?.visible;const index=side.children.indexOf(c),wrap=box(side,name+' · availability',width,'VERTICAL',0);side.insertChild(index,wrap);if(role)wrap.setBoundVariable('visible',await figma.variables.getVariableByIdAsync(role.id));wrap.appendChild(c);c.setBoundVariable('visible',normal);
   const disabled=c.clone();wrap.appendChild(disabled);created.push(disabled.id,...disabled.findAll(()=>true).map(n=>n.id));disabled.name=name+' · locked';disabled.setBoundVariable('visible',locked);await disabled.setReactionsAsync([]);disabled.fills=[paint('surface')];
   // A visible lock and the shared explanation distinguish a temporary restriction from missing permission.
   const lock=figma.createNodeFromSvg('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="5" y="10" width="14" height="11" rx="2" stroke="#a3adc2" stroke-width="1.7"/><path d="M8 10V6a4 4 0 0 1 8 0v4" stroke="#a3adc2" stroke-width="1.7"/></svg>');wrap.appendChild(lock);lock.layoutPositioning='ABSOLUTE';lock.x=width-26;lock.y=14;lock.setBoundVariable('visible',locked);created.push(lock.id,...lock.findAll(()=>true).map(n=>n.id));
   disabled.setBoundVariable('paddingRight',null);disabled.paddingRight=36;for(const tx of disabled.findAllWithCriteria({types:['TEXT']})){tx.resize(width-disabled.paddingLeft-36,tx.height);tx.layoutSizingHorizontal='FILL';tx.textAlignHorizontal='LEFT';}mutated.push(c.id,wrap.id);
  }else mutated.push(c.id);
 }
 const status=box(side,'Technical mode navigation status',width,'VERTICAL',6,'surface');status.paddingTop=12;status.setBoundVariable('visible',locked);text(status,'Технический режим','Technical mode',width,13,'Semi Bold');text(status,'$technical/status','',width,12);text(status,'Разделы с замком недоступны до выключения режима.','Locked sections are unavailable until this mode is turned off.',width,12,'Regular','muted');
 mutated.push(side.id,root.id);done.push({id,sidebar:side.id,mobile,active,children:side.children.length});
}
return {createdNodeIds:created,mutatedNodeIds:mutated,roots:done};
