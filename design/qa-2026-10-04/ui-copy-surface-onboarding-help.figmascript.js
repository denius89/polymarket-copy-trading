// Scope: existing onboarding copy and RU desktop Help only; preserve instances/reactions.
const page = await figma.getNodeByIdAsync("205:2");
await figma.setCurrentPageAsync(page);
const hiddenIds = ["954:4998", "954:19143", "955:3831", "1040:23587", "1039:24497"];
const headingPairs = [["I1039:24470;819:315", "Как работает shadow"], ["I1040:23563;819:315", "How shadow works"]];
const texts = await Promise.all([...hiddenIds, ...headingPairs.map(x=>x[0])].map(id=>figma.getNodeByIdAsync(id)));
const button = await figma.getNodeByIdAsync("955:3833");
const action = await figma.getNodeByIdAsync("1039:24496");
const primary = await figma.getNodeByIdAsync("1039:24493");
const fonts = new Map();
for (const t of [...texts, ...button.findAllWithCriteria({types:["TEXT"]})]) {
 for (const seg of t.getStyledTextSegments(["fontName"])) fonts.set(JSON.stringify(seg.fontName), seg.fontName);
}
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const mutated = [];
for (const t of texts.slice(0,5)) { t.visible=false; mutated.push(t.id); }
for (let i=0;i<headingPairs.length;i++) { texts[5+i].characters=headingPairs[i][1]; mutated.push(texts[5+i].id); }
const qa = await figma.getNodeByIdAsync("909:11820");
qa.visible=false; mutated.push(qa.id);
const reactionsBefore = JSON.stringify(button.reactions);
if (action.parent.id !== primary.id) primary.appendChild(action);
action.fills=[];action.strokes=[];action.cornerRadius=0;
action.paddingTop=0;action.paddingBottom=0;action.paddingLeft=0;action.paddingRight=0;
action.layoutMode="HORIZONTAL";action.resize(744,48);
action.primaryAxisSizingMode="FIXED";action.counterAxisSizingMode="AUTO";action.itemSpacing=12;
button.resize(240,48);button.layoutSizingHorizontal="FIXED";
mutated.push(action.id,primary.id,button.id);
for (const id of ["1039:24494", "955:3801"]) {
 const n=await figma.getNodeByIdAsync(id); n.visible=false;mutated.push(n.id);
}
return {mutatedNodeIds:[...new Set(mutated)],ctaReactionsPreserved:reactionsBefore===JSON.stringify(button.reactions)};

