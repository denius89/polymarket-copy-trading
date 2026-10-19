---
name: cct-server-hardening
description: Prepare or review environment-specific server provisioning and hardening runbooks with recovery access and evidence. Does not grant authorization to connect to or modify servers.
---

# S18 · Подготовка настройки и hardening

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Определи target OS/version/environment/provider, полномочия и доступный recovery path. Здесь текущая задача — учебный runbook, не подключение к серверу.
2. Раздели IAM/accounts/SSH, key lifecycle/MFA, network ingress/egress/firewall и trusted admin path; перед запретом доступа нужна проверенная новая сессия и console recovery.
3. Проверь DNS/TLS/renewal, patch/rollback, time sync, disk/runtime limits и service identity. Container root/daemon socket/privileged mounts меняют trust boundary.
4. Для secrets опиши защищённую доставку/rotation/revoke без реальных значений; persistence/logs/backups не должны утекать. Не считать контейнер полной изоляцией.
5. Составь version-specific шаги с preflight, verification, rollback и stop conditions. Недоступный официальный источник оставляй unverified; не запускай команды/IaC по документальной задаче.

## Знания и проверка

Для предметной работы: [пакет S18](../../../docs/ai-system/learning/S18.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/operations.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Найти риск lockout и неверный порядок проверки.
- Предложить preflight/recovery/verification, не выполнять команды на сервере.

Смежные процедуры: S08, S17, S20. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
