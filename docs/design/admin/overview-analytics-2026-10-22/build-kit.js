// Adapted native component builder from the current admin UI kit.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:2'));
const created=[],mutated=[];
const vs=await figma.variables.getLocalVariablesAsync(),vm=new Map(vs.map(v=>[v.name,v])),vi=new Map(vs.map(v=>[v.id,v]));
const cs=await figma.variables.getLocalVariableCollectionsAsync(),cm=new Map(cs.map(c=>[c.id,c]));
function value(v){const c=cm.get(v.variableCollectionId),x=v.valuesByMode[c.modes.find(m=>m.name==='Dark')?.modeId||c.defaultModeId];return x?.type==='VARIABLE_ALIAS'?value(vi.get(x.id)):x;}
function paint(name){const v=vm.get(name),c=value(v);return figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:c.r,g:c.g,b:c.b}},'color',v);}
const sm=new Map((await figma.getLocalTextStylesAsync()).map(s=>[s.name,s]));await Promise.all(['Caption','Label','Body/Small'].map(n=>figma.loadFontAsync(sm.get(n).fontName)));
const host=await figma.getNodeByIdAsync('2097:5418');
const found=host.children.find(n=>n.name==='Admin/Activity chart');if(found)return {existing:found.id,variants:found.children.map(n=>({id:n.id,name:n.name})),createdNodeIds:[],mutatedNodeIds:[]};
const tr=n=>(created.push(n.id),n);
function txt(p,s,x,y,w,style='Caption',tone='color/text/secondary'){const t=tr(figma.createText());p.appendChild(t);t.textStyleId=sm.get(style).id;t.characters=s;t.textAutoResize='HEIGHT';t.resize(w,t.height);t.x=x;t.y=y;t.fills=[paint(tone)];return t;}
function path(p,name,data,tone,weight=1){const v=tr(figma.createVector());p.appendChild(v);v.name=name;v.vectorPaths=[{windingRule:'NONZERO',data}];v.fills=[];v.strokes=[paint(tone)];v.strokeWeight=weight;return v;}
const modes=['12h','6h','Stale','Empty','Loading','Error'];const out={};
for(const mode of modes){const c=tr(figma.createComponent());host.appendChild(c);c.name='View='+mode;c.resize(725.333333,224);c.fills=[];c.clipsContent=false;out[mode]=c.id;
 if(['12h','6h','Stale'].includes(mode)){
  for(let i=0;i<3;i++){const y=184-i*80;path(c,'Grid · '+i,`M 48 ${y} L 705 ${y}`,'color/border/default');txt(c,String(i),12,y-8,25);}
  const start=mode==='6h'?6:0,vals=FIXTURE.activeUsers.slice(start),hours=FIXTURE.hoursUTC.slice(start);const dx=657/(vals.length-1);
  const points=vals.map((v,i)=>[48+i*dx,184-v*80]);const line=points.map((p,i)=>(i?'L':'M')+' '+p.join(' ')).join(' ');path(c,'Activity · unique users per hour',line,'color/accent/default',3);
  for(let i=0;i<points.length;i++){const [x,y]=points[i];const e=tr(figma.createEllipse());c.appendChild(e);e.name='Hour '+hours[i]+' · '+vals[i]+' users';e.resize(7,7);e.x=x-3.5;e.y=y-3.5;e.fills=[paint('color/accent/default')];if(i===0||i===points.length-1||i%2===0)txt(c,String(hours[i]).padStart(2,'0')+':00',x-20,201,40);}
  if(mode==='Stale')c.opacity=1;
 }else{const text=txt(c,mode==='Empty'?'Нет источника / No source':mode==='Loading'?'Загрузка / Loading':'Не удалось загрузить / Could not load',32,88,660,'Body/Small');text.name='State explanation';const p=c.addComponentProperty('Message','TEXT',text.characters);text.componentPropertyReferences={characters:p};}
 c.description='Native editable activity chart. Integer count axis starts at zero, 12 Oct 2026 UTC, 1-hour buckets. 6h selects 07–12; 12h selects 01–12. Unique users cannot be summed across buckets. Stale is a past snapshot, not current data. Empty/error/loading never display fabricated zero. Tabular alternative belongs to the consuming screen.';
}
const set=tr(figma.combineAsVariants(Object.values(out).map(id=>host.children.find(n=>n.id===id)),host));set.name='Admin/Activity chart';set.x=24;set.y=11640;set.resize(1540,810);for(let i=0;i<set.children.length;i++){set.children[i].x=24+(i%2)*765;set.children[i].y=24+Math.floor(i/2)*260;}
set.description='Overview activity chart; 6 variants: 12h, 6h, Stale, Empty, Loading, Error. Uses existing Shadow tokens and text styles. Geometry has fixed coordinates; axes and data remain editable.';
host.resize(3040,12500);mutated.push(host.id);
const examples=await figma.getNodeByIdAsync('2097:5419');examples.resize(1220,12520);mutated.push(examples.id);
const showcase=tr(figma.createAutoLayout('VERTICAL'));examples.appendChild(showcase);showcase.name='Admin / Analytics / Activity chart states';showcase.x=24;showcase.y=10850;showcase.resize(1172,100);showcase.primaryAxisSizingMode='AUTO';showcase.counterAxisSizingMode='FIXED';showcase.itemSpacing=16;showcase.fills=[paint('color/bg/canvas')];
for(const mode of modes){const row=tr(figma.createAutoLayout('HORIZONTAL'));showcase.appendChild(row);row.resize(1144,224);row.primaryAxisSizingMode='FIXED';row.counterAxisSizingMode='AUTO';row.itemSpacing=24;row.fills=[];const i=tr((await figma.getNodeByIdAsync(out[mode])).createInstance());row.appendChild(i);if(['Empty','Loading','Error'].includes(mode)){const key=Object.keys(i.componentProperties).find(k=>k.split('#')[0]==='Message');i.setProperties({[key]:mode==='Empty'?'Нет источника данных / No data source':mode==='Loading'?'Загрузка данных… / Loading data…':'Не удалось загрузить данные / Could not load data'});}const label=txt(row,mode,0,0,260,'Label');}
return {createdNodeIds:created,mutatedNodeIds:mutated,set:set.id,variants:out,showcase:showcase.id,chartWidth:725.333333};
