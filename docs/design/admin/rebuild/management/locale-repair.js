// Scoped repair of inherited locale modes. Construction recipe, not an exact Figma backup.
const ROOTS=["4238:1866", "4238:1867", "4238:1868", "4238:1869", "4238:1870", "4238:1871", "4238:1872", "4238:1873", "4238:1874", "4238:1875", "4245:64990", "4245:65078", "4245:65146", "4245:65206", "4245:65272", "4245:65336", "4245:65395", "4245:65456", "4245:65512", "4245:65531"];
const page=await figma.getNodeByIdAsync('1981:29');await figma.setCurrentPageAsync(page);
const roots=await Promise.all(ROOTS.map(id=>figma.getNodeByIdAsync(id)));
const fonts=new Map();for(const root of roots)for(const t of root.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))fonts.set(JSON.stringify(s.fontName),s.fontName);
await Promise.all([...fonts.values()].map(font=>figma.loadFontAsync(font)));
const lc=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:3986:28');const changed=[];
for(const id of ROOTS){const root=await figma.getNodeByIdAsync(id);for(const n of [root,...root.findAll(()=>true)]){let within=false;for(let a=n;a&&a!==root;a=a.parent)if(a.type==='INSTANCE'){within=true;break;}if(!within&&'clearExplicitVariableModeForCollection' in n){n.clearExplicitVariableModeForCollection(lc);if(n.type==='TEXT'&&n.boundVariables?.characters){const v=await figma.variables.getVariableByIdAsync(n.boundVariables.characters.id);n.setBoundVariable('characters',null);n.setBoundVariable('characters',v);}changed.push(n.id);}}}
return {mutatedNodeIds:changed,rootCount:ROOTS.length};
