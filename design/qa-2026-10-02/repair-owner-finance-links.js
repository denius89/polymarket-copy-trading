// Repair already-created owner sections. Never creates or duplicates a node.
const CONFIG = { pageId: '51:2', locale: 'RU', dryRun: true };
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing inspected admin page');
await figma.setCurrentPageAsync(page);
const sectionName = 'Proposed · Owner finance · ' + CONFIG.locale + ' · 2026-10-02';
const sections = page.children.filter(n => n.name === sectionName && n.type === 'SECTION');
if (sections.length !== 1) throw new Error('Expected one exact owner section; found ' + sections.length);
const section = sections[0];
const screens = Array.from({ length: 6 }, (_, i) => {
  const matches = section.children.filter(n => n.type === 'FRAME' && n.name.startsWith('OF0' + (i + 1) + ' · '));
  if (matches.length !== 1) throw new Error('Expected one owner screen OF0' + (i + 1));
  return matches[0];
});
const filters = section.children.find(n => n.type === 'FRAME' && n.name === 'OF · Фильтры · Предложение');
if (!filters) throw new Error('Exact filter state missing');
// Action node names use the canonical Russian labels in both localised branches.
const route = {
  'Обзор': 0, 'Журнал': 1, 'Основание': 2, 'Счета': 3, 'Обязательства': 4, 'Сверка': 5,
  'Открыть журнал': 1, 'Реферальные обязательства': 4,
  'Фильтры: всё время · все площадки · все статусы': 'filters',
  'Посмотреть структуру записи': 2, 'Счёт получателя и подтверждение': 3,
  'Вернуться в журнал': 1, 'Перейти к расхождениям сверки': 5,
  'Основание и история корректировок': 2, 'Вернуться к обзору': 0,
  'Посмотреть основание': 2, 'Применить и вернуться в журнал': 1,
};
const planned = [], unknown = [];
for (const n of section.findAll(node => /^(Action|Button)\s*\//.test(node.name))) {
  const label = n.name.replace(/^(Action|Button)\s*\/\s*/, '');
  if (!(label in route)) { unknown.push(n.id); continue; }
  const target = route[label];
  const destination = target === 'filters' ? filters : screens[target];
  let self = false;
  for (let x = n; x && x.type !== 'SECTION'; x = x.parent) if (x.id === destination.id) self = true;
  planned.push({ node: n, to: destination.id, self, overlay: target === 'filters' });
}
if (unknown.length) throw new Error('Unmapped existing action IDs: ' + unknown.join(','));
if (CONFIG.dryRun) return { dryRun: true, sectionId: section.id, screens: screens.map(n => n.id), filtersId: filters.id, actionCount: planned.length, selfNavigationCount: planned.filter(x => x.self).length, createdNodeIds: [], mutatedNodeIds: [] };
const mutated = [];
for (const { node, to, self, overlay } of planned) {
  const reactions = self ? [] : [{ trigger: { type: 'ON_CLICK' }, actions: [{ type: 'NODE', destinationId: to, navigation: overlay ? 'OVERLAY' : 'NAVIGATE', transition: null, resetScrollPosition: true }] }];
  await node.setReactionsAsync(reactions); mutated.push(node.id);
}
return { sectionId: section.id, screenIds: screens.map(n => n.id), filterId: filters.id, linkedCount: planned.filter(x => !x.self).length, skippedSelfCount: planned.filter(x => x.self).length, createdNodeIds: [], mutatedNodeIds: mutated };
