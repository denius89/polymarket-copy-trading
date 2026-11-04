"""Operator-coordinated HTTP race/unknown tests, without changing runtime code.

Private codes enter stdin. Events/reports contain no cookies, proofs, codes or
delivery addresses. No automatic retries; the only optional retry requires an
explicit operator assertion of an absent admission and retains the exact body/ID.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import re
import sys
import threading
import time
import uuid

from dependency import private_json
from client_probe import Client
from provider import six_digits


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def emit(value):
    print(json.dumps(value), flush=True)


def receive(keys):
    value = json.loads(sys.stdin.readline())
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("invalid operator input")
    return value


class Checks:
    def __init__(self):
        self.rows = []

    def __call__(self, case, passed):
        self.rows.append({"case": case, "passed": bool(passed)})
        if not passed:
            raise AssertionError(case)


def bootstrap(config, ca, name, check):
    fixture, client = config["fixtures"][name], Client(config["origin"], ca)
    reply = client.request(f"/__v00__/fixtures/{name}/context", {"requestSchemaVersion": "v1"},
                           {"Authorization": "Bearer " + fixture["fixture_token"]})
    check(name + "_context", reply[0] == 201 and reply[1] == {"authContextId": fixture["context_id"]})
    return fixture, client


def body(ctx, challenge, action, code):
    return {"requestSchemaVersion": "v1", "commandType": action, "authContextId": ctx,
            "authOperationId": str(uuid.uuid4()), "challengeId": challenge, "code": six_digits(code)}


def history(client, request):
    return client.operation(request["authContextId"], request["authOperationId"], request["commandType"])


def source(request):
    return {"context_id": request["authContextId"], "operation_id": request["authOperationId"],
            "action": request["commandType"]}


def run_race(config, ca, names, confirm_unadmitted_retry=False, independent=None):
    check, clients, fixtures, challenges, email_sources = Checks(), [], [], [], []
    for name in list(names) + ([independent] if independent else []):
        f, client = bootstrap(config, ca, name, check)
        emit({"event": "need_email_code", "fixture": name})
        request = body(f["context_id"], f["email_challenge_id"], "C02", receive({"code"})["code"])
        reply = client.request("/api/auth/verify", request)
        check(name + "_email_stage", reply[0] == 200 and reply[2].get("Set-Cookie") is None)
        saved = history(client, request)
        check(name + "_email_resolved", saved[0] == 200 and saved[1]["result"]["kind"] == "auth_step_required")
        check(name + "_email_history_no_cookie", saved[2].get("Set-Cookie") is None)
        challenges.append(saved[1]["result"]["challengeId"])
        clients.append(client); fixtures.append(f); email_sources.append(source(request))
    # Operator may acquire the shared actor row lock now; it must release within
    # the DB lock timeout after observing both actual waiters, not by a long sleep.
    emit({"event": "race_ready", "contexts": [f["context_id"] for f in fixtures],
          "instructions": "hold_shared_actor_then_supply_fresh_same_totp_code"})
    supplied = receive({"code", "independent_code"} if independent else {"code"})
    code = six_digits(supplied["code"])
    requests = [body(f["context_id"], challenge, "AUTH_TOTP_VERIFY",
                     supplied["independent_code"] if i == 2 else code)
                for i, (f, challenge) in enumerate(zip(fixtures, challenges))]
    emit({"event": "race_dispatching", "sources": [source(r) for r in requests]})
    barrier = threading.Barrier(len(requests) + 1)

    def one(i):
        barrier.wait(timeout=5)
        start, started_at = time.monotonic_ns(), stamp()
        response = clients[i].request("/api/auth/totp/verify", requests[i])
        if i == 2:
            emit({"event": "independent_response", "source": source(requests[i]),
                  "status": response[0], "finished_at": stamp()})
        return response, {"start_ns": start, "end_ns": time.monotonic_ns(), "started_at": started_at,
                          "finished_at": stamp(), "source": source(requests[i])}

    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        pending = [pool.submit(one, i) for i in range(len(requests))]
        barrier.wait(timeout=5)
        values = [future.result(timeout=20) for future in pending]
    independent_observation = None
    if independent:
        independent_reply, independent_observation = values[2]
        check("independent_actor_completes", independent_reply[0] == 200)
        saved = history(clients[2], requests[2])
        check("independent_original_login", saved[0] == 200 and saved[1]["result"]["kind"] == "login_completed")
        independent_observation = independent_observation | {"login_id": saved[1]["result"]["completion"]["loginId"]}
        check("independent_login_usable", clients[2].me(independent_observation["login_id"])[0] == 200)
    replies, chronology = [v[0] for v in values[:2]], [v[1] for v in values[:2]]
    check("http_intervals_overlap", max(v["start_ns"] for v in chronology) < min(v["end_ns"] for v in chronology))
    statuses = [r[0] for r in replies]
    check("one_initial_completion", statuses.count(200) == 1)
    winner, loser = statuses.index(200), 1 - statuses.index(200)
    check("other_rejected_or_unresolved", statuses[loser] in (401, 503))
    check("loser_no_cookie", replies[loser][2].get("Set-Cookie") is None)
    original = history(clients[winner], requests[winner])
    check("winner_original_result", original[0] == 200 and original[1]["result"]["kind"] == "login_completed")
    login = original[1]["result"]["completion"]["loginId"]
    loser_read = history(clients[loser], requests[loser])
    retry_evidence = None
    if statuses[loser] == 503:
        check("loser_stays_unresolved", loser_read[0] == 202 and loser_read[1]["result"] is None)
        emit({"event": "race_unresolved", "source": source(requests[loser]), "initial_statuses": statuses,
              "operator_requirement": "independent_snapshot_proves_no_admission_before_optional_exact_retry"})
        if confirm_unadmitted_retry:
            decision = receive({"retry", "admission_absent", "evidence_id"})
            if decision["retry"] is True:
                if decision["admission_absent"] is not True or not isinstance(decision["evidence_id"], str) or not decision["evidence_id"]:
                    raise ValueError("unadmitted retry not established")
                retry_evidence = decision["evidence_id"]
                # Explicit operator action. Same exact request/code/op; never a new key.
                replies[loser] = clients[loser].request("/api/auth/totp/verify", requests[loser])
                check("explicit_unadmitted_same_op_rejected", replies[loser][0] == 401)
                check("explicit_retry_no_cookie", replies[loser][2].get("Set-Cookie") is None)
                loser_read = history(clients[loser], requests[loser])
            elif decision["retry"] is not False:
                raise ValueError("invalid retry decision")
    if replies[loser][0] == 401:
        check("used_step_rejection_saved", loser_read[0] == 200 and loser_read[1]["result"] == {
            "kind": "verification_rejected", "reasonCode": "AUTH_VERIFICATION_FAILED"})
        # Known final rejection, explicit exact replay; counter must be checked
        # independently before/after in DB, not inferred from this 401 alone.
        repeat = clients[loser].request("/api/auth/totp/verify", requests[loser])
        check("rejection_exact_replay", repeat[0] == 401 and repeat[2].get("Set-Cookie") is None)
        check("rejection_history_immutable", history(clients[loser], requests[loser])[1]["result"] == loser_read[1]["result"])
    check("winner_still_current", clients[winner].me(login)[0] == 200)
    return {"profile": "upstream-same-user-race-v1", "checks": check.rows, "initial_statuses": statuses,
            "final_loser_status": replies[loser][0], "chronology": chronology,
            "email_sources": email_sources[:2], "sources": [source(r) for r in requests[:2]], "winner_login_id": login,
            "independent_email_source": email_sources[2] if independent else None,
            "explicit_retry_evidence_id": retry_evidence,
            "independent_observation": independent_observation,
            "lock_wait_evidence": "external_required", "used_step_and_counter_evidence": "external_required"}


def run_unknown(config, ca, names):
    check = Checks()
    f, client = bootstrap(config, ca, names[0], check)
    other, other_client = bootstrap(config, ca, names[1], check)
    emit({"event": "unknown_ready", "context_id": f["context_id"],
          "instructions": "proxy_must_be_ready_with_exact_email_code_then_supply_same_code"})
    code = six_digits(receive({"code"})["code"])
    request = body(f["context_id"], f["email_challenge_id"], "C02", code)
    emit({"event": "unknown_dispatching", "source": source(request)})
    first = client.request("/api/auth/verify", request)
    check("first_unknown_no_cookie", first[0] == 503 and first[2].get("Set-Cookie") is None)
    saved = history(client, request)
    check("original_unresolved", saved[0] == 202 and saved[1]["result"] is None and saved[1]["resolvedAt"] is None)
    repeat = client.request("/api/auth/verify", request)
    check("exact_repeat_still_unknown", repeat[0] == 503 and repeat[2].get("Set-Cookie") is None)
    recovered = client.operation(f["context_id"], request["authOperationId"], "C02", recover=True)
    check("unknown_cannot_recover_cookie", recovered[0] == 503 and recovered[2].get("Set-Cookie") is None)
    # Explicit negative bypass probes: expected denial before admission/dispatch.
    # These are never used to recover or continue the original unknown operation.
    forbidden = body(f["context_id"], f["email_challenge_id"], "C02", code)
    blocked = client.request("/api/auth/verify", forbidden)
    check("new_key_bypass_denied", blocked[0] == 503 and blocked[2].get("Set-Cookie") is None)
    other_request = body(other["context_id"], other["email_challenge_id"], "C02", code)
    blocked_other = other_client.request("/api/auth/verify", other_request)
    check("new_context_bypass_denied", blocked_other[0] == 503 and blocked_other[2].get("Set-Cookie") is None)
    final = history(client, request)
    check("original_still_unresolved", final[0] == 202 and final[1]["status"] == "unresolved"
          and final[1]["result"] is None and final[1]["resolvedAt"] is None
          and final[1]["operationRef"] == saved[1]["operationRef"])
    return {"profile": "upstream-dispatch-unknown-v1", "checks": check.rows, "source": source(request),
            "denied_probe_sources": [source(forbidden), source(other_request)],
            "proxy_evidence": "external_required_accepted1_forwarded0",
            "db_evidence": "external_required_one_original_admission_seal_no_outcome_result_login_counter_delta"}


def run_gap(config, ca, name, mode):
    check = Checks()
    fixture, client = bootstrap(config, ca, name, check)
    emit({"event": "gap_ready", "mode": mode, "context_id": fixture["context_id"],
          "instructions": "arm_scoped_wrapper_or_observer_then_supply_private_code"})
    request = body(fixture["context_id"], fixture["email_challenge_id"], "C02", receive({"code"})["code"])
    emit({"event": "gap_dispatching", "mode": mode, "source": source(request)})
    direct = client.request("/api/auth/verify", request)
    check("initial_unknown_without_cookie", direct[0] == 503 and direct[2].get("Set-Cookie") is None)
    saved = history(client, request)
    check("history_never_issues_cookie", saved[2].get("Set-Cookie") is None)
    login = None
    if mode == "completion_gap":
        check("original_completion_durable", saved[0] == 200 and saved[1]["status"] == "resolved"
              and saved[1]["result"]["kind"] == "login_completed")
        completion = saved[1]["result"]["completion"]
        login = completion["loginId"]
        check("original_source_retained", completion["authContextId"] == request["authContextId"]
              and completion["authOperationId"] == request["authOperationId"])
        check("no_login_cookie_before_recovery", client.me(login)[0] == 401)
        emit({"event": "await_completion_snapshot", "source": source(request), "login_id": login,
              "requirement": "capture_committed_bundle_and_original_recovery_window_before_q01_erasure"})
        captured = receive({"snapshot_captured", "evidence_id"})
        if captured["snapshot_captured"] is not True or not isinstance(captured["evidence_id"], str) or not captured["evidence_id"]:
            raise ValueError("original completion snapshot required")
        recovered = client.operation(request["authContextId"], request["authOperationId"], "C02", recover=True)
        check("explicit_recovery_original_login", recovered[0] == 200 and recovered[1]["completion"] == completion
              and recovered[2].get("Set-Cookie") is not None)
        replay = client.request("/api/auth/verify", request)
        check("exact_replay_same_completion_cookie", replay[0] == 200 and replay[1]["completion"] == completion
              and replay[2].get("Set-Cookie") == recovered[2].get("Set-Cookie"))
        check("same_login_confirmed", client.me(login)[0] == 200)
        closed = client.operation(request["authContextId"], request["authOperationId"], "C02", recover=True)
        check("q01_closes_original_recovery", closed[0] == 409 and closed[2].get("Set-Cookie") is None)
    else:
        check("original_unresolved", saved[0] == 202 and saved[1]["result"] is None and saved[1]["resolvedAt"] is None)
        if mode == "late":
            emit({"event": "await_late_outcome", "source": source(request),
                  "requirement": "independent_db_witness_after_original_deadline_and_proxy_closed"})
            ready = receive({"late_outcome_observed", "evidence_id"})
            if ready["late_outcome_observed"] is not True or not isinstance(ready["evidence_id"], str) or not ready["evidence_id"]:
                raise ValueError("late outcome evidence required")
        replay = client.request("/api/auth/verify", request)
        check("exact_replay_no_completion", replay[0] == 503 and replay[2].get("Set-Cookie") is None)
        recovered = client.operation(request["authContextId"], request["authOperationId"], "C02", recover=True)
        check("unknown_no_cookie_recovery", recovered[0] == 503 and recovered[2].get("Set-Cookie") is None)
        forbidden = body(fixture["context_id"], fixture["email_challenge_id"], "C02", request["code"])
        denied = client.request("/api/auth/verify", forbidden)
        check("new_key_negative_probe_denied", denied[0] == 503 and denied[2].get("Set-Cookie") is None)
    final = history(client, request)
    check("original_history_unchanged", final[0] == saved[0] and final[1]["operationRef"] == saved[1]["operationRef"]
          and final[1]["result"] == saved[1]["result"] and final[1]["resolvedAt"] == saved[1]["resolvedAt"])
    return {"profile": "upstream-" + mode + "-v1", "checks": check.rows,
            "source": source(request), "login_id": login,
            "denied_probe_source": source(forbidden) if mode != "completion_gap" else None,
            "late_evidence_id": ready["evidence_id"] if mode == "late" else None,
            "completion_evidence_id": captured["evidence_id"] if mode == "completion_gap" else None,
            "db_and_dispatch_evidence": "external_required"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("race", "unknown", "seal_gap", "completion_gap", "late"))
    parser.add_argument("config")
    parser.add_argument("--ca", required=True)
    parser.add_argument("--fixtures", nargs="+", required=True)
    parser.add_argument("--independent-fixture")
    parser.add_argument("--confirm-unadmitted-retry", action="store_true")
    args = parser.parse_args()
    try:
        config = private_json(args.config)
        expected = 2 if args.mode in {"race", "unknown"} else 1
        if len(args.fixtures) != expected or len(set(args.fixtures)) != expected:
            raise ValueError("invalid fixture selection")
        if args.independent_fixture and (args.mode != "race" or args.independent_fixture in args.fixtures):
            raise ValueError("invalid independent fixture")
        if args.mode == "race":
            report = run_race(config, args.ca, args.fixtures, args.confirm_unadmitted_retry, args.independent_fixture)
        elif args.mode == "unknown":
            report = run_unknown(config, args.ca, args.fixtures)
        else:
            report = run_gap(config, args.ca, args.fixtures[0], args.mode)
        emit(report)
    except Exception as exc:
        failed = {"passed": False, "error_type": type(exc).__name__}
        if isinstance(exc, AssertionError) and len(exc.args) == 1 and isinstance(exc.args[0], str) and re.fullmatch(r"[A-Za-z0-9_]{1,96}", exc.args[0]):
            failed["failed_check"] = exc.args[0]
        emit(failed)
        raise SystemExit(1)
