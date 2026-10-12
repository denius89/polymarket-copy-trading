const page=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(page);
const created=[];const track=n=>{created.push(n.id);return n;};
const styles=await figma.getLocalTextStylesAsync();const styleMap=Object.fromEntries(styles.map(s=>[s.name,s]));for(const s of styles) await figma.loadFontAsync(s.fontName);
const masters={};for(const [k,id] of Object.entries({metric:'1981:3',panel:'1981:7',notice:'1981:13',row:'2002:5',primary:'113:207',secondary:'113:209',quiet:'113:211',nav:'1978:1003',selected:'1978:1005',select:'1978:874'})) masters[k]=await figma.getNodeByIdAsync(id);
const variables={};for(const [k,id]of Object.entries({canvas:'2:28',surface:'2:29',text:'2:34',secondary:'2:35',muted:'2:36',gap:'2:54',pad:'2:56',radius:'2:62'}))variables[k]=await figma.variables.getVariableByIdAsync('VariableID:'+id);
function paint(n,key){n.fills=[figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:0,g:0,b:0}},'color',variables[key])];}
function container(parent,name,direction,w,h){const n=track(figma.createAutoLayout(direction));parent.appendChild(n);n.name=name;n.resize(w,h);n.primaryAxisSizingMode='AUTO';n.counterAxisSizingMode='FIXED';n.fills=[];n.itemSpacing=16;n.setBoundVariable('itemSpacing',variables.gap);return n;}
async function text(parent,value,style='Body/Small',width=1096,key='text'){const t=track(figma.createText());parent.appendChild(t);t.characters=value;await t.setTextStyleIdAsync(styleMap[style].id);t.textAutoResize='HEIGHT';t.resize(width,24);paint(t,key);return t;}
function instance(parent,type,values,width){const i=track(masters[type].createInstance());parent.appendChild(i);i.name=values.name||type;const props={};for(const [k,v]of Object.entries(values)){if(k==='name')continue;const prop=Object.keys(i.componentProperties).find(p=>p.split('#')[0]===k);if(prop)props[prop]=v;}i.setProperties(props);if(width)i.resize(width,i.height);return i;}
const frames=[];
for(let idx=START;idx<END;idx++){
 const d=DATA[idx];const L=LANG==='ru'?0:1;const choose=a=>a[L];const root=container(page,LANG.toUpperCase()+' · '+d.key+' · '+choose(d.title),'HORIZONTAL',1440,1000);root.primaryAxisSizingMode='FIXED';root.counterAxisSizingMode='FIXED';root.itemSpacing=16;root.resize(1440,1000);root.x=(idx%5)*1560;root.y=Math.floor(idx/5)*1120;root.clipsContent=true;paint(root,'canvas');root.setExplicitVariableModeForCollection('VariableCollectionId:2:3','2:1');
 const side=container(root,'Navigation','VERTICAL',232,1000);side.primaryAxisSizingMode='FIXED';side.resize(232,1000);paint(side,'surface');for(const k of ['paddingTop','paddingBottom','paddingLeft','paddingRight'])side.setBoundVariable(k,variables.pad);
 await text(side,'SHADOW','Heading/Medium',184);await text(side,L===0?'Админка · Дизайн':'Admin · Design','Caption',184,'secondary');
 const navs=[['finance',['Финансы','Finance']],['ledger',['Поступления / расходы','Receipts / expenses']],['partners',['Партнёры','Partners']],['payouts',['Выплаты','Payouts']],['pricing',['Тарифы / рефералы','Pricing / referrals']],['security-policy',['Защитные пороги','Security thresholds']]];
 for(const [dest,label]of navs){const i=instance(side,d.key===dest?'selected':'nav',{Label:choose(label),name:'Nav · '+dest},184);i.layoutSizingHorizontal='FILL';}
 await text(side,L===0?'Пакет 02 · макет\nOwner-only денежные действия\nБез реальных переводов':'Package 02 · preview\nOwner-only money actions\nNo real transfers','Caption',184,'muted');
 instance(side,'quiet',{Label:L===0?'Пакет 01 ↗':'Package 01 ↗',name:'Package 01 link'},184);
 const main=container(root,'Main','VERTICAL',1192,1000);main.primaryAxisSizingMode='FIXED';main.resize(1192,1000);for(const k of ['paddingTop','paddingBottom','paddingLeft','paddingRight'])main.setBoundVariable(k,variables.pad);
 const head=container(main,'Context','HORIZONTAL',1144,48);head.primaryAxisSizingMode='FIXED';head.counterAxisSizingMode='FIXED';await text(head,(L===0?'ДИЗАЙН / ПРИМЕР · ':'DESIGN / FIXTURE · ')+d.role,'Label',960);instance(head,'quiet',{Label:L===0?'EN':'RU',name:'Locale switch'},96);
 await text(main,choose(d.title),'Heading/Large',1144);
 await text(main,L===0?'Синтетические данные · пример будущего платного режима · источники не подключены':'Synthetic data · future paid-stage example · sources disconnected','Caption',1144,'muted');
 instance(main,'panel',{Title:L===0?'Контекст':'Context',Body:choose(d.body),name:'Context panel'},1144);
 if(d.metrics){const row=container(main,'Metrics','HORIZONTAL',1144,132);for(const m of d.metrics){const i=instance(row,'metric',{Title:m[L],Value:m[2],Hint:L===0?'Иллюстративный расчёт':'Illustrative calculation'},370);i.layoutSizingHorizontal='FILL';}}
 if(d.fields){const row=container(main,'Fields','HORIZONTAL',1144,110);for(const m of d.fields){const i=instance(row,'select',{Label:m[L],Value:m[2],name:'Field · '+m[1]},370);i.layoutSizingHorizontal='FILL';for(const n of i.findAllWithCriteria({types:['FRAME']})){if(n.name==='Control')n.layoutSizingHorizontal='FILL';}}}
 if(d.rows){const table=container(main,'Finance table','VERTICAL',1144,100);const h=instance(table,'row',{Entity:L===0?'Запись / партнёр':'Entry / partner',Venue:L===0?'Площадка':'Venue',Amount:L===0?'Сумма / правило':'Amount / rule',State:L===0?'Состояние':'State',Time:L===0?'Время UTC':'Time UTC',name:'Table header'},1144);for(const r of d.rows)instance(table,'row',{Entity:r[L],Venue:r[2],Amount:r[3],State:r[L===0?4:5],Time:'12 Oct · 12:00',name:'Row · '+r[1]},1144);}
 if(d.notice)instance(main,'notice',{Title:d.notice[L],Body:d.notice[L+2],name:'Notice'},1144);
 if(d.actions.length){const row=container(main,'Actions','HORIZONTAL',1144,48);for(let j=0;j<d.actions.length;j++){const a=d.actions[j];instance(row,j===0?'primary':'secondary',{Label:choose(a.label),name:'Action · '+a.target},350);}}
 await text(main,L===0?'Прототип: поля и результаты — примеры. Кнопки не выполняют реальные операции.':'Prototype: fields and results are examples. Buttons do not execute real operations.','Caption',1144,'muted');
 frames.push({id:root.id,key:d.key,name:root.name,role:d.role});
}
return {createdNodeIds:created,frames,count:frames.length};
