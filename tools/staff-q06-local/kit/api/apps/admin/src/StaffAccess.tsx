import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Button, Notice, type Locale } from '@cct/ui';
import { checkOutcome, confirmStaff, prepareRegistration, register, signIn, signOut, StaffError, type ConfirmedStaff, type Pending } from './staff-api';

const messages = {
  unavailable: ['Служба входа недоступна. Повторите позже.', 'Staff authentication is unavailable. Try again later.'],
  rejected: ['Сервер отклонил запрос. Проверьте доступ или обратитесь к оператору.', 'The server rejected the request. Check your access or contact the operator.'],
  cancelled: ['Проверка ключа не завершилась. Вы можете начать её заново.', 'The passkey check did not finish. You can start it again.'],
  unconfirmed: ['Вход не подтверждён в этом браузере. Начните новый вход.', 'Sign-in could not be confirmed in this browser. Start a new sign-in.'],
  'bootstrap-unknown': ['Ответ на подготовку регистрации не получен. Повторите исходный запрос. После закрытия или перезагрузки вкладки обратитесь к оператору.', 'The registration setup response was not received. Retry the original request. Contact the operator if this tab was closed or reloaded.'],
  pending: ['Исход операции пока неизвестен. Проверьте исходный запрос.', 'The outcome is still unknown. Check the original request.'],
  registered: ['Ключ зарегистрирован. Теперь войдите с ним.', 'Passkey registered. You can now sign in with it.'],
  'signed-out': ['Выход подтверждён.', 'Sign-out confirmed.'],
  expired: ['Вход больше не подтверждён. Для продолжения войдите снова.', 'Your sign-in is no longer confirmed. Sign in again to continue.'],
} as const;

export function StaffAccess({ locale }: { locale: Locale }) {
  const [staff, setStaff] = useState<ConfirmedStaff>();
  const [pending, setPending] = useState<Pending>();
  const [logoutTarget, setLogoutTarget] = useState<string>();
  const [registration, setRegistration] = useState<string>();
  const [showBootstrap, setShowBootstrap] = useState(false);
  const [message, setMessage] = useState<keyof typeof messages>();
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const bootstrapRequest = useRef<{ operationId: string; handle: string } | undefined>(undefined);
  const en = locale === 'en';
  const t = (ru: string, english: string) => en ? english : ru;

  useEffect(() => {
    if (!staff) return;
    let active = true;
    async function recheck() {
      if (!staff || lock.current || document.visibilityState !== 'visible') return;
      lock.current = true;
      try {
        const current = await confirmStaff(staff.loginId);
        if (current.staffId !== staff.staffId) throw new StaffError('unconfirmed');
      } catch {
        if (active) {
          setStaff(undefined);
          setMessage('expired');
        }
      } finally {
        lock.current = false;
      }
    }
    window.addEventListener('focus', recheck);
    document.addEventListener('visibilitychange', recheck);
    const timer = window.setInterval(recheck, 30000);
    return () => {
      active = false;
      window.removeEventListener('focus', recheck);
      document.removeEventListener('visibilitychange', recheck);
      window.clearInterval(timer);
    };
  }, [staff]);

  async function run(action: 'login' | 'register' | 'logout' | 'check' | 'prepare', handle?: string) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setMessage(undefined);
    let operation = pending;
    function started(value: Pending) {
      operation = value;
      setPending(value);
    }
    try {
      if (action === 'prepare') {
        if (!bootstrapRequest.current && handle !== undefined) {
          bootstrapRequest.current = { operationId: crypto.randomUUID(), handle };
        }
        const original = bootstrapRequest.current;
        if (!original) throw new StaffError('bootstrap-unknown');
        setRegistration(await prepareRegistration(original.handle, original.operationId));
        bootstrapRequest.current = undefined;
        return;
      }
      if (action === 'register' && registration) {
        await register(registration, started);
        setRegistration(undefined);
        setShowBootstrap(false);
        setMessage('registered');
      }
      if (action === 'login') setStaff(await signIn(started));
      if (action === 'logout' && (staff || logoutTarget)) {
        const loginId = staff?.loginId ?? logoutTarget!;
        setStaff(undefined);
        setLogoutTarget(loginId);
        await signOut(loginId, started);
        setLogoutTarget(undefined);
        setMessage('signed-out');
      }
      if (action === 'check' && operation) {
        const result = await checkOutcome(operation);
        if (result === 'pending') {
          setMessage('pending');
          return;
        }
        if (typeof result === 'object') setStaff(result);
        else {
          if (result === 'registered') {
            setRegistration(undefined);
            setShowBootstrap(false);
          }
          if (result === 'signed-out') setLogoutTarget(undefined);
          setMessage(result);
        }
      }
      setPending(undefined);
    } catch (error) {
      const kind = error instanceof StaffError ? error.kind : 'unavailable';
      const terminal = action === 'check' && (kind === 'unconfirmed' || kind === 'rejected');
      if (terminal) setPending(undefined);
      setMessage(operation && !terminal ? 'pending' : kind);
      if (action === 'prepare' && kind !== 'bootstrap-unknown') bootstrapRequest.current = undefined;
      if (kind === 'bootstrap-unknown') setShowBootstrap(false);
    } finally {
      setBusy(false);
      lock.current = false;
    }
  }

  function submitBootstrap(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const handle = new FormData(form).get('handle');
    form.reset();
    if (typeof handle === 'string') void run('prepare', handle.trim());
  }

  const supported = window.isSecureContext && Boolean(window.PublicKeyCredential && navigator.credentials);
  return <>
    <h1>{staff ? t('Рабочая область', 'Staff workspace') : t('Вход сотрудников', 'Staff sign-in')}</h1>
    <p className="ui-muted">{t('Закрытый тестовый полигон · учётные записи сотрудников', 'Closed test environment · staff accounts')}</p>
    {message && <Notice tone={message === 'registered' || message === 'signed-out' ? 'success' : 'warning'}>{messages[message][en ? 1 : 0]}</Notice>}
    {busy && <p role="status" className="ui-muted">{t('Проверяем…', 'Checking…')}</p>}
    {staff ? <>
      <Notice tone="success">{t('Вход сотрудника подтверждён.', 'Staff sign-in confirmed.')}</Notice>
      <p>{t('Рабочие разделы пока недоступны на полигоне.', 'Workspace sections are currently unavailable in this environment.')}</p>
      <Button type="button" variant="secondary" disabled={busy} onClick={() => void run('logout')}>{t('Выйти', 'Sign out')}</Button>
    </> : pending ? (
      <Button type="button" disabled={busy} onClick={() => void run('check')}>{t('Проверить исход операции', 'Check original outcome')}</Button>
    ) : bootstrapRequest.current ? (
      <Button type="button" disabled={busy} onClick={() => void run('prepare')}>{t('Повторить исходный запрос регистрации', 'Retry original registration request')}</Button>
    ) : logoutTarget ? (
      <Button type="button" disabled={busy} onClick={() => void run('logout')}>{t('Повторить подготовку выхода', 'Prepare sign-out again')}</Button>
    ) : !supported ? (
      <Notice tone="warning">{t('Для входа откройте полигон в браузере с поддержкой ключей доступа и доверенным сертификатом.', 'Open the test environment in a browser with passkey support and a trusted certificate.')}</Notice>
    ) : registration ? (
      <Button type="button" disabled={busy} onClick={() => void run('register')}>{t('Зарегистрировать ключ на устройстве', 'Register a passkey on this device')}</Button>
    ) : showBootstrap ? (
      <form className="admin-sign-in-form" onSubmit={submitBootstrap}>
        <label>{t('Одноразовый код регистрации', 'One-time registration code')}
          <input className="ui-field" name="handle" type="password" autoComplete="off" spellCheck={false} maxLength={43} required />
        </label>
        <Button type="submit" disabled={busy}>{t('Подготовить регистрацию', 'Prepare registration')}</Button>
        <Button type="button" variant="ghost" disabled={busy} onClick={() => setShowBootstrap(false)}>{t('Назад ко входу', 'Back to sign-in')}</Button>
      </form>
    ) : <>
      <Button type="button" disabled={busy} onClick={() => void run('login')}>{t('Войти с ключом доступа', 'Sign in with a passkey')}</Button>
      <Button type="button" variant="secondary" disabled={busy || message === 'bootstrap-unknown'} onClick={() => setShowBootstrap(true)}>{t('Первый вход · зарегистрировать ключ', 'First sign-in · register a passkey')}</Button>
    </>}
  </>;
}
