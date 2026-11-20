import { useRef, useState, type FormEvent } from 'react';
import { Button, Notice, type Locale } from '@cct/ui';

type Props = {
  locale: Locale;
  submitCredentials: (identifier: string, secret: string) => Promise<void>;
};

export function StaffPilotSignInForm({ locale, submitCredentials }: Props) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const pending = useRef(false);
  const t = (ru: string, en: string) => locale === 'en' ? en : ru;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const identifier = data.get('identifier');
    const secret = data.get('secret');
    const secretInput = form.elements.namedItem('secret');
    if (secretInput instanceof HTMLInputElement) secretInput.value = '';
    if (typeof identifier !== 'string' || !identifier.trim() || typeof secret !== 'string' || !secret) return;

    pending.current = true;
    setBusy(true);
    setFailed(false);
    try {
      await submitCredentials(identifier.trim(), secret);
    } catch {
      setFailed(true);
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }

  return <>
    <h1>{t('Тестовый вход', 'Test sign-in')}</h1>
    <p id="staff-test-code-hint" className="ui-muted">
      {t('Введите личный идентификатор и секрет, выданные на срок пилота.', 'Enter your personal identifier and secret issued for this pilot.')}
    </p>
    <form method="post" className="admin-sign-in-form" onSubmit={submit}>
      <label>{t('Идентификатор', 'Identifier')}
        <input name="identifier" className="ui-field" autoComplete="username" spellCheck={false}
          aria-describedby="staff-test-code-hint" disabled={busy} required />
      </label>
      <label>{t('Секрет', 'Secret')}
        <input name="secret" className="ui-field" type="password" autoComplete="off" spellCheck={false}
          disabled={busy} required />
      </label>
      <Button type="submit" disabled={busy}>{busy ? t('Проверяем…', 'Checking…') : t('Войти', 'Sign in')}</Button>
    </form>
    {failed && <Notice tone="warning">{t('Тестовый вход пока недоступен.', 'Test sign-in is currently unavailable.')}</Notice>}
  </>;
}
