// Inputs PAGE, LOCALE, DATA, PAIRS. Bounded UI-only finishing and native readback.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE));
const ru=LOCALE==='RU',L=ru?0:1,ids=Object.fromEntries(PAIRS.map(p=>[p.key,p[ru?'ru':'en']]));
ids.sessions=ru?'1982:38062':'1982:38885';ids['user-noor']=ru?'2210:21620':'2210:82672';ids['order-history']=ru?'3014:58072':'3016:58059';
const roots=await Promise.all(DATA.map(d=>figma.getNodeByIdAsync(ids[d.key])));
const oldEntry=await figma.getNodeByIdAsync(ru?'3040:62188':'3042:62175');
const edits=ru?{'2105:5768':'618 RU +618 EN · 613 основных состояний на язык · карта 0.21 · UI kit 0.4.21','2105:5790':'Макеты есть · 53 RU / 53 EN','2105:5791':'Позиции, заявки, действия трейдера и решения. Связи, причины пропуска, отмена и поздние исполнения.','2105:5793':'Открыть: Рабочее место сессии'}:{};
const mapTexts=await Promise.all(Object.keys(edits).map(id=>figma.getNodeByIdAsync(id)));
const fonts=new Map();for(const n of [roots[0],oldEntry,...mapTexts])for(const t of n.type==='TEXT'?[n]:n.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const changed=[],errors=[],screens=[],links=[],tokens=[];
const source=await figma.getNodeByIdAsync(ru?'3014:58256':'3016:58243'),sm=source.children.find(n=>n.name==='Main');
const sourceActions=sm.children.find(n=>n.name==='Actions'),sourceTable=sm.children.find(n=>n.name==='Operation evidence and amounts');
const bindFields=new Set(['itemSpacing','counterAxisSpacing','paddingLeft','paddingRight','paddingTop','paddingBottom','topLeftRadius','topRightRadius','bottomLeftRadius','bottomRightRadius']);
const binders=[];for(const [kind,src]of [['row',sourceActions],['table',sourceTable]])for(const [field,value]of Object.entries(src.boundVariables||{}))if(bindFields.has(field)&&value?.id){const v=await figma.variables.getVariableByIdAsync(value.id);if(v){binders.push({kind,field,v});tokens.push({kind,field,id:v.id,name:v.name});}}
function prop(n,name,value){const k=Object.keys(n.componentProperties).find(k=>k.split('#')[0]===name);if(k)n.setProperties({[k]:value});}
function nav(node,to){node.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:to,navigation:'NAVIGATE',transition:null,preserveScrollPosition:false}]}];changed.push(node.id);}
prop(oldEntry,'Label',ru?'Пример: рабочее место сессии':'Example: session workspace');oldEntry.primaryAxisSizingMode='AUTO';oldEntry.layoutSizingHorizontal='HUG';nav(oldEntry,ids['session-inspection']);
for(const t of mapTexts){t.characters=edits[t.id];t.textAutoResize='HEIGHT';changed.push(t.id);}
if(ru)nav(await figma.getNodeByIdAsync('2105:5793'),ids['session-inspection']);
for(let k=0;k<DATA.length;k++){
 const d=DATA[k],r=roots[k],main=r.children.find(n=>n.name==='Main'),table=main.children.find(n=>n.name==='Session records');
 for(const n of main.children){const kind=n===table?'table':['Session sections','Decision filters','Read-only actions','Prototype scenarios'].includes(n.name)?'row':null;if(kind)for(const b of binders.filter(b=>b.kind===kind)){n.setBoundVariable(b.field,b.v);changed.push(n.id);}}
 const rows=table.children.filter(n=>n.type==='INSTANCE');if(rows.length!==d.rows.length+1)errors.push({root:r.id,reason:'record count'});
 for(let i=0;i<rows.length;i++){
  const row=rows[i],ts=row.children.filter(n=>n.type==='TEXT');const expected=i===0?d.headers.map(x=>x[L]):[d.rows[i-1][L],d.rows[i-1][L+2],d.rows[i-1][L+4]];
  for(let c=0;c<ts.length;c++){const t=ts[c];if(t.characters!==expected[c])errors.push({root:r.id,row:i,column:c,reason:'text mismatch',expected:expected[c],actual:t.characters});if(t.width<300||t.x<row.paddingLeft-3||t.x+t.width>row.width-row.paddingRight+3)errors.push({root:r.id,row:i,column:c,reason:'column bounds',x:t.x,w:t.width});}
  if(i>0&&row.reactions.length){ts[0].textDecoration='UNDERLINE';changed.push(ts[0].id);}
 }
 const activeSections=main.children.find(n=>n.name==='Session sections');if(Boolean(activeSections)===Boolean(d.hideTabs))errors.push({root:r.id,reason:'section navigation visibility'});
 for(const frame of main.children.filter(n=>['Session sections','Decision filters','Read-only actions','Prototype scenarios'].includes(n.name)))for(const b of frame.children){for(const reaction of b.reactions||[])for(const a of reaction.actions||[])if(a.type==='NODE'){if(!Object.values(ids).includes(a.destinationId)||a.destinationId===r.id)errors.push({root:r.id,reason:'action destination',to:a.destinationId});links.push({from:r.id,node:b.id,to:a.destinationId,kind:frame.name});}}
 for(const row of rows.slice(1))for(const reaction of row.reactions||[])for(const a of reaction.actions||[])if(a.type==='NODE')links.push({from:r.id,node:row.id,to:a.destinationId,kind:'Record detail'});
 const footer=main.children.at(-1);if(main.y+footer.y+footer.height>r.height-16)errors.push({root:r.id,reason:'footer overflow'});
 for(let i=1;i<main.children.length;i++){const prev=main.children[i-1],next=main.children[i];if(next.y<prev.y+prev.height-0.5)errors.push({root:r.id,reason:'block overlap',previous:prev.id,next:next.id});}
 if(r.placeholder)errors.push({root:r.id,reason:'unfinished placeholder'});
 screens.push({key:d.key,id:r.id,width:r.width,height:r.height,rows:d.rows.length,table:table.id,footerBottom:main.y+footer.y+footer.height,placeholder:r.placeholder});
}
return {mutatedNodeIds:[...new Set(changed)],screens,links,errors,sourceTokenBindings:tokens,entry:{node:oldEntry.id,target:ids['session-inspection']},rootsPerLocale:figma.currentPage.children.filter(n=>n.type==='FRAME').length};
