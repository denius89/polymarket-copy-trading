"""Private synthetic transport probe for real context creation and C01/C03.

Operator inputs arrive on stdin. Reports never contain addresses, codes, proofs,
cookies or provider responses. No automatic resend, wait extension or unknown retry.
"""
import argparse
import json
import sys
import uuid

from client_probe import Client
from dependency import private_json
from fault_probe import Checks, emit, receive, source
from provider import six_digits


def create(client, check, label):
    response = client.request("/api/auth/contexts", {"requestSchemaVersion": "v1"})
    check(label + "_created", response[0] == 201 and response[1]["authContext"]["stage"] == "ready"
          and response[1]["authContext"]["accessConfirmed"] is False)
    ctx = response[1]["authContext"]["authContextId"]
    check(label + "_only_context_cookie", "__Host-shadow-authctx-" + ctx in response[2].get("Set-Cookie", "")
          and "user-login" not in response[2].get("Set-Cookie", ""))
    current = client.request("/api/auth/contexts/" + ctx + "?requestSchemaVersion=v1")
    check(label + "_confirmed", current[0] == 200 and current[1]["authContext"]["accessConfirmed"] is True
          and current[2].get("Set-Cookie") is None)
    return ctx


def request(ctx, email, locale="en"):
    return {"requestSchemaVersion": "v1", "commandType": "C01", "authContextId": ctx,
            "authOperationId": str(uuid.uuid4()), "email": email, "locale": locale}


def verify(ctx, challenge, code):
    return {"requestSchemaVersion": "v1", "commandType": "C02", "authContextId": ctx,
            "authOperationId": str(uuid.uuid4()), "challengeId": challenge, "code": six_digits(code)}


def historical(client, req):
    return client.operation(req["authContextId"], req["authOperationId"], req["commandType"])


def run(config, ca, mode):
    client, check = Client(config["origin"], ca), Checks()
    ctx = create(client, check, "initial")
    original = request(ctx, config["email"], "ru" if mode == "unsupported_locale" else "en")
    sources = [source(original)]
    emit({"event": "email_request_ready", "source": sources[0], "mode": mode})
    first = client.request("/api/auth/request", original)
    if mode == "unsupported_locale":
        check("locale_unavailable_no_cookie", first[0] == 503 and first[2].get("Set-Cookie") is None)
        saved = historical(client, original)
        check("locale_no_false_accepted", saved[0] == 202 and saved[1]["result"] is None)
        return {"profile": "email-entry-locale-v1", "checks": check.rows, "sources": sources,
                "limits": ["no external effect requires independent DB/provider/mailbox observation"]}
    if mode == "unknown":
        check("send_unknown_no_cookie", first[0] == 503 and first[2].get("Set-Cookie") is None)
        saved = historical(client, original)
        check("unknown_original_unresolved", saved[0] == 202 and saved[1]["status"] == "unresolved"
              and saved[1]["result"] is None and saved[1]["resolvedAt"] is None)
        repeated = client.request("/api/auth/request", original)
        check("unknown_exact_repeat_still_unknown", repeated[0] == 503)
        # Deliberate negative bypass test, never used as recovery of the original.
        other = Client(config["origin"], ca)
        other_ctx = create(other, check, "other")
        bypass = request(other_ctx, config["email"])
        sources.append(source(bypass))
        blocked = other.request("/api/auth/request", bypass)
        check("unknown_address_blocks_other_context", blocked[0] == 503)
        return {"profile": "email-entry-unknown-v1", "checks": check.rows, "sources": sources,
                "limits": ["unknown remains unresolved", "dispatch counts require independent observation"]}
    check("request_accepted_resolved", first[0] == 202 and first[1]["status"] == "resolved"
          and first[1]["result"]["kind"] == "email_dispatch_accepted" and first[2].get("Set-Cookie") is None)
    original_history = historical(client, original)
    check("request_history_no_cookie", original_history[0] == 200 and original_history[2].get("Set-Cookie") is None)
    repeated = client.request("/api/auth/request", original)
    check("accepted_exact_replay", repeated[0] == 202 and repeated[1]["result"] == first[1]["result"]
          and repeated[1]["resolvedAt"] == first[1]["resolvedAt"])
    challenge = first[1]["result"]["challengeId"]
    emit({"event": "need_proven_wrong_code", "context_id": ctx, "challenge_id": challenge})
    negative = verify(ctx, challenge, receive({"code"})["code"])
    sources.append(source(negative))
    rejected = client.request("/api/auth/verify", negative)
    check("wrong_active_code_rejected", rejected[0] == 401 and rejected[1]["reasonCode"] == "AUTH_VERIFICATION_FAILED"
          and rejected[2].get("Set-Cookie") is None)
    history = historical(client, negative)
    check("wrong_result_saved", history[0] == 200 and history[1]["result"] == {
        "kind": "verification_rejected", "reasonCode": "AUTH_VERIFICATION_FAILED"})
    check("wrong_exact_replay", client.request("/api/auth/verify", negative)[0] == 401)
    emit({"event": "await_resend_window_and_snapshot", "context_id": ctx,
          "resend_not_before_at": first[1]["result"]["resendNotBeforeAt"]})
    ready = receive({"window_open", "snapshot_captured"})
    check("operator_resend_ready", ready["window_open"] is True and ready["snapshot_captured"] is True)
    resend = {"requestSchemaVersion": "v1", "commandType": "C03", "authContextId": ctx,
              "authOperationId": str(uuid.uuid4()), "expectedChallengeId": challenge, "locale": "en"}
    sources.append(source(resend))
    second = client.request("/api/auth/resend", resend)
    check("resend_new_challenge", second[0] == 202 and second[1]["result"]["kind"] == "email_dispatch_accepted"
          and second[1]["result"]["challengeId"] != challenge)
    old = historical(client, original)
    check("resend_preserves_first_history", old[1]["result"] == original_history[1]["result"]
          and old[1]["resolvedAt"] == original_history[1]["resolvedAt"])
    old_attempt = verify(ctx, challenge, negative["code"])
    sources.append(source(old_attempt))
    stale = client.request("/api/auth/verify", old_attempt)
    check("old_challenge_conflict", stale[0] == 409 and stale[1]["reasonCode"] == "AUTH_CONTEXT_STATE_CONFLICT")
    emit({"event": "need_current_email_code", "context_id": ctx,
          "challenge_id": second[1]["result"]["challengeId"]})
    good = verify(ctx, second[1]["result"]["challengeId"], receive({"code"})["code"])
    sources.append(source(good))
    direct = client.request("/api/auth/verify", good)
    check("current_email_success", direct[0] == 200)
    saved = historical(client, good)
    check("current_email_saved", saved[0] == 200)
    result = saved[1]["result"]
    action, final_op = "C02", good["authOperationId"]
    if result["kind"] == "auth_step_required":
        check("requires_totp", result["stage"] == "totp_verification" and direct[2].get("Set-Cookie") is None
              and direct[1]["nextAction"] == "complete_totp")
        emit({"event": "need_totp_code", "context_id": ctx, "challenge_id": result["challengeId"]})
        totp = verify(ctx, result["challengeId"], receive({"code"})["code"])
        totp["commandType"] = action = "AUTH_TOTP_VERIFY"
        final_op = totp["authOperationId"]
        sources.append(source(totp))
        check("totp_success", client.request("/api/auth/totp/verify", totp)[0] == 200)
        saved = historical(client, totp)
        result = saved[1]["result"]
    check("full_login_from_original", result["kind"] == "login_completed"
          and result["completion"]["authContextId"] == ctx and result["completion"]["authOperationId"] == final_op)
    login = result["completion"]["loginId"]
    me = client.me(login)
    check("same_login_q01", me[0] == 200 and me[1]["authenticated"] is True and me[2].get("X-Shadow-Login-Id") == login)
    recovery = client.operation(ctx, final_op, action, recover=True)
    check("q01_closed_original_window", recovery[0] == 409 and recovery[1]["reasonCode"] == "AUTH_COOKIE_RECOVERY_CLOSED")
    return {"profile": "email-entry-success-v1", "checks": check.rows, "sources": sources, "login_id": login,
            "limits": ["synthetic confirmed existing user only", "not browser evidence", "provider/mail/DB counts require independent collection"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--ca", required=True)
    parser.add_argument("--mode", choices=("success", "unknown", "unsupported_locale"), required=True)
    args = parser.parse_args()
    try:
        emit(run(private_json(args.config), args.ca, args.mode))
    except Exception as exc:
        emit({"passed": False, "error_type": type(exc).__name__})
        raise SystemExit(1)
