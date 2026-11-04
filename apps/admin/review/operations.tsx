import { Link } from 'react-router-dom';
import { Card, Notice } from '@cct/ui';
import { reconciliationForIncident } from './reconciliation';
import { users, type Assignment } from './fixtures';

export const operationSections = {
  support: ['Обращения', 'Tickets'],
  feedback: ['Обратная связь', 'Feedback'],
  incidents: ['Инциденты', 'Incidents'],
} as const;

export type OperationSection = keyof typeof operationSections;
type Translation = readonly [string, string];

interface RecordFixture {
  id: string;
  user?: string;
  title: Translation;
  status: Translation;
  body: string | Translation;
  date: string;
  assignee?: string;
  related?: Partial<Record<OperationSection, string>>;
}

const records: Record<OperationSection, readonly RecordFixture[]> = {
  support: [
    { id: 'T-101', user: 'U-DEMO-002', title: ['Неизвестен результат заявки', 'Order outcome unknown'], status: ['Ожидает поддержки', 'Waiting for support'], body: 'Не вижу результат заявки ORD-002. Можно отправить её ещё раз?', date: '2026-10-23', assignee: 'STAFF-203', related: { incidents: 'INC-101' } },
    { id: 'T-102', user: 'U-DEMO-005', title: ['Исполнилась только часть заявки', 'Only part of my order filled'], status: ['Новое', 'New'], body: 'Почему исполнена только часть заявки ORD-005?', date: '2026-10-22', related: { feedback: 'FB-102', incidents: 'INC-103' } },
    { id: 'T-103', user: 'U-DEMO-009', title: ['Данные сессии не обновляются', 'Session data is not updating'], status: ['Ожидает пользователя', 'Waiting for user'], body: 'Последнее обновление вижу в 10:20 UTC. Что делать?', date: '2026-10-21', assignee: 'STAFF-206', related: { incidents: 'INC-102' } },
  ],
  feedback: [
    { id: 'FB-101', user: 'U-DEMO-002', title: ['Не понимаю результат заявки', 'Order result is unclear'], status: ['Новое', 'New'], body: 'I cannot tell whether my order went through. Please make the pending state clearer.', date: '2026-10-23' },
    { id: 'FB-102', user: 'U-DEMO-005', title: ['Пояснение частичного исполнения', 'Explain partial fills'], status: ['В разборе', 'In review'], body: 'Покажите рядом с исполненной суммой, сколько ещё осталось в заявке.', date: '2026-10-22', assignee: 'STAFF-203', related: { support: 'T-102' } },
    { id: 'FB-103', title: ['Тексты первого входа', 'First-run copy'], status: ['Новое', 'New'], body: 'На первом экране хотелось бы короткий пример. Не понял, с чего начать.', date: '2026-10-21' },
  ],
  incidents: [
    { id: 'INC-101', user: 'U-DEMO-002', title: ['Неизвестен результат заявки', 'Order outcome unknown'], status: ['Ожидает подтверждения', 'Awaiting evidence'], body: ['Заявка ORD-002 отправлена. Площадка ещё не подтвердила итог. Повторная отправка недоступна до сверки.', 'Order ORD-002 was submitted. The venue has yet to confirm the outcome. Resending is unavailable until reconciliation.'], date: '2026-10-23', assignee: 'STAFF-203', related: { support: 'T-101' } },
    { id: 'INC-102', user: 'U-DEMO-009', title: ['Не обновляются данные сессии', 'Session data is not updating'], status: ['В работе', 'Investigating'], body: ['Последний снимок получен в 10:20 UTC. Подтверждения восстановления пока нет.', 'The latest snapshot was received at 10:20 UTC. Recovery has not been confirmed.'], date: '2026-10-22', assignee: 'STAFF-206', related: { support: 'T-103' } },
    { id: 'INC-103', user: 'U-DEMO-005', title: ['Задержка уведомления об исполнении', 'Fill notification delay'], status: ['Закрыто', 'Closed'], body: ['Проверена задержка уведомления. Частичное исполнение заявки остаётся отдельным фактом.', 'The notification delay was checked. The partial order fill remains a separate fact.'], date: '2026-10-21', assignee: 'STAFF-203', related: { support: 'T-102' } },
  ],
};

interface Props {
  section: OperationSection;
  entity?: string;
  role: Assignment;
  language: 0 | 1;
  params: URLSearchParams;
  href: (path: string, overrides?: Record<string, string>) => { pathname: string; search: string };
  update: (key: string, value: string) => void;
}

export function Operations({ section, entity, role, language, params, href, update }: Props) {
  const t = (ru: string, en: string) => language ? en : ru;
  const visible = (record: RecordFixture) => role !== 'marketing' && (role !== 'limited' || record.user === 'U-DEMO-002');
  const permitted = records[section].filter(visible);
  const item = permitted.find(record => record.id === entity);
  const root = '/' + section;
  const searchKey = section + 'Query';
  const statusKey = section + 'Status';
  const search = params.get(searchKey) ?? '';
  const state = params.get(statusKey) ?? '';
  const rows = permitted.filter(record => (!state || record.status[1] === state)
    && [record.id, record.title[0], record.title[1], record.user, users.find(user => user.id === record.user)?.name]
      .join(' ').toLowerCase().includes(search.trim().toLowerCase()));
  const user = item && users.find(candidate => candidate.id === item.user);
  const reconciliation = section === 'incidents' && item ? reconciliationForIncident(item.id) : undefined;
  const changes = role === 'ownerA' || role === 'ownerB' || role === 'lead' || role === 'ops';
  const tabs = section !== 'incidents' && <nav className="review-path" aria-label={t('Вкладки поддержки', 'Support sections')}>
    <Link to={href('/support')} aria-current={section === 'support' ? 'page' : undefined}>{operationSections.support[language]}</Link>
    <Link to={href('/feedback')} aria-current={section === 'feedback' ? 'page' : undefined}>{operationSections.feedback[language]}</Link>
  </nav>;
  if (role === 'marketing') return <Notice tone="warning">{t('У назначения нет доступа к разделу.', 'This assignment has no access to this section.')}</Notice>;
  if (entity && !item) return <Notice tone="warning">{t('Запись недоступна.', 'This record is unavailable.')}</Notice>;
  if (item) return <>
    {tabs}
    <Link to={href(root)}>{t('К списку', 'Back to list')}</Link>
    <div className="review-columns">
      <Card className="review-panel">
        <h2>{item.title[language]}</h2>
        <p className="ui-muted">{item.id} · {item.date}</p>
        <p>{typeof item.body === 'string' ? item.body : item.body[language]}</p>
        <Notice>{changes ? t('Изменения недоступны до подключения служебного API.', 'Changes are unavailable until the staff API is connected.') : t('Назначение позволяет только просмотр.', 'This assignment is read-only.')}</Notice>
      </Card>
      <Card className="review-panel">
        <h2>{t('Контекст записи', 'Record context')}</h2>
        <p>{item.status[language]}</p>
        <p className="ui-muted">{t('Ответственный', 'Assignee')} · {item.assignee ?? t('Не назначен', 'Unassigned')}</p>
        {user && <Link to={href('/users/' + user.id, { source: root + '/' + item.id })}>{user.name}</Link>}
        {user?.session && <Link to={href('/sessions/' + user.session.id, { source: root + '/' + item.id })}>{user.session.id} · {user.session.venue}</Link>}
        {reconciliation && <Link to={href('/reconciliation/' + reconciliation, { source: '' })}>{t('Сверка операций', 'Operation reconciliation')} · {reconciliation}</Link>}
        {Object.entries(item.related ?? {}).map(([kind, id]) => {
          const target = kind as OperationSection;
          return records[target].some(record => record.id === id && visible(record))
            ? <Link key={kind} to={href('/' + kind + '/' + id)}>{operationSections[target][language]} · {id}</Link>
            : null;
        })}
      </Card>
    </div>
  </>;
  return <>
    {tabs}
    <Card className="review-panel review-filters">
      <label>{t('Поиск по теме, имени или ID', 'Search by subject, name or ID')}<input className="ui-field" type="search" value={search} onChange={event => update(searchKey, event.target.value)} /></label>
      <label>{t('Статус', 'Status')}<select aria-label={t('Статус', 'Status')} className="ui-field" value={state} onChange={event => update(statusKey, event.target.value)}>
        <option value="">{t('Все статусы', 'All statuses')}</option>
        {[...new Map(permitted.map(record => [record.status[1], record.status])).values()].map(label => <option value={label[1]} key={label[1]}>{label[language]}</option>)}
      </select></label>
    </Card>
    {rows.length ? <Card className="review-table" tabIndex={0} aria-label={operationSections[section][language]}>
      <table>
        <thead><tr>
          <th scope="col">{t('Тема', 'Subject')}</th>
          <th scope="col">{t('Пользователь', 'User')}</th>
          <th scope="col">{t('Статус', 'Status')}</th>
          <th scope="col">{t('Ответственный', 'Assignee')}</th>
          <th scope="col">{t('Дата', 'Date')}</th>
        </tr></thead>
        <tbody>{rows.map(record => <tr key={record.id}>
          <td><Link to={href(root + '/' + record.id)}>{record.title[language]}</Link><small>{record.id}</small></td>
          <td>{users.find(candidate => candidate.id === record.user)?.name ?? '—'}</td>
          <td>{record.status[language]}</td>
          <td>{record.assignee ?? t('Не назначен', 'Unassigned')}</td>
          <td>{record.date}</td>
        </tr>)}</tbody>
      </table>
    </Card> : <Notice>{t('Записей по этим фильтрам нет.', 'No records match these filters.')}</Notice>}
  </>;
}
