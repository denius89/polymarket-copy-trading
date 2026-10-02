// Five bounded shared masters. Existing screen layers are not replaced by instances.
// Uses verified sources and existing variables; does not recreate Button/Switch/Status sets.
const CONFIG = { pageId: '2:79', dryRun: true };
const SPECS = [
  { name: 'Shared/App bar/Mobile', sourceId: '121:1794', kind: 'mobile-header' },
  { name: 'Shared/Navigation/Mobile', sourceId: '121:1832', kind: 'mobile-nav' },
  { name: 'Shared/Page header/Desktop', sourceId: '205:404', kind: 'desktop-header' },
  { name: 'Shared/Button/Warning', sourceId: '113:240', kind: 'warning' },
  { name: 'Shared/Button/Danger', sourceId: '113:240', kind: 'danger' },
];
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing verified component page');
await figma.setCurrentPageAsync(page);
const variables = Object.fromEntries((await figma.variables.getLocalVariablesAsync()).map(v => [v.name, v]));
for (const key of ['color/warning/bg', 'color/warning/text', 'color/danger/bg', 'color/danger/text']) if (!variables[key]) throw new Error('Missing existing semantic token: ' + key);
const sourceNodes = [];
for (const spec of SPECS) {
  const existing = page.findAllWithCriteria({ types: ['COMPONENT'] }).filter(n => n.name === spec.name);
  if (existing.length > 1) throw new Error('Duplicate shared master: ' + spec.name);
  const source = await figma.getNodeByIdAsync(spec.sourceId);
  if (!source || !['FRAME', 'COMPONENT'].includes(source.type)) throw new Error('Missing verified source ' + spec.sourceId);
  sourceNodes.push({ ...spec, source, existing: existing[0] || null });
}
if (CONFIG.dryRun) return { dryRun: true, planned: sourceNodes.map(s => ({ name: s.name, sourceId: s.source.id, existingId: s.existing?.id || null })), createdNodeIds: [], mutatedNodeIds: [] };
const fonts = new Map();
for (const spec of sourceNodes) for (const t of spec.source.findAllWithCriteria({ types: ['TEXT'] })) for (const s of t.getStyledTextSegments(['fontName'])) fonts.set(JSON.stringify(s.fontName), s.fontName);
await Promise.all([...fonts.values()].map(f => figma.loadFontAsync(f)));
const created = new Set(), masters = [], skipped = [], diagnostics = [];
const paint = key => figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: 0, g: 0, b: 0 } }, 'color', variables[key]);
const rootName = 'Shared masters · 2026-10-02';
let holder = page.children.find(n => n.type === 'FRAME' && n.name === rootName);
if (!holder) {
  holder = figma.createAutoLayout('VERTICAL'); page.appendChild(holder); created.add(holder.id); holder.name = rootName;
  holder.x = Math.max(0, ...page.children.filter(n => n !== holder).map(n => n.x + n.width)) + 160; holder.y = 100;
  holder.resize(1300, 1); holder.primaryAxisSizingMode = 'AUTO'; holder.counterAxisSizingMode = 'FIXED'; holder.paddingLeft = holder.paddingRight = holder.paddingTop = holder.paddingBottom = 32; holder.itemSpacing = 40; holder.fills = [];
}
for (const spec of sourceNodes) {
  if (spec.existing) { skipped.push({ name: spec.name, id: spec.existing.id }); continue; }
  const copy = spec.source.clone(); holder.appendChild(copy);
  const master = copy.type === 'COMPONENT' ? copy : figma.createComponentFromNode(copy);
  master.name = spec.name;
  const tree = [master, ...master.findAll(() => true)]; for (const node of tree) created.add(node.id);
  // Components do not embed demo fixture routes. Instances receive context-specific links.
  for (const node of tree) if ('reactions' in node && node.reactions.length) await node.setReactionsAsync([]);
  const labels = master.findAllWithCriteria({ types: ['TEXT'] });
  const properties = [];
  if (spec.kind === 'warning' || spec.kind === 'danger') {
    const tone = spec.kind;
    master.fills = [paint('color/' + tone + '/bg')]; master.strokes = [paint('color/' + tone + '/text')]; master.strokeWeight = 1;
    master.layoutMode = 'HORIZONTAL'; master.resize(300, 48); master.primaryAxisSizingMode = master.counterAxisSizingMode = 'FIXED'; master.primaryAxisAlignItems = master.counterAxisAlignItems = 'CENTER'; master.itemSpacing = 8;
    const pad = variables['spacing/4']; if (pad) for (const key of ['paddingLeft', 'paddingRight']) master.setBoundVariable(key, pad); else master.paddingLeft = master.paddingRight = 16;
    if (labels.length !== 1) throw new Error('Expected one source Button label');
    const label = labels[0], defaultValue = tone === 'warning' ? 'Приостановить новые покупки' : 'Закрыть и отключить';
    const definition = Object.entries(master.componentPropertyDefinitions).find(([key, value]) => value.type === 'TEXT' && /label/i.test(key));
    const labelKey = definition ? definition[0] : master.addComponentProperty('Label', 'TEXT', defaultValue);
    if (definition) master.editComponentProperty(labelKey, { defaultValue });
    label.characters = defaultValue; label.fills = [paint('color/' + tone + '/text')]; label.componentPropertyReferences = { characters: labelKey };
    label.textAutoResize = 'HEIGHT'; label.layoutSizingHorizontal = 'FILL'; label.layoutSizingVertical = 'HUG'; label.textAlignHorizontal = 'CENTER'; properties.push(labelKey);
    master.description = 'Default ' + tone + ' action. Semantic color uses existing tokens; label editable. Warning pauses new purchases; danger requires a separate confirmation. Hover/focus/loading variants and replacement of current screen buttons are not completed by this master.';
  } else {
    const seen = new Set();
    for (const [i, label] of labels.entries()) {
      let key = spec.kind === 'mobile-nav' ? 'Nav label ' + (i + 1) : /160|\d[,.]\d|\$/.test(label.characters) ? 'Balance value' : /Демо|Demo|доступно|available/.test(label.characters) ? 'Balance context' : /^shadow$/.test(label.characters) ? 'Brand' : 'Text ' + (i + 1);
      while (seen.has(key)) key += ' ' + (i + 1); seen.add(key);
      const defaultValue = key.startsWith('Balance value') ? 'Нет данных' : label.characters;
      const property = master.addComponentProperty(key, 'TEXT', defaultValue); label.componentPropertyReferences = { characters: property }; label.characters = defaultValue; properties.push(property);
    }
    master.description = 'Shared ' + spec.kind + ' extracted from inspected current composition. Text properties support localisation and actual account context. Prototype fixture routes are removed; connect instances to the correct screen/account. This extraction does not convert existing product screens to instances or certify all responsive/interaction states.';
  }
  masters.push({ id: master.id, name: master.name, sourceId: spec.sourceId, propertyKeys: properties });
}
return { containerId: holder.id, createdNodeIds: [...created], mutatedNodeIds: [], masters, skipped, diagnostics, integrationStatus: 'Masters created only; original screen instance integration remains separate work.' };
