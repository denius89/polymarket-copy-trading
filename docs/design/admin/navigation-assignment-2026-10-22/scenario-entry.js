// Append to the navigation prelude. Explicit prototype chooser only, outside working navigation.
const changes=[];
for(const id of HUBS){const root=await figma.getNodeByIdAsync(id),main=root.children.find(n=>/^Main/.test(n.name));const ctx=main.children.find(n=>/context/i.test(n.name)&&'children'in n),title=ctx?.children.find(n=>n.type==='TEXT'),avatar=ctx?.children.find(n=>n.type==='INSTANCE');if(title){for(const f of title.getStyledTextSegments(['fontName']))await figma.loadFontAsync(f.fontName);title.setBoundVariable('characters',null);title.characters=LOCALE==='ru'?'Отдельная карта учебных сценариев · выберите участника':'Separate prototype scenario map · choose a participant';mutated.push(title.id);}if(avatar){avatar.visible=false;await avatar.setReactionsAsync([]);mutated.push(avatar.id);}
 const rows=main.query('INSTANCE').values(['id','componentProperties','reactions']).filter(n=>n.reactions?.some(r=>targets(r.actions||[]).length));
 for(const row of rows){const n=await figma.getNodeByIdAsync(row.id),text=label(n),dest=row.reactions.flatMap(r=>targets(r.actions||[]))[0];let role=CONFIG.defaultRole[dest]||'owner-a';if(/владелец B|Owner B|Максим|Maxim/i.test(text))role='owner-b';else if(/Ирина|Irina|маркетолог|marketing role/i.test(text))role='marketing';else if(/аудитор|auditor/i.test(text))role='audit';else if(/Олег|Oleg/i.test(text))role='ops';else if(/Нора|Nora/i.test(text))role=/огранич|restricted|ASG-DEMO-41/i.test(text)?'limited':'nora-operations';
  await n.setReactionsAsync(row.reactions.map(r=>({trigger:r.trigger,actions:[...contextActions(role),...(r.actions||[])]})));mutated.push(n.id);changes.push({id:n.id,label:text,role,destination:dest});
 }
}
return {createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],changes};
