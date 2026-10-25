// Inject JOB [{key,id,kind,index}]. Clone bounded roots; existing desktop roots are preserved.
const p=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(p);figma.skipInvisibleInstanceChildren=false;
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const sc=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:3986:27');
const lc=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:3986:28');
const all=await figma.variables.getLocalVariablesAsync();
let menu=all.find(v=>v.name==='mobile/menuOpen');if(!menu){menu=figma.variables.createVariable('mobile/menuOpen',sc,'BOOLEAN');menu.setValueForMode('3986:0',false);menu.hiddenFromPublishing=true;}
let label=all.find(v=>v.name==='mobile/menuLabel');if(!label){label=figma.variables.createVariable('mobile/menuLabel',lc,'STRING');label.setValueForMode('3986:1','Меню');label.setValueForMode('3986:2','Menu');label.hiddenFromPublishing=true;}
const result=[];
function adapt(n,w){
 if(n.type==='TEXT'){n.textAutoResize='HEIGHT';n.resize(Math.max(40,w),n.height);return;}
 if(n.type==='INSTANCE'){n.resize(Math.min(n.width,w),Math.max(n.height,44));return;}
 if(n.type!=='FRAME')return;
 if(n.name==='Daily bars'){n.layoutMode='VERTICAL';n.resize(w,n.height);n.primaryAxisSizingMode='AUTO';n.counterAxisSizingMode='FIXED';n.itemSpacing=8;for(const day of n.children){day.layoutMode='HORIZONTAL';day.resize(w,44);day.primaryAxisSizingMode='FIXED';day.counterAxisSizingMode='FIXED';day.counterAxisAlignItems='CENTER';day.itemSpacing=8;const count=day.children.find(c=>c.type==='TEXT');const bar=day.children.find(c=>c.type==='FRAME');const btn=day.children.find(c=>c.type==='INSTANCE');day.insertChild(0,btn);btn.resize(84,44);count.resize(20,20);count.textAutoResize='HEIGHT';bar.resize(Math.max(6,(w-128)*Number(count.characters)/5),12);bar.primaryAxisSizingMode='FIXED';}return;}

 // Wide comparison/list data keeps its column headings and independent horizontal scrolling.
 if(/table|comparison/i.test(n.name)&&!/tools/i.test(n.name)&&n.width>w&&n.children.length){const original=n.width;const parent=n.parent;const index=parent.children.indexOf(n);const wrap=figma.createAutoLayout('VERTICAL');wrap.name='Mobile horizontal scroll / '+n.name;wrap.resize(w,n.height);wrap.primaryAxisSizingMode='AUTO';wrap.counterAxisSizingMode='FIXED';wrap.fills=[];wrap.clipsContent=true;wrap.overflowDirection='HORIZONTAL';parent.insertChild(index,wrap);wrap.appendChild(n);n.resize(original,n.height);return;}
 if(n.name==='Breadcrumbs'){n.resize(w,n.height);n.layoutWrap='WRAP';return;}
 if(n.layoutMode==='HORIZONTAL')n.layoutMode='VERTICAL';
 n.resize(w,n.height);if(n.layoutMode!=='NONE'){n.counterAxisSizingMode='FIXED';n.primaryAxisSizingMode='AUTO';n.itemSpacing=Math.min(n.itemSpacing,24);}
 n.paddingLeft=Math.min(n.paddingLeft,16);n.paddingRight=Math.min(n.paddingRight,16);
 const inner=Math.max(40,w-n.paddingLeft-n.paddingRight);
 for(const c of [...n.children])adapt(c,inner);
}
for(const j of JOB){
 const old=await figma.getNodeByIdAsync(j.id);const existing=p.children.find(n=>n.name==='MOBILE / '+j.key);if(existing){result.push({key:j.key,desktop:j.id,id:existing.id,reused:true});continue;}
 const fonts=new Map();for(const t of old.findAllWithCriteria({types:['TEXT']}))for(const seg of t.getStyledTextSegments(['fontName']))if(seg.fontName.family!=='Inter')fonts.set(JSON.stringify(seg.fontName),seg.fontName);await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
 const n=old.clone();n.name='MOBILE / '+j.key;n.x=24000+(j.index%5)*470;n.y=30000+Math.floor(j.index/5)*2000;
 n.layoutMode='VERTICAL';n.itemSpacing=20;n.paddingLeft=n.paddingRight=16;n.paddingTop=n.paddingBottom=16;
 const navigation=n.children.find(c=>c.name==='Persistent navigation');
 if(navigation){navigation.setBoundVariable('visible',menu);navigation.resize(358,navigation.height);navigation.primaryAxisSizingMode='AUTO';navigation.paddingLeft=navigation.paddingRight=0;navigation.name='Mobile menu content';
 const header=figma.createAutoLayout('HORIZONTAL');header.name='Mobile navigation header';header.resize(358,44);header.counterAxisSizingMode='FIXED';header.primaryAxisSizingMode='FIXED';header.itemSpacing=130;header.fills=[];n.insertChild(0,header);
 const brand=figma.createText();brand.fontName={family:'Inter',style:'Bold'};brand.fontSize=20;brand.characters='shadow';brand.fills=old.findAllWithCriteria({types:['TEXT']})[0].fills;header.appendChild(brand);
 const btn=(await figma.getNodeByIdAsync('2077:22087')).createInstance();header.appendChild(btn);btn.name='Mobile menu toggle';btn.resize(130,44);btn.findAllWithCriteria({types:['TEXT']})[0].setBoundVariable('characters',label);await btn.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'SET_VARIABLE',variableId:menu.id,variableValue:{type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'NOT',expressionArguments:[{type:'VARIABLE_ALIAS',resolvedType:'BOOLEAN',value:{type:'VARIABLE_ALIAS',id:menu.id}}]}}}]}]);
 }
 for(const c of [...n.children])if(c.name!=='Mobile navigation header')adapt(c,358);
 n.resize(390,j.kind==='overlay'?Math.min(Math.max(n.height,200),760):844);n.primaryAxisSizingMode='FIXED';n.counterAxisSizingMode='FIXED';n.clipsContent=true;n.overflowDirection='VERTICAL';
 result.push({key:j.key,desktop:j.id,id:n.id,width:n.width,height:n.height,kind:j.kind});
}
return {roots:result,menu:menu.id};
