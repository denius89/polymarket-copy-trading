"""Exact public recovery input before any proof or quota access."""
import re

import bootstrap
from controller import Rejection, exact
from email_app import EmailApp


class RecoveryApp(EmailApp):
    def dispatch_entry(self, method, path, query, body, headers):
        if method == "POST" and re.fullmatch(r"/api/auth/contexts/[^/]+/operations/[^/]+/login-cookie", path):
            exact(body, {"requestSchemaVersion", "commandType"})
            if type(body["commandType"]) is not str or body["commandType"] not in {"C02", "AUTH_TOTP_VERIFY"}:
                raise Rejection(400, "INVALID_REQUEST")
        return super().dispatch_entry(method, path, query, body, headers)
