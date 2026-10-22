await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
const changed=[];
for(const [id,ru] of [['1982:37735',true],['1982:38558',false]]){
 const root=await figma.getNodeByIdAsync(id);
 const texts=root.findAllWithCriteria({types:['TEXT']}).filter(t=>t.characters.includes(ru?'Последний успешный ответ:':'Last successful response:')||t.characters.startsWith(ru?'Прошлый учебный снимок':'Past fictional snapshot'));
 await Promise.all(texts.flatMap(t=>t.getStyledTextSegments(['fontName']).map(s=>figma.loadFontAsync(s.fontName))));
 for(const t of texts){
  if(t.characters.startsWith(ru?'Прошлый':'Past'))t.characters=ru?'Пользователи с действиями по часам · 01:00–12:00 UTC, 12 октября · прошлый учебный снимок':'Users with activity per hour · 01:00–12:00 UTC, 12 October · past fictional snapshot';
  else t.characters=ru?'Последний успешный ответ: 11:45 UTC. Данные подключения устарели.\nLimitless: свежий учебный снимок. Реальные подключения не проверялись.':'Last successful response: 11:45 UTC. Connection data is stale.\nLimitless: fresh fictional snapshot. Real connections have not been checked.';
  changed.push(t.id);
 }
}
return {createdNodeIds:[],mutatedNodeIds:changed};
