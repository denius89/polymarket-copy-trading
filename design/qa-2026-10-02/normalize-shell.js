// Embed this file in use_figma after replacing CONFIG with inspected page IDs.
// No screen deletion, no detach, no rewriting existing prototype reactions.
const CONFIG = {
  pageId: '33:2', locale: 'RU', device: 'mobile', dryRun: true,
  targets: { home: '33:236', traders: '33:31', positions: null,
    activity: '33:289', funds: '270:129', notifications: '191:266', profile: '133:580' },
  // Optional exact screen IDs constrain a control-screen batch. Empty = whole page.
  screenIds: [],
};

const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Inspected page is missing');
await figma.setCurrentPageAsync(page);
const ru = CONFIG.locale === 'RU';
const L = (en, rus) => ru ? rus : en;
const created = new Set(), mutated = new Set(), removed = [], diagnostics = [];
const touch = n => (mutated.add(n.id), n);
const track = n => (created.add(n.id), n);
const descendants = n => [n, ...('findAll' in n ? n.findAll(() => true) : [])];
const trackTree = n => (descendants(n).forEach(c => created.add(c.id)), n);
const textNodes = n => n.type === 'TEXT' ? [n] : ('findAllWithCriteria' in n ? n.findAllWithCriteria({ types: ['TEXT'] }) : []);
const before = new Map();
for (const n of page.findAll(() => true)) if ('reactions' in n) before.set(n.id, JSON.stringify(n.reactions));
const frames = page.findAllWithCriteria({ types: ['FRAME'] });
const allowed = n => {
  if (!CONFIG.screenIds.length) return true;
  for (let x = n; x && x.type !== 'PAGE'; x = x.parent) if (CONFIG.screenIds.includes(x.id)) return true;
  return false;
};
const mobileHeaders = frames.filter(n => allowed(n) && (n.name === 'App bar' || /^Header\s*\/\s*320/.test(n.name) || (n.height <= 88 && n.children.some(c => c.type === 'TEXT' && c.characters === 'shadow'))));
const utilities = frames.filter(n => allowed(n) && n.name === 'Utilities');
const navs = frames.filter(n => allowed(n) && n.name === 'Bottom navigation');
const sidebars = frames.filter(n => allowed(n) && n.name === 'App shell / Sidebar');
const summary = { pageId: page.id, headers: mobileHeaders.map(n => n.id), utilities: utilities.map(n => n.id), navs: navs.map(n => n.id), sidebars: sidebars.map(n => n.id) };
if (CONFIG.dryRun) return { dryRun: true, ...summary, createdNodeIds: [], mutatedNodeIds: [] };

// Fail before mutation if a requested new destination does not exist.
for (const [key, id] of Object.entries(CONFIG.targets)) if (id && !(await figma.getNodeByIdAsync(id))) throw new Error('Missing destination ' + key + ': ' + id);
const fonts = new Map();
for (const t of page.findAllWithCriteria({ types: ['TEXT'] })) {
  for (const s of t.getStyledTextSegments(['fontName'])) fonts.set(JSON.stringify(s.fontName), s.fontName);
}
await Promise.all([...fonts.values()].map(f => figma.loadFontAsync(f)));
const fallback = [...fonts.values()].find(f => f.family === 'Inter' && f.style === 'Medium') || [...fonts.values()][0];
if (!fallback) throw new Error('No inspected font available');
const colors = Object.fromEntries((await figma.variables.getLocalVariablesAsync()).filter(v => v.resolvedType === 'COLOR').map(v => [v.name, v]));
const paint = key => colors[key] ? figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: .65, g: .7, b: .8 } }, 'color', colors[key]) : { type: 'SOLID', color: { r: .65, g: .7, b: .8 } };
const setText = (t, s, width, size = 12, center = false) => {
  if (s !== null) t.characters = s;
  t.fontSize = size; t.lineHeight = { unit: 'PIXELS', value: size <= 12 ? 16 : 20 };
  t.textAutoResize = 'HEIGHT'; t.resize(Math.max(1, width), t.height); t.textAutoResize = 'HEIGHT';
  t.textAlignHorizontal = center ? 'CENTER' : 'LEFT'; touch(t);
};
const horizontal = (n, w, h, gap = 8) => {
  n.layoutMode = 'HORIZONTAL'; n.resize(w, h);
  n.primaryAxisSizingMode = 'FIXED'; n.counterAxisSizingMode = 'FIXED';
  n.primaryAxisAlignItems = 'MIN'; n.counterAxisAlignItems = 'CENTER'; n.itemSpacing = gap;
  n.paddingLeft = n.paddingRight = n.paddingTop = n.paddingBottom = 0; touch(n);
};
const click = async (n, id) => { let top=n; while(top.parent && top.parent.type !== 'PAGE' && top.parent.type !== 'SECTION') top=top.parent; if (id && top.id !== id) await n.setReactionsAsync([{ trigger: { type: 'ON_CLICK' }, actions: [{ type: 'NODE', destinationId: id, navigation: 'NAVIGATE', transition: null, resetScrollPosition: true }] }]); };
const addControl = async (header, kind) => {
  const n = track(figma.createAutoLayout('HORIZONTAL')); header.appendChild(n);
  n.name = kind === 'notifications' ? 'Button/Notifications' : kind === 'profile' ? 'Profile / Open account' : 'Balance / Open wallets';
  horizontal(n, kind === 'funds' ? 112 : 44, 44, 0); n.primaryAxisAlignItems = 'CENTER'; n.fills = [paint('color/bg/elevated')]; n.cornerRadius = 10;
  if (kind === 'funds') {
    const t = track(figma.createText()); n.appendChild(t); t.fontName = fallback; t.characters = L('Funds', 'Средства'); t.fills = [paint('color/text/primary')]; setText(t, null, 96, 13, true);
  } else {
    const path = kind === 'notifications' ? '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>' : '<circle cx="12" cy="8" r="4"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>';
    const icon = trackTree(figma.createNodeFromSvg('<svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="#A3ADC2" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + path + '</g></svg>'));
    n.appendChild(icon); icon.name = kind === 'notifications' ? 'Icon/Bell' : 'Icon/Profile';
  }
  await click(n, CONFIG.targets[kind]); return n;
};
const classify = n => /Balance|Open wallets/.test(n.name) ? 'funds' : /Notifications/.test(n.name) ? 'notifications' : /Profile.*(?:Open account|avatar)/.test(n.name) ? 'profile' : null;
const normalizeControl = (n, kind, balanceWidth) => {
  if (n.type !== 'FRAME') { diagnostics.push({ id: n.id, issue: 'Instance control requires component edit' }); return; }
  if (kind === 'funds') {
    n.layoutMode = 'VERTICAL'; n.resize(balanceWidth, 44); n.primaryAxisSizingMode = n.counterAxisSizingMode = 'FIXED';
    n.primaryAxisAlignItems = 'CENTER'; n.counterAxisAlignItems = 'MIN'; n.paddingLeft = n.paddingRight = 8; n.paddingTop = n.paddingBottom = 4; n.itemSpacing = 0;
    for (const [i, t] of textNodes(n).entries()) setText(t, t.characters.replace(/\s*→\s*$/, ''), balanceWidth - 16, i === 0 ? 12 : 14);
  } else if (kind === 'notifications') {
    horizontal(n, 44, 44, 0); n.primaryAxisAlignItems = 'CENTER';
    const icons = n.children.filter(c => c.type !== 'TEXT');
    for (const t of n.children.filter(c => c.type === 'TEXT')) { t.visible = icons.length === 0; touch(t); }
    for (const c of icons) { c.layoutPositioning = 'AUTO'; touch(c); }
  } else {
    // Avatar glyph overlays its circle; preserve the overlay relationship.
    const circle = n.children.find(c => c.type === 'ELLIPSE');
    if (circle) {
      n.layoutMode = 'NONE'; n.resize(44, 44); circle.x = 8; circle.y = 8; circle.resize(28, 28); touch(circle);
      for (const t of n.children.filter(c => c.type === 'TEXT')) {
        if (t.characters.length <= 2) { t.visible = true; setText(t, null, 28, 13, true); t.x = 8; t.y = 13; }
        else { t.visible = false; touch(t); }
      }
    } else { horizontal(n, 44, 44, 0); n.primaryAxisAlignItems = 'CENTER'; }
  }
  touch(n);
};

for (const h of [...mobileHeaders, ...utilities]) {
  const current = Object.fromEntries(h.children.map(n => [classify(n), n]).filter(([key]) => key));
  // A brand+demo badge header is a guest/wizard shell, not proof of a funded account.
  if (!Object.keys(current).length) { diagnostics.push({ id: h.id, issue: 'Guest/wizard shell retained; no inferred balance' }); continue; }
  for (const kind of ['funds', 'notifications', 'profile']) if (!current[kind] && CONFIG.targets[kind]) current[kind] = await addControl(h, kind);
  const isDesktop = h.name === 'Utilities';
  const width = h.width, balanceWidth = isDesktop ? 144 : width < 300 ? 112 : 120;
  for (const kind of ['funds', 'notifications', 'profile']) if (current[kind]) normalizeControl(current[kind], kind, balanceWidth);
  const brand = isDesktop ? null : h.children.find(n => n.type === 'TEXT' && n.characters === 'shadow') || h.children.find(n => n.name === 'Compact brand mark');
  const extras = h.children.filter(n => n !== brand && !Object.values(current).includes(n));
  for (const extra of extras) if (/Status.*(?:Demo|Демо)|Badge.*PAPER/.test(extra.name)) { extra.visible = false; touch(extra); }
  horizontal(h, isDesktop ? balanceWidth + 88 + 16 : width, 44, 8);
  if (brand) {
    const bw = Math.max(32, width - balanceWidth - 88 - 24);
    if (brand.type === 'TEXT') setText(brand, null, bw, bw < 65 ? 14 : 18);
    else { brand.resize(Math.min(44, bw), 44); touch(brand); }
  }
  const order = [brand, current.funds, current.notifications, current.profile].filter(Boolean);
  for (const [i, n] of order.entries()) { h.insertChild(i, n); n.layoutPositioning = 'AUTO'; touch(n); }
  h.primaryAxisAlignItems = isDesktop ? 'MAX' : 'SPACE_BETWEEN';
  const parent = h.parent;
  if (isDesktop && parent && parent.type === 'FRAME' && /Page header/i.test(parent.name)) {
    // Title block stays independent of fixed-width utilities; no overlapping absolute x.
    horizontal(parent, parent.width, Math.max(68, parent.height), 24);
    const left = parent.children.find(c => c !== h && c.visible);
    if (left) { left.layoutPositioning = 'AUTO'; left.resize(Math.max(1, parent.width - h.width - 24), left.height); left.layoutSizingHorizontal = 'FILL'; touch(left); }
    h.layoutSizingHorizontal = 'FIXED'; parent.primaryAxisAlignItems = 'SPACE_BETWEEN';
  }
}

for (const nav of navs) {
  const items = nav.children.filter(n => n.type === 'FRAME' && /^Navigation\s*\//.test(n.name));
  let positions = items.find(n => /Positions/.test(n.name));
  if (!positions && CONFIG.targets.positions && items.length) {
    positions = trackTree(items[0].clone()); nav.appendChild(positions); positions.name = 'Navigation / Positions'; positions.fills = [];
    // Remove only the old icon descendants inside this newly-created clone.
    // Existing user-owned navigation nodes are never removed here.
    for (const c of [...positions.children].filter(c => c.type !== 'TEXT')) {
      for (const old of descendants(c)) { created.delete(old.id); removed.push(old.id); }
      c.remove();
    }
    const icon = trackTree(figma.createNodeFromSvg('<svg width="22" height="22" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 4h16v16H4zM8 8h8M8 12h8M8 16h5" fill="none" stroke="#A3ADC2" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>'));
    positions.insertChild(0, icon); await click(positions, CONFIG.targets.positions);
    for (const t of textNodes(positions)) setText(t, L('Positions', 'Позиции'), t.width, 12, true);
  }
  const all = positions && !items.includes(positions) ? [...items, positions] : items;
  const rank = n => /Overview|Home/.test(n.name) ? 0 : /Traders/.test(n.name) ? 1 : /Positions/.test(n.name) ? 2 : /Activity/.test(n.name) ? 3 : 4;
  all.sort((a, b) => rank(a) - rank(b)); horizontal(nav, nav.width, Math.max(64, nav.height), 4);
  const w = (nav.width - 4 * Math.max(0, all.length - 1)) / Math.max(1, all.length);
  for (const [i, n] of all.entries()) {
    nav.insertChild(i, n); n.resize(w, 56); n.primaryAxisSizingMode = n.counterAxisSizingMode = 'FIXED'; n.primaryAxisAlignItems = 'CENTER'; n.counterAxisAlignItems = 'CENTER';
    n.paddingLeft = n.paddingRight = n.paddingTop = n.paddingBottom = 4; n.itemSpacing = 4;
    for (const t of textNodes(n)) setText(t, rank(n) === 0 ? L('Home', 'Главная') : null, w - 8, 12, true);
    touch(n);
  }
  if (!positions) diagnostics.push({ id: nav.id, issue: 'Positions destination missing; no invented route' });
}
for (const sidebar of sidebars) {
  const entries = sidebar.children.filter(n => ['Nav/Home', 'Nav/Traders', 'Nav/Positions', 'Nav/Activity'].includes(n.name));
  entries.sort((a, b) => ['Nav/Home', 'Nav/Traders', 'Nav/Positions', 'Nav/Activity'].indexOf(a.name) - ['Nav/Home', 'Nav/Traders', 'Nav/Positions', 'Nav/Activity'].indexOf(b.name));
  const start = Math.min(...entries.map(n => sidebar.children.indexOf(n)));
  for (const [i, n] of entries.entries()) { sidebar.insertChild(start + i, n); n.resize(n.width, Math.max(44, n.height)); touch(n); }
  touch(sidebar);
  for (const t of textNodes(sidebar).filter(t => /^(Overview|Обзор)$/.test(t.characters))) setText(t, L('Home', 'Главная'), t.width, 14);
}
const changedReactions = [];
for (const [id, value] of before) {
  const n = await figma.getNodeByIdAsync(id);
  if (!n) throw new Error('Existing node unexpectedly missing: ' + id);
  if ('reactions' in n && JSON.stringify(n.reactions) !== value) changedReactions.push(id);
}
if (changedReactions.length) diagnostics.push({ issue: 'Existing reactions changed unexpectedly', ids: changedReactions });
return { ...summary, createdNodeIds: [...created], mutatedNodeIds: [...mutated], removedNodeIds: removed, diagnostics, preservedExistingReactions: changedReactions.length === 0 };
