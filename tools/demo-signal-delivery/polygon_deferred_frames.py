"""Yield a blocked source frame without losing its original freshness clock."""
from collections import deque
from queue import Empty
from time import monotonic


QUEUE_WAIT_REASONS = frozenset({'POLYGON_QUEUE_PREDECESSOR', 'POLYGON_QUEUE_NOT_READY'})
RETRY_SECONDS = 0.25


class DeferredFrames:
    def __init__(self, source, *, clock=monotonic, max_deferred=12):
        self.source = source
        self.clock = clock
        self.max_deferred = max_deferred
        self.pending = deque()

    def defer(self, frame, reason, remaining_ns):
        if (reason not in QUEUE_WAIT_REASONS or remaining_ns <= RETRY_SECONDS * 1_000_000_000
                or len(self.pending) >= self.max_deferred):
            return False
        self.pending.append((self.clock() + RETRY_SECONDS, frame))
        return True

    def get(self, *, timeout):
        if not self.pending:
            return self.source.get(timeout=timeout)
        retry_at, frame = self.pending[0]
        wait = retry_at - self.clock()
        if wait <= 0:
            self.pending.popleft()
            return frame
        try:
            return self.source.get(timeout=min(timeout, wait))
        except Empty:
            if self.clock() < retry_at:
                raise
            self.pending.popleft()
            return frame

    def close(self):
        while self.pending:
            _, frame = self.pending.popleft()
            self.source.complete(frame)
