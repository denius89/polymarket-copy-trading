---
name: cct-server-hardening
description: Prepare or review environment-specific server provisioning and hardening runbooks with recovery access and evidence. Does not grant authorization to connect to or modify servers.
---

# S18 · Подготовка настройки и hardening

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Определи target OS/version/environment/provider, полномочия и доступный recovery path. Если поручен runbook/review, не подключайся к серверу; иной явно порученный режим оценивай по текущим полномочиям, не по историческому этапу подготовки навыка.
2. Раздели IAM/accounts/SSH, key lifecycle/MFA, network ingress/egress/firewall и trusted admin path; перед запретом доступа нужна проверенная новая сессия и console recovery.
3. Проверь DNS/TLS/renewal, patch/rollback, time sync, disk/runtime limits и service identity. Container root/daemon socket/privileged mounts меняют trust boundary.
4. Для secrets опиши защищённую доставку/rotation/revoke без реальных значений; persistence/logs/backups не должны утекать. Не считать контейнер полной изоляцией.
5. Составь version-specific шаги с preflight, verification, rollback и stop conditions. Недоступный официальный источник оставляй unverified; не запускай команды/IaC по документальной задаче.

## Дополнительные материалы

[пакет S18](../../../docs/ai-system/learning/S18.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/operations.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
