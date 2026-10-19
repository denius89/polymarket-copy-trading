Модель доступа содержит блокирующие несоответствия intent. Границы доверия: support API→approval payload, worker→signer, owner session→исполнение и local disable→внешний credential. Название non-custodial не доказывает ограниченность полномочий.

| Угроза | Требуемый control | Имеющееся evidence / gap |
|---|---|---|
| Компрометация worker выводит средства | Signer разрешает только trade/cancel | Report даёт trade+withdraw |
| Support подменяет recipient | Read-only support; approval связан с recipient+amount+network | API редактирует recipient после approval |
| Устаревшая owner session | Проверка session и authorization при исполнении | Проверка только при открытии UI |
| Повтор/подмена подписи | Domain, nonce, payload binding | Протокол не приложен; в log только approvalId |
| Использование после disable | Подтверждённый внешний revoke | Disable 12:00; expiry 18:00; receipt отсутствует |

До expiry остаётся потенциальное шестичасовое окно внешних полномочий; фактическое злоупотребление не установлено. Раздельный treasury указан как intent, но независимость credentials, кошельков и signer enforcement не доказана.

Минимальные независимые проверки в изолированном контуре: прямой withdrawal запрос worker должен отвергаться signer; support mutation должна отвергаться сервером; изменение recipient, amount или network после approval должно инвалидировать approval. Повтор nonce и подпись другого domain должны отклоняться. Закрытая/revoked owner session должна блокировать исполнение независимо от открытого UI. После disable отдельно сверить внешний статус credential и receipt, не предполагая revoke.

Аудит должен связывать approvalId с неизменяемым hash одобренного payload и решением исполнителя без secrets. До получения этого evidence перечисленные gaps блокируют утверждение о соответствии модели доступа. Реальные переводы, revoke, сканирование и работа с ключами не выполнялись.
