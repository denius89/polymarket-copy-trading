// Scoped final sidebar alignment, after profile-screen/profile-polish.
// The live result uses the same client Nav components as the first-route screens.
const root=await figma.getNodeByIdAsync(PROFILE.profile);
const side=root.findOne(n=>n.type==='FRAME'&&n.name==='Persistent navigation');
const normal=await figma.getNodeByIdAsync('1978:1003');
const selected=await figma.getNodeByIdAsync('1978:1005');
for(const old of [...side.children].filter(n=>n.type==='INSTANCE')){
 const component=old.name==='Личный профиль'?selected:normal;
 if(old.mainComponent?.id===component.id)continue;
 const label=old.findAllWithCriteria({types:['TEXT']})[0];
 for(const t of component.findAllWithCriteria({types:['TEXT']}))for(const segment of t.getStyledTextSegments(['fontName']))await figma.loadFontAsync(segment.fontName);
 const n=component.createInstance();side.insertChild(side.children.indexOf(old),n);n.resize(200,44);n.name=old.name;
 const text=n.findAllWithCriteria({types:['TEXT']})[0];
 if(label.boundVariables.characters)text.setBoundVariable('characters',await figma.variables.getVariableByIdAsync(label.boundVariables.characters.id));
 if(old.boundVariables.visible)n.setBoundVariable('visible',await figma.variables.getVariableByIdAsync(old.boundVariables.visible.id));
 if(old.reactions.length)await n.setReactionsAsync(old.reactions);
 created.push(n.id,...n.findAll(()=>true).map(x=>x.id));old.remove();mutated.push(side.id);
}
return await finish();
