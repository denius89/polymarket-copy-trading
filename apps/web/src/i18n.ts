import type {Locale} from './api';
export const copy = {
  ru: {
    home:'Главная',traders:'Трейдеры',positions:'Позиции',activity:'Активность',help:'Помощь',account:'Профиль',funds:'Средства',
    demo:'Демо · без реальных денег',intro:'Познакомьтесь с копированием на демо',introText:'Выберите трейдера, задайте ограничения и проверьте настройки. Старт создаёт пустую виртуальную сессию.',
    explore:'Выбрать трейдера',firstCatalog:'Выберите трейдера',synthetic:'Учебные данные',notConnected:'Копирование сделок пока не подключено.',
    retry:'Повторить',unavailable:'Данные пока недоступны',catalogChanged:'Каталог изменился. Обновите список.',refresh:'Обновить список',
    setup:'Настройки копирования',yourSettings:'Ваши настройки',amount:'Сумма',percent:'% от сделки',budget:'Демо-бюджет',fixedBuy:'Сумма новой покупки',copyPercent:'Доля сделки трейдера',marketLimit:'Лимит на рынок',dailyLimit:'Лимит покупок за день',limits:'Ограничения',check:'Проверить настройки',
    review:'Проверка перед запуском',start:'Запустить демо-сессию',back:'Назад',login:'Войти по email',email:'Email',sendCode:'Отправить код',emailCode:'Код из письма',totpCode:'Код из приложения',confirm:'Подтвердить',
    signIn:'Вход',signInInfo:'Кошелёк и оплата не нужны. Подключённая 2FA нужна при новом входе.',unknown:'Результат пока не подтверждён. Проверьте исходную операцию, прежде чем повторять действие.',checkOutcome:'Проверить результат',
    emptySession:'Пустая демо-сессия',emptyCopy:'Копирование пока не подключено. Исполнений нет.',available:'Доступно',inPositions:'В позициях',inReserve:'В резерве',balance:'Стоимость демо-счёта',
    pending:'Ожидаем результат',notReady:'Этот раздел ещё не подключён к серверу полигона.',selectVenue:'Площадка',noTraders:'На этой площадке пока нет доступных трейдеров.',viewProfile:'Посмотреть профиль',configure:'Настроить копирование',
    loginRequired:'Для запуска нужен подтверждённый вход.',recover:'Потеряли устройство?',totpUnavailable:'Подключение 2FA на полигоне пока недоступно.',logout:'Выйти',loading:'Загрузка…'
  },
  en: {
    home:'Home',traders:'Traders',positions:'Positions',activity:'Activity',help:'Help',account:'Account',funds:'Funds',
    demo:'Demo · no real money',intro:'Explore copying in a demo',introText:'Choose a trader, set your limits, and review the setup. Starting creates an empty virtual session.',
    explore:'Choose a trader',firstCatalog:'Choose a trader',synthetic:'Synthetic data',notConnected:'Trade copying is not connected yet.',
    retry:'Retry',unavailable:'Data is currently unavailable',catalogChanged:'The catalog changed. Refresh the list.',refresh:'Refresh list',
    setup:'Copy settings',yourSettings:'Your settings',amount:'Amount',percent:'% of trade',budget:'Demo budget',fixedBuy:'New purchase amount',copyPercent:'Share of trader trade',marketLimit:'Market limit',dailyLimit:'Daily buy limit',limits:'Limits',check:'Review settings',
    review:'Review before starting',start:'Start demo session',back:'Back',login:'Sign in with email',email:'Email',sendCode:'Send code',emailCode:'Email code',totpCode:'Authenticator code',confirm:'Confirm',
    signIn:'Sign in',signInInfo:'No wallet or payment. Connected 2FA is required at each new sign-in.',unknown:'The result is not confirmed yet. Check the original operation before trying again.',checkOutcome:'Check result',
    emptySession:'Empty demo session',emptyCopy:'Copying is not connected yet. No fills.',available:'Available',inPositions:'In positions',inReserve:'In reserve',balance:'Demo account value',
    pending:'Waiting for result',notReady:'This section is not connected to the polygon server yet.',selectVenue:'Venue',noTraders:'There are no available traders on this venue yet.',viewProfile:'View profile',configure:'Configure copying',
    loginRequired:'A confirmed sign-in is required to start.',recover:'Lost your device?',totpUnavailable:'2FA enrollment is not available on the polygon yet.',logout:'Sign out',loading:'Loading…'
  }
} as const;
export function getInitialLocale():Locale { const query=new URLSearchParams(location.search).get('lang'); return query==='en'||query==='ru'?query:(localStorage.getItem('shadow.locale')==='en'?'en':'ru'); }
