import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Card, Notice, type Locale } from '@cct/ui';
import './admin.css';

const copy = {
  ru: {
    admin: 'Админка',
    language: 'Язык интерфейса',
    title: 'Вход сотрудников',
    description: 'Рабочая область Shadow для сотрудников.',
    unavailable: 'Вход сотрудников пока недоступен на тестовом полигоне.',
    account: 'Для входа потребуется отдельная учётная запись сотрудника.',
  },
  en: {
    admin: 'Administration',
    language: 'Interface language',
    title: 'Staff sign-in',
    description: 'The Shadow staff workspace.',
    unavailable: 'Staff sign-in is currently unavailable in this test environment.',
    account: 'You will need a separate staff account to sign in.',
  },
} satisfies Record<Locale, Record<string, string>>;

function initialLocale(): Locale {
  return new URL(window.location.href).searchParams.get('lang') === 'en' ? 'en' : 'ru';
}

function App() {
  const [locale, setLocale] = useState(initialLocale);
  const labels = copy[locale];

  useEffect(() => {
    document.documentElement.lang = locale;
    document.title = `Shadow · ${labels.admin}`;
    function restoreLocale() {
      setLocale(initialLocale());
    }
    window.addEventListener('popstate', restoreLocale);
    return () => window.removeEventListener('popstate', restoreLocale);
  }, [labels.admin, locale]);

  function changeLocale(value: Locale) {
    const url = new URL(window.location.href);
    url.searchParams.set('lang', value);
    window.history.replaceState(window.history.state, '', url);
    setLocale(value);
  }

  return (
    <div className="admin-entry">
      <header className="admin-entry-header">
        <span className="admin-wordmark">shadow</span>
        <label className="admin-language">
          {labels.language}
          <select className="ui-field" value={locale} onChange={event => changeLocale(event.target.value === 'en' ? 'en' : 'ru')}>
            <option value="ru" lang="ru">Русский</option>
            <option value="en" lang="en">English</option>
          </select>
        </label>
      </header>
      <main className="admin-entry-content">
        <Card className="admin-sign-in">
          <h1>{labels.title}</h1>
          <p className="ui-muted">{labels.description}</p>
          <Notice tone="warning">{labels.unavailable}</Notice>
          <p className="ui-muted">{labels.account}</p>
        </Card>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
