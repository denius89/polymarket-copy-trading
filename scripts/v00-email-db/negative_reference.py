"""Independent source-pinned classifier oracle, synthetic inputs only.

Not a provider client or an authorization to finalize any runtime result.
No raw input or expected token is returned.
"""
import hashlib
import re


def classify(email, code, now, challenge_expiry, recovery_token, recovery_issued,
             confirmation_token='', confirmation_issued=None):
    if not isinstance(code, str) or re.fullmatch('[0-9]{6}', code) is None:
        return 'malformed'
    pattern = r'(?:pkce_)?[0-9a-f]{56}'
    if (not isinstance(email, str) or not email.isascii() or email != email.lower()
            or re.fullmatch(pattern, recovery_token or '') is None or recovery_issued is None
            or recovery_issued > now or confirmation_issued is not None and confirmation_issued > now
            or confirmation_token and (re.fullmatch(pattern, confirmation_token) is None or confirmation_issued is None)):
        return 'unavailable'
    if now >= challenge_expiry:
        return 'expired_current'
    computed = hashlib.sha224((email + code).encode('ascii')).hexdigest()
    matching = (computed, 'pkce_' + computed)
    # Provider implementation uses now.After: equality is still valid for its other branch.
    if confirmation_token in matching and confirmation_issued + 600 >= now:
        return 'unsupported_other_family'
    return 'positive_candidate' if recovery_token in matching else 'live_mismatch'
