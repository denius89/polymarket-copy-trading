// Targeted adaptation of figma-generate-library createComponentWithVariants.
// Native editable components; existing shared tokens and Inter text styles.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:2'));
const created=[],mutated=[];
const vars=await figma.variables.getLocalVariablesAsync(),vm=new Map(vars.map(v=>[v.name,v]));
const collections=await figma.variables.getLocalVariableCollectionsAsync(),cm=new Map(collections.map(c=>[c.id,c]));
const vi=new Map(vars.map(v=>[v.id,v]));
function value(v){const c=cm.get(v.variableCollectionId),x=v.valuesByMode[c.modes.find(m=>m.name==='Dark')?.modeId||c.defaultModeId];return x?.type==='VARIABLE_ALIAS'?value(vi.get(x.id)):x;}
function fill(name){const v=vm.get(name),c=value(v);return figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:c.r,g:c.g,b:c.b}},'color',v);}
const styles=await figma.getLocalTextStylesAsync(),sm=new Map(styles.map(s=>[s.name,s]));
for(const name of ['Body/Small','Body/Small medium','Label','Caption','Heading/Small'])await figma.loadFontAsync(sm.get(name).fontName);
const track=n=>(created.push(n.id),n);
const existing=figma.currentPage.query('COMPONENT_SET[name="Admin/User table row"]').first();
if(existing)return {existing:existing.id,createdNodeIds:[],mutatedNodeIds:[]};
const host=await figma.getNodeByIdAsync('2097:5418');
const KIT_Y=11040;host.resize(3040,11600);mutated.push(host.id);
const widths=[208,112,124,124,72,88,132,140];
const labels=['Пользователь','Площадки','Баланс, $','Доступно, $','Сессии','VIP','Статус','Активность · UTC'];
const sample=['Demo Atlas\nU-DEMO-001','Limitless','1 000,00','1 000,00','1','Не назначен','Активен','12 Oct 2026\n12:00'];
function component(name,content,state){const c=track(figma.createComponent());host.appendChild(c);c.name=name;c.layoutMode='HORIZONTAL';c.resize(1144,state==='Header'?48:80);c.primaryAxisSizingMode='FIXED';c.counterAxisSizingMode='FIXED';c.counterAxisAlignItems='CENTER';c.paddingLeft=c.paddingRight=16;c.paddingTop=c.paddingBottom=12;c.itemSpacing=16;c.setBoundVariable('itemSpacing',vm.get('spacing/4'));for(const k of ['paddingLeft','paddingRight'])c.setBoundVariable(k,vm.get('spacing/4'));c.fills=[fill(state==='Hover'?'color/bg/elevated':'color/bg/surface')];c.strokes=[fill(state==='Focus'?'color/focus/ring':'color/border/default')];c.strokeBottomWeight=1;c.strokeTopWeight=state==='Focus'?2:0;c.strokeLeftWeight=c.strokeRightWeight=state==='Focus'?2:0;if(state==='Disabled')c.opacity=0.45;
 for(let i=0;i<8;i++){const t=track(figma.createText());c.appendChild(t);t.name='Column '+(i+1);t.textStyleId=sm.get(state==='Header'?'Caption':i===0?'Label':'Body/Small').id;t.characters=content[i];t.textAutoResize='HEIGHT';t.resize(widths[i],t.height);t.fills=[fill(state==='Header'?'color/text/secondary':'color/text/primary')];if(i===2||i===3)t.textAlignHorizontal='RIGHT';const p=c.addComponentProperty('Column '+(i+1),'TEXT',content[i]);t.componentPropertyReferences={characters:p};}
 return c;}
const header=component('Admin/User table header',labels,'Header');header.x=24;header.y=KIT_Y;
header.description='Eight columns at 1144 px. Cash balance excludes positions; numbers align right. Match row widths. Headings do not imply sorting.';
const variants=['Default','Hover','Focus','Disabled'].map(s=>component('State='+s,sample,s));
const set=track(figma.combineAsVariants(variants,host));set.name='Admin/User table row';set.x=24;set.y=KIT_Y+80;set.resize(1192,424);for(let i=0;i<variants.length;i++){variants[i].x=24;variants[i].y=16+i*96;}
set.description='Customer identity and permitted cash snapshot. Whole row opens the same customer. Default/Hover/Focus/Disabled. Read-only synthetic money; no editing or payment commands. Missing differs from zero. Do not expose these columns without financial read permission.';
const examples=await figma.getNodeByIdAsync('2097:5419');examples.resize(1220,10820);mutated.push(examples.id);const view=track(figma.createAutoLayout('VERTICAL'));examples.appendChild(view);view.name='Admin / Users / Table patterns';view.x=24;view.y=10170;view.resize(1172,300);view.primaryAxisSizingMode='AUTO';view.counterAxisSizingMode='FIXED';view.paddingLeft=view.paddingRight=14;view.paddingTop=view.paddingBottom=16;view.itemSpacing=8;view.fills=[fill('color/bg/canvas')];for(const c of [header,...variants])view.appendChild(track(c.createInstance()));
return {showcase:view.id,createdNodeIds:created,mutatedNodeIds:mutated,header:header.id,set:set.id,defaultRow:variants[0].id,widths,totalWidth:widths.reduce((a,b)=>a+b,0)+7*16+32,states:variants.map(n=>({id:n.id,name:n.name})),host:host.id};
