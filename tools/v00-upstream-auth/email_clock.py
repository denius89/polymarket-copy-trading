"""Trusted request-local ingress clock; never sourced from HTTP payload/header."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
import time

from dependency import Unavailable


@dataclass(frozen=True)
class RequestClock:
    started_at: str
    deadline: float


_clock = ContextVar("email_ingress_clock", default=None)


@contextmanager
def request_clock():
    # Captured before request parsing and all DB/key/cipher work in this handler.
    monotonic_start = time.monotonic()
    wall = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    token = _clock.set(RequestClock(wall, monotonic_start + 10))
    try:
        yield
    finally:
        _clock.reset(token)


def current_clock():
    value = _clock.get()
    if value is None:
        raise Unavailable("missing trusted ingress clock")
    return value
