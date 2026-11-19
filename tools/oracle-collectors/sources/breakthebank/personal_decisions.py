"""Hold each verified BUY for its producers before closing a nonfinancial decision."""
from collections import Counter
from dataclasses import dataclass
from queue import Queue
from threading import RLock
from time import monotonic

from personal_range import identity, wire_time

WAIT_SECONDS = 30


@dataclass
class Sight:
    log: dict
    first_utc: int
    first_monotonic: float


class DecisionQueue(Queue):
    def __init__(self, guard, *, maxsize):
        super().__init__(maxsize)
        self.guard = guard

    def put_nowait(self, capture):
        tx = capture.event_key[0]
        with self.guard.lock:
            super().put_nowait(capture)
            self.guard.pending[tx] += 1

    def complete(self, capture):
        tx = capture.event_key[0]
        with self.guard.lock:
            self.guard.pending[tx] -= 1
            if not self.guard.pending[tx]:
                del self.guard.pending[tx]
        self.task_done()


class DecisionGuard:
    def __init__(self):
        self.lock = RLock()
        self.pending = Counter()
        self.sights = {}
        self.refusals = {}

    def queue(self, maxsize):
        return DecisionQueue(self, maxsize=maxsize)

    def remember(self, log, reason, digest):
        key = identity(log)
        with self.lock:
            previous = self.refusals.get(key)
            candidate = (log, reason, digest)
            if key not in self.refusals:
                self.refusals[key] = candidate
            elif previous != candidate:
                # Two different proofs may support the same refusal, but a changed
                # log or conflicting refusal stays unclassified.
                if previous[:2] != candidate[:2]:
                    self.refusals[key] = (previous[0], None, None)

    def observe(self, logs, now):
        elapsed = monotonic()
        for log in logs:
            if log['side'] == 'BUY':
                self.sights.setdefault(identity(log), Sight(log, now, elapsed))

    def evidence(self, log, now):
        """Called under lock for a canonical row; UTC supports DB verification."""
        key = identity(log)
        sight = self.sights.get(key)
        if (sight is None or sight.log != log or self.pending[key[0]]
                or monotonic() - sight.first_monotonic < WAIT_SECONDS
                or now - sight.first_utc < WAIT_SECONDS * 1000):
            return None
        exact = self.refusals.get(key)
        evidence = dict(schemaVersion='paper-buy-evidence-v1', kind='skip', binding=None)
        if exact and exact[0] == log and exact[1] is not None:
            return evidence | {'reason': exact[1], 'evidenceSha256': exact[2]}
        return evidence | {
            'reason': 'copy_decision_unavailable',
            'evidenceSha256': log['receiptSha256'],
            'decisionFence': {
                'firstFinalizedObservedAt': wire_time(sight.first_utc),
                'closedAt': wire_time(now),
            },
        }

    def retire(self, through):
        for key, sight in list(self.sights.items()):
            if int(sight.log['blockNumber']) <= through:
                del self.sights[key]
        for key, refusal in list(self.refusals.items()):
            if int(refusal[0]['blockNumber']) <= through:
                del self.refusals[key]
