const page = await figma.getNodeByIdAsync('29:2');
await figma.setCurrentPageAsync(page);
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const vars = Object.fromEntries((await figma.variables.getLocalVariablesAsync()).map(v=>[v.name,v]));
const paint=(name)=>figma.variables.setBoundVariableForPaint({type:'SOLID',color:{r:0,g:0,b:0}},'color',vars[name]);
const created=[];
const track=n=>(created.push(n.id),n);
const bind=(n,k,name)=>n.setBoundVariable(k,vars[name]);
const round=(n,name)=>['topLeftRadius','topRightRadius','bottomLeftRadius','bottomRightRadius'].forEach(k=>bind(n,k,name));
let library=page.children.find(n=>n.name==='Mobile controls · 2026-09-28');
if(library) return {existing:library.id};
library=track(figma.createFrame());page.appendChild(library);library.name='Mobile controls · 2026-09-28';library.x=0;library.y=1100;library.resize(1100,600);library.fills=[paint('color/bg/canvas')];
const defs={};
function label(comp,s,size=15){const t=track(figma.createText());t.name='Label';t.fontName={family:'Inter',style:'Semi Bold'};t.fontSize=size;t.lineHeight={unit:'PIXELS',value:20};t.characters=s;t.fills=[paint('color/text/primary')];comp.appendChild(t);return t;}
const buttons=[];
for(const [i,style] of ['Primary','Secondary','Quiet'].entries()){
const c=track(figma.createComponent());library.appendChild(c);c.name='Style='+style;c.resize(300,48);c.layoutMode='HORIZONTAL';c.primaryAxisSizingMode='FIXED';c.counterAxisSizingMode='FIXED';c.primaryAxisAlignItems='CENTER';c.counterAxisAlignItems='CENTER';for(const k of ['paddingLeft','paddingRight'])bind(c,k,'spacing/4');for(const k of ['paddingTop','paddingBottom','itemSpacing'])bind(c,k,'spacing/0');round(c,'radius/md');c.fills=style==='Quiet'?[]:[paint(style==='Primary'?'color/accent/default':'color/bg/surface')];c.strokes=style==='Secondary'?[paint('color/border/default')]:[];c.strokeWeight=1;label(c,'Button');buttons.push(c);defs[style]=c.id;
}
const bs=track(figma.combineAsVariants(buttons,library));bs.name='Mobile/Button';bs.x=24;bs.y=24;bs.resize(1020,96);buttons.forEach((c,i)=>{c.x=16+i*332;c.y=16;});const bp=bs.addComponentProperty('Label','TEXT','Button');buttons.forEach(c=>c.children[0].componentPropertyReferences={characters:bp});bs.description='48px mobile actions. Label supports EN/RU. Primary is reserved for the next main action.';
const badges=[];
for(const tone of ['Neutral','Success','Warning']){
const c=track(figma.createComponent());library.appendChild(c);c.name='Tone='+tone;c.layoutMode='HORIZONTAL';c.primaryAxisSizingMode='AUTO';c.counterAxisSizingMode='AUTO';c.primaryAxisAlignItems='CENTER';c.counterAxisAlignItems='CENTER';for(const k of ['paddingLeft','paddingRight'])bind(c,k,'spacing/3');for(const k of ['paddingTop','paddingBottom'])bind(c,k,'spacing/1');bind(c,'itemSpacing','spacing/0');round(c,'radius/pill');c.fills=[paint(tone==='Neutral'?'color/bg/elevated':tone==='Success'?'color/success/bg':'color/warning/bg')];const t=label(c,'Demo',12);t.fills=[paint(tone==='Neutral'?'color/text/secondary':tone==='Success'?'color/success/text':'color/warning/text')];badges.push(c);defs['Badge'+tone]=c.id;
}
const badgeSet=track(figma.combineAsVariants(badges,library));badgeSet.name='Mobile/Status';badgeSet.x=24;badgeSet.y=150;badgeSet.resize(600,80);badges.forEach((c,i)=>{c.x=16+i*180;c.y=16;});const prop=badgeSet.addComponentProperty('Label','TEXT','Demo');badges.forEach(c=>c.children[0].componentPropertyReferences={characters:prop});badgeSet.description='Compact content-hugging status. Status is information, not a button.';
const toggles=[];
for(const state of ['On','Off']){const c=track(figma.createComponent());library.appendChild(c);c.name='State='+state;c.resize(48,32);c.layoutMode='HORIZONTAL';c.primaryAxisSizingMode='FIXED';c.counterAxisSizingMode='FIXED';c.counterAxisAlignItems='CENTER';c.primaryAxisAlignItems=state==='On'?'MAX':'MIN';for(const k of ['paddingLeft','paddingRight','paddingTop','paddingBottom'])bind(c,k,'spacing/1');round(c,'radius/pill');c.fills=[paint(state==='On'?'color/accent/default':'color/bg/elevated')];const knob=track(figma.createEllipse());c.appendChild(knob);knob.name='Thumb';knob.resize(24,24);knob.fills=[paint('white/1000')];toggles.push(c);defs['Switch'+state]=c.id;}
const ts=track(figma.combineAsVariants(toggles,library));ts.name='Mobile/Switch';ts.x=24;ts.y=280;ts.resize(220,80);toggles.forEach((c,i)=>{c.x=16+i*96;c.y=16;});ts.description='32px switch track used inside a minimum 44px interactive row. Label remains outside track.';
return {createdNodeIds:created,libraryId:library.id,definitions:defs,properties:{button:bp,badge:prop}};
