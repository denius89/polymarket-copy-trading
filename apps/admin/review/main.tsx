import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter, Link, useLocation, useSearchParams } from 'react-router-dom';
import { Card, Notice } from '@cct/ui';
import { assignments, users, type Assignment, type Issue, type UserFixture } from './fixtures';
import { Operations, operationSections, type OperationSection } from './operations';
import { Reconciliation, type ReconciliationRuns } from './reconciliation';
import '../src/admin.css';
import './review.css';

const supportedAssignments = Object.keys(assignments) as Assignment[];
const dates = ['2026-10-17', '2026-10-18', '2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23'];
const status: Record<Issue, readonly [string, string]> = {
  ok: ['Без проблем', 'No issues'],
  unknown: ['Результат неизвестен', 'Outcome unknown'],
  partial: ['Частичное исполнение', 'Partially filled'],
  stale: ['Данные устарели', 'Stale data'],
};

function Review() {
  const { pathname } = useLocation();
  const [params, setParams] = useSearchParams();
  const [menuOpen, setMenuOpen] = useState(false);
  const [runs, setRuns] = useState<ReconciliationRuns>({});
  const en = params.get('lang') === 'en';
  const role = supportedAssignments.find(value => value === params.get('assignment')) ?? 'lead';
  const actor = assignments[role][en ? 1 : 0];
  const allowed = role !== 'marketing';
  const money = role !== 'audit' && role !== 'limited' && allowed;
  const t = (ru: string, english: string) => en ? english : ru;
  const [section, entity, subpage] = pathname.split('/').slice(1);
  const venues = ['Polymarket', 'Limitless'];
  const venue = params.get('venue') || '';
  const query = params.get('q') || '';
  const attention = params.get('issue') === 'attention';
  const sort = params.get('sort') || 'name';
  const from = params.get('from') || dates[0];
  const to = params.get('to') || dates[dates.length - 1];
  const scoped = !allowed ? [] : users.filter(user => role !== 'limited' || user.id === 'U-DEMO-002');
  const selected = scoped.filter(user => (!venue || user.session?.venue === venue) && user.date >= from && user.date <= to);
  const needsAttention = (user: UserFixture) => Boolean(user.session && user.session.issue !== 'ok');
  const listed = selected.filter(user => {
    const searchText = [user.name, user.id, section === 'sessions' ? user.session?.id : ''].join(' ');
    return (!attention || needsAttention(user)) && searchText.toLowerCase().includes(query.trim().toLowerCase());
  })
    .sort((a, b) => sort === 'recent' ? b.date.localeCompare(a.date) : a.name.localeCompare(b.name));
  const user = scoped.find(item => section === 'users' ? item.id === entity : item.session?.id === entity);
  const session = user?.session;
  const isDetail = Boolean(entity);

  useEffect(() => {
    document.documentElement.lang = en ? 'en' : 'ru';
    document.title = en ? 'Shadow · Admin review' : 'Shadow · Проверка админки';
  }, [en]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  function href(path: string, overrides: Record<string, string> = {}) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(overrides)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    return { pathname: path, search: next.toString() };
  }

  function format(amount: number | null) {
    return amount === null ? t('Нет данных', 'Unavailable') : new Intl.NumberFormat(en ? 'en-US' : 'ru-RU').format(amount) + ' USD';
  }

  function statusLabel(item: UserFixture) {
    return item.session ? status[item.session.issue][en ? 1 : 0] : t('Нет сессий', 'No sessions');
  }

  function table(rows: readonly UserFixture[], sessions = false) {
    if (!rows.length) return <Notice>{t('Записей по этим фильтрам нет.', 'No records match these filters.')}</Notice>;
    return (
      <Card className="review-table" tabIndex={0} aria-label={t('Результаты', 'Results')}>
        <table>
          <thead><tr>
            <th scope="col">{sessions ? t('Сессия', 'Session') : t('Пользователь', 'User')}</th>
            <th scope="col">{t('Площадка', 'Venue')}</th>
            <th scope="col">{t('Состояние', 'Status')}</th>
            {money && <th scope="col">{t('Демо · доступно', 'Demo · available')}</th>}
            <th scope="col">{t('Активность', 'Activity')}</th>
          </tr></thead>
          <tbody>{rows.map(item => <tr key={item.id}>
            <td><Link to={href(sessions ? '/sessions/' + item.session?.id : '/users/' + item.id)}>
              {sessions ? item.session?.id : item.name}
            </Link><small>{sessions ? item.name : item.id}</small></td>
            <td>{item.session?.venue ?? '—'}</td>
            <td><span className="review-status" data-issue={item.session?.issue}>{statusLabel(item)}</span></td>
            {money && <td>{item.session ? format(item.session.free) : '—'}</td>}
            <td>{item.date}</td>
          </tr>)}</tbody>
        </table>
      </Card>
    );
  }

  const isOverview = !section;
  const isReconciliation = section === 'reconciliation';
  const operations = Object.hasOwn(operationSections, section) ? section as OperationSection : undefined;
  const source = params.get('source');
  const returnToSource = source && /^\/(support|feedback|incidents|reconciliation)\/[A-Z]+-[0-9]+$/.test(source) ? source : undefined;
  const isUsers = section === 'users';
  const isSessions = section === 'sessions';
  const isOrder = isSessions && subpage === 'order' && Boolean(session);
  const orderId = session ? session.id.replace('S-DEMO-', 'ORD-') : '';
  const title = isOverview ? t('Обзор', 'Overview') : isUsers ? user?.name ?? t('Пользователи', 'Users') : isSessions ? (isOrder ? orderId : session?.id) ?? t('Сессии', 'Sessions') : isReconciliation ? t('Сверка операций', 'Operation reconciliation') : operations ? operationSections[operations][en ? 1 : 0] : t('Раздел не найден', 'Page not found');
  const backPath = isUsers ? '/users' : '/sessions';

  return <div className="review-shell">
    <aside className="review-sidebar">
      <div className="admin-wordmark">shadow</div>
      <p className="ui-muted">{t('Управление платформой', 'Platform management')}</p>
      <button className="ui-btn ui-btn-secondary review-menu-toggle" aria-expanded={menuOpen} aria-controls="review-nav" onClick={() => setMenuOpen(!menuOpen)}>{t('Меню', 'Menu')}</button>
      <nav id="review-nav" aria-label={t('Рабочие разделы', 'Workspace navigation')} data-open={menuOpen}>
        <Link to={href('/')} onClick={() => setMenuOpen(false)} aria-current={isOverview ? 'page' : undefined}>{t('Обзор', 'Overview')}</Link>
        {allowed && <details open>
          <summary>{t('Пользователи и торговля', 'Users and trading')}</summary>
          <Link to={href('/users')} onClick={() => setMenuOpen(false)} aria-current={isUsers ? 'page' : undefined}>{t('Пользователи', 'Users')}</Link>
          <Link to={href('/sessions')} onClick={() => setMenuOpen(false)} aria-current={isSessions ? 'page' : undefined}>{t('Сессии', 'Sessions')}</Link>
        </details>}
        {allowed && <Link to={href('/support')} onClick={() => setMenuOpen(false)} aria-current={operations === 'support' || operations === 'feedback' ? 'page' : undefined}>{t('Поддержка', 'Support')}</Link>}
        {allowed && <details open>
          <summary>{t('Финансы', 'Finance')}</summary>
          <Link to={href('/reconciliation')} onClick={() => setMenuOpen(false)} aria-current={isReconciliation ? 'page' : undefined}>{t('Сверка операций', 'Operation reconciliation')}</Link>
        </details>}
        {allowed && <details open>
          <summary>{t('Управление', 'Management')}</summary>
          <Link to={href('/incidents')} onClick={() => setMenuOpen(false)} aria-current={operations === 'incidents' ? 'page' : undefined}>{t('Инциденты', 'Incidents')}</Link>
        </details>}
      </nav>
    </aside>
    <div className="review-body">
      <header className="review-header">
        <div><strong>{actor}</strong><p className="ui-muted">{t('Локальная проверка · учебные данные', 'Local review · synthetic data')}</p></div>
        <div className="review-controls">
          <label>{t('Учебное назначение', 'Test assignment')}<select className="ui-field" aria-label={t('Учебное назначение', 'Test assignment')} value={role} onChange={event => update('assignment', event.target.value)}>
            {supportedAssignments.map(key => <option key={key} value={key}>{assignments[key][en ? 1 : 0].split(' · ').at(-1)}</option>)}
          </select></label>
          <label>{t('Язык', 'Language')}<select className="ui-field" aria-label={t('Язык', 'Language')} value={en ? 'en' : 'ru'} onChange={event => update('lang', event.target.value)}><option value="ru">Русский</option><option value="en">English</option></select></label>
        </div>
      </header>
      <main className="review-main">
        {!isOverview && <nav aria-label={t('Путь', 'Breadcrumb')} className="review-path">
          <Link to={href('/')}>{t('Обзор', 'Overview')}</Link>
          {isDetail && !operations && !isReconciliation && <> / <Link to={href(backPath)}>{isUsers ? t('Пользователи', 'Users') : t('Сессии', 'Sessions')}</Link></>}
          {isOrder && session && <> / <Link to={href('/sessions/' + session.id)}>{session.id}</Link></>}
        </nav>}
        <h1>{title}</h1>
        <p className="ui-muted">{operations || isReconciliation ? t('Учебный снимок', 'Synthetic snapshot') : t('Демо-торговля · учебный снимок', 'Demo trading · synthetic snapshot')}</p>

        {operations && <Operations section={operations} entity={entity} role={role} language={en ? 1 : 0} params={params} href={href} update={update} />}
        {isReconciliation && <Reconciliation entity={entity} role={role} language={en ? 1 : 0} params={params} href={href} update={update} runs={runs}
          setResult={(id, result) => setRuns(previous => ({ ...previous, [id]: result }))} />}
        {!isOverview && !operations && !isReconciliation && !isUsers && !isSessions && <Notice>{t('Этот маршрут ещё недоступен.', 'This route is currently unavailable.')}</Notice>}
        {(isUsers || isSessions) && !allowed && <Notice tone="warning">{t('У назначения нет доступа к разделу.', 'This assignment has no access to this section.')}</Notice>}

        {(isOverview || ((isUsers || isSessions) && allowed && !isDetail)) && <Card className="review-panel review-filters">
          {(isUsers || isSessions) && <label>{t('Поиск по имени или ID', 'Find by name or ID')}<input className="ui-field" type="search" value={query} onChange={event => update('q', event.target.value)} /></label>}
          <label>{t('Площадка', 'Venue')}<select className="ui-field" aria-label={t('Площадка', 'Venue')} value={venue} onChange={event => update('venue', event.target.value)}><option value="">{t('Все площадки', 'All venues')}</option>{venues.map(value => <option key={value}>{value}</option>)}</select></label>
          <label>{t('С', 'From')}<input className="ui-field" type="date" value={from} max={to} onChange={event => update('from', event.target.value)} /></label>
          <label>{t('По', 'To')}<input className="ui-field" type="date" value={to} min={from} onChange={event => update('to', event.target.value)} /></label>
          {(isUsers || isSessions) && <><label>{t('Состояние', 'Status')}<select className="ui-field" aria-label={t('Состояние', 'Status')} value={attention ? 'attention' : ''} onChange={event => update('issue', event.target.value)}><option value="">{t('Все состояния', 'All statuses')}</option><option value="attention">{t('Требуют внимания', 'Needs attention')}</option></select></label>
          <label>{t('Сортировка', 'Sort by')}<select className="ui-field" aria-label={t('Сортировка', 'Sort by')} value={sort} onChange={event => update('sort', event.target.value)}><option value="name">{t('Имя', 'Name')}</option><option value="recent">{t('Последняя активность', 'Recent activity')}</option></select></label></>}
        </Card>}

        {isOverview && (allowed ? <>
          <div className="review-kpis">
            <Card className="review-panel"><span>{t('Пользователи', 'Users')}</span><strong>{selected.length}</strong></Card>
            <Card className="review-panel"><span>{t('Сессии в выборке', 'Sessions in view')}</span><strong>{selected.filter(item => item.session).length}</strong></Card>
            <Card className="review-panel"><Link to={href('/users', { issue: 'attention', q: '' })}>{t('Требуют внимания', 'Needs attention')}</Link><strong>{selected.filter(needsAttention).length}</strong></Card>
          </div>
          <Card className="review-panel">
            <h2>{t('Активность сессий по дням', 'Session activity by day')}</h2>
            <ul className="review-chart">{dates.filter(date => date >= from && date <= to).map(date => {
              const count = selected.filter(item => item.session && item.date === date).length;
              return <li key={date}><span>{date.slice(5)}</span><meter aria-label={date} value={count} min={0} max={Math.max(1, selected.length)} /><span>{count}</span></li>;
            })}</ul>
          </Card>
          {table(selected.filter(needsAttention))}
        </> : <Notice>{t('Показатели торговли недоступны для этого назначения.', 'Trading metrics are unavailable to this assignment.')}</Notice>)}

        {(isUsers || isSessions) && allowed && !isDetail && table(isSessions ? listed.filter(item => item.session) : listed, isSessions)}
        {(isUsers || isSessions) && allowed && isDetail && !user && <Notice tone="warning">{t('Запись недоступна.', 'This record is unavailable.')}</Notice>}
        {(isUsers || isSessions) && user && isDetail && <>
          {returnToSource && <Link to={href(returnToSource, { source: '' })}>{t('К исходной записи', 'Back to source record')}</Link>}
          <Link to={href(isOrder ? '/sessions/' + session?.id : backPath)}>{isOrder ? t('К сессии', 'Back to session') : isUsers ? t('К списку пользователей', 'Back to users') : t('К списку сессий', 'Back to sessions')}</Link>
          <Card className="review-panel">
            <h2>{isUsers ? user.id : user.name}</h2>
            <p>{session?.venue ?? t('Нет сессий', 'No sessions')} · {statusLabel(user)}</p>
            {session && isUsers && <Link to={href('/sessions/' + session.id)}>{t('Открыть сессию', 'Open session')} {session.id}</Link>}
            {session && isSessions && <Link to={href('/users/' + user.id)}>{t('Открыть пользователя', 'Open user')}</Link>}
          </Card>
          {session?.id === 'S-DEMO-002' && <Link to={href('/reconciliation/REC-101')}>{t('Открыть сверку заявки', 'Open order reconciliation')}</Link>}
          {session?.issue === 'unknown' && <Notice tone="warning">{t('Результат заявки неизвестен. Резерв удерживается до сверки.', 'The order outcome is unknown. The reserve is held until reconciliation.')}</Notice>}
          {session && money && !isOrder && <div className="review-kpis">
            {[[t('Бюджет', 'Budget'), session.budget], [t('Доступно', 'Available'), session.free], [t('Резерв', 'Reserved'), session.reserved], [t('Стоимость позиций', 'Position cost'), session.positions]].map(([label, amount]) =>
              <Card className="review-panel" key={label}><span>{label}</span><strong>{format(typeof amount === 'number' ? amount : null)}</strong></Card>)}
          </div>}
          {isSessions && session && !isOrder && <Card className="review-panel">
            <h2>{t('Заявки', 'Orders')}</h2>
            <Link to={href('/sessions/' + session.id + '/order')}>{orderId}</Link>
            <span>{statusLabel(user)}</span>
          </Card>}
          {isOrder && session && <Card className="review-panel">
            <h2>{t('События заявки', 'Order events')}</h2>
            <ol className="review-events">
              <li><time>11:58 UTC</time> {t('Средства зарезервированы', 'Funds reserved')}</li>
              <li><time>11:59 UTC</time> {t('Заявка отправлена', 'Order submitted')}</li>
              <li><time>12:00 UTC</time> {statusLabel(user)}</li>
            </ol>
            {money && <dl className="review-events">
              <div><dt>{t('Запрошено', 'Requested')}</dt><dd>{format(20)}</dd></div>
              <div><dt>{t('Исполнено', 'Filled')}</dt><dd>{format(session.issue === 'partial' ? 8 : session.issue === 'ok' ? 0 : null)}</dd></div>
              <div><dt>{t('Остаток', 'Remainder')}</dt><dd>{format(session.issue === 'partial' ? 12 : session.issue === 'ok' ? 20 : null)}</dd></div>
              <div><dt>{t('Резерв', 'Reserved')}</dt><dd>{format(session.reserved)}</dd></div>
            </dl>}
          </Card>}
          {isUsers && <Card className="review-panel"><h2>{t('Условия', 'Terms')}</h2><p>{t('Комиссия Shadow в Paper Alpha', 'Shadow fee in Paper Alpha')} · 0%</p></Card>}
        </>}
      </main>
    </div>
  </div>;
}

if (import.meta.env.DEV) {
  createRoot(document.getElementById('root')!).render(<StrictMode><HashRouter><Review /></HashRouter></StrictMode>);
}
