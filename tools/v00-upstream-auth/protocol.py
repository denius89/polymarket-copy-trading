"""Closed private decoder for the PR239 V00 bridge. Unknown fields fail closed."""
from datetime import datetime
import re
import uuid

from dependency import Unavailable, aad

ERRORS = {
    400: {"INVALID_REQUEST"},
    401: {"AUTH_REQUIRED", "AUTH_EXPIRED", "AUTH_REVOKED", "AUTH_VERIFICATION_FAILED"},
    403: {"ACCESS_DENIED"},
    404: {"RESOURCE_NOT_FOUND"},
    409: {"KEY_REUSE_CONFLICT", "AUTH_CONTEXT_STATE_CONFLICT",
          "AUTH_COOKIE_RECOVERY_CLOSED", "AUTH_COOKIE_RECOVERY_NOT_APPLICABLE"},
    429: {"RATE_LIMITED"},
    503: {"SERVICE_UNAVAILABLE", "RECORD_UNAVAILABLE"},
}


def require(ok):
    if not ok:
        raise Unavailable("invalid upstream contract")


def exact(value, fields):
    require(type(value) is dict and set(value) == set(fields.split()))


def uid(value):
    try:
        require(type(value) is str and str(uuid.UUID(value)) == value)
    except (ValueError, AttributeError, TypeError):
        raise Unavailable("invalid upstream identifier") from None
    return value


def timestamp(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", value))
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise Unavailable("invalid upstream time") from None


def result(value, ref):
    require(type(value) is dict)
    kind = value.get("kind")
    if kind == "login_completed":
        exact(value, "kind completion")
        c = value["completion"]
        exact(c, "authContextId authOperationId loginId realm completedAt")
        require(c["authContextId"] == ref["context_id"] and
                c["authOperationId"] == ref["operation_id"] and c["realm"] == "user")
        uid(c["loginId"]); timestamp(c["completedAt"])
    elif kind == "auth_step_required":
        exact(value, "kind stage challengeId challengeIssuedAt challengeExpiresAt")
        require(ref["action"] == "C02" and value["stage"] == "totp_verification")
        uid(value["challengeId"])
        lifetime = timestamp(value["challengeExpiresAt"]) - timestamp(value["challengeIssuedAt"])
        require(0 < lifetime.total_seconds() <= 300)
    elif kind == "verification_rejected":
        exact(value, "kind reasonCode")
        require(value["reasonCode"] == "AUTH_VERIFICATION_FAILED")
    elif kind == "auth_completion_not_issued":
        exact(value, "kind completionAttemptRef completedAt login cause decidedAt")
        attempt = value["completionAttemptRef"]
        exact(attempt, "authContextId authOperationId commandType")
        require(attempt == {"authContextId": ref["context_id"],
                            "authOperationId": ref["operation_id"], "commandType": ref["action"]})
        require(value["completedAt"] is None and value["login"] is None)
        # Cause whitelist is supplied below from the accepted D02, never provider text.
        require(value["cause"] in LATE_CAUSES)
        timestamp(value["decidedAt"])
    else:
        raise Unavailable("unsupported upstream result")
    return kind


# D02 §8; the decoder reads the outcome, never chooses a reconciliation cause.
LATE_CAUSES = frozenset({"security_revoked", "context_revoked", "context_expired", "execution_closed"})


def metadata(value, ref, ids=None):
    aad(value)
    require(value["source_context_id"] == ref["context_id"] and
            value["source_operation_id"] == ref["operation_id"])
    uid(value["login_id"]); uid(value["secret_id"]); timestamp(value["reveal_until"])
    if ids:
        require(value["login_id"] == ids["login_id"] and value["secret_id"] == ids["secret_id"])


def decode(method, value, ref=None, ids=None):
    require(type(value) is dict and type(value.get("http")) is int)
    http = value["http"]
    if "reason" in value:
        exact(value, "http reason")
        require(http in ERRORS and type(value["reason"]) is str and value["reason"] in ERRORS[http])
        return "error"
    if method == "seal_email":
        if "replay" in value:
            exact(value, "http replay result")
            require(http == 200 and value["replay"] is True)
            result(value["result"], ref)
            return "replay"
        exact(value, "http dispatch_allowed dispatch_id")
        require(http == 200 and type(value["dispatch_allowed"]) is bool)
        uid(value["dispatch_id"])
        return "seal"
    if method in {"plan_email", "plan_totp"}:
        require(type(value.get("replay")) is bool)
        if "result" in value:
            exact(value, "http replay result")
            kind = result(value["result"], ref)
            if value["replay"]:
                require(http == 200)
                return "replay"
            require((method == "plan_email" and kind == "auth_step_required" and http == 200)
                    or (method == "plan_totp" and kind == "verification_rejected" and http == 401))
            return "intermediate"
        exact(value, "http replay metadata completed_at login_expires_at")
        require(http == 200 and value["replay"] is False)
        metadata(value["metadata"], ref, ids)
        completed = timestamp(value["completed_at"])
        require(completed < timestamp(value["login_expires_at"]))
        lifetime = timestamp(value["metadata"]["reveal_until"]) - completed
        require(0 < lifetime.total_seconds() <= 300)
        return "plan"
    if method == "complete":
        exact(value, "http result login_expires_at")
        require(http == 200 and result(value["result"], ref) == "login_completed")
        require(timestamp(value["login_expires_at"]) > timestamp(value["result"]["completion"]["completedAt"]))
        return "complete"
    if method == "read_operation":
        exact(value, "http status result resolved_at")
        if value["status"] == "resolved":
            require(http == 200); result(value["result"], ref); timestamp(value["resolved_at"])
        else:
            require(http == 202 and value["status"] == "unresolved" and
                    value["result"] is None and value["resolved_at"] is None)
        return "read"
    if method == "recover":
        exact(value, "http result ciphertext nonce key_id credential_key_id cookie_digest metadata login_expires_at")
        require(http == 200 and result(value["result"], ref) == "login_completed")
        metadata(value["metadata"], ref)
        require(value["result"]["completion"]["loginId"] == value["metadata"]["login_id"])
        require(all(type(value[k]) is str and value[k] for k in
                    ("ciphertext", "nonce", "key_id", "credential_key_id", "cookie_digest")))
        require(re.fullmatch(r"[0-9a-f]{64}", value["cookie_digest"]))
        timestamp(value["login_expires_at"])
        return "recover"
    if method == "q01":
        exact(value, "http authenticated login_id actor_id")
        require(http == 200 and value["authenticated"] is True)
        uid(value["login_id"]); uid(value["actor_id"])
        require(value["login_id"] == ref["login_id"])
        return "q01"
    if method in {"logout_prepare", "logout_continue"}:
        exact(value, "http logout_context_id target_login_id source_context_id created_at expires_at")
        require(http == 201 and value["logout_context_id"] == ref["logout_context_id"])
        uid(value["target_login_id"])
        require(value["source_context_id"] == ref.get("source_context_id"))
        if method == "logout_prepare":
            require(value["target_login_id"] == ref["login_id"])
        require((timestamp(value["expires_at"]) - timestamp(value["created_at"])).total_seconds() == 900)
        return "logout_prepare"
    if method in {"logout", "logout_result"}:
        if method == "logout":
            exact(value, "http result")
            require(http == 204)
        else:
            exact(value, "http status result target_login_id")
            uid(value["target_login_id"])
            if value["status"] == "unresolved":
                require(http == 202 and value["result"] is None)
                return "logout_read"
            require(http == 200 and value["status"] == "completed")
        r = value["result"]
        exact(r, "logout_context_id operation_id target_login_id confirmed_at")
        require(r["logout_context_id"] == ref["logout_context_id"] and r["operation_id"] == ref["operation_id"])
        uid(r["target_login_id"]); timestamp(r["confirmed_at"])
        if method == "logout_result":
            require(value["target_login_id"] == r["target_login_id"])
        return "logout"
    raise Unavailable("unsupported upstream wrapper result")
