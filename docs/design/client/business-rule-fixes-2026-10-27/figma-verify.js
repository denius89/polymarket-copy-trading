// Inject CONFIG (key,page,en,mobile), MAP and STATES. Read-only.
const p=await figma.getNodeByIdAsync(CONFIG.page);await figma.setCurrentPageAsync(p);
const roots=MAP.roots,results=[],errors=[];
const flatten=actions=>actions.flatMap(a=>a.type==="CONDITIONAL"?a.conditionalBlocks.flatMap(b=>flatten(b.actions)):[a]);
for(const s of STATES){
 const n=await figma.getNodeByIdAsync(roots[s.key]);if(!n){errors.push("Missing "+s.key);continue;}
 const texts=n.query("TEXT").toArray().filter(t=>{let x=t;while(x&&x!==n){if(!x.visible)return false;x=x.parent;}return true;});
 const body=texts.map(t=>t.characters).join("\n").replace(/\u00a0/g," ");
 if(!body.includes(s.alert[CONFIG.en?1:0]))errors.push("Alert mismatch "+s.key);
 if(!body.includes(s.body[CONFIG.en?1:0]))errors.push("Body mismatch "+s.key);
 if(texts.some(t=>t.width<=0||t.height<=0))errors.push("Zero-size text "+s.key);
 const buttons=n.query("INSTANCE").toArray().filter(b=>b.name.startsWith("BI action / "));
 const controls=[];
 for(const b of buttons){const actions=flatten(b.reactions.flatMap(r=>r.actions||[]));if(!actions.length)errors.push("Dead action "+s.key+" "+b.name);const target=actions.filter(a=>a.type==="NODE").map(a=>a.destinationId);if(["period-end","manual","unknown","dust"].includes(s.key)&&target.some(t=>t===roots.reset||t===roots["reset-done"]))errors.push("Unsafe direct reset "+s.key);controls.push({id:b.id,name:b.name,targets:target});}
 const header=n.children.find(c=>c.type==="INSTANCE");if(!header?.visible||header.removed)errors.push("Hidden/removed header "+s.key);const areas=header.query("FRAME,INSTANCE").toArray();for(const pattern of ["help","notification|bell","profile|avatar"]){const hit=areas.find(x=>new RegExp(pattern,"i").test(x.name)&&x.width>=40&&x.height>=40);if(!hit?.reactions.length)errors.push("Header hit area "+s.key+" "+pattern);}
 const field=n.query("INSTANCE").find(x=>x.name==="BI budget input");if(field){const value=field.query("TEXT").find(t=>t.name.toLowerCase()==="value");const expected=CONFIG.en?"$"+(s.key==="budget"?"300":"100"):(s.key==="budget"?"300":"100")+" $";if(value.characters.replace(/\u00a0/g," ")!==expected)errors.push("Field value "+s.key);for(const box of field.children.filter(c=>c.type==="FRAME"))if(box.width>field.width+0.1)errors.push("Field overflow "+s.key);if(CONFIG.en&&field.query("TEXT").toArray().some(t=>/[А-Яа-яЁё]/.test(t.characters)))errors.push("Untranslated field "+s.key);}
 if(s.key==="period-end"){const review=buttons.find(b=>b.name==="BI action / operations");const ops=review?flatten(review.reactions.flatMap(r=>r.actions||[])):[];if(!ops.some(a=>a.type==="NODE"&&a.destinationId===MAP.utility&&a.navigation==="OVERLAY"))errors.push("Operations view changes period mode");}
 if(!CONFIG.mobile){const bar=n.children.find(x=>x.name==="App shell / Sidebar");if(!bar?.visible)errors.push("Hidden sidebar "+s.key);}
 if(n.overflowDirection!=="NONE")errors.push("Root scroll "+s.key);
 results.push({key:s.key,id:n.id,texts:texts.length,controls});
}
const lang=await figma.getNodeByIdAsync(MAP.languageButton);const links=flatten(lang.reactions.flatMap(r=>r.actions||[])).filter(a=>a.type==="URL");
if(links.length!==14)errors.push("Locale destinations "+links.length);
return {page:p.id,rootCount:results.length,localeDestinations:links.length,errors,states:results};
