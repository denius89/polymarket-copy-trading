// Recreate technical-mode button instances from the same main components to refresh locale rendering.
// Source is a scoped repair recipe, not an exact file backup. Preserve root IDs and actions.
const page=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(page);
figma.skipInvisibleInstanceChildren=false;
const TARGETS=['4305:2345','4305:2376','4311:2342','4311:2359','4143:489','4161:65477'];
const ROOTS=['4304:2295','4311:2321','4143:371','4161:65427'];
const roots=await Promise.all(ROOTS.map(id=>figma.getNodeByIdAsync(id)));
const jobs=[];const fonts=new Map();
for(const root of roots)for(const n of root.findAllWithCriteria({types:['INSTANCE']})){if(!TARGETS.includes(n.id))continue;let p=n.parent,nested=false;while(p&&p!==root){if(p.type==='INSTANCE')nested=true;p=p.parent;}if(nested)continue;const t=n.findAllWithCriteria({types:['TEXT']});if(t.length!==1||!t[0].boundVariables?.characters)continue;for(const s of t[0].getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);jobs.push({n,t:t[0]});}
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const replacements=[],createdNodeIds=[],removedNodeIds=[];
for(const {n,t} of jobs){const main=await n.getMainComponentAsync();if(!main)throw Error('Missing main component '+n.id);const parent=n.parent,index=parent.children.indexOf(n),b=main.createInstance();parent.insertChild(index,b);b.name=n.name;b.resize(n.width,n.height);
for(const key of ['fills','strokes','strokeWeight','cornerRadius','opacity','visible','clipsContent','layoutAlign','layoutGrow','layoutPositioning','paddingLeft','paddingRight','paddingTop','paddingBottom','itemSpacing','primaryAxisAlignItems','counterAxisAlignItems'])if(key in n&&key in b&&typeof n[key]!=='symbol')b[key]=JSON.parse(JSON.stringify(n[key]));
if(parent.layoutMode==='NONE'||n.layoutPositioning==='ABSOLUTE'){b.x=n.x;b.y=n.y;}
if(n.boundVariables?.visible)b.setBoundVariable('visible',await figma.variables.getVariableByIdAsync(n.boundVariables.visible.id));
const label=b.findAllWithCriteria({types:['TEXT']})[0];label.fontName=t.fontName;label.fontSize=t.fontSize;label.lineHeight=t.lineHeight;label.textAlignHorizontal=t.textAlignHorizontal;label.textAutoResize='HEIGHT';label.resize(Math.max(40,b.width-32),t.height);label.setBoundVariable('characters',await figma.variables.getVariableByIdAsync(t.boundVariables.characters.id));
if(b.layoutMode!=='NONE')label.layoutSizingHorizontal='FILL';
const rx=JSON.parse(JSON.stringify(n.reactions));for(const r of rx)delete r.action;await b.setReactionsAsync(rx);
if(parent.layoutMode&&parent.layoutMode!=='NONE'){b.layoutSizingHorizontal=n.layoutSizingHorizontal;b.layoutSizingVertical=n.layoutSizingVertical;}
for(const node of [b,label]){node.setExplicitVariableModeForCollection('VariableCollectionId:3986:28','3986:2');node.clearExplicitVariableModeForCollection('VariableCollectionId:3986:28');}
replacements.push({root:roots.find(r=>{let a=n;while(a){if(a===r)return true;a=a.parent;}return false;}).id,from:n.id,to:b.id,name:b.name});removedNodeIds.push(n.id);createdNodeIds.push(b.id,...b.findAll(()=>true).map(c=>c.id));n.remove();}
return {createdNodeIds,removedNodeIds,replacements,count:replacements.length};
