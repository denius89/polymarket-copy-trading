import { useEffect, useState } from 'react';
import { Button, Card, Notice, type Locale } from '@cct/ui';
import { decodePilotEvents, decodePilotLinks, decodePilotSession, type Money, type PilotEvent, type PilotSessionLink } from './paper-pilot-data';
import './paper-pilot.css';

export type PilotReader = {
  list(signal: AbortSignal): Promise<unknown>;
  session(sessionId: string, signal: AbortSignal): Promise<unknown>;
  events(sessionId: string, signal: AbortSignal): Promise<unknown>;
};

export class PilotReadError extends Error {
  constructor(readonly status: number) { super('Pilot read failed'); }
}

type Load<T> = { kind: 'loading' } | { kind: 'ready'; value: T } | { kind: 'denied' | 'failed' };
type Screen = { kind: 'list' | 'access' } | { kind: 'session'; link: PilotSessionLink };

function failure(error: unknown, expire: () => void): { kind: 'denied' | 'failed' } {
  const status = error instanceof PilotReadError ? error.status : 503;
  if (status === 401) expire();
  return { kind: [401, 403, 404].includes(status) ? 'denied' : 'failed' };
}

function decimal(value: Money, locale: Locale) {
  const numerator = BigInt(value.n) * 100n;
  const denominator = BigInt(value.d);
  const cents = numerator / denominator;
  const approx = numerator % denominator !== 0n ? '≈ ' : '';
  return approx + (cents / 100n).toLocaleString(locale === 'en' ? 'en-US' : 'ru-RU')
    + (locale === 'en' ? '.' : ',') + String(cents % 100n).padStart(2, '0') + ' USD';
}

interface Props {
  locale: Locale;
  staffId: string;
  reader: PilotReader;
  expire: () => void;
  signOut: () => void;
  busy?: boolean;
}

export function PaperPilotWorkspace({ locale, staffId, reader, expire, signOut, busy }: Props) {
  const [screen, setScreen] = useState<Screen>({ kind: 'list' });
  const [revision, setRevision] = useState(0);
  const [links, setLinks] = useState<Load<PilotSessionLink[]>>({ kind: 'loading' });
  const [session, setSession] = useState<Load<ReturnType<typeof decodePilotSession>>>({ kind: 'loading' });
  const [events, setEvents] = useState<Load<PilotEvent[]>>({ kind: 'loading' });
  const t = (ru: string, en: string) => locale === 'en' ? en : ru;
  const sessionId = screen.kind === 'session' ? screen.link.sessionId : undefined;

  useEffect(() => {
    if (screen.kind === 'access') return;
    const controller = new AbortController();
    const { signal } = controller;
    if (screen.kind === 'list') {
      setLinks({ kind: 'loading' });
      void reader.list(signal).then(decodePilotLinks).then(value => {
        if (!signal.aborted) setLinks({ kind: 'ready', value });
      }).catch(error => {
        if (!signal.aborted) setLinks(failure(error, expire));
      });
    } else if (sessionId) {
      setSession({ kind: 'loading' });
      setEvents({ kind: 'loading' });
      void reader.session(sessionId, signal).then(value => decodePilotSession(value, sessionId)).then(value => {
        if (signal.aborted) return;
        setSession({ kind: 'ready', value });
        return reader.events(sessionId, signal).then(value => decodePilotEvents(value, sessionId)).then(value => {
          if (!signal.aborted) setEvents({ kind: 'ready', value });
        }).catch(error => {
          if (!signal.aborted) setEvents(failure(error, expire));
        });
      }).catch(error => {
        if (!signal.aborted) setSession(failure(error, expire));
      });
    }
    return () => controller.abort();
  }, [screen.kind, sessionId, revision, reader, expire]);

  function open(link: PilotSessionLink) {
    setSession({ kind: 'loading' });
    setEvents({ kind: 'loading' });
    setScreen({ kind: 'session', link });
  }

  function showList() {
    setLinks({ kind: 'loading' });
    setScreen({ kind: 'list' });
    setRevision(value => value + 1);
  }

  function refresh() {
    if (screen.kind === 'list') setLinks({ kind: 'loading' });
    else {
      setSession({ kind: 'loading' });
      setEvents({ kind: 'loading' });
    }
    setRevision(value => value + 1);
  }

  function status(value: Load<unknown>, denied: string, failed: string) {
    if (value.kind === 'ready') return null;
    if (value.kind === 'loading') return <p role="status" className="ui-muted">{t('Загрузка…', 'Loading…')}</p>;
    return <Notice tone="warning">{value.kind === 'denied' ? denied : failed}</Notice>;
  }

  function values(items: [string, string][]) {
    return <dl className="pilot-values">{items.map(([label, value]) =>
      <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
  }

  return <div className="pilot-workspace">
    <nav className="pilot-nav" aria-label={t('Разделы пилота', 'Pilot sections')}>
      <Button variant="secondary" aria-current={screen.kind !== 'access' ? 'page' : undefined} onClick={showList}>
        {t('Сессии пилота', 'Pilot sessions')}
      </Button>
      <Button variant="secondary" aria-current={screen.kind === 'access' ? 'page' : undefined} onClick={() => setScreen({ kind: 'access' })}>
        {t('Мой доступ', 'My access')}
      </Button>
    </nav>
    <p className="ui-muted">{t('Изолированный paper-пилот · синтетические данные · просмотр', 'Isolated paper pilot · synthetic data · read only')}</p>

    {screen.kind === 'list' && <>
      <header className="pilot-heading"><h1>{t('Сессии пилота', 'Pilot sessions')}</h1>
        <Button variant="secondary" onClick={refresh} disabled={links.kind === 'loading'}>{t('Обновить', 'Refresh')}</Button>
      </header>
      {status(links, t('Список недоступен.', 'Session list is unavailable.'), t('Не удалось загрузить список.', 'Could not load the session list.'))}
      {links.kind === 'ready' && (links.value.length ? <ul className="pilot-list">
        {links.value.map(link => <li key={link.sessionId}><Card className="pilot-panel">
          <Button variant="ghost" onClick={() => open(link)}>{link.displayLabel}</Button>
          <small className="ui-muted">{link.sessionId}</small>
        </Card></li>)}
      </ul> : <Notice>{t('Подтверждённых сессий в списке пока нет.', 'There are no confirmed sessions in the list yet.')}</Notice>)}
    </>}

    {screen.kind === 'session' && <>
      <Button variant="ghost" onClick={showList}>{t('К сессиям пилота', 'Back to pilot sessions')}</Button>
      <header className="pilot-heading"><h1>{screen.link.displayLabel}</h1>
        <Button variant="secondary" onClick={refresh} disabled={session.kind === 'loading'}>{t('Обновить', 'Refresh')}</Button>
      </header>
      <p className="ui-muted">{screen.link.sessionId}</p>
      {status(session, t('Сессия недоступна.', 'Session is unavailable.'), t('Не удалось загрузить сессию.', 'Could not load the session.'))}
      {session.kind === 'ready' && <>
        <Card className="pilot-panel">
          <h2>{t('Сводка сессии', 'Session summary')}</h2>
          {values([
            [t('Трейдер', 'Trader'), session.value.summary.traderDisplayName],
            [t('Площадка · ID', 'Venue · ID'), session.value.summary.venueId],
            [t('Версия снимка', 'Snapshot version'), session.value.summary.snapshotVersion],
            [t('Время снимка · UTC', 'Snapshot time · UTC'), session.value.summary.asOf],
          ])}
          {session.value.kind === 'empty' && <Notice>{t('Копирование не подключено. Торговых данных пока нет.', 'Copying is not connected. There is no trading data yet.')}</Notice>}
        </Card>
        {session.value.kind === 'positions' ? <>
          <Card className="pilot-panel"><h2>{t('Виртуальные средства', 'Virtual funds')}</h2>
            {values([
              [t('Доступно', 'Available'), decimal(session.value.available, locale)],
              [t('В резерве', 'Reserved'), decimal(session.value.reserved, locale)],
              [t('Деньги на счёте', 'Cash balance'), decimal(session.value.cash, locale)],
            ])}
          </Card>
          <Card className="pilot-panel"><h2>{t('Открытые позиции', 'Open positions')}</h2>
            {session.value.positions.length ? <ul className="pilot-list">{session.value.positions.map(position =>
              <li key={position.conditionId + ':' + position.tokenId}>
                {values([
                  [t('Токен исхода', 'Outcome token'), position.tokenId],
                  [t('Количество долей', 'Shares'), decimal(position.quantity, locale).replace(' USD', '')],
                  [t('Стоимость покупки', 'Cost basis'), decimal(position.cost, locale)],
                ])}
              </li>)}</ul> : <Notice>{t('Пока нет позиций.', 'No open positions yet.')}</Notice>}
          </Card>
        </> : <div className="pilot-columns">
          <Card className="pilot-panel"><h2>{t('Настройки', 'Settings')}</h2>
            {session.value.settings ? values([
              [t('Виртуальный бюджет', 'Virtual budget'), decimal(session.value.settings.budget, locale)],
              session.value.settings.fixedAmount
                ? [t('Фиксированный размер', 'Fixed size'), decimal(session.value.settings.fixedAmount, locale)]
                : [t('Доля копирования', 'Copy percentage'), session.value.settings.copyPercent + ' %'],
              [t('Лимит рынка', 'Market limit'), session.value.settings.marketLimitPercent + ' %'],
              [t('Лимит покупок в сутки', 'Daily buy limit'), session.value.settings.dailyBuyLimitPercent + ' %'],
            ]) : <Notice>{t('Нет доступа к настройкам.', 'Settings access is restricted.')}</Notice>}
          </Card>
          <Card className="pilot-panel"><h2>{t('Виртуальные средства', 'Virtual funds')}</h2>
            {session.value.financialSnapshot ? values([
              [t('Начальное финансирование', 'Initial funding'), decimal(session.value.financialSnapshot.initialFunding, locale)],
              [t('Доступно', 'Available'), decimal(session.value.financialSnapshot.free, locale)],
              [t('В резерве', 'Reserved'), decimal(session.value.financialSnapshot.reserved, locale)],
              [t('Капитал', 'Equity'), decimal(session.value.financialSnapshot.equity, locale)],
              [t('Сделки', 'Trades'), session.value.financialSnapshot.tradeCount],
              [t('Позиции', 'Positions'), session.value.financialSnapshot.positionCount],
              [t('Заявки', 'Orders'), session.value.financialSnapshot.orderCount],
            ]) : <Notice>{t('Нет доступа к финансовому снимку.', 'Financial snapshot access is restricted.')}</Notice>}
          </Card>
        </div>}
        <Card className="pilot-panel"><h2>{t('События', 'Events')}</h2>
          {status(events, t('События недоступны.', 'Events are unavailable.'), t('Не удалось загрузить события.', 'Could not load events.'))}
          {events.kind === 'ready' && <ul className="pilot-list">
            {events.value.map(event => <li key={event.eventId}>{t('Демо-сессия запущена', 'Demo session started')} · <time dateTime={event.occurredAt}>{event.occurredAt}</time></li>)}
          </ul>}
        </Card>
      </>}
    </>}

    {screen.kind === 'access' && <Card className="pilot-panel">
      <h1>{t('Мой доступ', 'My access')}</h1>
      <Notice tone="success">{t('Служебный вход подтверждён.', 'Staff sign-in confirmed.')}</Notice>
      {values([[t('Идентификатор сотрудника', 'Staff identifier'), staffId]])}
      <div><Button variant="secondary" onClick={signOut} disabled={busy}>{t('Выйти', 'Sign out')}</Button></div>
    </Card>}
  </div>;
}
