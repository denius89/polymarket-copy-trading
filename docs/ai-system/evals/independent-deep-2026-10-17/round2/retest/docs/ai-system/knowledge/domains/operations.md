# Инфраструктура, серверы и эксплуатация

Опоры: KB08 proposed architecture; P07/P08 financial recovery; D09 SLO, D10 backups, D13 Docker, D15 telemetry, D16 DoS. D14 Ubuntu не предоставил достаточный текст при текущем чтении; выбрать доступную version-specific официальную главу перед конкретным runbook.

## Планирование

Сначала требования: нагрузка/freshness, region/residency, доверенные границы, RPO/RTO, SLO и бюджет. Managed vs VPS оцениваются с эксплуатационной стоимостью, ограничениями и exit; предложение стека не deployed fact. Разделение процессов/контейнеров само по себе не создаёт независимый failure domain.

В cost model включаются backup/restore testing, storage/egress, telemetry, CDN/WAF, secrets/key custody, provider quotas и support. Неизвестные цены не нулевые; текущая цена требует даты/региона/условий. Не арендовать ресурсы из планировочного сравнения.

## Hardening и доступ

До закрытия старого доступа проверить новый путь и console recovery. Отдельно identity/MFA/SSH, firewall/ingress/egress, runtime identity, daemon socket/privileged mounts, time sync, patch/rollback и DNS/TLS renewal. Ограничение портов не решает компрометацию signer; контейнер не абсолютная security boundary.

Секреты доставляются и отзываются через предусмотренные доверенные механизмы; в обучении только условные placeholders без рабочих значений. Рекомендация «rootless» или конкретная команда нуждается в совместимости с OS/runtime и не исполняется автоматически.

## Эксплуатация и восстановление

- SLI описывает наблюдение, SLO — целевой уровень на окне, error budget/alert — решение по риску. Придуманный 99.99% не измеренная надёжность.
- Различать edge/origin/app limits, quotas, WS/backpressure, retry/reconnect storms и дорогие запросы. WAF без origin controls — не полная защита от DDoS.
- Telemetry должна соединять operation IDs и причины/статусы, но не содержать secrets/лишнюю PII или бесконечную cardinality адресов/трейдеров.
- Backup создаёт копию; restore drill доказывает конкретное восстановление в условиях. Восстановление БД не доказывает безопасный повтор внешних side effects.
- После восстановления сначала read-only reconciliation submitted/unknown operations и актуальных controls. Не запускать старый outbox вслепую. Recovery подтверждение не заменяет подтверждение самой денежной операции.

Deployment/runbook содержит preflight, bounded rollout, verification, abort/rollback или forward repair, ответственного и evidence. Ни один документ этой базы не является поручением применять его к реальному серверу.
