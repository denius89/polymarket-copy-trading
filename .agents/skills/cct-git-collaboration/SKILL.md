---
name: cct-git-collaboration
description: Manage scoped Git collaboration and review in the existing project, preserving dirty work and distinguishing commit, push, merge and deploy. Use for Git workflows, not automatic publication.
---

# S20 · Git, PR и сохранение изменений

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Определи репозиторий, task baseline, branch/HEAD, dirty/untracked work и remotes. Не stage/reset/clean чужие изменения; worktree использовать по ситуации и применимым инструкциям, не требуя нового по умолчанию.
2. Ограничь diff результатом поручения; до редактирования прочитай относящиеся ADR и ownership. Конфликты, затрагивающие смысл, не решай выбором ours/theirs вслепую.
3. В review проверяй дефекты и evidence на конкретных строках; стиль отдели от ошибки. Branch protected=false не доказывает отсутствие rulesets или иных controls.
4. Перед запрошенным commit выполни требуемые CONTRIBUTING проверки и проверь staged diff на постороннее/секреты; сообщения и PR описывают итог, не историю диалога.
5. Сохраняй результат по действующему REPOSITORY_GUIDE и уже данному разрешению владельца на commit/push/PR/merge; не запрашивай его заново. Deploy, финансовые действия и права доступа этим разрешением не покрываются. После создания PR прикрепи его через доступный app tool; отдельный PR только ради synthetic проверки не нужен.

## Дополнительные материалы

[пакет S20](../../../docs/ai-system/learning/S20.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/collaboration.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
