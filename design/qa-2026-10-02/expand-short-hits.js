// Exact audit IDs only. No guessed target discovery and no reaction migration.
const CONFIG = { pageId: '33:2', nodeIds: [], minHeight: 44, minWidth: 44, dryRun: true };
const minHeight = CONFIG.minHeight ?? 44, minWidth = CONFIG.minWidth ?? 44;
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing inspected page');
await figma.setCurrentPageAsync(page);
const targets = [], diagnostics = [], changed = new Set();
const belongs = n => { for (let x = n; x; x = x.parent) if (x.id === page.id) return true; return false; };
const childrenInFlow = p => p.children.filter(c => c.visible && c.layoutPositioning !== 'ABSOLUTE');
function fitsAncestors(node, width, height) {
  let child = node, dw = width - node.width, dh = height - node.height;
  for (let p = node.parent; p && p.type !== 'PAGE' && p.type !== 'SECTION'; child = p, p = p.parent) {
    if (Math.abs(dw) < .1 && Math.abs(dh) < .1) return null;
    if (p.type !== 'FRAME') return 'Non-frame ancestor requires manual layout';
    const proposedW = child.width + dw, proposedH = child.height + dh;
    const innerW = p.width - p.paddingLeft - p.paddingRight, innerH = p.height - p.paddingTop - p.paddingBottom;
    if (p.layoutMode === 'VERTICAL' || p.layoutMode === 'HORIZONTAL') {
      const vertical = p.layoutMode === 'VERTICAL', nodes = childrenInFlow(p);
      const used = nodes.reduce((a, c) => a + (vertical ? c.height : c.width), 0) + Math.max(0, nodes.length - 1) * p.itemSpacing;
      const primaryGrowth = vertical ? dh : dw, crossSize = vertical ? proposedW : proposedH;
      const primarySpace = vertical ? innerH : innerW, crossSpace = vertical ? innerW : innerH;
      const scrollablePrimary = vertical && ['VERTICAL', 'BOTH'].includes(p.overflowDirection);
      if (p.primaryAxisSizingMode === 'FIXED' && used + primaryGrowth > primarySpace + .1 && !scrollablePrimary) return 'Fixed auto-layout parent has insufficient space';
      if (p.counterAxisSizingMode === 'FIXED' && crossSize > crossSpace + .1) return 'Fixed cross-axis cannot fit the hit area';
      const nextPrimary = p.primaryAxisSizingMode === 'AUTO' ? primaryGrowth : 0;
      const nextCross = p.counterAxisSizingMode === 'AUTO' ? Math.max(0, crossSize - crossSpace) : 0;
      dw = vertical ? nextCross : nextPrimary; dh = vertical ? nextPrimary : nextCross;
    } else {
      if (child.x + proposedW > p.width + .1 || child.y + proposedH > p.height + .1) return 'Absolute parent bounds would be exceeded';
      const area = (other, w, h) => Math.max(0, Math.min(child.x + w, other.x + other.width) - Math.max(child.x, other.x)) * Math.max(0, Math.min(child.y + h, other.y + other.height) - Math.max(child.y, other.y));
      if (p.children.some(c => c !== child && c.visible && area(c, proposedW, proposedH) > area(c, child.width, child.height) + .1)) return 'Expanded hit would overlap a sibling';
      dw = dh = 0;
    }
  }
  return null;
}
for (const id of CONFIG.nodeIds || []) {
  const n = await figma.getNodeByIdAsync(id);
  if (!n || !belongs(n)) throw new Error('Audited target missing from requested page: ' + id);
  if (!['TEXT', 'FRAME'].includes(n.type)) { diagnostics.push({ id, reason: 'Only frame/text reaction owners can safely expand without scaling icons' }); continue; }
  if (!('reactions' in n) || !n.reactions.some(r => ['ON_CLICK', 'ON_PRESS', 'ON_DRAG'].includes(r.trigger?.type))) { diagnostics.push({ id, reason: 'No current click/press/drag action' }); continue; }
  const width = Math.max(minWidth, n.width), height = Math.max(minHeight, n.height);
  const issue = fitsAncestors(n, width, height);
  if (issue) { diagnostics.push({ id, reason: issue, proposedWidth: width, proposedHeight: height }); continue; }
  targets.push({ node: n, width, height });
}
if (CONFIG.dryRun) return { dryRun: true, expandableNodeIds: targets.map(t => t.node.id), diagnostics, createdNodeIds: [], mutatedNodeIds: [] };
const fonts = new Map();
for (const { node } of targets) for (const t of node.type === 'TEXT' ? [node] : node.findAllWithCriteria({ types: ['TEXT'] })) for (const s of t.getStyledTextSegments(['fontName'])) fonts.set(JSON.stringify(s.fontName), s.fontName);
await Promise.all([...fonts.values()].map(f => figma.loadFontAsync(f)));
const expanded = [];
for (const { node: n, width, height } of targets) {
  // Recheck after earlier changes consumed shared-parent space.
  const issue = fitsAncestors(n, width, height);
  if (issue) { diagnostics.push({ id: n.id, reason: issue }); continue; }
  const before = JSON.stringify(n.reactions), oldWidth = n.width, oldHeight = n.height;
  const oldHorizontal = n.layoutSizingHorizontal;
  n.resize(width, height);
  if (n.type === 'TEXT') { n.textAutoResize = 'NONE'; n.textAlignVertical = 'CENTER'; }
  else if (n.layoutMode === 'HORIZONTAL' || n.layoutMode === 'VERTICAL') {
    n.counterAxisAlignItems = 'CENTER';
    if (/^(Action|Button)[ /]/.test(n.name)) n.primaryAxisAlignItems = 'CENTER';
    n.primaryAxisSizingMode = n.counterAxisSizingMode = 'FIXED';
  } else if (n.children.length) {
    const visible = n.children.filter(c => c.visible);
    if (visible.length) {
      const top = Math.min(...visible.map(c => c.y)), bottom = Math.max(...visible.map(c => c.y + c.height));
      const delta = (height - (bottom - top)) / 2 - top;
      for (const child of visible) { child.y += delta; changed.add(child.id); }
    }
  }
  if (oldHorizontal === 'FILL' && n.parent && 'layoutMode' in n.parent && n.parent.layoutMode !== 'NONE') n.layoutSizingHorizontal = 'FILL';
  if (JSON.stringify(n.reactions) !== before) throw new Error('Reaction changed unexpectedly: ' + n.id);
  changed.add(n.id); expanded.push({ id: n.id, oldWidth, oldHeight, width: n.width, height: n.height });
}
return { createdNodeIds: [], mutatedNodeIds: [...changed], expanded, diagnostics };
