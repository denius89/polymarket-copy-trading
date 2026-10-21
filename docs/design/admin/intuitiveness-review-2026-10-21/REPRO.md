# Narrow repeat attempt · TKT-1042 status transition

2026-10-21. Requested one-chain fresh-tab repeat: direct 2185:22038 -> Change status -> Waiting for customer. No settings changes, message input or sending authorized/performed.

Attempted CUA createBrowserTab('iab', 'https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2185-22038&starting-point-node-id=2185-22038&scaling=scale-down', {visible:false}). Tool returned: Browser is not available: iab.

No tab was created, so no before/after screenshots or second-run AX observations were obtainable. No tab remained to close. Did not switch to an existing/user tab or modify browser/settings. No second reproduction claimed.

Original-run exact observed chain, preserved as evidence rather than new observations:

- Source 2185:22038, arrived from support queue after users sidebar Support: AX Message user Amina Rahman, 'Трейдер купил позицию, но в моём демо-копировании покупки нет. Почему?', '13 октября · 10:12 UTC · MSG-1042-A · Получено'; Message reply Nora Aziz, 'Проверяем связанную сессию. Поддержка не меняет ваши торговые лимиты и не отправляет сделки.', '13 октября · 10:15 UTC · MSG-1042-B · Отправлено'. No MSG-1042-C in this source AX output or source screenshot.
- Clicked visible Change status -> 2187:23231. AX instruction: 'Состояние отправки сообщения отдельно от статуса обращения. Закрытие и возобновление проверяются по полномочиям.'
- Clicked visible Waiting for customer -> 2187:23342. New AX Message reply Oleg Smirnov, 'Полная сумма покупки не помещалась в лимит сессии. Проверьте свои настройки риска. Историю пропуска можно открыть в активности.', '10:20 UTC · MSG-1042-C · Отправлено'. Ticket status 'Ждём клиента'. No response entered/sent during the intervening steps.

Severity qualification: retain P1 as a single observed prototype-state inconsistency. The requested fresh direct-entry reproduction is NOT VERIFIED due browser unavailability; do not label reproducible on every entry or runtime message behavior. If the parent requires repeatability before ranking as P1, report this as an observed high-impact hypothesis requiring recheck instead of a confirmed recurring defect.
