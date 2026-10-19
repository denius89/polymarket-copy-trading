Статус runbook: учебный черновик с непроверенными platform-specific шагами. Официальная OS chapter вернула403, package version неизвестна, target OS/version/provider и recovery access не установлены. Блог для другой OS не является подтверждённой процедурой для этого target. Staging не устраняет риск lockout, компрометации и утечки secrets.

Блокирующие gaps: точная OS/runtime/package matrix, доступная официальная инструкция, trust chain установщика, console recovery, service identity, сертификаты/DNS, secret delivery/rotation/revoke и проверяемый rollback. Не включать curl installer | sudo sh, отключение TLS verification или seed в compose env как одобренные шаги. Credentials отсутствуют и не требуются для составления этого документа.

Безопасный skeleton:

1. Preflight: зафиксировать environment/version, scope разрешения, владельца, backup/restore evidence и доступную console. Старую сессию сохранять до проверки новой независимой сессии.
2. Service identity: описать отдельную минимальную роль, file permissions и runtime capabilities; проверить отсутствие privileged mounts и daemon socket доступа. Конкретные параметры оставить pending official verification.
3. TLS renewal: определить issuer, DNS/challenge и renewal mechanism; проверить dry-run/expiry alert и восстановление сертификата с проверкой chain/hostname, сохраняя verification.
4. Time sync: определить OS-supported механизм, источник времени, допустимое расхождение и мониторинг до signing-dependent операций.
5. Secrets: защищённая доставка, минимальные scopes, staged rotation, проверка нового credential и отдельное подтверждение revoke старого; никаких значений в logs/backups/KB.
6. Verification/rollback: health, permissions, renewal и восстановление в изоляции с evidence. При отсутствии recovery или несовместимости версии остановить применение.

Это порядок будущей проверки; команды не проверены и не выполнялись.
