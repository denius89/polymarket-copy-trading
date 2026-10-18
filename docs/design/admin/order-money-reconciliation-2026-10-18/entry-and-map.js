// Inputs PAGE and LOCALE. Uses existing components; no new roots or variants.
await figma.setCurrentPageAsync(await figma.getNodeByIdAsync(PAGE));
const ru=LOCALE==='RU',changed=[],created=[];
const payout=await figma.getNodeByIdAsync(ru?'2003:520':'2007:520');
const profile=await figma.getNodeByIdAsync(ru?'2210:21620':'2210:82672');
const actions=await figma.getNodeByIdAsync(ru?'2003:568':'2007:543');
const sessionCard=profile.findAllWithCriteria({types:['FRAME']}).find(n=>n.name==='Linked user session');
const template=await figma.getNodeByIdAsync('113:209');
const fonts=new Map();for(const n of [template,sessionCard,actions])for(const t of n.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
const edits=ru?{
 '2105:5768':'601 RU +601 EN · 596 основных состояний на язык · карта 0.20 · UI kit 0.4.21',
 '2105:5790':'Макеты есть · 36 RU / 36 EN',
 '2105:5791':'Сессии, частичное исполнение, отмена остатка и поздние исполнения. Дизайн на вычитке.',
 '2105:5793':'Открыть: Исполнение и отмена остатка',
 '2105:5801':'Макеты есть · 29 RU / 29 EN',
 '2105:5802':'Типы денежных операций, исходная идентичность, подтверждение, ошибка и недостаток данных.',
 '2105:5804':'Открыть: Денежная сверка',
 '2210:22352':'Paper Alpha: комиссия 0%. 1% — только неактивный пример будущей платной версии.'
}:{'2210:83246':'Paper Alpha service fee: 0%. 1% is only an inactive example of a future paid version.'};
const textNodes=await Promise.all(Object.keys(edits).map(id=>figma.getNodeByIdAsync(id)));
for(const t of textNodes)for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
for(const t of textNodes){t.characters=edits[t.id];t.textAutoResize='HEIGHT';changed.push(t.id);}
function add(parent,label,target,name){if(parent.children.some(n=>n.name===name))return;const b=template.createInstance();parent.appendChild(b);b.name=name;const p=b.componentProperties,k=Object.keys(p).find(k=>k.split('#')[0]==='Label'),icon=Object.keys(p).find(k=>k.split('#')[0]==='Show icon');b.setProperties({[k]:label,[icon]:false});b.primaryAxisSizingMode='AUTO';b.layoutSizingHorizontal='HUG';b.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:target,navigation:'NAVIGATE',transition:null,preserveScrollPosition:false}]}];created.push(b.id);}
actions.layoutWrap='WRAP';actions.counterAxisSpacing=12;actions.layoutSizingVertical='HUG';add(actions,ru?'Денежная сверка':'Money reconciliation',ru?'3014:58394':'3016:58381','Open · typed money reconciliation');
add(sessionCard,ru?'Пример: исполнение и отмена':'Example: fills and cancellation',ru?'3014:58072':'3016:58059','Open · isolated ORD-DEMO-03');
if(ru)for(const [id,dst]of [['2105:5793','3014:58072'],['2105:5804','3014:58394']]){const n=await figma.getNodeByIdAsync(id);n.reactions=[{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:dst,navigation:'NAVIGATE',transition:null,preserveScrollPosition:false}]}];changed.push(id);}
return {createdNodeIds:created,mutatedNodeIds:changed,entries:[{root:payout.id,to:ru?'3014:58394':'3016:58381'},{root:profile.id,to:ru?'3014:58072':'3016:58059'}],rootCounts:figma.currentPage.children.filter(n=>n.type==='FRAME').length};
