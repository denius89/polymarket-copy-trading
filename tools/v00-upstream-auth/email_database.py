"""Closed roles for the separate v00_email test namespace; no installer calls."""
import base64
import json

from dependency import SessionTransaction, Unavailable


class EmailTransaction(SessionTransaction):
    methods = frozenset({"context_read", "context_for_send", "seal_send", "finalize_send",
        "seal_verify", "plan_email", "plan_totp", "complete", "read_operation", "recover",
        "q01", "logout_prepare", "logout_continue", "logout", "logout_result"})

    def call(self, method, fields):
        if method not in self.methods:
            raise Unavailable("unsupported email wrapper")
        encoded = base64.b64encode(json.dumps(fields, separators=(",", ":"), allow_nan=False).encode()).decode()
        self.send("SELECT v00_email." + method +
                  "(convert_from(decode($1,'base64'),'UTF8')::jsonb)::text\n" +
                  "\\bind '" + encoded + "'\n\\g")
        try:
            value = json.loads(self.line())
            if type(value) is not dict:
                raise ValueError()
            return value
        except (ValueError, TypeError):
            raise Unavailable("invalid email wrapper response") from None


class EmailIngressTransaction(EmailTransaction):
    methods = frozenset({"context_create", "capture"})


class EmailWitnessTransaction(EmailTransaction):
    methods = frozenset({"send_observed"})
