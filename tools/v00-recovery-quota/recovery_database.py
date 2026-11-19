"""Deadline-bounded, role-separated calls for the isolated recovery profile."""
import time

import bootstrap
from dependency import Unavailable
from email_database import EmailTransaction, EmailIngressTransaction


class RecoveryTransaction(EmailTransaction):
    methods = (EmailTransaction.methods - {"recover"}) | {
        "recovery_target", "recovery_once", "recover_completion_replay"}

    def __init__(self, command, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Unavailable("original recovery deadline elapsed")
        super().__init__(command, budget=min(4.5, remaining))
        # Process creation and every read/write use the original absolute bound.
        self.deadline = min(self.deadline, deadline)


class RecoveryQuotaTransaction(RecoveryTransaction):
    methods = frozenset({"recovery_admit", "recovery_seal"})


class CompletionTransaction(EmailTransaction):
    """Existing10s commands: plan creates the DB-local replay permit."""
    methods = (EmailTransaction.methods - {"recover"}) | {"recover_completion_replay"}
