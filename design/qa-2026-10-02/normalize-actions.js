// Embed in use_figma; fill exact inspected screenIds before execution.
// Visual-only normalization. Existing reaction owners and node IDs remain intact.
const CONFIG = { pageId: '33:2', screenIds: [], dryRun: true, minHeight: 44, paddingX: 16, paddingY: 8, gap: 8 };
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing inspected page');
await figma.setCurrentPageAsync(page);
const affected = new Set(), created = [], diagnostics = [];
const touch = n => (affected.add(n.id), n);
const allowed = n => {
  for (let x = n; x && x.type !== 'PAGE'; x = x.parent) {
    if (/Sidebar|Bottom navigation|App bar|Utilities|Header\s*\//i.test(x.name)) return false;
  }
  if (!CONFIG.screenIds.length) return true;
  for (let x = n; x && x.type !== 'PAGE'; x = x.parent) if (CONFIG.screenIds.includes(x.id)) return true;
  return false;
};
const candidate = n => n.type === 'FRAME' && /^(Button|Action)[ /]/.test(n.name) && n.height <= 88 &&
  n.name !== 'Action / Content group' && !/Balance|Notifications|Profile|Wallet|Badge/i.test(n.name) && allowed(n);
const buttons = page.findAllWithCriteria({ types: ['FRAME'] }).filter(candidate);
const texts = n => n.findAllWithCriteria({ types: ['TEXT'] }).filter(t => t.visible);
const specs = [];
for (const n of buttons) {
  const existingGroup = n.children.find(c => c.name === 'Action / Content group' && c.type === 'FRAME');
  const content = existingGroup || n;
  const ts = texts(content);
  const children = content.children.filter(c => c.visible);
  const icons = children.filter(c => c.type !== 'TEXT');
  const isIcon = c => ['VECTOR', 'BOOLEAN_OPERATION', 'GROUP'].includes(c.type) ||
    (c.type === 'FRAME' && c.width <= 32 && c.height <= 32 && c.findAllWithCriteria({ types: ['TEXT'] }).length === 0);
  if (ts.length !== 1 || !children.includes(ts[0]) || icons.length > 1 || icons.some(c => !isIcon(c))) {
    diagnostics.push({ id: n.id, reason: 'Complex button content left unchanged' }); continue;
  }
  const t = ts[0], icon = icons[0] || null;
  const available = n.width - 2 * CONFIG.paddingX - (icon ? icon.width + CONFIG.gap : 0);
  if (available < 24) { diagnostics.push({ id: n.id, reason: 'Insufficient label width' }); continue; }
  specs.push({ n, t, icon, existingGroup, available });
}
if (CONFIG.dryRun) return { dryRun: true, candidateNodeIds: specs.map(s => s.n.id), diagnostics, createdNodeIds: [], mutatedNodeIds: [] };
const fonts = new Map();
for (const s of specs) for (const segment of s.t.getStyledTextSegments(['fontName'])) fonts.set(JSON.stringify(segment.fontName), segment.fontName);
await Promise.all([...fonts.values()].map(f => figma.loadFontAsync(f)));

function growthFits(n, desiredHeight) {
  if (desiredHeight <= n.height + .1) return true;
  const p = n.parent;
  if (!p || p.type !== 'FRAME') return false;
  if (p.layoutMode === 'VERTICAL') {
    if (p.primaryAxisSizingMode === 'AUTO') return true;
    const visible = p.children.filter(c => c.visible && c.layoutPositioning !== 'ABSOLUTE');
    const used = visible.reduce((sum, c) => sum + c.height, 0) + Math.max(0, visible.length - 1) * p.itemSpacing + p.paddingTop + p.paddingBottom;
    return used + desiredHeight - n.height <= p.height + .1;
  }
  if (p.layoutMode === 'HORIZONTAL') return p.counterAxisSizingMode === 'AUTO' || desiredHeight <= p.height - p.paddingTop - p.paddingBottom + .1;
  if (n.y + desiredHeight > p.height + .1) return false;
  return !p.children.some(c => c !== n && c.visible && c.y >= n.y + n.height - .1 && c.y < n.y + desiredHeight && c.x < n.x + n.width && c.x + c.width > n.x);
}
const records = [];
for (const { n, t, icon, existingGroup, available } of specs) {
  const originalHeight = n.height;
  const reactionBefore = JSON.stringify(n.reactions);
  const textBefore = { width: t.width, height: t.height, mode: t.textAutoResize, x: t.x, y: t.y, sizingH: t.layoutSizingHorizontal, sizingV: t.layoutSizingVertical };
  // Measure with the existing font and size. No guessed font shrinking.
  t.textAutoResize = 'WIDTH_AND_HEIGHT';
  const naturalWidth = t.width;
  if (naturalWidth > available) { t.textAutoResize = 'HEIGHT'; t.resize(available, t.height); t.textAutoResize = 'HEIGHT'; }
  const labelWidth = Math.min(naturalWidth, available), labelHeight = t.height;
  const desiredHeight = Math.max(CONFIG.minHeight, originalHeight, Math.max(labelHeight, icon ? icon.height : 0) + 2 * CONFIG.paddingY);
  if (desiredHeight > 88 || !growthFits(n, desiredHeight)) {
    t.resize(textBefore.width, textBefore.height); t.textAutoResize = textBefore.mode; t.x = textBefore.x; t.y = textBefore.y;
    if (t.parent && 'layoutMode' in t.parent && t.parent.layoutMode !== 'NONE') { t.layoutSizingHorizontal = textBefore.sizingH; t.layoutSizingVertical = textBefore.sizingV; }
    diagnostics.push({ id: n.id, reason: 'Fixed parent cannot fit required height; unchanged', neededHeight: desiredHeight, previousHeight: n.height, labelWidth });
    continue;
  }
  const oldHeight = originalHeight;
  n.layoutMode = 'HORIZONTAL'; n.resize(n.width, desiredHeight);
  n.primaryAxisSizingMode = n.counterAxisSizingMode = 'FIXED'; n.primaryAxisAlignItems = n.counterAxisAlignItems = 'CENTER';
  n.paddingLeft = n.paddingRight = CONFIG.paddingX; n.paddingTop = n.paddingBottom = CONFIG.paddingY; n.itemSpacing = 0;
  let group = existingGroup;
  if (!group) { group = figma.createAutoLayout('HORIZONTAL'); created.push(group.id); n.appendChild(group); group.name = 'Action / Content group'; group.fills = []; }
  if (icon) { group.appendChild(icon); icon.layoutPositioning = 'AUTO'; touch(icon); }
  group.appendChild(t); t.layoutPositioning = 'AUTO';
  t.resize(Math.max(1, labelWidth), labelHeight); t.textAutoResize = 'HEIGHT'; t.textAlignHorizontal = 'CENTER';
  group.layoutMode = 'HORIZONTAL'; group.primaryAxisSizingMode = group.counterAxisSizingMode = 'AUTO';
  group.primaryAxisAlignItems = group.counterAxisAlignItems = 'CENTER'; group.itemSpacing = icon ? CONFIG.gap : 0;
  group.paddingLeft = group.paddingRight = group.paddingTop = group.paddingBottom = 0; group.layoutPositioning = 'AUTO';
  group.layoutSizingHorizontal = group.layoutSizingVertical = 'HUG';
  touch(n); touch(t); touch(group);
  if (JSON.stringify(n.reactions) !== reactionBefore) throw new Error('Unexpected reaction change: ' + n.id);
  records.push({ id: n.id, oldHeight, newHeight: n.height, labelWidth: t.width, labelHeight: t.height, groupId: group.id, reactionsPreserved: true });
}
return { pageId: page.id, createdNodeIds: created, mutatedNodeIds: [...affected], buttons: records, diagnostics };
