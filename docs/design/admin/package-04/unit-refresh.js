
const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);const ss=await figma.getLocalTextStylesAsync();for(const s of ss)await figma.loadFontAsync(s.fontName);const mutated=[],i=LANG==='ru'?0:1;
function props(n,obj){const ps={};for(const[k,v]of Object.entries(obj)){const key=Object.keys(n.componentProperties).find(p=>p.split('#')[0]===k);if(key)ps[key]=v;}n.setProperties(ps);mutated.push(n.id);}
for(const d of DATA){const r=await figma.getNodeByIdAsync(TARGETS[d.key]),heading=r.findOne(n=>n.name==='Page heading');if(heading){const ts=heading.children.filter(n=>n.type==='TEXT');ts[1].characters=d.subtitle[i];mutated.push(ts[1].id);}
const form=r.findOne(n=>n.name==='Form · static design values');if(form){const fields=form.findAll(n=>n.type==='INSTANCE'&&n.componentProperties?.['Label#2019:0']);for(let j=0;j<fields.length;j++)props(fields[j],{Label:d.fields[j][0][i],Value:d.fields[j][1][i]});}
const table=r.findOne(n=>n.name==='Data / metadata table');if(table)for(let j=0;j<table.children.length;j++){const parts=d.rows[j][i].split(' | ');props(table.children[j],{Title:parts[0],Detail:parts.length>2?parts.slice(1,-1).join(' · '):parts[1]??'',Meta:parts.length>2?parts.at(-1):''});}
}
return {mutatedNodeIds:mutated};
