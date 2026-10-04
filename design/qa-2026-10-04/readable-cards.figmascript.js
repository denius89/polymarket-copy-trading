await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));
figma.skipInvisibleInstanceChildren=false;
const ru=PAGE_ID==="33:2"||PAGE_ID==="205:2";
function active(n){for(let p=n;p&&p.type!=="PAGE";p=p.parent)if(p.visible===false)return false;return true;}
const changed=[],created=[],maps=[];
const vars=await figma.variables.getLocalVariablesAsync();
const small=await figma.getNodeByIdAsync("1216:49"),large=await figma.getNodeByIdAsync("1216:48");
const fontNodes=[...small.findAllWithCriteria({types:["TEXT"]}),...large.findAllWithCriteria({types:["TEXT"]})];
for(const t of fontNodes)for(const s of t.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
const format=s=>typeof s==="string"?(s.includes(":")?s.slice(s.indexOf(":")+1).trim():s):s;
const candidates=figma.currentPage.findAllWithCriteria({types:["FRAME"]}).filter(n=>active(n)&&n.layoutMode==="VERTICAL"&&n.children.filter(c=>c.type==="TEXT"&&c.visible&&c.characters.length<150&&/:/.test(c.characters)&&/\d/.test(c.characters)).length>=3&&!n.children.some(c=>c.name==="Readable metric grid"));
for(const card of candidates){
 const lines=card.children.filter(c=>c.type==="TEXT"&&c.visible&&c.characters.length<150&&/:/.test(c.characters)&&/\d/.test(c.characters));
 if(lines.some(t=>/Object body|Context|Message|Parameter/.test(t.name)))continue;
 const grid=figma.createAutoLayout("VERTICAL",{name:"Readable metric grid",itemSpacing:16,fills:[]});
 card.insertChild(card.children.indexOf(lines[0]),grid);grid.layoutSizingHorizontal="FILL";created.push(grid.id);changed.push(card.id);
 const cols=card.width<500?2:3;let row;
 for(let i=0;i<lines.length;i++){
  const source=lines[i];for(const s of source.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
  if(i%cols===0){row=figma.createAutoLayout("HORIZONTAL",{name:"Readable metrics row",itemSpacing:12,fills:[]});grid.appendChild(row);row.layoutSizingHorizontal="FILL";created.push(row.id);}
  const label=source.characters.slice(0,source.characters.indexOf(":")).trim();
  const m=(source.name==="Budget"?large:small).createInstance();row.appendChild(m);m.layoutSizingHorizontal="FILL";created.push(m.id);
  let value=format(source.characters);
  const alias=source.boundVariables.characters;
  if(alias){
   const v=await figma.variables.getVariableByIdAsync(alias.id);
   const name="ReadableCards/Value/"+v.id.replace("VariableID:","");
   let derived=vars.find(a=>a.name===name&&a.variableCollectionId===v.variableCollectionId);
   if(!derived){derived=figma.variables.createVariable(name,v.variableCollectionId,"STRING");derived.scopes=["TEXT_CONTENT"];derived.setVariableCodeSyntax("WEB","var(--card-value-"+v.id.replace(/[^0-9]/g,"-")+")");vars.push(derived);}
   for(const [mode,val]of Object.entries(v.valuesByMode))derived.setValueForMode(mode,typeof val==="string"?format(val):val);
   value={type:"VARIABLE_ALIAS",id:derived.id};maps.push({source:v.id,derived:derived.id});
  }
  m.setProperties({"Label#1216:0":label,"Value#1216:3":value});
  source.visible=false;changed.push(source.id);
 }
 card.itemSpacing=16;card.paddingTop=16;card.paddingBottom=16;card.paddingLeft=16;card.paddingRight=16;
 const title=card.children.find(c=>c.type==="TEXT"&&c.visible&&/Selected trader|Card title/.test(c.name));
 if(title){for(const s of title.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);await title.setTextStyleIdAsync("S:91e4e6f77407c842a145f672d90065d16fbfcf28,");changed.push(title.id);}
 const preset=card.children.find(c=>c.type==="TEXT"&&c.visible&&/Selected preset|Global value/.test(c.name)&&!c.characters.includes(":"));
 if(preset){
  for(const s of preset.getStyledTextSegments(["fontName"]))await figma.loadFontAsync(s.fontName);
  const wrap=figma.createAutoLayout("HORIZONTAL",{name:"Risk level",itemSpacing:8,fills:[]});card.insertChild(card.children.indexOf(preset),wrap);wrap.layoutSizingHorizontal="FILL";
  const label=preset.clone();label.setBoundVariable("characters",null);label.characters=ru?"Уровень риска":"Risk level";await label.setTextStyleIdAsync("S:3383453afee1e6a118c6d49295501d664091bd8a,");wrap.appendChild(label);label.textAutoResize="WIDTH_AND_HEIGHT";label.layoutSizingHorizontal="HUG";
  wrap.appendChild(preset);preset.textAutoResize="WIDTH_AND_HEIGHT";preset.layoutSizingHorizontal="HUG";created.push(wrap.id,label.id);changed.push(preset.id);
 }
}
return {created,changed,maps,cards:candidates.filter(c=>c.children.some(n=>n.name==="Readable metric grid")).map(c=>({id:c.id,name:c.name,w:c.width,h:c.height,grid:c.children.find(n=>n.name==="Readable metric grid").id}))};
