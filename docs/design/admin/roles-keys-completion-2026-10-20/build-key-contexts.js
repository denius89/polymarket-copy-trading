// Figma-only construction intent. Supply PAGE, LOCALE, DATA and SOURCE_PAIRS.
// Inspect the canvas before retrying after an error. This is not a Figma backup.
const page = await figma.getNodeByIdAsync(PAGE);
await figma.setCurrentPageAsync(page);
const L = LOCALE === 'RU' ? 0 : 1;
const created = [], changed = [], removed = [], screens = [], links = [];
const sources = new Map();
for (const pair of SOURCE_PAIRS) sources.set(pair.key, await figma.getNodeByIdAsync(L === 0 ? pair.ru : pair.en));
const fonts = new Map();
for (const source of sources.values()) {
  const main = source.children.find(n => n.name === 'Main content');
  for (const t of main.findAllWithCriteria({types: ['TEXT']}))
    for (const s of t.getStyledTextSegments(['fontName'])) fonts.set(JSON.stringify(s.fontName), s.fontName);
}
await Promise.all([...fonts.values()].map(f => figma.loadFontAsync(f)));
const byKey = new Map();
const yBase = Math.max(...page.children.filter(n => 'height' in n).map(n => n.y + n.height)) + 240;
function prop(n, name, value) {
  const key = Object.keys(n.componentProperties).find(k => k.split('#')[0] === name);
  if (!key) throw Error('Missing property ' + name + ' on ' + n.id);
  n.setProperties({[key]: value}); changed.push(n.id);
}
function remove(n) { removed.push(n.id); n.remove(); }
for (let i = 0; i < DATA.length; i++) {
  const d = DATA[i];
  let root = d.existing ? await figma.getNodeByIdAsync(d.existing[L]) : page.children.find(n => n.name.startsWith(LOCALE + ' · ' + d.key + ' · '));
  if (!root) {
    root = sources.get(d.sourceKey).clone(); page.appendChild(root);
    root.x = (i % 3) * 1560; root.y = yBase + Math.floor(i / 3) * 1400;
    root.name = LOCALE + ' · ' + d.key + ' · assembling'; created.push(root.id);
  }
  byKey.set(d.key, root);
}
const outside = {
  'account-security': L === 0 ? '2155:20217' : '2155:79959',
  'mfa-replace': L === 0 ? '2155:77215' : '2155:81364',
  'admin-login': L === 0 ? '2138:9959' : '2138:67538'
};
for (const d of DATA) {
  const root = byKey.get(d.key), template = sources.get(d.sourceKey);
  const oldMain = root.children.find(n => n.name === 'Main content');
  const main = template.children.find(n => n.name === 'Main content').clone();
  root.appendChild(main); created.push(main.id); if (oldMain) remove(oldMain);
  const heading = main.children.find(n => n.name === 'Page heading');
  const title = heading.children.find(n => n.type === 'TEXT'); title.characters = d.title[L];
  title.textAutoResize = 'HEIGHT'; changed.push(title.id);
  const crumb = main.children.find(n => n.name === 'Breadcrumb trail');
  const note = main.children.find(n => n.name === 'Review decision note');
  note.characters = d.context[L]; note.textAutoResize = 'HEIGHT'; changed.push(note.id);
  const section = main.children.find(n => n.name === 'Section layout · 2 + 10');
  const content = section.children.find(n => n.name === 'Section content · 10 columns');
  if (d.mode === 'recovery') {
    for (const n of [...root.children]) if (n !== main) remove(n);
    const header = main.children.find(n => n.name === 'Account header');
    for (const n of [...header.children]) if (n.type !== 'TEXT') remove(n);
    const label = header.children.find(n => n.type === 'TEXT');
    label.characters = L === 0 ? 'Восстановление защиты · STAFF-201 · учебный пример' : 'Protection recovery · STAFF-201 · demo'; changed.push(label.id);
    if (crumb) remove(crumb);
    for (const n of [...section.children]) if (n !== content) remove(n);
    const identity = content.children.find(n => n.name === 'Account identity · compact'); if (identity) remove(identity);
    main.x = 0; main.resize(1440, root.height);
    main.paddingLeft = main.paddingRight = 360; main.paddingTop = 80;
    for (const child of main.children) { child.resize(720, child.height); child.layoutSizingHorizontal = 'FILL'; }
    for (const t of heading.children.filter(n => n.type === 'TEXT')) { t.resize(720, t.height); t.textAutoResize = 'HEIGHT'; changed.push(t.id); }
    header.resize(720, header.height); header.layoutSizingHorizontal = 'FILL';
    label.resize(720, label.height); label.textAutoResize = 'HEIGHT';
    section.resize(720, section.height); content.resize(720, content.height);
    content.layoutSizingHorizontal = 'FILL';
  } else if (crumb) prop(crumb, 'Current', d.title[L]);
  const W = content.width;
  const panel = content.children.find(n => n.name === 'Context panel');
  prop(panel, 'Title', L === 0 ? 'Текущий шаг' : 'Current step'); prop(panel, 'Body', d.message[L]);
  for (const child of content.children) {
    child.resize(W, child.height); child.layoutSizingHorizontal = 'FILL';
    if (child.type === 'TEXT') child.textAutoResize = 'HEIGHT';
    changed.push(child.id);
  }
  const table = content.children.find(n => n.name === 'Key verification results');
  const rows = table.children.filter(n => n.type === 'INSTANCE');
  prop(rows[1], 'Title', L === 0 ? 'Новый основной ключ' : 'New primary key');
  prop(rows[2], 'Title', L === 0 ? 'Другой запасной ключ' : 'Distinct backup key');
  for (const row of rows) {
    row.resize(W - 2, row.height); row.layoutSizingHorizontal = 'FILL';
    for (const t of row.children.filter(n => n.type === 'TEXT')) { t.resize((W - 66) / 3, t.height); t.textAutoResize = 'HEIGHT'; t.layoutSizingHorizontal = 'FILL'; changed.push(t.id); }
    row.counterAxisSizingMode = 'AUTO'; row.layoutSizingVertical = 'HUG'; changed.push(row.id);
  }
  for (const t of panel.findAllWithCriteria({types: ['TEXT']})) { t.resize(W - panel.paddingLeft - panel.paddingRight, t.height); t.textAutoResize = 'HEIGHT'; changed.push(t.id); }
  panel.primaryAxisSizingMode = 'AUTO'; panel.layoutSizingVertical = 'HUG';
  const ordinary = content.children.find(n => n.name === 'Actions');
  const scenarios = content.children.find(n => n.name === 'Prototype scenarios · do not implement');
  for (const [container, actions, prototypeOnly] of [[ordinary, d.actions, false], [scenarios, d.scenarios || [], true]]) {
    if (!container && !actions.length) continue;
    if (!container || container.children.length !== actions.length) throw Error('Action count mismatch: ' + d.key);
    container.layoutWrap = 'WRAP'; container.layoutSizingVertical = 'HUG';
    for (let i = 0; i < actions.length; i++) {
      const a = actions[i], button = container.children[i], target = byKey.get(a[2])?.id || outside[a[2]];
      if (!target) throw Error('Missing target ' + a[2]);
      prop(button, 'Label', a[L]); prop(button, 'Show icon', false);
      button.name = (prototypeOnly ? 'Prototype outcome · ' : 'Action · ') + a[2];
      button.reactions = [{trigger: {type: 'ON_CLICK'}, actions: [{type: 'NODE', destinationId: target, navigation: 'NAVIGATE', transition: null, resetScrollPosition: true}]}]; changed.push(button.id);
      links.push({from: root.id, button: button.id, target, prototypeOnly, key: d.key, toKey: a[2]});
    }
  }
  for (const t of main.findAllWithCriteria({types: ['TEXT']})) if (L === 0 && t.characters === 'Елена Морозова · Owner') { t.characters = 'Елена Морозова · владелец'; changed.push(t.id); }
  root.name = LOCALE + ' · ' + d.key + ' · ' + d.title[L];
  const height = Math.max(1200, Math.ceil((main.paddingTop + Math.max(...main.children.filter(n => n.visible).map(n => n.y + n.height)) + 80) / 40) * 40);
  root.resize(1440, height); main.resize(main.width, height); changed.push(root.id, main.id);
  screens.push({key: d.key, id: root.id, title: d.title[L], mode: d.mode, created: !d.existing});
}
return {locale: LOCALE, createdNodeIds: created, mutatedNodeIds: [...new Set(changed)], removedNodeIds: removed, screens, links};
