"""Allowlisted upstream wrappers only. Runtime cannot invoke synthetic completion."""
import base64
import json

from dependency import SessionTransaction, Unavailable

METHODS = frozenset({"seal_email", "read_operation", "plan_email", "plan_totp",
                     "complete", "recover", "q01", "logout_prepare",
                     "logout_continue", "logout", "logout_result"})


class Transaction(SessionTransaction):
    def call(self, method, fields):
        if method not in METHODS:
            raise Unavailable("unsupported upstream wrapper")
        encoded = base64.b64encode(json.dumps(fields, separators=(",", ":"),
                                             allow_nan=False).encode()).decode()
        # PostgreSQL17 psql extended protocol: the parameter value is NOT part of
        # the server statement. PC12 must additionally disable error parameter
        # logging and verify that function error contexts never echo secrets.
        # Base64 has no quotes, whitespace, backslash or psql interpolation syntax.
        self.send("SELECT v00_upstream." + method +
                  "(convert_from(decode($1,'base64'),'UTF8')::jsonb)::text\n" +
                  "\\bind '" + encoded + "'\n\\g")
        try:
            result = json.loads(self.line())
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (ValueError, TypeError):
            raise Unavailable("invalid upstream response") from None


class IngressTransaction(Transaction):
    def call(self, method, fields):
        if method != "capture":
            raise Unavailable("unsupported ingress wrapper")
        return self._capture(fields)

    def _capture(self, fields):
        encoded = base64.b64encode(json.dumps(fields, separators=(",", ":"),
                                             allow_nan=False).encode()).decode()
        self.send("SELECT v00_upstream.capture(convert_from(decode($1,'base64'),'UTF8')::jsonb)::text\n" +
                  "\\bind '" + encoded + "'\n\\g")
        try:
            value = json.loads(self.line())
            if type(value) is not dict:
                raise ValueError()
            return value
        except (ValueError, TypeError):
            raise Unavailable("invalid ingress response") from None
