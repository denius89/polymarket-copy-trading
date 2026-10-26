// Final mode normalization after binding/instance repair. Final mode is inherited, not pinned EN.
const page=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(page);
const ids=['4238:1866','4238:1867','4238:1868','4238:1869','4238:1870','4238:1871','4238:1872','4238:1873','4238:1874','4238:1875','4245:64990','4245:65078','4245:65146','4245:65206','4245:65272','4245:65336','4245:65395','4245:65456','4245:65512','4245:65531'];
const nodes=[],fonts=new Map();for(const id of ids){const r=await figma.getNodeByIdAsync(id);nodes.push(r,...r.findAll(()=>true));for(const t of r.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);}
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const collection=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:3986:28');const changed=[];
for(const n of nodes)if('setExplicitVariableModeForCollection'in n){n.setExplicitVariableModeForCollection(collection,'3986:2');n.clearExplicitVariableModeForCollection(collection);changed.push(n.id);}
return {mutatedNodeIds:changed,count:changed.length};
