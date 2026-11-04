"""Operator-only: derive client cases without exporting factor secrets/DB credentials.

Reads DB-generated fixture config. Outputs NEW private controller/client configs.
Generate immediately before running; the wall-clock OTP is intentionally short lived.
"""
import json
import os
from pathlib import Path
import time
import uuid
from totp import decode_secret, hotp


def save_new(path, value):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream: json.dump(value, stream)


def prepare():
    controller = json.loads(Path(os.environ["V00_SEED_CONFIG"]).read_text())
    tokens = {principal: token for token, principal in controller["principals"].items()}
    client = {"controller_origin": os.environ["V00_CONTROLLER_ORIGIN"],
              "forbidden_tcp": json.loads(os.environ["V00_FORBIDDEN_TCP_JSON"]),
              "cases": [], "races": [], "lost_client_reply": []}

    def case(label, status, expected, code="468457", name=None):
        fixture = controller["cases"][label]
        return {"id": name or label, "api_token": tokens[fixture["principal_id"]], "route": "/v00/totp",
                "payload": {"operationId": str(uuid.uuid4()), "contextId": fixture["contextId"],
                            "challengeId": fixture["challengeId"], "code": code},
                "expected_http": status, "expected": expected}

    wall = controller["cases"]["wall_clock"]
    wall_code = hotp(decode_secret(controller["contexts"][wall["contextId"]]["secret_base32"]), int(time.time()) // 30)
    client["cases"].append(case("wall_clock", 200, {"kind": "totp_consumed"}, wall_code))
    first = case("collision", 200, {"kind": "totp_consumed", "consumed_steps": [153567, 153569]})
    client["cases"] += [first, first | {"id": "exact_replay", "same_as": "collision"},
        first | {"id": "key_conflict", "payload": first["payload"] | {"code": "000000"},
                 "expected_http": 409, "expected": {"reason": "payload_conflict"}}]
    for label in ["collision_reuse", "partial_overlap"]:
        client["cases"].append(case(label, 401, {"kind": "verification_rejected", "consumed_steps": []}))
    client["cases"].append(case("new_factor_version", 200, {"kind": "totp_consumed"}))
    for label in ["expired_challenge", "missing_current_challenge"]:
        client["cases"].append(case(label, 409, {"reason": "challenge_unavailable"}))
    for i in range(5):
        wrong = case("wrong_codes", 401, {"kind": "verification_rejected"}, "000000", "wrong_" + str(i + 1))
        client["cases"].append(wrong)
    client["cases"].append(wrong | {"id": "wrong_replay_no_counter", "same_as": "wrong_5"})
    client["cases"].append(case("wrong_codes", 429, {"reason": "verification_paused"}, "000000", "paused"))
    client["cases"].append(first | {"id": "caller_cannot_choose_time", "payload": first["payload"] | {"now": 1},
        "expected_http": 400, "expected": {"reason": "invalid_request"}})
    client["races"].append({"id": "two_device_same_factor", "requests": [
        case("concurrent_a", 200, {}), case("concurrent_b", 401, {})], "expected_http": [200, 401]})
    if "lost_client_reply" in controller["cases"]:
        client["lost_client_reply"].append(case("lost_client_reply", 200, {"kind": "totp_consumed"}) | {
            "result_route": "/v00/totp/result", "expected_status": "resolved"})

    if os.environ.get("V00_EMAIL_FIXTURES"):
        controller["provider_origin"] = os.environ["V00_PROVIDER_ORIGIN"]
        controller["email_operations"] = json.loads(Path(os.environ["V00_EMAIL_FIXTURES"]).read_text())
        for operation, fixture in controller["email_operations"].items():
            fault = fixture["fault"]
            base = {"id": "email_" + fault, "route": "/v00/email", "payload": {"operationId": operation},
                    "api_token": tokens[fixture["principal_id"]], "expected": {"full_login_issued": False}}
            if fault == "after_effect_before_result":
                client["cases"] += [base | {"expected_http": 503}, base | {
                    "id": base["id"] + "_read", "route": "/v00/email/result", "expected_http": 200,
                    "expected": {"status": "confirmed_effect", "full_login_issued": False}}]
            elif fault == "before_send":
                client["cases"] += [base | {"expected_http": 202}, base | {
                    "id": base["id"] + "_replay_no_dispatch", "expected_http": 202,
                    "expected": {"status": "uncertain", "full_login_issued": False}}]
            elif fault == "before_headers":
                # A real TCP close can cause commit OR rollback: neither is guessed.
                client["cases"] += [base | {"expected_http": [200, 202]}, base | {
                    "id": base["id"] + "_read", "route": "/v00/email/result", "expected_http": [200, 202]}]
            elif fault == "none":
                client["lost_client_reply"].append(base | {"result_route": "/v00/email/result",
                    "expected_http": 200, "expected_status": "confirmed_effect"})
    if os.environ.get("V00_ONLY_LOST_TOTP") == "1":
        selected = [entry for entry in client["lost_client_reply"] if entry["id"] == "lost_client_reply"]
        if len(selected) != 1:
            raise ValueError("fresh lost_client_reply fixture required")
        client["cases"], client["races"], client["lost_client_reply"] = [], [], selected
    save_new(os.environ["V00_CONTROLLER_OUTPUT"], controller)
    save_new(os.environ["V00_CLIENT_OUTPUT"], client)
    print(json.dumps({"prepared_cases": len(client["cases"]), "prepared_races": len(client["races"]),
                      "private_files_written": True}))


if __name__ == "__main__":
    try:
        prepare()
    except Exception as exc:
        print(json.dumps({"prepared": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
