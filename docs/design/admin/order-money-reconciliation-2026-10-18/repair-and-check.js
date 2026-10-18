// Inputs PAGE, LOCALE, PAIRS, DATA. Repairs only this package's existing roots.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE));
const L=LOCALE==='RU'?0:1, field=L===0?'ru':'en';
const map=Object.fromEntries(PAIRS.map(p=>[p.key,p[field]]));
map['user-noor']=L===0?'2210:21620':'2210:82672';
const roots=await Promise.all(DATA.map(d=>figma.getNodeByIdAsync(map[d.key])));
const fonts=new Map();
for(const t of roots[0].findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const changed=[],checks=[],errors=[],links=[];
function prop(n,key,val){const k=Object.keys(n.componentProperties).find(k=>k.split('#')[0]===key);if(k&&n.componentProperties[k].value!==val){n.setProperties({[k]:val});changed.push(n.id);}}
for(let i=0;i<DATA.length;i++){
 const d=DATA[i],r=roots[i],main=r.children.find(n=>n.name==='Main');
 const nav=r.children[0];
 const nr=nav.findAllWithCriteria({types:['INSTANCE']}).map(n=>({n,p:n.componentProperties})).filter(x=>x.p.State&&Object.keys(x.p).some(k=>k.split('#')[0]==='Label'));
 const target=L===0?(d.section==='ADM-03'?'Сессии':'Инциденты и сверка'):(d.section==='ADM-03'?'Sessions':'Incidents & reconciliation');
 for(const {n,p}of nr){const lab=Object.entries(p).find(([k])=>k.split('#')[0]==='Label')[1].value;if(p.State.value==='Selected'||lab===target){prop(n,'State',lab===target?'Selected':'Default');}}
 const table=main.children.find(n=>n.name==='Operation evidence and amounts');
 table.resize(1144,table.height);table.counterAxisSizingMode='FIXED';table.layoutSizingHorizontal='FILL';
 for(let j=0;j<table.children.length;j++){
  const row=table.children[j];row.resize(1142,row.height);row.primaryAxisSizingMode='FIXED';row.layoutSizingHorizontal='FILL';row.counterAxisSizingMode=j===0?'FIXED':'AUTO';
  if(j===0){row.resize(1142,48);row.layoutSizingHorizontal='FILL';row.layoutSizingVertical='FIXED';}else row.layoutSizingVertical='HUG';
  const texts=row.children.filter(n=>n.type==='TEXT');const w=(1142-row.paddingLeft-row.paddingRight-(texts.length-1)*row.itemSpacing)/texts.length;
  for(const t of texts){t.textAutoResize='HEIGHT';t.resize(w,t.height);t.layoutSizingHorizontal='FIXED';changed.push(t.id);}
  changed.push(row.id);
  const expected=j===0?(d.headers?.map(x=>x[L])||(L===0?['Параметр','Значение / состояние','Подтверждение / граница']:['Parameter','Value / state','Evidence / boundary'])):[d.rows[j-1][L],d.rows[j-1][L+2],d.rows[j-1][L+4]];
  texts.forEach((t,k)=>{if(t.characters!==expected[k])errors.push({root:r.id,row:j,col:k,reason:'content',actual:t.characters,expected:expected[k]});if(Math.abs(t.width-w)>1||t.x<row.paddingLeft-1||t.x+t.width>row.width-row.paddingRight+3)errors.push({root:r.id,row:j,col:k,reason:'column bounds',x:t.x,w:t.width});});
 }
 for(const [name,acts]of [['Actions',d.actions],['Prototype scenarios · do not implement',d.scenarios||[]]]){
  const a=main.children.find(n=>n.name===name);if(!a&&acts.length){errors.push({root:r.id,reason:'missing actions'});continue;}if(!a)continue;
  if(a.children.length!==acts.length)errors.push({root:r.id,reason:'action count'});
  a.children.forEach((b,k)=>{const act=acts[k];if(!act)return;prop(b,'Label',act[L]);b.name=(name==='Actions'?'Action · ':'Prototype outcome · ')+act[2];b.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:map[act[2]],navigation:'NAVIGATE',transition:null,preserveScrollPosition:false}]}];changed.push(b.id);links.push({from:r.id,button:b.id,to:map[act[2]],prototypeOnly:name!=='Actions'});});
 }
 const footer=main.children.at(-1);r.resize(1440,Math.max(1120,Math.ceil((main.y+footer.y+footer.height+24)/40)*40));nav.layoutSizingVertical='FILL';r.placeholder=false;
 changed.push(r.id,table.id);checks.push({key:d.key,id:r.id,rows:table.children.length-1,height:r.height,placeholder:r.placeholder});
}
return {mutatedNodeIds:changed,screens:checks,links,errors};
