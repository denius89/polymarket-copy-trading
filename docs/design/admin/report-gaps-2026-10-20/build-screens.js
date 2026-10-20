// Figma construction receipt. Supply CONFIG {locale,pageId,specs}; not a backup or application.
const page=await figma.getNodeByIdAsync(CONFIG.pageId);await figma.setCurrentPageAsync(page);
const base=await figma.getNodeByIdAsync(CONFIG.locale==='ru'?'3050:62186':'3050:187312');
const allFonts=new Map();
for(const t of base.findAllWithCriteria({types:['TEXT']}))for(const seg of t.getStyledTextSegments(['fontName']))allFonts.set(JSON.stringify(seg.fontName),seg.fontName);
await Promise.all([...allFonts.values()].map(f=>figma.loadFontAsync(f)));
const sourceButton=await figma.getNodeByIdAsync('3051:63842');
const sourceRow=await figma.getNodeByIdAsync('3051:63820');
const sourceField=await Promise.all(['2081:229','2081:181','2081:150'].map(id=>figma.getNodeByIdAsync(id)));
const navRoots=CONFIG.locale==='ru'?{'ADM-02':'1982:37788','ADM-03':'3050:62186','ADM-04':'2414:117985','ADM-09':'2188:23990','ADM-14':'2110:6876','ADM-15':'2109:5947'}:{'ADM-02':'1982:38611','ADM-03':'3050:187312','ADM-04':'2414:121405','ADM-09':'2188:88355','ADM-14':'2110:55811','ADM-15':'2110:54585'};
const sectionLabels={ru:{'ADM-02':'Пользователи','ADM-03':'Сессии','ADM-04':'Инциденты','ADM-09':'Поддержка','ADM-14':'Сотрудники и роли','ADM-15':'Подключения'},en:{'ADM-02':'Users','ADM-03':'Sessions','ADM-04':'Incidents','ADM-09':'Support','ADM-14':'Staff and roles','ADM-15':'Connections'}};
const out=[],created=[],mutated=[];
let x=Math.max(...page.children.map(n=>n.x+n.width))+200;
for(const spec of CONFIG.specs){
 const name=CONFIG.locale.toUpperCase()+' · '+spec.key+' · '+spec.title[CONFIG.locale];
 let root=page.children.find(n=>n.name===name);
 if(root){out.push({key:spec.key,id:root.id,reused:true});continue;}
 root=base.clone();page.appendChild(root);root.x=x;root.y=0;x+=1640;root.name=name;
 const main=root.children.find(n=>n.name==='Main');
 if(!main)throw new Error('main missing');
 // Existing role-specific menu is cloned without adding grants.
 if(spec.section!=='ADM-03'){
  const nav=root.children.find(n=>n!==main);const sourceRoot=await figma.getNodeByIdAsync(navRoots[spec.section]);const n=sourceRoot.children[0];
  if(!n)throw new Error('nav missing '+spec.section+' '+CONFIG.locale);
  const copy=n.clone();root.insertChild(0,copy);copy.x=0;copy.y=0;nav.remove();
 }
 for(const c of [...main.children])if(['Session sections','Prototype scenarios label','Prototype scenarios'].includes(c.name))c.remove();
 const title=main.findAllWithCriteria({types:['FRAME']}).find(n=>n.name==='Page heading');
 const heading=title.findAllWithCriteria({types:['TEXT']});heading[0].characters=spec.title[CONFIG.locale];heading[1].characters=CONFIG.locale==='ru'?'Учебный макет · Paper Alpha: комиссия 0% · реальные действия выключены':'Synthetic design · Paper Alpha fee 0% · real actions disabled';
 const actor=main.children.find(n=>n.name==='Context');
 const actorText=actor.findAllWithCriteria({types:['TEXT']})[0];
 actorText.characters=spec.role==='ops'?(CONFIG.locale==='ru'?'Олег Смирнов · STAFF-206 · просмотр по полномочиям':'Oleg Smirnov · STAFF-206 · scoped access'):(CONFIG.locale==='ru'?'Елена Морозова · STAFF-201 · владелец A':'Elena Morozova · STAFF-201 · Owner A');
 for(const b of actor.findAll(n=>'reactions'in n&&(/My account|open profile/i.test(n.name)||(n.reactions||[]).some(r=>(r.actions||[]).some(a=>a.type==='NODE'&&a.destinationId===(CONFIG.locale==='ru'?'2155:19298':'2155:79040'))))))await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:spec.role==='ops'?(CONFIG.locale==='ru'?'3182:78753':'3182:221737'):(CONFIG.locale==='ru'?'2155:19298':'2155:79040'),navigation:'NAVIGATE',transition:null}]}]);
 const crumb=main.children.find(n=>n.name==='Breadcrumb trail');crumb.setProperties({'Current#2211:2':spec.title[CONFIG.locale],'Section#2211:1':sectionLabels[CONFIG.locale][spec.section]});
 const context=main.children.find(n=>n.name==='Session context');context.name='Scenario context';context.setProperties({'Title#1981:3':CONFIG.locale==='ru'?'Контекст и доступ':'Context and access','Body#1981:4':spec.context[CONFIG.locale]});
 const table=main.children.find(n=>n.name==='Session records');table.name='Scenario records';
 const header=table.children.find(n=>n.type==='INSTANCE');
 header.setProperties({'Column 1#2202:6':CONFIG.locale==='ru'?'Объект / условие':'Object / condition','Column 2#2202:7':CONFIG.locale==='ru'?'Состояние / значение':'State / value','Column 3#2202:8':CONFIG.locale==='ru'?'Пояснение и последствия':'Meaning and consequences'});
 for(const c of [...table.children])if(c!==header)c.remove();
 for(const row of spec.rows[CONFIG.locale]){const r=sourceRow.clone();table.appendChild(r);r.name='Record · '+row[0];r.setProperties({'Title#2137:0':row[0],'Detail#2137:1':row[1],'Meta#2137:2':row[2]});r.layoutSizingHorizontal='FILL';}
 if(spec.fields?.length){
  const form=figma.createAutoLayout('VERTICAL');form.name='Prepared form controls';form.fills=[];form.setBoundVariable('itemSpacing',await figma.variables.getVariableByIdAsync('VariableID:2:56'));main.insertChild(main.children.indexOf(table),form);form.layoutSizingHorizontal='FILL';
  for(let i=0;i<spec.fields.length;i+=3){const row=figma.createAutoLayout('HORIZONTAL');row.fills=[];form.appendChild(row);row.layoutSizingHorizontal='FILL';row.setBoundVariable('itemSpacing',await figma.variables.getVariableByIdAsync('VariableID:2:56'));
   for(const f of spec.fields.slice(i,i+3)){const c=sourceField[f.kind==='Search'?0:f.kind==='Select'?1:2].createInstance();row.appendChild(c);c.resize(365,96);c.setProperties({'Label#2019:0':f.label[CONFIG.locale],'Value#2019:3':f.value[CONFIG.locale],'Hint#2019:6':CONFIG.locale==='ru'?'Подготовленный пример':'Prepared example'});}
  }
 }
 const actions=figma.createAutoLayout('HORIZONTAL');actions.name='Scenario actions';actions.fills=[];actions.setBoundVariable('itemSpacing',await figma.variables.getVariableByIdAsync('VariableID:2:56'));main.insertChild(main.children.length-1,actions);actions.layoutSizingHorizontal='FILL';
 for(const a of spec.actions){const b=sourceButton.clone();actions.appendChild(b);b.name='Gap action · '+a.target;b.setProperties({'Label#113:1':a.label[CONFIG.locale]});await b.setReactionsAsync([]);}
 main.layoutSizingVertical='HUG';root.resize(1440,Math.max(1120,main.height+48));
 const nav=root.children.find(n=>n!==main);if('resize'in nav)nav.resize(nav.width,root.height);
 const ids=[root.id,...root.findAll(()=>true).map(n=>n.id)];created.push(...ids);
 out.push({key:spec.key,id:root.id,section:spec.section,title:spec.title[CONFIG.locale],width:root.width,height:root.height,descendants:ids.length-1,actions:actions.children.map(n=>({id:n.id,name:n.name})),fonts:[...new Set(root.findAllWithCriteria({types:['TEXT']}).flatMap(t=>t.getStyledTextSegments(['fontName']).map(s=>s.fontName.family)))],imagePaintCount:root.findAll(n=>'fills'in n&&Array.isArray(n.fills)&&n.fills.some(f=>f.type==='IMAGE')).length});
}
return {locale:CONFIG.locale,createdNodeIds:created,mutatedNodeIds:mutated,roots:out};
