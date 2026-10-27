// Inject DATA. Bring only bounded client states onto the admin page for native stateful navigation.
const source=figma.root.children.find(p=>p.id===DATA.page);await figma.setCurrentPageAsync(source);
const admin=figma.root.children.find(p=>p.id==='1981:29');
const sourceNodes=new Map(source.query(DATA.records.map(r=>'#'+r.id).join(',')).map(n=>[n.id,n]));
const fonts=new Map();for(const n of sourceNodes.values())for(const t of n.query('TEXT'))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const specs=[...DATA.records.map(r=>({key:r.key,id:r.id})),...['home','help','notifications','profile'].map(key=>({key,id:DATA.records.find(r=>r.key==='client-order-unknown').id}))];
const roots={},made=[],changed=[],baseY=Math.max(...admin.children.map(n=>n.y+n.height))+200;
for(const [i,item]of specs.entries()){
 const name='JOINT CLIENT / '+(DATA.mobile?'mobile':'desktop')+' / '+item.key;
 let n=admin.children.find(n=>n.name===name);
 if(!n){
  n=sourceNodes.get(item.id).clone();
  for(const b of n.query('INSTANCE').filter(b=>b.name.startsWith('Linked client / ')))b.remove();
  for(const x of [n,...n.query('FRAME,INSTANCE')])if(x.reactions?.length)await x.setReactionsAsync([]);
  admin.appendChild(n);n.name=name;n.x=(DATA.mobile?7600:100)+(i%4)*(DATA.mobile?470:1600);n.y=baseY+Math.floor(i/4)*1600;n.visible=true;n.setBoundVariable('visible',null);
  made.push(n.id,...n.query('*').map(c=>c.id));
 }else changed.push(n.id);
 roots[item.key]=n.id;
}
return {createdNodeIds:[...new Set(made)],mutatedNodeIds:changed,roots,mobile:DATA.mobile};
