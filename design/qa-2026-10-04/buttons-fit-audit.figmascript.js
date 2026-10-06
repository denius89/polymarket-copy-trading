await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE_ID));figma.skipInvisibleInstanceChildren=false;HELPER
function lum(c){return [.2126,.7152,.0722].reduce((s,w,i)=>{const x=[c.r,c.g,c.b][i];return s+w*(x<=.04045?x/12.92:((x+.055)/1.055)**2.4);},0);}
function rgb(n){const p=n.fills?.find(p=>p.type==="SOLID");if(!p)return null;const v=byId.get(p.boundVariables?.color?.id);return v?v.resolveForConsumer(n).value:p.color;}
const nodes=figma.currentPage.findAllWithCriteria({types:["FRAME","INSTANCE"]}).filter(n=>active(n)&&isButton(n));const contrast=[],smallIcons=[],placement=[];
for(const n of nodes){const bg=rgb(n);if(!bg||role(n)==="disabled")continue;for(const t of n.findAllWithCriteria({types:["TEXT"]}).filter(t=>active(t)&&t.characters)){const fg=rgb(t);if(!fg)continue;const a=lum(bg),b=lum(fg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);if(ratio<4.5)contrast.push({button:n.id,label:t.characters,role:role(n),ratio:Math.round(ratio*100)/100});}
const p=n.parent;if(p.type==="FRAME"&&p.layoutMode==="HORIZONTAL"&&n.height>p.height+1)placement.push({id:n.id,parent:p.id,height:n.height,parentHeight:p.height});
}
for(const n of figma.currentPage.findAllWithCriteria({types:["FRAME","INSTANCE"]}).filter(active)){if(!n.reactions?.length||!/(Button|Icon|Close|Header)/i.test(n.name)||n.findAllWithCriteria({types:["TEXT"]}).some(t=>active(t)&&t.characters))continue;if(n.width<44||n.height<44)smallIcons.push({id:n.id,name:n.name,w:n.width,h:n.height});}
return {count:nodes.length,contrast,smallIcons,placement};