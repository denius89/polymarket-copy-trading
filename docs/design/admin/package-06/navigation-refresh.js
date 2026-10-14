
const p=await figma.getNodeByIdAsync(PAGE);await figma.setCurrentPageAsync(p);for(const s of await figma.getLocalTextStylesAsync())await figma.loadFontAsync(s.fontName);const created=[],mutated=[],issues=[];
const roots=p.children.filter(n=>n.type==='FRAME'&&n.width===1440&&!NEWIDS.includes(n.id));
for(const root of roots){const side=root.children.find(n=>n.width===248&&(n.type==='FRAME'||n.type==='INSTANCE'));if(!side)continue;
let support=side.children.find(n=>n.type==='INSTANCE'&&(n.id.split(';').pop()===SUPPORT_NAV||Object.entries(n.componentProperties).some(([k,v])=>k.split('#')[0]==='Label'&&['Support','Поддержка'].includes(v.value))));
if(!support){if(side.type!=='FRAME'){issues.push({id:side.id,issue:'missing linked support'});continue;}support=(await figma.getNodeByIdAsync('2032:67')).createInstance();let at=side.children.findIndex(n=>n.type==='INSTANCE'&&Object.values(n.componentProperties).some(v=>v.type==='TEXT'&&['Защита выплат','Payout safeguards'].includes(v.value)));if(at<0)at=side.children.length;side.insertChild(at,support);created.push(support.id);mutated.push(side.id);support.resize(208,44);}
support.name='Admin · support';support.setProperties({'Label#2033:0':LANG==='ru'?'Поддержка':'Support',State:'Default'});await support.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:TARGET,navigation:'NAVIGATE',transition:null}]}]);mutated.push(support.id);}
return {createdNodeIds:created,mutatedNodeIds:mutated,issues,rootCount:roots.length};
