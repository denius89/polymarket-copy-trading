// Native prototype state only. One verified page per call; root supplies all IDs.
// Does not set live-account data or replace ambiguous Back actions.
const CONFIG = {
  pageId: '33:2', locale: 'RU', device: 'mobile', dryRun: true,
  variables: { stage: null, auth: null, balance: null, frequency: null },
  masters: { mobileHeader: '819:294', desktopHeader: '819:330', mobileNav: '819:312' },
  routes: {
    home: { before: null, empty: null, active: null },
    funds: { before: null, empty: null, active: null },
    positions: { before: null, empty: null, active: null },
    activity: { before: null, empty: null, active: null },
    management: { before: null, empty: null, active: null },
    catalog: null, profile: null, notifications: null, genericEmailEntry: null,
  },
  publicHeaderScreenIds: [], scopeScreenIds: [],
  // Exact audited Back/Return nodes only: {nodeId, role:'home'|'catalog'|'management'}.
  explicitActions: [],
  // Optional exact summary controls: {nodeId,value:'weekly'|'daily'}.
  frequencyActions: [],
};
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing inspected page');
await figma.setCurrentPageAsync(page);
const getVar = async (id, type, key) => {
  const variable = id && await figma.variables.getVariableByIdAsync(id);
  if (!variable || variable.resolvedType !== type) throw new Error('Required ' + type + ' prototype variable missing: ' + key);
  return variable;
};
const stage = await getVar(CONFIG.variables.stage, 'STRING', 'stage');
const auth = await getVar(CONFIG.variables.auth, 'BOOLEAN', 'auth');
const balance = await getVar(CONFIG.variables.balance, 'STRING', 'balance');
const frequency = CONFIG.frequencyActions.length ? await getVar(CONFIG.variables.frequency, 'STRING', 'frequency') : null;
const flattenIds = v => typeof v === 'string' ? [v] : v && typeof v === 'object' ? Object.values(v).flatMap(flattenIds) : [];
for (const id of new Set(flattenIds(CONFIG.routes))) if (!(await figma.getNodeByIdAsync(id))) throw new Error('Missing context destination: ' + id);
for (const { nodeId } of [...CONFIG.explicitActions, ...CONFIG.frequencyActions]) if (!(await figma.getNodeByIdAsync(nodeId))) throw new Error('Missing explicitly audited control: ' + nodeId);
for (const item of CONFIG.frequencyActions) if (!['weekly', 'daily'].includes(item.value)) throw new Error('Invalid summary frequency');
const scope = n => {
  if (!CONFIG.scopeScreenIds.length) return true;
  for (let x = n; x && x.type !== 'PAGE'; x = x.parent) if (CONFIG.scopeScreenIds.includes(x.id)) return true;
  return false;
};
const samePage = n => { for (let x = n; x; x = x.parent) if (x.id === page.id) return true; return false; };
const headersToReplace = [];
if (CONFIG.device === 'mobile') for (const id of CONFIG.publicHeaderScreenIds) {
  const screen = await figma.getNodeByIdAsync(id);
  if (!screen || screen.type !== 'FRAME' || !samePage(screen)) throw new Error('Invalid public-header screen: ' + id);
  const header = screen.children.find(n => n.type === 'FRAME' && (n.name === 'App bar' || /^Header\s*\//.test(n.name)));
  if (!header) throw new Error('Public header wrapper not found: ' + id);
  headersToReplace.push(header);
}
const master = headersToReplace.length ? await figma.getNodeByIdAsync(CONFIG.masters.mobileHeader) : null;
if (headersToReplace.length && (!master || master.type !== 'COMPONENT')) throw new Error('Shared mobile header master missing');
const alias = (variable, type) => ({ type: 'VARIABLE_ALIAS', resolvedType: type, value: { type: 'VARIABLE_ALIAS', id: variable.id } });
const literal = (value, type) => ({ type, resolvedType: type, value });
const equals = (variable, value, type) => ({ type: 'EXPRESSION', resolvedType: 'BOOLEAN', value: { expressionFunction: 'EQUALS', expressionArguments: [alias(variable, type), literal(value, type)] } });
const nav = destinationId => ({ type: 'NODE', destinationId, navigation: 'NAVIGATE', transition: null, resetScrollPosition: true });
const ancestorHas = (n, id) => { for (let x = n; x && x.type !== 'PAGE'; x = x.parent) if (x.id === id) return true; return false; };
const safeNav = (source, id) => !id || ancestorHas(source, id) ? [] : [nav(id)];
const stageAction = (source, role) => {
  const destinations = CONFIG.routes[role];
  if (typeof destinations === 'string') return safeNav(source, destinations);
  if (!destinations) return null;
  const firstVisit = destinations.before || destinations.firstVisit;
  const fresh = destinations.empty || destinations.fresh;
  if (!firstVisit || !fresh || !destinations.active) return null;
  // Provider read-back retains only IF/ELSE per CONDITIONAL; a third block is lost.
  // Do not replace these three flat actions with one 3-block or nested conditional.
  return [['before', firstVisit], ['empty', fresh], ['active', destinations.active]].map(([value, target]) => ({
    type: 'CONDITIONAL', conditionalBlocks: [
      { condition: equals(stage, value, 'STRING'), actions: safeNav(source, target) },
      { actions: [] },
    ],
  }));
};
const avatarActions = source => {
  if (!CONFIG.routes.profile || !CONFIG.routes.genericEmailEntry) return null;
  return [{ type: 'CONDITIONAL', conditionalBlocks: [
    { condition: equals(auth, true, 'BOOLEAN'), actions: safeNav(source, CONFIG.routes.profile) },
    { actions: safeNav(source, CONFIG.routes.genericEmailEntry) },
  ] }];
};
const role = n => /^Nav\/Home$|^Navigation\s*\/\s*(Overview|Home)$/.test(n.name) ? 'home' :
  /^Nav\/Traders$|^Navigation\s*\/\s*Traders$/.test(n.name) ? 'catalog' :
  /^Nav\/Positions$|^Navigation\s*\/\s*Positions$/.test(n.name) ? 'positions' :
  /^Nav\/Activity$|^Navigation\s*\/\s*Activity$/.test(n.name) ? 'activity' :
  /^(?:Balance\s*\/\s*Open wallets|Button\/Balance)/.test(n.name) ? 'funds' :
  /^(?:Profile\s*\/\s*Open account|Button\/Profile avatar)/.test(n.name) ? 'avatar' :
  /^Button\/Notifications$/.test(n.name) ? 'notifications' : null;
const existingCandidates = page.findAll(n => scope(n) && role(n) !== null);
if (CONFIG.dryRun) return { dryRun: true, replaceHeaderIds: headersToReplace.map(n => n.id), roleControlCount: existingCandidates.length, explicitActionCount: CONFIG.explicitActions.length, createdNodeIds: [], mutatedNodeIds: [] };
const fonts = new Map();
for (const n of [master, ...headersToReplace, ...existingCandidates].filter(Boolean)) for (const t of n.type === 'TEXT' ? [n] : ('findAllWithCriteria' in n ? n.findAllWithCriteria({ types: ['TEXT'] }) : [])) for (const s of t.getStyledTextSegments(['fontName'])) fonts.set(JSON.stringify(s.fontName), s.fontName);
await Promise.all([...fonts.values()].map(font => figma.loadFontAsync(font)));
const created = new Set(), mutated = new Set(), removed = [], diagnostics = [], wired = [];
const visibilityBindings = [];
const tree = n => [n, ...('findAll' in n ? n.findAll(() => true) : [])];
for (const header of headersToReplace) {
  const already = header.children.find(n => n.type === 'INSTANCE' && n.name === 'Shared public header / context');
  if (already) continue;
  for (const child of [...header.children]) { for (const n of tree(child)) removed.push(n.id); child.remove(); }
  const instance = master.createInstance(); header.appendChild(instance); instance.name = 'Shared public header / context';
  instance.resize(header.width, 44); if (header.layoutMode !== 'NONE') { instance.layoutSizingHorizontal = 'FILL'; instance.layoutSizingVertical = 'FIXED'; }
  header.resize(header.width, 44); for (const n of tree(instance)) created.add(n.id); mutated.add(header.id);
}
const controls = page.findAll(n => scope(n) && role(n) !== null);
for (const control of controls) {
  const kind = role(control);
  if (kind === 'funds' || kind === 'notifications') visibilityBindings.push(control);
  if (kind === 'funds') {
    const texts = control.findAllWithCriteria({ types: ['TEXT'] });
    const value = texts.find(t => /Available balance|Balance value|^[\d$—]|Нет данных|No data/.test(t.name) || /\d[,.]\d|\$|Нет данных|No data/.test(t.characters)) || texts[texts.length - 1];
    if (value) { value.setBoundVariable('characters', balance); mutated.add(value.id); }
    else diagnostics.push({ id: control.id, issue: 'Balance text layer not found' });
  }
  const actions = kind === 'avatar' ? avatarActions(control) : kind === 'notifications' ? safeNav(control, CONFIG.routes.notifications) : stageAction(control, kind);
  if (actions === null) { diagnostics.push({ id: control.id, issue: 'Incomplete context routes for role ' + kind }); continue; }
  await control.setReactionsAsync(actions.length ? [{ trigger: { type: 'ON_CLICK' }, actions }] : []); mutated.add(control.id); wired.push(control.id);
}
for (const item of CONFIG.explicitActions) {
  const node = await figma.getNodeByIdAsync(item.nodeId);
  if (!samePage(node)) throw new Error('Explicit return action belongs to another page');
  const actions = stageAction(node, item.role);
  if (actions === null) { diagnostics.push({ id: node.id, issue: 'Incomplete explicit return route' }); continue; }
  await node.setReactionsAsync(actions.length ? [{ trigger: { type: 'ON_CLICK' }, actions }] : []); mutated.add(node.id); wired.push(node.id);
}
for (const item of CONFIG.frequencyActions) {
  if (!['weekly', 'daily'].includes(item.value)) throw new Error('Invalid summary frequency');
  const node = await figma.getNodeByIdAsync(item.nodeId);
  if (!samePage(node)) throw new Error('Frequency control belongs to another page');
  await node.setReactionsAsync([{ trigger: { type: 'ON_CLICK' }, actions: [{ type: 'SET_VARIABLE', variableId: frequency.id, variableValue: literal(item.value, 'STRING') }] }]); mutated.add(node.id);
}
// Apply visibility last: Auth=false must not hide descendants before binding text/routes.
for (const control of visibilityBindings) { control.setBoundVariable('visible', auth); mutated.add(control.id); }
return { pageId: page.id, createdNodeIds: [...created], mutatedNodeIds: [...mutated].filter(id => !created.has(id)), removedNodeIds: removed, replacedHeaderCount: headersToReplace.length, wiredControlCount: wired.length, diagnostics, state: 'Native review variables control navigation only; no live system integration.' };
