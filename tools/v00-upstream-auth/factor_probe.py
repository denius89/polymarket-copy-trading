"""One stale-factor-version HTTP probe. No factor writer or provider TOTP call.

The operator independently changes the trusted test mapping while the probe is
paused. This client sends one original TOTP attempt and never retries it.
"""
import argparse
import json
import re

from dependency import private_json
from fault_probe import Checks, bootstrap, body, emit, history, receive, source


def run(config, ca, name):
    check = Checks()
    fixture, client = bootstrap(config, ca, name, check)
    emit({"event": "need_email_code", "fixture": name})
    email_request = body(fixture["context_id"], fixture["email_challenge_id"], "C02", receive({"code"})["code"])
    direct = client.request("/api/auth/verify", email_request)
    check("email_stage_no_login_cookie", direct[0] == 200 and direct[2].get("Set-Cookie") is None)
    email_saved = history(client, email_request)
    check("email_original_totp_stage", email_saved[0] == 200
          and email_saved[1]["result"]["kind"] == "auth_step_required"
          and email_saved[1]["result"]["stage"] == "totp_verification"
          and email_saved[2].get("Set-Cookie") is None)
    challenge = email_saved[1]["result"]["challengeId"]
    emit({"event": "factor_guard_ready", "context_id": fixture["context_id"],
          "email_source": source(email_request), "challenge_id": challenge,
          "requirement": "operator_commits_trusted_current_version_change_and_captures_rr_snapshots"})
    transition = receive({"transition_observed", "evidence_id", "code"})
    if (transition["transition_observed"] is not True or not isinstance(transition["evidence_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}", transition["evidence_id"])):
        raise ValueError("independent transition evidence required")
    request = body(fixture["context_id"], challenge, "AUTH_TOTP_VERIFY", transition["code"])
    emit({"event": "stale_factor_dispatching", "source": source(request)})
    reply = client.request("/api/auth/totp/verify", request)
    check("stale_version_conflict_no_cookie", reply[0] == 409
          and reply[1]["reasonCode"] == "AUTH_CONTEXT_STATE_CONFLICT"
          and reply[2].get("Set-Cookie") is None)
    saved = history(client, request)
    expected_ref = {"authContextId": request["authContextId"], "authOperationId": request["authOperationId"],
                    "commandType": "AUTH_TOTP_VERIFY"}
    check("original_unresolved_without_wrong_code_result", saved[0] == 202
          and saved[1]["operationRef"] == expected_ref and saved[1]["status"] == "unresolved"
          and saved[1]["result"] is None and saved[1]["resolvedAt"] is None
          and saved[2].get("Set-Cookie") is None)
    prior = history(client, email_request)
    check("historical_email_stage_preserved", prior[0] == 200
          and prior[1]["result"] == email_saved[1]["result"]
          and prior[1]["resolvedAt"] == email_saved[1]["resolvedAt"]
          and prior[2].get("Set-Cookie") is None)
    final = history(client, request)
    check("original_still_unresolved", final[0] == 202 and final[1]["operationRef"] == expected_ref
          and final[1]["status"] == "unresolved" and final[1]["result"] is None
          and final[1]["resolvedAt"] is None and final[2].get("Set-Cookie") is None)
    return {"profile": "upstream-stale-factor-version-v1", "checks": check.rows,
            "source": source(request), "email_source": source(email_request),
            "transition_evidence_id": transition["evidence_id"],
            "limits": ["DB guards, factor mapping, counters and zero effects require independent snapshots",
                       "no factor-management lifecycle, external MFA callback or concurrent transition proof",
                       "no exact retry, new key, challenge renewal or provider verification retry"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--ca", required=True)
    parser.add_argument("--fixture", default="factor_stale")
    args = parser.parse_args()
    try:
        emit(run(private_json(args.config), args.ca, args.fixture))
    except Exception as exc:
        failed = {"passed": False, "error_type": type(exc).__name__}
        if isinstance(exc, AssertionError) and len(exc.args) == 1 and isinstance(exc.args[0], str) and re.fullmatch(r"[A-Za-z0-9_]{1,96}", exc.args[0]):
            failed["failed_check"] = exc.args[0]
        emit(failed)
        raise SystemExit(1)
