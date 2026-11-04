import { Link } from 'react-router-dom';
import { Button, Card, Notice } from '@cct/ui';
import type { Assignment, Venue } from './fixtures';

type Text = readonly [string, string];

const labels = {
  unchecked: ['Не проверено', 'Not checked'],
  missing: ['Недостаточно данных', 'Insufficient evidence'],
  difference: ['Есть расхождение', 'Difference found'],
  matched: ['Снимок совпадает', 'Snapshot matches'],
} as const;
type Result = keyof typeof labels;

interface Snapshot {
  id: string;
  user: string;
  name: string;
  session: string;
  order: string;
  incident: string;
  venue: Venue;
  timestamp: string;
  source: string;
  metric: Text;
  recorded: number | null;
  observed: number | null;
  reserve: number;
  next: Text;
}

const snapshots: readonly Snapshot[] = [
  {
    id: 'REC-101', user: 'U-DEMO-002', name: 'Demo Noor', session: 'S-DEMO-002', order: 'ORD-002', incident: 'INC-101',
    venue: 'Polymarket', timestamp: '2026-10-23 12:00 UTC', source: 'DEMO-ORDER-002',
    metric: ['Исполнение заявки', 'Order fill'], recorded: null, observed: null, reserve: 20,
    next: ['Дождаться подтверждения исходной заявки и повторить сверку. Повторная отправка недоступна.', 'Wait for evidence about the original order, then recheck. Resending remains unavailable.'],
  },
  {
    id: 'REC-102', user: 'U-DEMO-009', name: 'Demo Orion', session: 'S-DEMO-009', order: 'ORD-009', incident: 'INC-102',
    venue: 'Limitless', timestamp: '2026-10-23 10:20 UTC', source: 'DEMO-SNAPSHOT-009',
    metric: ['Учётная стоимость позиций', 'Recorded position cost'], recorded: 20, observed: 24, reserve: 20,
    next: ['Разобрать исторический снимок в INC-102. Текущие суммы не подтверждены.', 'Investigate the historical snapshot in INC-102. Current amounts are unconfirmed.'],
  },
  {
    id: 'REC-103', user: 'U-DEMO-005', name: 'Demo Robin', session: 'S-DEMO-005', order: 'ORD-005', incident: 'INC-103',
    venue: 'Limitless', timestamp: '2026-10-22 12:00 UTC', source: 'DEMO-FILL-005',
    metric: ['Исполнение заявки', 'Order fill'], recorded: 8, observed: 8, reserve: 12,
    next: ['Продолжать наблюдать за остатком заявки. Отмена остатка не подтверждена.', 'Continue monitoring the order remainder. Cancellation of the remainder is unconfirmed.'],
  },
];

function delta(snapshot: Snapshot) {
  if (snapshot.recorded === null || snapshot.observed === null) return null;
  return snapshot.observed - snapshot.recorded;
}

export function reconciliationForIncident(incident: string) {
  return snapshots.find(snapshot => snapshot.incident === incident)?.id;
}

export type ReconciliationRuns = Readonly<Partial<Record<string, Result>>>;

interface Props {
  entity?: string;
  role: Assignment;
  language: 0 | 1;
  params: URLSearchParams;
  href: (path: string, overrides?: Record<string, string>) => { pathname: string; search: string };
  update: (key: string, value: string) => void;
  runs: ReconciliationRuns;
  setResult: (id: string, result: Result) => void;
}

export function Reconciliation({ entity, role, language, params, href, update, runs, setResult }: Props) {
  const t = (ru: string, en: string) => language ? en : ru;
  const amounts = role !== 'marketing' && role !== 'audit' && role !== 'limited';
  const permitted = snapshots.filter(snapshot => role !== 'limited' || snapshot.user === 'U-DEMO-002');
  const selected = permitted.find(snapshot => snapshot.id === entity);
  const result = (id: string): Result => runs[id] ?? 'unchecked';
  const q = params.get('recQuery') ?? '';
  const state = params.get('recStatus') ?? '';
  const venue = params.get('recVenue') ?? '';
  const from = params.get('recFrom') ?? '';
  const to = params.get('recTo') ?? '';
  const rows = permitted.filter(snapshot => {
    const date = snapshot.timestamp.slice(0, 10);
    return (!state || result(snapshot.id) === state) && (!venue || snapshot.venue === venue)
      && (!from || date >= from) && (!to || date <= to)
      && [snapshot.id, snapshot.user, snapshot.name, snapshot.order, snapshot.incident].join(' ').toLowerCase().includes(q.trim().toLowerCase());
  });

  function amount(value: number | null, signed = false) {
    if (value === null) return t('Не подтверждено', 'Unconfirmed');
    const formatter = new Intl.NumberFormat(language ? 'en-US' : 'ru-RU', {
      minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: signed ? 'exceptZero' : 'auto',
    });
    return formatter.format(value) + ' USD';
  }

  if (role === 'marketing') return <Notice tone="warning">{t('У назначения нет доступа к разделу.', 'This assignment has no access to this section.')}</Notice>;
  if (entity && !selected) return <Notice tone="warning">{t('Запись недоступна.', 'This record is unavailable.')}</Notice>;

  const explanation = <Notice>{t('Сравниваются данные одного снимка. Сверка не отправляет заявки, не меняет учёт и не освобождает резерв.', 'Reconciliation compares one snapshot. It does not submit orders, change ledger records or release reserves.')}</Notice>;
  if (selected) {
    const status = result(selected.id);
    const difference = delta(selected);
    const source = '/reconciliation/' + selected.id;
    return <>
      <Link to={href('/reconciliation', { source: '' })}>{t('К списку сверки', 'Back to reconciliation')}</Link>
      {explanation}
      <div className="review-columns">
        <Card className="review-panel">
          <h2>{selected.metric[language]}</h2>
          <p>{selected.id} · {selected.name} · {selected.venue}</p>
          <p className="ui-muted">{selected.timestamp} · {selected.source} · {t('Версия 1', 'Version 1')}</p>
          {amounts && <dl className="review-events">
            <div><dt>{t('По учёту Shadow', 'Shadow record')}</dt><dd>{amount(selected.recorded)}</dd></div>
            <div><dt>{t('По учебному подтверждению', 'Synthetic evidence')}</dt><dd>{amount(selected.observed)}</dd></div>
            <div><dt>{t('Разница: подтверждение − учёт', 'Difference: evidence − record')}</dt><dd>{status === 'unchecked' ? '—' : amount(difference, true)}</dd></div>
            <div><dt>{t('Резерв снимка', 'Snapshot reserve')}</dt><dd>{amount(selected.reserve)}</dd></div>
          </dl>}
          <Notice>{labels[status][language]}</Notice>
          {status !== 'unchecked' && <p>{selected.next[language]}</p>}
          {amounts
            ? <div><Button onClick={() => setResult(selected.id, difference === null ? 'missing' : difference === 0 ? 'matched' : 'difference')}>
              {t('Проверить учебный снимок', 'Check synthetic snapshot')}
            </Button></div>
            : <p className="ui-muted">{t('Назначение позволяет просматривать запись без сумм.', 'This assignment can view the record without amounts.')}</p>}
        </Card>
        <Card className="review-panel">
          <h2>{t('Связанные записи', 'Related records')}</h2>
          <Link to={href('/incidents/' + selected.incident, { source })}>{t('Инцидент', 'Incident')} · {selected.incident}</Link>
          <Link to={href('/users/' + selected.user, { source })}>{t('Пользователь', 'User')} · {selected.user}</Link>
          <Link to={href('/sessions/' + selected.session, { source })}>{t('Сессия', 'Session')} · {selected.session}</Link>
          <Link to={href('/sessions/' + selected.session + '/order', { source })}>{t('Заявка', 'Order')} · {selected.order}</Link>
        </Card>
      </div>
    </>;
  }

  return <>
    {explanation}
    <p className="ui-muted">{t('Виртуальные USD · комиссия Shadow в Paper Alpha 0%. Суммы разных площадок не складываются.', 'Virtual USD · Shadow fee in Paper Alpha 0%. Amounts from different venues are kept separate.')}</p>
    <Card className="review-panel review-filters">
      <label>{t('Пользователь, заявка или ID', 'User, order or ID')}<input className="ui-field" type="search" value={q} onChange={event => update('recQuery', event.target.value)} /></label>
      <label>{t('Результат', 'Result')}<select className="ui-field" aria-label={t('Результат', 'Result')} value={state} onChange={event => update('recStatus', event.target.value)}>
        <option value="">{t('Все результаты', 'All results')}</option>
        {Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label[language]}</option>)}
      </select></label>
      <label>{t('Площадка', 'Venue')}<select className="ui-field" aria-label={t('Площадка', 'Venue')} value={venue} onChange={event => update('recVenue', event.target.value)}>
        <option value="">{t('Все площадки', 'All venues')}</option><option>Polymarket</option><option>Limitless</option>
      </select></label>
      <label>{t('Снимок с', 'Snapshot from')}<input className="ui-field" type="date" value={from} max={to || undefined} onChange={event => update('recFrom', event.target.value)} /></label>
      <label>{t('Снимок по', 'Snapshot through')}<input className="ui-field" type="date" value={to} min={from || undefined} onChange={event => update('recTo', event.target.value)} /></label>
      <Link to={href('/reconciliation', { recQuery: '', recStatus: '', recVenue: '', recFrom: '', recTo: '' })}>{t('Сбросить фильтры', 'Reset filters')}</Link>
    </Card>
    {rows.length ? <Card className="review-table" tabIndex={0} aria-label={t('Проверки', 'Checks')}>
      <table>
        <thead><tr>
          <th scope="col">{t('Проверка', 'Check')}</th><th scope="col">{t('Площадка', 'Venue')}</th>
          <th scope="col">{t('Показатель', 'Measure')}</th><th scope="col">{t('Результат', 'Result')}</th>
          {amounts && <th scope="col">{t('Разница', 'Difference')}</th>}<th scope="col">{t('Снимок', 'Snapshot')}</th>
        </tr></thead>
        <tbody>{rows.map(snapshot => <tr key={snapshot.id}>
          <td><Link to={href('/reconciliation/' + snapshot.id)}>{snapshot.id}</Link><small>{snapshot.name} · {snapshot.order} · {snapshot.incident}</small></td>
          <td>{snapshot.venue}</td><td>{snapshot.metric[language]}</td><td>{labels[result(snapshot.id)][language]}</td>
          {amounts && <td>{result(snapshot.id) === 'unchecked' ? '—' : amount(delta(snapshot), true)}</td>}<td>{snapshot.timestamp}</td>
        </tr>)}</tbody>
      </table>
    </Card> : <Notice>{t('Записей по этим фильтрам нет.', 'No records match these filters.')}</Notice>}
  </>;
}
