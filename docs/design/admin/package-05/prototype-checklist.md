# Проверка прототипа личного аккаунта

- [x] Структурно: 254 RU + 254 EN, 76 новых макета, profile destinations существуют.
- [x] Снаружи профиля нет прежних RU/EN-кнопок; вход/expired/revoked без чужого personal avatar.
- [x] Present RU: профиль → язык → EN saved.
- [x] Present RU: профиль → сессии → завершить остальные → результат → logout/login.
- [x] Визуально: имя RU, сессии RU, profile RU/EN, current language EN, UI kit.
- [ ] Совместно вычитать email verification, MFA setup/replace/lost, recovery codes, все error paths RU/EN.
- [ ] При реализации: keyboard/focus, provider state, real server revocation, CSRF/replay/rate limits, avatar validation, all-role own-resource tests.

Числа и результаты — fixture. Проверка прототипа не означает работу безопасности. Переход языка между страницами Figma открывает другой URL; сохранение предпочтения и сохранение текущего маршрута относятся к реализации.
