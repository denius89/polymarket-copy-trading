// Whole-frame reference clones. Originals and their flow starting points are untouched.
// Use one call per page; review complete screenshots before claiming responsive readiness.
const CONFIG = {
  pageId: '33:2', locale: 'RU', device: 'mobile', widths: [320, 360], dryRun: true,
  sources: [
    { role: 'catalog', id: '33:31' }, { role: 'trader', id: '33:90' },
    { role: 'setup', id: '235:241' }, { role: 'empty-session', id: '788:99' },
    { role: 'position-detail', id: '344:498' },
  ],
};
const MIN_HIT = 44, MIN_TEXT = 12;
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing inspected user page');
await figma.setCurrentPageAsync(page);
const sectionName = 'Reference · Five control compositions · ' + CONFIG.device + ' ' + CONFIG.locale + ' · 2026-10-02';
const existing = page.children.find(n => n.type === 'SECTION' && n.name === sectionName);
if (existing) return { existingSectionId: existing.id, frames: existing.children.map(n => ({ id: n.id, name: n.name })), createdNodeIds: [], mutatedNodeIds: [], diagnostics: ['Existing references retained; inspect instead of recreating.'] };
const sources = [];
for (const source of CONFIG.sources) {
  const n = source.id && await figma.getNodeByIdAsync(source.id);
  if (!n || n.type !== 'FRAME') throw new Error('Missing inspected control frame for role ' + source.role);
  let ownerPage = n;
  while (ownerPage && ownerPage.type !== 'PAGE') ownerPage = ownerPage.parent;
  if (!ownerPage || ownerPage.id !== page.id) throw new Error('Control frame is on a different page: ' + n.id);
  sources.push({ role: source.role, node: n });
}
if (!CONFIG.widths.every(w => Number.isFinite(w) && w > 0)) throw new Error('Invalid reference widths');
if (CONFIG.dryRun) return { dryRun: true, pageId: page.id, sourceIds: sources.map(s => s.node.id), widths: CONFIG.widths, plannedFrameCount: sources.length * CONFIG.widths.length, createdNodeIds: [], mutatedNodeIds: [] };
const fonts = new Map();
for (const { node } of sources) for (const t of node.findAllWithCriteria({ types: ['TEXT'] })) for (const s of t.getStyledTextSegments(['fontName'])) fonts.set(JSON.stringify(s.fontName), s.fontName);
await Promise.all([...fonts.values()].map(f => figma.loadFontAsync(f)));
const created = new Set(), changed = new Set(), diagnostics = [], references = [];
const section = figma.createSection(); created.add(section.id); page.appendChild(section); section.name = sectionName;
section.x = Math.max(0, ...page.children.filter(n => n !== section).map(n => n.x + n.width)) + 240; section.y = 100;
const all = n => [n, ...('findAll' in n ? n.findAll(() => true) : [])];
const inFlow = p => p.children.filter(c => c.visible && c.layoutPositioning !== 'ABSOLUTE');
function widthOf(n, width, fill = false) {
  if (!(n.type === 'FRAME' || n.type === 'INSTANCE' || n.type === 'TEXT')) return;
  const w = Math.max(1, width);
  const verticalHug = n.type === 'FRAME' && n.layoutMode === 'VERTICAL' && n.primaryAxisSizingMode === 'AUTO';
  const horizontalHugHeight = n.type === 'FRAME' && n.layoutMode === 'HORIZONTAL' && n.counterAxisSizingMode === 'AUTO';
  if ('minWidth' in n && n.minWidth && n.minWidth > w) n.minWidth = w;
  n.resize(w, n.height); changed.add(n.id);
  if (verticalHug) n.primaryAxisSizingMode = 'AUTO';
  if (horizontalHugHeight) n.counterAxisSizingMode = 'AUTO';
  if (n.type === 'TEXT') {
    n.textAutoResize = 'HEIGHT';
    if (n.parent && n.parent.type === 'FRAME' && ['VERTICAL', 'HORIZONTAL'].includes(n.parent.layoutMode) && n.layoutPositioning !== 'ABSOLUTE') {
      n.layoutSizingVertical = 'HUG'; if (fill) n.layoutSizingHorizontal = 'FILL';
    }
  } else if (fill && n.parent && n.parent.type === 'FRAME' && ['VERTICAL', 'HORIZONTAL'].includes(n.parent.layoutMode) && n.layoutPositioning !== 'ABSOLUTE') n.layoutSizingHorizontal = 'FILL';
}
function reflow(n, oldWidths) {
  if (!('children' in n)) return;
  const flow = inFlow(n), inner = Math.max(1, n.width - (n.paddingLeft || 0) - (n.paddingRight || 0));
  if (n.layoutMode === 'VERTICAL') {
    const originalInner = Math.max(1, (oldWidths.get(n.id) || n.width) - (n.paddingLeft || 0) - (n.paddingRight || 0));
    for (const child of flow) {
      const originalW = oldWidths.get(child.id) || child.width;
      if (child.width > inner || originalW >= originalInner * .8) widthOf(child, inner, true);
    }
  } else if (n.layoutMode === 'HORIZONTAL') {
    const gap = n.itemSpacing || 0, available = Math.max(1, inner - Math.max(0, flow.length - 1) * gap);
    const total = flow.reduce((sum, c) => sum + c.width, 0);
    const headerBrand = /App bar|Header\s*\//.test(n.name) && flow.find(c => c.type === 'TEXT' && c.characters === 'shadow');
    if (headerBrand) {
      const remaining = available - flow.filter(c => c !== headerBrand).reduce((sum, c) => sum + c.width, 0);
      if (remaining > 0) widthOf(headerBrand, remaining);
      else diagnostics.push({ id: n.id, issue: 'Header utilities need an explicit compact variant', available, total });
    } else if (total > available + .1) {
      const cards = flow.filter(c => c.type === 'FRAME' && c.width >= 160 && c.height >= 64 && /Card|Trader|Metric|Account|Position|Panel/i.test(c.name));
      if (cards.length >= 2 && cards.length === flow.length) {
        for (const card of cards) widthOf(card, available / cards.length);
      } else {
        const fixed = flow.filter(c => !['FRAME', 'INSTANCE', 'TEXT'].includes(c.type) || c.width <= 44);
        const adjustable = flow.filter(c => !fixed.includes(c));
        const remaining = available - fixed.reduce((sum, c) => sum + c.width, 0);
        const weight = adjustable.reduce((sum, c) => sum + c.width, 0);
        if (remaining >= adjustable.length * 32 && weight > 0) for (const c of adjustable) widthOf(c, Math.max(32, remaining * c.width / weight));
        else diagnostics.push({ id: n.id, issue: 'Horizontal row needs an explicit wrap or composition decision', available, total });
      }
    }
  } else if (n.type === 'FRAME' && n.layoutMode === 'NONE') {
    // Preserve absolute X positions unless a child overflows its own container.
    for (const child of flow) if (child.x + child.width > inner + (n.paddingLeft || 0) + .1 && ['FRAME', 'INSTANCE', 'TEXT'].includes(child.type)) widthOf(child, Math.max(1, n.width - child.x - (n.paddingRight || 0)));
  }
  for (const child of n.children) reflow(child, oldWidths);
}
let cursorY = 40, maxRight = 0;
for (const source of sources) {
  let rowHeight = 0, cursorX = 40;
  for (const width of CONFIG.widths) {
    const n = source.node.clone(); section.appendChild(n); for (const c of all(n)) created.add(c.id);
    n.name = 'Reference · ' + source.role + ' · ' + CONFIG.locale + ' · ' + width + ' px';
    const oldWidths = new Map(all(n).filter(c => 'width' in c).map(c => [c.id, c.width]));
    const originalReactions = new Map(all(n).filter(c => 'reactions' in c).map(c => [c.id, JSON.stringify(c.reactions)]));
    for (const t of n.findAllWithCriteria({ types: ['TEXT'] })) if (typeof t.fontSize === 'number' && t.fontSize < MIN_TEXT && /[A-Za-zА-Яа-я0-9]/.test(t.characters)) {
      t.fontSize = MIN_TEXT;
      if (t.lineHeight.unit === 'PIXELS' && t.lineHeight.value < 16) t.lineHeight = { unit: 'PIXELS', value: 16 };
      changed.add(t.id);
    }
    n.resize(width, source.node.height); n.x = cursorX; n.y = cursorY; changed.add(n.id);
    if (CONFIG.device === 'mobile') {
      const pad = width <= 320 ? 16 : 20;
      if (n.layoutMode === 'VERTICAL') { n.paddingLeft = n.paddingRight = pad; }
      else for (const child of n.children.filter(c => c.visible && ['FRAME', 'INSTANCE', 'TEXT'].includes(c.type))) {
        child.x = pad; widthOf(child, width - 2 * pad);
      }
    } else {
      const sidebar = n.children.find(c => c.type === 'FRAME' && /Sidebar|^Navigation$/.test(c.name));
      const main = n.children.find(c => c.type === 'FRAME' && /Main content|^Main$/.test(c.name));
      const standaloneHeader = n.children.find(c => c.type === 'FRAME' && /Page\s*header/i.test(c.name));
      const standaloneContent = n.children.find(c => c.type === 'FRAME' && /^Content\s*\//.test(c.name));
      if (!sidebar || (!main && !(standaloneHeader && standaloneContent))) throw new Error('Inspected desktop screen lacks a supported sidebar/content shell: ' + source.node.id);
      sidebar.x = 0; widthOf(sidebar, 224);
      if (main) {
        main.x = 224; widthOf(main, width - 224); main.paddingLeft = main.paddingRight = 32;
      } else {
        // New empty-session controls keep independent header/content roots.
        for (const child of [standaloneHeader, standaloneContent]) {
          child.x = 256; widthOf(child, width - 288);
        }
      }
    }
    reflow(n, oldWidths);
    // The balance/bell/profile row has an explicit, bounded brand width.
    for (const header of n.findAll(node => node.type === 'FRAME' && /App bar|Header\s*\//.test(node.name))) {
      const brand = header.children.find(c => c.type === 'TEXT' && c.characters === 'shadow');
      if (brand && header.layoutMode === 'HORIZONTAL') {
        const others = inFlow(header).filter(c => c !== brand), gap = header.itemSpacing || 0;
        const remaining = header.width - header.paddingLeft - header.paddingRight - others.reduce((sum, c) => sum + c.width, 0) - gap * others.length;
        if (remaining > 0) widthOf(brand, remaining);
        const lineHeight = brand.lineHeight.unit === 'PIXELS' ? brand.lineHeight.value : (typeof brand.fontSize === 'number' ? brand.fontSize * 1.3 : 24);
        if (brand.height > lineHeight + 1) diagnostics.push({ id: brand.id, issue: 'Brand wraps; use an explicit compact-mark variant after review' });
      }
    }
    for (const c of all(n)) if ('reactions' in c && JSON.stringify(c.reactions) !== originalReactions.get(c.id)) throw new Error('Reference reaction changed: ' + c.id);
    references.push({ id: n.id, sourceId: source.node.id, role: source.role, width, height: n.height });
    cursorX += width + 60; rowHeight = Math.max(rowHeight, n.height); maxRight = Math.max(maxRight, cursorX - 20);
  }
  cursorY += rowHeight + 80;
}
section.resizeWithoutConstraints(maxRight + 40, cursorY + 40);
const overflows = [], shortHits = [];
for (const reference of references) {
  const root = await figma.getNodeByIdAsync(reference.id);
  for (const child of root.findAll(() => true)) {
    if (!child.visible || !child.parent || !('width' in child.parent)) continue;
    let hidden = false; for (let p = child.parent; p && p.id !== root.id; p = p.parent) if ('visible' in p && !p.visible) hidden = true;
    if (hidden) continue;
    if ('reactions' in child && child.reactions.some(r => ['ON_CLICK', 'ON_PRESS', 'ON_DRAG'].includes(r.trigger?.type)) && (child.height < MIN_HIT || child.width < MIN_HIT)) shortHits.push({ referenceId: root.id, id: child.id, name: child.name, width: child.width, height: child.height });
    const p = child.parent;
    const horizontal = child.x < -.5 || child.x + child.width > p.width + .5;
    const vertical = child.y < -.5 || child.y + child.height > p.height + .5;
    if (horizontal || vertical) overflows.push({ referenceId: root.id, id: child.id, parentId: p.id, name: child.name, horizontal, vertical, parentClips: !!p.clipsContent, parentScroll: 'overflowDirection' in p ? p.overflowDirection : 'NONE' });
  }
}
return { sectionId: section.id, createdNodeIds: [...created], mutatedNodeIds: [...changed].filter(id => !created.has(id)), references, overflowCount: overflows.length, overflows: overflows.slice(0, 40), shortHitCount: shortHits.length, shortHits: shortHits.slice(0, 40), thresholds: { minHit: MIN_HIT, minText: MIN_TEXT }, diagnosticCount: diagnostics.length, diagnostics: diagnostics.slice(0, 40), limitation: 'References are structural reflow candidates. Detailed diagnostics are capped at 40 per kind; counts include all findings. Whole-screen screenshots and font/financial/interaction checks must be reviewed. Original routes are preserved and return to canonical product frames.' };
