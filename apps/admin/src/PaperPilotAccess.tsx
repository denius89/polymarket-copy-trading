import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card, Notice, type Locale } from '@cct/ui';
import { PaperPilotWorkspace } from './PaperPilotWorkspace';
import { StaffPilotSignInForm } from './StaffPilotSignInForm';
import { paperPilotReader } from './paper-pilot-api';
import { checkPilotLogin, pilotSignIn, recoverPilotCookie, type PilotLogin, type PilotRecovery } from './paper-pilot-auth';
import { checkOutcome, confirmStaff, signOut, StaffError, type ConfirmedStaff, type Pending } from './staff-api';

type Phase =
  | { kind: 'entry'; message?: 'rejected' | 'unavailable' | 'expired' | 'signed-out' }
  | { kind: 'checking-login'; operation: PilotLogin }
  | { kind: 'recover'; recovery: PilotRecovery }
  | { kind: 'workspace'; staff: ConfirmedStaff }
  | { kind: 'logout'; loginId: string; pending?: Pending };

export function PaperPilotAccess({ locale }: { locale: Locale }) {
  const [phase, setPhase] = useState<Phase>({ kind: 'entry' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const lock = useRef(false);
  const t = (ru: string, en: string) => locale === 'en' ? en : ru;
  const staff = phase.kind === 'workspace' ? phase.staff : undefined;
  const reader = useMemo(() => staff && paperPilotReader(staff.loginId), [staff]);
  const expire = useCallback(() => setPhase({ kind: 'entry', message: 'expired' }), []);

  useEffect(() => {
    if (!staff) return;
    let active = true;
    async function revalidate() {
      if (!staff || lock.current || document.visibilityState !== 'visible') return;
      lock.current = true;
      try {
        const result = await confirmStaff(staff.loginId);
        if (active && result.staffId !== staff.staffId) expire();
      } catch {
        if (active) expire();
      } finally {
        lock.current = false;
      }
    }
    window.addEventListener('focus', revalidate);
    document.addEventListener('visibilitychange', revalidate);
    const timer = window.setInterval(revalidate, 30000);
    return () => {
      active = false;
      window.removeEventListener('focus', revalidate);
      document.removeEventListener('visibilitychange', revalidate);
      window.clearInterval(timer);
    };
  }, [staff, expire]);

  async function action(task: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError(false);
    try {
      await task();
    } catch {
      setError(true);
    } finally {
      setBusy(false);
      lock.current = false;
    }
  }

  function apply(result: Awaited<ReturnType<typeof checkPilotLogin>>) {
    if (result.kind === 'confirmed') setPhase({ kind: 'workspace', staff: result.staff });
    if (result.kind === 'rejected') setPhase({ kind: 'entry', message: 'rejected' });
    if (result.kind === 'recover') setPhase({ kind: 'recover', recovery: result.recovery });
  }

  function login(identifier: string, secret: string) {
    return action(async () => {
      let started = false;
      setPhase({ kind: 'entry' });
      try {
        apply(await pilotSignIn(identifier, secret, operation => {
          started = true;
          setPhase({ kind: 'checking-login', operation });
        }));
      } catch (failure) {
        if (started) return;
        setPhase({ kind: 'entry', message: failure instanceof StaffError && failure.kind === 'rejected' ? 'rejected' : 'unavailable' });
      }
    });
  }

  function logout(loginId: string) {
    return action(async () => {
      setPhase({ kind: 'logout', loginId });
      await signOut(loginId, pending => setPhase({ kind: 'logout', loginId, pending }));
      setPhase({ kind: 'entry', message: 'signed-out' });
    });
  }

  if (staff && reader) return <PaperPilotWorkspace locale={locale} staffId={staff.staffId} reader={reader}
    expire={expire} signOut={() => void logout(staff.loginId)} busy={busy} />;

  return <Card className="admin-sign-in">
    {phase.kind === 'entry' ? <>
      {phase.message === 'rejected' && <Notice tone="warning">{t('Вход не подтверждён. Проверьте данные доступа.', 'Sign-in was not confirmed. Check your access details.')}</Notice>}
      {phase.message === 'unavailable' && <Notice tone="warning">{t('Тестовый вход пока недоступен.', 'Test sign-in is currently unavailable.')}</Notice>}
      {phase.message === 'expired' && <Notice tone="warning">{t('Служебный вход больше не подтверждён.', 'Staff sign-in is no longer confirmed.')}</Notice>}
      {phase.message === 'signed-out' && <Notice tone="success">{t('Выход подтверждён.', 'Sign-out confirmed.')}</Notice>}
      <StaffPilotSignInForm locale={locale} submitCredentials={login} />
    </> : <>
      <h1>{t('Тестовый вход', 'Test sign-in')}</h1>
      {error && <Notice tone="warning">{t('Не удалось подтвердить результат. Проверьте исходную операцию.', 'The result could not be confirmed. Check the original operation.')}</Notice>}
      {phase.kind === 'checking-login' && <>
        <p role="status">{busy ? t('Подтверждаем вход…', 'Confirming sign-in…') : t('Исход входа пока неизвестен.', 'The sign-in outcome is still unknown.')}</p>
        <Button disabled={busy} onClick={() => void action(async () => apply(await checkPilotLogin(phase.operation)))}>
          {t('Проверить исход входа', 'Check sign-in outcome')}
        </Button>
      </>}
      {phase.kind === 'recover' && <>
        <p>{t('Сервер подтвердил вход. Восстановите сессию в этом браузере.', 'The server confirmed sign-in. Restore the session in this browser.')}</p>
        <Button disabled={busy} onClick={() => void action(async () => {
          try {
            const recovered = await recoverPilotCookie(phase.recovery);
            setPhase({ kind: 'workspace', staff: recovered });
          } catch (failure) {
            if (failure instanceof StaffError && failure.kind === 'unconfirmed') {
              setPhase({ kind: 'entry', message: 'expired' });
            } else throw failure;
          }
        })}>{t('Восстановить сессию', 'Restore session')}</Button>
      </>}
      {phase.kind === 'logout' && <>
        <p role="status">{busy ? t('Подтверждаем выход…', 'Confirming sign-out…') : t('Исход выхода пока неизвестен.', 'The sign-out outcome is still unknown.')}</p>
        {phase.pending ? <Button disabled={busy} onClick={() => void action(async () => {
          const result = await checkOutcome(phase.pending!);
          if (result === 'signed-out') setPhase({ kind: 'entry', message: 'signed-out' });
        })}>{t('Проверить исход выхода', 'Check sign-out outcome')}</Button>
          : <Button disabled={busy} onClick={() => void logout(phase.loginId)}>{t('Повторить подготовку выхода', 'Prepare sign-out again')}</Button>}
      </>}
    </>}
  </Card>;
}
