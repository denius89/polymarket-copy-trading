"""Strict private decoder for the isolated email-entry profile."""
from email_api import context_view, dispatch_result
from email_crypto import FIELDS as MATERIAL_FIELDS, FORMAT
from protocol import decode as legacy_decode, exact, require, result as legacy_result, timestamp, uid


def result(value, ref):
    if type(value) is dict and value.get("kind") == "email_dispatch_accepted":
        dispatch_result(value, ref["action"])
        return value["kind"]
    require(ref["action"] in {"C02", "AUTH_TOTP_VERIFY"})
    return legacy_result(value, ref)


def decode(method, value, ref=None, ids=None):
    require(type(value) is dict and type(value.get("http")) is int)
    if "reason" in value:
        return legacy_decode(method, value, ref, ids)
    if method in {"context_create", "context_read", "context_for_send"}:
        exact(value, "http auth_context observed_at paused_until pending_operation")
        require(value["http"] == (201 if method == "context_create" else 200))
        context_view(value["auth_context"], ref["context_id"], method == "context_create")
        observed = timestamp(value["observed_at"])
        require(observed >= timestamp(value["auth_context"]["createdAt"]))
        require(type(value["pending_operation"]) is bool)
        if value["paused_until"] is not None:
            timestamp(value["paused_until"])
        if method == "context_create":
            require(value["paused_until"] is None and not value["pending_operation"])
        return "context"
    if method in {"seal_send", "finalize_send", "seal_verify", "plan_email", "plan_totp"} and "result" in value:
        exact(value, "http replay result resolved_at historical_http_status")
        require(type(value["replay"]) is bool)
        kind = result(value["result"], ref)
        resolved = timestamp(value["resolved_at"])
        if kind == "email_dispatch_accepted":
            require(timestamp(value["result"]["acceptedAt"]) <= resolved)
        expected = {"email_dispatch_accepted": 202, "verification_rejected": 401,
                    "auth_step_required": 200, "login_completed": 200, "auth_completion_not_issued": 409}[kind]
        require(type(value["historical_http_status"]) is int and value["historical_http_status"] == expected
                and value["http"] == (200 if value["replay"] else expected))
        if not value["replay"]:
            require((method == "finalize_send" and kind == "email_dispatch_accepted")
                    or (method == "seal_verify" and kind == "verification_rejected")
                    or (method in {"plan_email", "plan_totp"} and kind in {"verification_rejected", "auth_step_required"}))
        return "replay" if value["replay"] else "intermediate"
    if method in {"seal_send", "seal_verify"}:
        fields = "http dispatch_allowed dispatch_id email_material" + (" locale" if method == "seal_send" else "")
        exact(value, fields)
        require(value["http"] == 200 and type(value["dispatch_allowed"]) is bool)
        uid(value["dispatch_id"])
        material = value["email_material"]
        exact(material, MATERIAL_FIELDS + " context_id")
        require(material["context_id"] == ref["context_id"] and material["cipher_format"] == FORMAT)
        if method == "seal_send":
            require(value["locale"] in {"en", "ru"})
        return "seal"
    if method == "send_observed":
        exact(value, "http recorded")
        require(value["http"] == 200 and type(value["recorded"]) is bool)
        return "witness"
    if method == "read_operation":
        exact(value, "http status result resolved_at")
        if value["status"] == "resolved":
            require(value["http"] == 200)
            result(value["result"], ref); timestamp(value["resolved_at"])
        else:
            require(value["http"] == 202 and value["status"] == "unresolved"
                    and value["result"] is None and value["resolved_at"] is None)
        return "read"
    return legacy_decode(method, value, ref, ids)
