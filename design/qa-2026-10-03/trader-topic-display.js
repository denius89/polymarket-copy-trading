await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(CFG.page));
for(const s of ["Regular","Medium","Semi Bold","Bold"])await figma.loadFontAsync({family:"Inter",style:s});
const page=figma.currentPage, changed=[],created=[],vars=await figma.variables.getLocalVariablesAsync();
const tokens=Object.fromEntries(vars.map(v=>[v.name,v]));
function live(n){let a=n;while(a&&a.type!=="PAGE"){if(/Legacy preserved|Archive|Архив/.test(a.name))return false;a=a.parent;}return true;}
const texts=page.findAll(n=>n.type==="TEXT"&&n.name==="Theme"&&live(n));
const oldIds=new Set(texts.map(n=>n.boundVariables.characters?.id).filter(Boolean));
let collection=(await figma.variables.getLocalVariableCollectionsAsync()).find(c=>c.name===CFG.ns);
if(!collection){collection=figma.variables.createVariableCollection(CFG.ns);created.push(collection.id);}
const mode=collection.defaultModeId, state={};
function variable(key,value){const name=CFG.ns+"/"+key;let v=vars.find(v=>v.name===name);if(!v){v=figma.variables.createVariable(name,collection,"STRING");v.scopes=["TEXT_CONTENT"];v.setVariableCodeSyntax("WEB","var(--"+key.replaceAll("/","-")+")");created.push(v.id);}v.setValueForMode(mode,value);changed.push(v.id);return v;}
for(const p of ["24h","7d","30d","90d"]){const data=DATA.traders[0].periods[p];state[p]={topics:variable(p+"/topics",data[CFG.lang]),note:variable(p+"/note",data[CFG.lang==="ru"?"noteRu":"noteEn"])};}
const profileBlocks={};
for(const text of texts){
let a=text;while(a.parent&&a.parent.type!=="PAGE"&&a.parent.type!=="SECTION")a=a.parent;
const period=(CFG.periodRoots&&CFG.periodRoots[a.id])||(a.name.match(/trader-(24h|7d|30d|90d)/)||[])[1]||"30d";
const card=text.parent,title=card.children.find(n=>n.type==="TEXT"&&n.name==="Card title"),body=card.children.find(n=>n.type==="TEXT"&&n.name==="Card body");
if(title){title.characters=CFG.lang==="ru"?"Темы торговли":"Trading topics";changed.push(title.id);}
if(body){body.characters=CFG.lang==="ru"?"Темы рынков с исполненными сделками за выбранный период. Синтетические данные.":"Topics of markets traded in the selected period. Synthetic data.";body.textAutoResize="HEIGHT";changed.push(body.id);}
text.setBoundVariable("characters",state[period].topics);text.textAutoResize="HEIGHT";text.resize(card.width-(card.paddingLeft||0)-(card.paddingRight||0),text.height);changed.push(text.id);
let note=card.children.find(n=>n.name==="Topic period and coverage");if(!note){note=figma.createText();note.name="Topic period and coverage";note.fontName={family:"Inter",style:"Regular"};card.appendChild(note);created.push(note.id);}
note.fontSize=12;note.lineHeight={unit:"PIXELS",value:18};note.fills=[figma.variables.setBoundVariableForPaint({type:"SOLID",color:{r:163/255,g:173/255,b:194/255}},"color",tokens["color/text/secondary"])];
note.characters="";note.setBoundVariable("characters",state[period].note);note.textAutoResize="HEIGHT";note.resize(text.width,18);changed.push(note.id);
card.itemSpacing=12;card.primaryAxisSizingMode="AUTO";changed.push(card.id);
if((()=>{let n=text;while(n&&n.type!=="PAGE"){if(!n.visible)return false;n=n.parent;}return true;})())profileBlocks[a.id]=card.id;
}
const cards=page.findAll(n=>n.type==="INSTANCE"&&/Trader\/trader-/.test(n.name)&&live(n));
const summaries=[];
for(const card of cards){
const id=(card.name.match(/trader-\d+/)||[])[0],trader=DATA.traders.find(t=>t.id===id);if(!trader)continue;
const p=trader.periods["30d"],labels=DATA.labels[CFG.lang],parts=p.topics;
const properties=card.componentProperties;function prop(name){return Object.keys(properties).find(k=>k.split("#")[0]===name);}
const first=parts.length?labels[parts[0]]:p[CFG.lang],second=parts[1]?labels[parts[1]]:"",more=parts.length>2?"+"+(parts.length-2):"";
card.setProperties({[prop("Topics")]:first,[prop("TopicSecond")]:second,[prop("TopicMore")]:more,[prop("ShowTopicSecond")]:!!second,[prop("ShowTopicMore")]:!!more});card.resize(card.width,230);changed.push(card.id);
const updates=[];for(const period of ["24h","7d","30d","90d"]){const d=trader.periods[period];updates.push({type:"SET_VARIABLE",variableId:state[period].topics.id,variableValue:{type:"STRING",resolvedType:"STRING",value:d[CFG.lang]}},{type:"SET_VARIABLE",variableId:state[period].note.id,variableValue:{type:"STRING",resolvedType:"STRING",value:d[CFG.lang==="ru"?"noteRu":"noteEn"]}});}
const reactions=card.reactions.map(r=>{const acts=(r.actions||[r.action]).filter(Boolean).filter(x=>!(x.type==="SET_VARIABLE"&&Object.values(state).some(s=>[s.topics.id,s.note.id].includes(x.variableId))));const navIndex=acts.findIndex(a=>a.type==="NODE");acts.splice(navIndex<0?acts.length:navIndex,0,...updates);return {...r,actions:acts};});
await card.setReactionsAsync(reactions);
const moreNode=card.findOne(n=>n.name==="Topic more / open profile");
if(moreNode&&more){const rs=reactions.map(r=>{const acts=[...r.actions],nav=acts.find(a=>a.type==="NODE"&&a.navigation==="NAVIGATE");const target=nav&&profileBlocks[nav.destinationId];if(target)acts.push({type:"NODE",destinationId:target,navigation:"SCROLL_TO",transition:null,resetScrollPosition:false});return {...r,actions:acts};});await moreNode.setReactionsAsync(rs);changed.push(moreNode.id);}
summaries.push({id:card.id,trader:id,first,second,more});
}
const first=cards.find(n=>/trader-01$/.test(n.name));if(first)await first.screenshot({scale:1});
return {page:CFG.page,createdNodeIds:created,mutatedNodeIds:changed,cards:summaries.length,profiles:Object.keys(profileBlocks).length,profileBlocks,state:Object.fromEntries(Object.entries(state).map(([k,v])=>[k,{topics:v.topics.id,note:v.note.id}])),samples:summaries.slice(0,4)};
