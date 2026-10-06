// Proposed owner-finance wireframes only. Set inspected template/button IDs.
// Six proposed screens per CONFIG.locale. No existing admin screens are changed and no financial values are invented.
const CONFIG = { pageId: '51:2', templateId: '51:3', locale: 'RU', buttonComponentId: '113:207', dryRun: true };
const COPY_EN = {
  "Обзор финансов": "Finance overview",
  "Начисления и поступления": "Accruals and receipts",
  "Основание записи": "Entry basis",
  "Счета сервиса": "Service accounts",
  "Реферальные обязательства": "Referral liabilities",
  "Расхождения сверки": "Reconciliation exceptions",
  "Нет данных": "No data",
  "Финансы сервиса": "Service finances",
  "Предложение · данные не подключены": "Proposed · data not connected",
  "Обзор": "Overview",
  "Журнал": "Journal",
  "Основание": "Basis",
  "Счета": "Accounts",
  "Обязательства": "Liabilities",
  "Сверка": "Reconciliation",
  "ФИНАНСЫ СЕРВИСА · ПРЕДЛОЖЕНИЕ": "SERVICE FINANCES · PROPOSED",
  "Данные пока не подключены. Это отдельный учёт сервиса; клиентские средства сюда не входят.": "Data is not connected yet. This is separate service accounting; client funds are excluded.",
  "Фильтры журнала": "Journal filters",
  "Состояние фильтров для проверки структуры. Источники и список ещё не подключены.": "Filter state for structure review. Data sources and the list are not connected yet.",
  "Период": "Period",
  "Всё время": "All time",
  "Площадка": "Venue",
  "Все площадки": "All venues",
  "Статус": "Status",
  "Все статусы": "All statuses",
  "Источник": "Source",
  "Все источники": "All sources",
  "Валюта": "Currency",
  "Исходная валюта": "Original currency",
  "Применить и вернуться в журнал": "Apply and return to journal",
  "Начислено": "Accrued",
  "Подтверждено к выплате": "Confirmed payable",
  "Фактически получено": "Actually received",
  "Ожидается": "Pending",
  "Возвраты": "Refunds",
  "Операционные расходы": "Operating expenses",
  "Сумма и исходная валюта уточняются после подключения источника.": "Amount and original currency become available after connecting the source.",
  "Открыть журнал": "Open journal",
  "Что считается результатом сервиса": "How service results are defined",
  "Начисления, денежный остаток и результат после расходов различаются. Реферальные обязательства учитываются отдельно. Итог без полного учёта не называется чистой прибылью.": "Accruals, cash balance and results after expenses are different measures. Referral liabilities are separate. An incomplete accounting result is not labelled net profit.",
  "Фильтры: всё время · все площадки · все статусы": "Filters: all time · all venues · all statuses",
  "Начисления и поступления пока не загружены": "Accruals and receipts have not been loaded",
  "Нет данных не означает нулевой доход. Начисления и фактические поступления будут связаны по подтверждённому основанию; агрегат не суммируется повторно с деталями.": "Missing data does not mean zero revenue. Accruals and receipts will share a verified basis; an aggregate is not added again to its underlying entries.",
  "Поля записи": "Entry fields",
  "Дата · Площадка · Источник · Сумма и валюта · Статус · Основание · Счёт получателя": "Date · Venue · Source · Amount and currency · Status · Basis · Receiving account",
  "Посмотреть структуру записи": "View entry structure",
  "Экспорт недоступен: источник данных ещё не подключён.": "Export is unavailable: the data source is not connected yet.",
  "Структура записи · без фактического начисления": "Entry structure · no actual accrual",
  "Источник дохода": "Revenue source",
  "Сумма и исходная валюта": "Amount and original currency",
  "Версия тарифа": "Tariff version",
  "Дата начисления": "Accrual date",
  "Дата поступления": "Receipt date",
  "Внешний идентификатор": "External identifier",
  "Не получен от источника": "Not provided by source",
  "Подтверждение платежа отсутствует. Запись не считается полученной без сверки; исправления добавляются отдельными связанными записями.": "Payment evidence is unavailable. The entry is not considered received without reconciliation; corrections are separate linked entries.",
  "Счёт получателя и подтверждение": "Receiving account and evidence",
  "Вернуться в журнал": "Back to journal",
  "Назначение": "Purpose",
  "Получение подтверждённого дохода": "Receiving verified service revenue",
  "Сеть и валюта": "Network and currency",
  "Не подтверждены": "Not verified",
  "Адрес / платёжный счёт": "Address / payment account",
  "Не задан": "Not configured",
  "Подтверждённый остаток": "Verified balance",
  "Последняя сверка": "Last reconciliation",
  "Источник не подключён": "Source not connected",
  "Ключи и секреты не показываются. История поступлений появится после подключения подтверждённого источника. Вывод и ручная выплата в этой ветке не доступны.": "Keys and secrets are not displayed. Receipt history requires a verified source. Withdrawals and manual payouts are unavailable in this branch.",
  "Перейти к расхождениям сверки": "Open reconciliation exceptions",
  "Вознаграждения приглашённых пользователей": "Rewards for referred users",
  "Начислено участникам": "Accrued to participants",
  "Фактически выплачено": "Actually paid",
  "Обязательства к исполнению": "Outstanding liabilities",
  "Возвраты и корректировки": "Refunds and corrections",
  "Согласованные условия реферальной программы должны быть связаны с версией правил. Начисления площадки сервису и выплаты участникам — разные записи. Демо не создаёт реальных выплат.": "Approved referral terms must reference a rules version. Venue rewards to the service and payouts to participants are separate entries. Demo does not create real payouts.",
  "Основание и история корректировок": "Basis and correction history",
  "Вернуться к обзору": "Back to overview",
  "Сверка ещё не запускалась": "Reconciliation has not run yet",
  "Нет данных о расхождениях — это не подтверждение совпадения остатков и начислений.": "Missing exception data does not confirm that balances and accruals match.",
  "Начислено, но не получено": "Accrued but not received",
  "Получено без найденного основания": "Received without a matching basis",
  "Исправленное начисление": "Corrected accrual",
  "Устаревший источник": "Stale source",
  "Требуется источник": "Source required",
  "Деталь будущего расхождения": "Future exception detail",
  "Объяснение": "Explanation",
  "Не получено": "Not available",
  "Ответственный": "Assignee",
  "Не назначен": "Unassigned",
  "История сверки": "Reconciliation history",
  "Нет подтверждённых проверок": "No verified checks",
  "Нельзя вручную подменять финансовую сумму. Поздняя корректировка и платёж сохраняют связь с исходным основанием.": "Financial amounts cannot be silently overwritten. Late corrections and payments retain their original basis.",
  "Посмотреть основание": "View basis"
};
const copy = s => CONFIG.locale === 'EN' ? (COPY_EN[s] || s) : s;
const page = await figma.getNodeByIdAsync(CONFIG.pageId);
if (!page || page.type !== 'PAGE') throw new Error('Missing inspected admin page');
await figma.setCurrentPageAsync(page);
const sectionName = 'Proposed · Owner finance · ' + CONFIG.locale + ' · 2026-10-02';
const existing = page.children.find(n => n.name === sectionName);
if (existing) return { existingSectionId: existing.id, frames: existing.children.map(n => ({ id: n.id, name: n.name })), createdNodeIds: [], mutatedNodeIds: [], diagnostics: ['Existing proposal retained. Inspect before any update.'] };
const template = CONFIG.templateId && await figma.getNodeByIdAsync(CONFIG.templateId);
if (!template || template.type !== 'FRAME') throw new Error('Set a verified admin template frame ID before running');
const buttonComponent = await figma.getNodeByIdAsync(CONFIG.buttonComponentId);
if (!buttonComponent || buttonComponent.type !== 'COMPONENT') throw new Error('Verified admin Button component is required');
const titles = ['Обзор финансов', 'Начисления и поступления', 'Основание записи', 'Счета сервиса', 'Реферальные обязательства', 'Расхождения сверки'];
if (CONFIG.dryRun) return { dryRun: true, templateId: template.id, buttonComponentId: buttonComponent.id, plannedScreens: titles, createdNodeIds: [], mutatedNodeIds: [] };
const fonts = new Map();
for (const n of [template, buttonComponent]) for (const t of n.findAllWithCriteria({ types: ['TEXT'] })) for (const s of t.getStyledTextSegments(['fontName'])) fonts.set(JSON.stringify(s.fontName), s.fontName);
await Promise.all([...fonts.values()].map(f => figma.loadFontAsync(f)));
const font = [...fonts.values()].find(f => f.family === 'Inter' && f.style === 'Regular') || [...fonts.values()][0];
if (!font) throw new Error('Template has no usable inspected font');
const vars = Object.fromEntries((await figma.variables.getLocalVariablesAsync()).map(v => [v.name, v]));
const styles = await figma.getLocalTextStylesAsync();
const owner = buttonComponent.parent && buttonComponent.parent.type === 'COMPONENT_SET' ? buttonComponent.parent : buttonComponent;
const labelKey = Object.entries(owner.componentPropertyDefinitions).find(([key, value]) => value.type === 'TEXT' && /label|text/i.test(key))?.[0];
if (!labelKey) throw new Error('Button requires an inspected editable label property');
const paint = key => {
  if (!vars[key]) throw new Error('Missing existing semantic token: ' + key);
  return figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: 0, g: 0, b: 0 } }, 'color', vars[key]);
};
// Validate required foundations before the first canvas mutation.
for (const key of ['color/bg/canvas', 'color/bg/surface', 'color/text/primary', 'color/text/secondary', 'color/border/default']) paint(key);
const created = new Set(), removed = [], links = [];
const dropTree = n => { for (const c of [n, ...('findAll' in n ? n.findAll(() => true) : [])]) { created.delete(c.id); removed.push(c.id); } n.remove(); };
const tr = n => (created.add(n.id), n);
const trTree = n => { created.add(n.id); if ('findAll' in n) for (const child of n.findAll(() => true)) created.add(child.id); return n; };
const floatToken = value => Object.values(vars).find(v => v.resolvedType === 'FLOAT' && v.name.startsWith('spacing/') && Object.values(v.valuesByMode).every(x => x === value));
const spacing = (n, property, value) => { n[property] = value; const token = floatToken(value); if (token) n.setBoundVariable(property, token); };
function box(parent, name, w, direction = 'VERTICAL', gap = 16, pad = 0, bg = null) {
  const n = tr(figma.createAutoLayout(direction)); parent.appendChild(n); n.name = name;
  n.resize(w, 1); n.primaryAxisSizingMode = direction === 'VERTICAL' ? 'AUTO' : 'FIXED'; n.counterAxisSizingMode = direction === 'VERTICAL' ? 'FIXED' : 'AUTO';
  spacing(n, 'itemSpacing', gap); for (const k of ['paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom']) spacing(n, k, pad);
  n.fills = bg ? [paint(bg)] : []; return n;
}
function text(parent, raw, size = 16, color = 'color/text/secondary', width = null) {
  const resolved = copy(raw);
  const n = tr(figma.createText()); parent.appendChild(n); n.name = resolved.slice(0, 56); n.fontName = font;
  const matchingStyle = styles.find(s => s.fontSize === size && s.fontName.family === font.family && s.fontName.style === font.style);
  if (matchingStyle) n.textStyleId = matchingStyle.id;
  n.fontSize = size; n.lineHeight = { unit: 'PIXELS', value: size >= 28 ? 38 : 24 }; n.characters = resolved; n.fills = [paint(color)]; n.textAutoResize = 'HEIGHT';
  n.resize(width || Math.max(1, parent.width - parent.paddingLeft - parent.paddingRight), n.height); n.textAutoResize = 'HEIGHT';
  // resize() resets sizing to FIXED. Restore text height after width is set.
  n.layoutSizingVertical = 'HUG';
  // Explicit widths form stable columns; body copy fills its vertical container.
  n.layoutSizingHorizontal = width === null ? 'FILL' : 'FIXED';
  return n;
}
function card(parent, name, width, heading, description = null) {
  const n = box(parent, name, width, 'VERTICAL', 12, 20, 'color/bg/surface'); n.strokes = [paint('color/border/default')]; n.strokeWeight = 1;
  const radius = vars['radius/lg']; if (radius) for (const k of ['topLeftRadius', 'topRightRadius', 'bottomLeftRadius', 'bottomRightRadius']) n.setBoundVariable(k, radius); else n.cornerRadius = 12;
  text(n, heading, 20, 'color/text/primary'); if (description) text(n, description); return n;
}
function row(parent, label, value = 'Нет данных') {
  const w = parent.width - parent.paddingLeft - parent.paddingRight;
  const n = box(parent, 'Поле / ' + label, w, 'HORIZONTAL', 16);
  text(n, label, 16, 'color/text/secondary', Math.max(1, w - 270)); const v = text(n, value, 16, 'color/text/primary', 254); v.textAlignHorizontal = 'RIGHT';
  n.counterAxisAlignItems = 'CENTER'; return n;
}
function action(parent, label, target, width = null) {
  const n = trTree(buttonComponent.createInstance()); parent.appendChild(n); n.name = 'Action / ' + label;
  n.setProperties({ [labelKey]: copy(label) }); n.resize(width || parent.width - parent.paddingLeft - parent.paddingRight, 48);
  for (const t of n.findAllWithCriteria({ types: ['TEXT'] })) {
    if (t.parent && 'layoutMode' in t.parent && t.parent.layoutMode !== 'NONE') {
      t.textAutoResize = 'HEIGHT'; t.layoutSizingHorizontal = 'FILL'; t.layoutSizingVertical = 'HUG'; t.textAlignHorizontal = 'CENTER';
    }
  }
  if (target !== null && target !== undefined) links.push([n, target]); return n;
}
const section = tr(figma.createSection()); page.appendChild(section); section.name = sectionName;
section.x = Math.max(0, ...page.children.filter(n => n !== section).map(n => n.x + n.width)) + 240; section.y = 100;
const W = Math.max(1280, template.width), H = 1280, navWidth = 224, inner = W - navWidth - 64;
section.resizeWithoutConstraints(3 * W + 160, 2 * H + 160);
const screens = titles.map((title, i) => {
  const n = trTree(template.clone()); section.appendChild(n); n.name = 'OF0' + (i + 1) + ' · ' + title + ' · ' + CONFIG.locale + ' · Proposed';
  n.resize(W, H); n.x = 40 + (i % 3) * (W + 40); n.y = 40 + Math.floor(i / 3) * (H + 40); n.clipsContent = true;
  const nav = n.children.find(c => c.type === 'FRAME' && c.name === 'Navigation');
  const main = n.children.find(c => c.type === 'FRAME' && c.name === 'Main content');
  if (!nav || !main) throw new Error('Template must retain inspected Navigation and Main content frames');
  for (const child of [...main.children]) dropTree(child);
  for (const child of [...nav.children]) dropTree(child);
  nav.layoutMode = 'VERTICAL'; nav.resize(navWidth, H); nav.primaryAxisSizingMode = nav.counterAxisSizingMode = 'FIXED';
  nav.paddingLeft = nav.paddingRight = nav.paddingTop = nav.paddingBottom = 20; nav.itemSpacing = 12;
  text(nav, 'shadow', 24, 'color/text/primary'); text(nav, 'Финансы сервиса', 18, 'color/text/primary'); text(nav, 'Предложение · данные не подключены', 14);
  for (const [j, short] of ['Обзор', 'Журнал', 'Основание', 'Счета', 'Обязательства', 'Сверка'].entries()) action(nav, short, j, navWidth - 40);
  main.name = 'Main content'; main.layoutMode = 'VERTICAL'; main.resize(W - navWidth, H); main.x = navWidth; main.y = 0;
  main.primaryAxisSizingMode = main.counterAxisSizingMode = 'FIXED'; main.paddingLeft = main.paddingRight = main.paddingTop = main.paddingBottom = 32; main.itemSpacing = 24; main.fills = [paint('color/bg/canvas')];
  text(main, 'ФИНАНСЫ СЕРВИСА · ПРЕДЛОЖЕНИЕ', 14);
  text(main, title, 32, 'color/text/primary');
  text(main, 'Данные пока не подключены. Это отдельный учёт сервиса; клиентские средства сюда не входят.');
  const body = box(main, 'Содержимое финансов', inner, 'VERTICAL', 20); return { frame: n, body };
});
const filters = tr(figma.createAutoLayout('VERTICAL')); section.appendChild(filters); filters.name = 'OF · Фильтры · Предложение'; filters.resize(640, 600); filters.x = 40; filters.y = 2 * H + 160;
filters.primaryAxisSizingMode = 'AUTO'; filters.counterAxisSizingMode = 'FIXED'; filters.paddingLeft = filters.paddingRight = filters.paddingTop = filters.paddingBottom = 24; filters.itemSpacing = 16; filters.fills = [paint('color/bg/surface')]; filters.cornerRadius = 16;
text(filters, 'Фильтры журнала', 28, 'color/text/primary'); text(filters, 'Состояние фильтров для проверки структуры. Источники и список ещё не подключены.');
for (const [label, value] of [['Период', 'Всё время'], ['Площадка', 'Все площадки'], ['Статус', 'Все статусы'], ['Источник', 'Все источники'], ['Валюта', 'Исходная валюта']]) row(filters, label, value);
action(filters, 'Применить и вернуться в журнал', 1);
// Expand section to include the auxiliary filter state without overlapping screens.
section.resizeWithoutConstraints(section.width, 2 * H + filters.height + 220);

const overview = screens[0].body;
for (const labels of [['Начислено', 'Подтверждено к выплате', 'Фактически получено'], ['Ожидается', 'Возвраты', 'Операционные расходы']]) {
  const grid = box(overview, 'Показатели / ' + labels.join(' · '), inner, 'HORIZONTAL', 16);
  for (const label of labels) { const c = card(grid, 'Показатель / ' + label, (inner - 32) / 3, label); text(c, 'Нет данных', 28, 'color/text/primary'); text(c, 'Сумма и исходная валюта уточняются после подключения источника.'); action(c, 'Открыть журнал', 1); }
}
const scope = card(overview, 'Границы финансового результата', inner, 'Что считается результатом сервиса');
text(scope, 'Начисления, денежный остаток и результат после расходов различаются. Реферальные обязательства учитываются отдельно. Итог без полного учёта не называется чистой прибылью.'); action(scope, 'Реферальные обязательства', 4);

const list = screens[1].body;
action(list, 'Фильтры: всё время · все площадки · все статусы', 'filters');
const empty = card(list, 'Журнал / источник не подключён', inner, 'Начисления и поступления пока не загружены');
text(empty, 'Нет данных не означает нулевой доход. Начисления и фактические поступления будут связаны по подтверждённому основанию; агрегат не суммируется повторно с деталями.');
const columns = card(list, 'Структура будущего журнала', inner, 'Поля записи');
text(columns, 'Дата · Площадка · Источник · Сумма и валюта · Статус · Основание · Счёт получателя');
action(columns, 'Посмотреть структуру записи', 2);
text(list, 'Экспорт недоступен: источник данных ещё не подключён.');

const detail = screens[2].body;
const basis = card(detail, 'Основание / пример структуры', inner, 'Структура записи · без фактического начисления');
for (const label of ['Источник дохода', 'Площадка', 'Сумма и исходная валюта', 'Версия тарифа', 'Дата начисления', 'Дата поступления', 'Внешний идентификатор']) row(basis, label);
row(basis, 'Статус', 'Не получен от источника'); text(basis, 'Подтверждение платежа отсутствует. Запись не считается полученной без сверки; исправления добавляются отдельными связанными записями.');
action(detail, 'Счёт получателя и подтверждение', 3); action(detail, 'Вернуться в журнал', 1);

const accounts = screens[3].body;
for (const venue of ['Polymarket', 'Limitless']) {
  const c = card(accounts, 'Счёт сервиса / ' + venue, inner, venue + (CONFIG.locale === 'EN' ? ' · service revenue recipient' : ' · получатель дохода сервиса'));
  row(c, 'Назначение', 'Получение подтверждённого дохода'); row(c, 'Сеть и валюта', 'Не подтверждены'); row(c, 'Адрес / платёжный счёт', 'Не задан'); row(c, 'Подтверждённый остаток'); row(c, 'Последняя сверка', 'Источник не подключён');
}
text(accounts, 'Ключи и секреты не показываются. История поступлений появится после подключения подтверждённого источника. Вывод и ручная выплата в этой ветке не доступны.'); action(accounts, 'Перейти к расхождениям сверки', 5);

const liabilities = screens[4].body;
const obligation = card(liabilities, 'Реферальные обязательства', inner, 'Вознаграждения приглашённых пользователей');
for (const label of ['Начислено участникам', 'Подтверждено к выплате', 'Фактически выплачено', 'Обязательства к исполнению', 'Возвраты и корректировки']) row(obligation, label);
text(obligation, 'Согласованные условия реферальной программы должны быть связаны с версией правил. Начисления площадки сервису и выплаты участникам — разные записи. Демо не создаёт реальных выплат.');
action(liabilities, 'Основание и история корректировок', 2); action(liabilities, 'Вернуться к обзору', 0);

const reconciliation = screens[5].body;
const exceptions = card(reconciliation, 'Расхождения / источник не подключён', inner, 'Сверка ещё не запускалась');
text(exceptions, 'Нет данных о расхождениях — это не подтверждение совпадения остатков и начислений.');
for (const label of ['Начислено, но не получено', 'Получено без найденного основания', 'Исправленное начисление', 'Устаревший источник']) row(exceptions, label, 'Требуется источник');
const log = card(reconciliation, 'История проверки', inner, 'Деталь будущего расхождения');
row(log, 'Объяснение', 'Не получено'); row(log, 'Ответственный', 'Не назначен'); row(log, 'История сверки', 'Нет подтверждённых проверок');
text(log, 'Нельзя вручную подменять финансовую сумму. Поздняя корректировка и платёж сохраняют связь с исходным основанием.'); action(reconciliation, 'Посмотреть основание', 2);

for (const [n, target] of links) {
  const destinationId = target === 'filters' ? filters.id : screens[target].frame.id;
  let self = false;
  for (let ancestor = n; ancestor && ancestor.type !== 'PAGE'; ancestor = ancestor.parent) if (ancestor.id === destinationId) self = true;
  // Figma forbids NAVIGATE to the containing screen. Current-page nav is inert.
  if (self) { await n.setReactionsAsync([]); continue; }
  await n.setReactionsAsync([{ trigger: { type: 'ON_CLICK' }, actions: [{ type: 'NODE', destinationId, navigation: target === 'filters' ? 'OVERLAY' : 'NAVIGATE', transition: null, resetScrollPosition: true }] }]);
}
return { sectionId: section.id, createdNodeIds: [...created], removedNodeIds: removed, mutatedNodeIds: [], screens: screens.map((s, i) => ({ id: s.frame.id, name: s.frame.name, contentHeight: s.body.height, screenHeight: s.frame.height })), filterId: filters.id, linkedActionCount: links.length, diagnostics: ['Proposed wireframes only. No live data, payment instruction, payout action, or tariff assumptions.'] };
