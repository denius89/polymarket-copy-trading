// Read-only QA. Run one invocation for each verified user page:
// mobile RU 33:2, mobile EN 29:2, desktop RU 205:2, desktop EN 186:2.
// Never switch multiple pages inside one use_figma invocation.
const CONFIG = { pageId: '33:2', minHitHeight: 44, minHitWidth: 44, tinyTextHeight: 1.1, includeHidden: false, baselineFrameIds: [], startFrameIds: [] };
const minHitHeight = Number.isFinite(CONFIG.minHitHeight) ? CONFIG.minHitHeight : 44;
const minHitWidth = Number.isFinite(CONFIG.minHitWidth) ? CONFIG.minHitWidth : 44;
const tinyTextHeight = Number.isFinite(CONFIG.tinyTextHeight) ? CONFIG.tinyTextHeight : 1.1;
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing inspected page');
await figma.setCurrentPageAsync(page);
const visible = n => {
  if (CONFIG.includeHidden) return true;
  for (let x = n; x && x.type !== 'PAGE'; x = x.parent) if ('visible' in x && !x.visible) return false;
  return true;
};
const nearestScreen = n => {
  let best = null;
  for (let x = n; x && x.type !== 'PAGE'; x = x.parent) if (x.type === 'FRAME' && x.width >= 300 && x.height >= 400) best = x;
  return best ? { id: best.id, name: best.name } : null;
};
const detail = n => ({ id: n.id, name: n.name, type: n.type, width: n.width, height: n.height, screen: nearestScreen(n) });
const nodes = page.findAll(() => true);
const tinyTexts = nodes.filter(n => n.type === 'TEXT' && visible(n) && n.characters.trim() && n.height <= tinyTextHeight).map(n => ({ ...detail(n), text: n.characters.slice(0, 160), textAutoResize: n.textAutoResize, layoutSizingVertical: n.layoutSizingVertical }));
const shortHits = [], edges = [], missingDestinations = [], allReactions = [];
const targetCache = new Map();
function* actionTree(actions, path = []) {
  for (const [index, action] of actions.entries()) {
    const currentPath = [...path, index];
    yield { action, path: currentPath };
    if (action.type === 'CONDITIONAL') for (const [blockIndex, block] of (action.conditionalBlocks || []).entries()) {
      yield* actionTree(block.actions || [], [...currentPath, 'block', blockIndex]);
    }
  }
}
for (const n of nodes) {
  if (!('reactions' in n) || !n.reactions.length) continue;
  for (const reaction of n.reactions) {
    const actions = reaction.actions || (reaction.action ? [reaction.action] : []);
    if (visible(n) && ['ON_CLICK', 'ON_PRESS', 'ON_DRAG'].includes(reaction.trigger?.type) && (n.height < minHitHeight || n.width < minHitWidth)) {
      if (!shortHits.some(x => x.id === n.id)) shortHits.push({ ...detail(n), trigger: reaction.trigger.type });
    }
    for (const { action, path } of actionTree(actions)) {
      allReactions.push({ sourceId: n.id, trigger: reaction.trigger?.type, actionType: action.type });
      if (action.type !== 'NODE' || !action.destinationId) continue;
      const destinationId = action.destinationId;
      if (!targetCache.has(destinationId)) targetCache.set(destinationId, await figma.getNodeByIdAsync(destinationId));
      const target = targetCache.get(destinationId);
      const screen = nearestScreen(n), destinationScreen = target ? nearestScreen(target) : null;
      const edge = { sourceId: n.id, sourceName: n.name, sourceScreenId: screen?.id || null, destinationId, destinationScreenId: destinationScreen?.id || (target && target.type === 'FRAME' ? target.id : null), navigation: action.navigation, branchPath: path, screen, sourceVisible: visible(n) };
      edges.push(edge);
      if (!target) missingDestinations.push(edge);
    }
  }
}
const horizontalTextOverflows = [];
for (const t of nodes.filter(n => n.type === 'TEXT' && visible(n) && n.characters.trim())) {
  const textBounds = t.absoluteBoundingBox;
  if (!textBounds) continue;
  const left = textBounds.x, right = textBounds.x + textBounds.width;
  let allowedLeft = -Infinity, allowedRight = Infinity;
  const clipIds = [];
  for (let ancestor = t.parent; ancestor && ancestor.type !== 'PAGE'; ancestor = ancestor.parent) {
    if (!('clipsContent' in ancestor) || !ancestor.clipsContent || !ancestor.absoluteBoundingBox) continue;
    const bounds = ancestor.absoluteBoundingBox;
    allowedLeft = Math.max(allowedLeft, bounds.x); allowedRight = Math.min(allowedRight, bounds.x + bounds.width); clipIds.push(ancestor.id);
  }
  if (clipIds.length && (left < allowedLeft - .5 || right > allowedRight + .5)) horizontalTextOverflows.push({ ...detail(t), text: t.characters.slice(0, 120), leftOverflow: Math.max(0, allowedLeft - left), rightOverflow: Math.max(0, right - allowedRight), clippingAncestorIds: clipIds });
}
const baselineIds = [...new Set(CONFIG.baselineFrameIds || [])], retained = [], missingBaseline = [], changedBaselineType = [];
for (const id of baselineIds) {
  const node = await figma.getNodeByIdAsync(id);
  if (!node) missingBaseline.push(id);
  else if (node.type !== 'FRAME') changedBaselineType.push({ id, type: node.type });
  else retained.push(id);
}
const adjacency = new Map();
for (const edge of edges) if (edge.sourceScreenId && edge.destinationScreenId) {
  if (!adjacency.has(edge.sourceScreenId)) adjacency.set(edge.sourceScreenId, new Set());
  adjacency.get(edge.sourceScreenId).add(edge.destinationScreenId);
}
const starts = CONFIG.startFrameIds || [], reachable = new Set(starts), queue = [...starts];
while (queue.length) { const current = queue.shift(); for (const next of adjacency.get(current) || []) if (!reachable.has(next)) { reachable.add(next); queue.push(next); } }
const unreachableBaseline = starts.length ? retained.filter(id => !reachable.has(id)) : [];
const tops = page.children.filter(n => n.type === 'SECTION' && visible(n));
const topSectionOverlaps = [];
for (let i = 0; i < tops.length; i++) for (let j = i + 1; j < tops.length; j++) {
  const a = tops[i], b = tops[j];
  const width = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
  const height = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
  if (width > .5 && height > .5) topSectionOverlaps.push({ a: { id: a.id, name: a.name }, b: { id: b.id, name: b.name }, overlapWidth: width, overlapHeight: height });
}
return {
  pageId: page.id, pageName: page.name, inspectedNodeCount: nodes.length, thresholds: { minHitHeight, minHitWidth, tinyTextHeight },
  counts: { deletedLinks: missingDestinations.length, topSectionOverlaps: topSectionOverlaps.length, hitHeightBelow44: shortHits.filter(x => x.height < minHitHeight).length, hitWidthBelow44: shortHits.filter(x => x.width < minHitWidth).length, shortHits: shortHits.length, textHeightOnePixel: tinyTexts.length, horizontalTextOverflows: horizontalTextOverflows.length, reactionCount: allReactions.length, linkedTargets: targetCache.size, graphEdges: edges.length, baselineFrames: baselineIds.length, baselineRetained: retained.length, baselineMissing: missingBaseline.length, baselineTypeChanged: changedBaselineType.length, unreachableBaseline: unreachableBaseline.length },
  missingDestinations: missingDestinations.slice(0, 40), topSectionOverlaps: topSectionOverlaps.slice(0, 40), shortHits: shortHits.slice(0, 40), tinyTexts: tinyTexts.slice(0, 40), horizontalTextOverflows: horizontalTextOverflows.slice(0, 40), graph: edges.slice(0, 40),
  baseline: { frameIds: baselineIds, retainedIds: retained, missingIds: missingBaseline.slice(0, 40), changedTypes: changedBaselineType.slice(0, 40), startIds: starts, unreachableIds: unreachableBaseline.slice(0, 40) },
  createdNodeIds: [], mutatedNodeIds: [],
  limitations: ['Detailed finding lists and graph are capped at 40; counts and reachability use the full inspected graph.', 'Conditional branches are all traversed structurally; reachability does not prove every variable-state combination.', 'Short hits are actual reaction owners, including clickable text; visual siblings do not enlarge their hit area.', 'Horizontal text overflow uses visible text boxes intersected with clipping ancestors; group/vector geometry is excluded.', 'Section overlap checks canvas organization, not overlap of elements inside screens.', 'No screen-reader, keyboard, runtime layout, financial-data or API validation is performed.'],
};
