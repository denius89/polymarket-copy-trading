
const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);const created=[],mutated=[],removed=[],headers=[],issues=[];
for(const s of await figma.getLocalTextStylesAsync())await figma.loadFontAsync(s.fontName);
const master=await figma.getNodeByIdAsync('2153:72804');
const roots=p.children.filter(n=>n.type==='FRAME'&&n.name.startsWith(LANG.toUpperCase()+' · ')&&n.width===1440&&!NEWIDS.includes(n.id));
for(const root of roots.slice(START,END)){
 const main=root.children.find(n=>n.type==='FRAME'&&n.width>=1190);if(!main){issues.push(root.id);continue;}
 const ctx=main.children.find(n=>n.type==='FRAME'&&/context|locale/i.test(n.name));if(!ctx){issues.push(root.id);continue;}
 const locales=ctx.children.filter(n=>n.type==='INSTANCE'&&Object.values(n.componentProperties).some(v=>v.type==='TEXT'&&/^(RU|EN)$/.test(v.value)));
 for(const n of locales){removed.push(n.id);n.remove();}
 if(/admin-login|admin-mfa|admin-session-|owners-unavailable/.test(root.name)){headers.push({rootId:root.id,auth:true});continue;}
 const n=master.createInstance();ctx.appendChild(n);created.push(n.id);n.name='My account · open profile';n.resize(44,44);
 ctx.resize(main.width-48,Math.max(ctx.height,44));ctx.primaryAxisSizingMode='FIXED';ctx.counterAxisAlignItems='CENTER';mutated.push(ctx.id);
 const label=ctx.children.find(n=>n.type==='TEXT');if(label){label.resize(ctx.width-60,label.height);label.textAutoResize='HEIGHT';label.layoutSizingHorizontal='FILL';mutated.push(label.id);}
 await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:PROFILE,navigation:'NAVIGATE',transition:null}]}]);
 headers.push({rootId:root.id,buttonId:n.id,contextId:ctx.id});
}
return {createdNodeIds:created,mutatedNodeIds:mutated,removedNodeIds:removed,headers,issues,totalOldRoots:roots.length};
