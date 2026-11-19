"""Closed public C01/C03 input and Auth-context projection validators."""
from datetime import timedelta
import uuid

from email_input import canonical_email
from controller import Rejection, exact as request_exact, uid as request_uid
from protocol import exact, require, timestamp, uid


def private_uid(value):
    uid(value)
    require(uuid.UUID(value).version == 4)
    return value


def send_request(body, action):
    fields = {"requestSchemaVersion", "commandType", "authContextId", "authOperationId", "locale"}
    fields.add("email" if action == "C01" else "expectedChallengeId")
    request_exact(body, fields)
    if action not in {"C01", "C03"} or body["requestSchemaVersion"] != "v1" or body["commandType"] != action:
        raise Rejection(400, "INVALID_REQUEST")
    request_uid(body["authContextId"]); request_uid(body["authOperationId"])
    if type(body["locale"]) is not str or body["locale"] not in {"en", "ru"}:
        raise Rejection(400, "INVALID_REQUEST")
    if action == "C03":
        request_uid(body["expectedChallengeId"])
        return None
    try:
        return canonical_email(body["email"])
    except ValueError:
        raise Rejection(400, "INVALID_REQUEST") from None


def context_view(value, context_id, creating=False):
    exact(value, "authContextId stage accessConfirmed createdAt expiresAt emailCodeIssuedAt "
          "emailCodeExpiresAt currentEmailChallengeId currentTotpChallengeId totpChallengeIssuedAt "
          "totpChallengeExpiresAt loginCookieRecoveryDeadlineAt")
    require(value["authContextId"] == context_id)
    private_uid(context_id)
    stage = value["stage"]
    require(type(stage) is str and stage in {"ready", "email_verification", "totp_verification", "totp_enrollment", "completed"})
    require(type(value["accessConfirmed"]) is bool and value["accessConfirmed"] is not creating)
    created, expiry = timestamp(value["createdAt"]), timestamp(value["expiresAt"])
    require(expiry - created == timedelta(minutes=30))
    if creating:
        require(stage == "ready")
    for expected_stage, group, seconds in (
            ("email_verification", ("currentEmailChallengeId", "emailCodeIssuedAt", "emailCodeExpiresAt"), 600),
            ("totp_verification", ("currentTotpChallengeId", "totpChallengeIssuedAt", "totpChallengeExpiresAt"), 300)):
        if stage == expected_stage:
            private_uid(value[group[0]])
            issued, ends = timestamp(value[group[1]]), timestamp(value[group[2]])
            require(created <= issued < ends and ends - issued <= timedelta(seconds=seconds))
        else:
            require(all(value[k] is None for k in group))
    recovery = value["loginCookieRecoveryDeadlineAt"]
    if stage == "completed":
        require(recovery is not None and created < timestamp(recovery) <= expiry)
    else:
        require(recovery is None)
    return value


def dispatch_result(value, action):
    exact(value, "kind acceptedAt challengeId resendNotBeforeAt")
    require(action in {"C01", "C03"} and value["kind"] == "email_dispatch_accepted")
    private_uid(value["challengeId"])
    require(timestamp(value["resendNotBeforeAt"]) >= timestamp(value["acceptedAt"]) + timedelta(seconds=60))
    return value
