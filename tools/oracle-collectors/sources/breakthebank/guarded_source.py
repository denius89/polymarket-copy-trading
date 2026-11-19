"""Private writer adapter for the existing RTDS and maker Polymarket collectors."""
import copy
from dataclasses import dataclass
from fractions import Fraction


class ScopeRefusal(Exception):
    pass


@dataclass(frozen=True)
class FollowScope:
    session_id: str
    assignment_id: str
    settings_revision_id: str
    wallet: str
    started_at_ms: int
    fixed_budget: Fraction


def exact(value):
    if not isinstance(value, dict) or set(value) != {'n', 'd'}:
        raise ScopeRefusal('Invalid exact amount')
    result = Fraction(int(value['n']), int(value['d']))
    if value != {'n': str(result.numerator), 'd': str(result.denominator)}:
        raise ScopeRefusal('Noncanonical exact amount')
    return result


class SessionCollectorAdapter:
    """The fixed scope derives from the assigned PostgreSQL worker, not route arguments."""

    def __init__(self, scope, transport, metadata=None):
        self.scope = scope
        self.transport = transport
        self.metadata = metadata

    def bind(self, metadata):
        if metadata['venue'] != 'polymarket' or metadata['wallet'] != self.scope.wallet:
            raise ScopeRefusal('Wrong personal trader')
        return SessionCollectorAdapter(self.scope, self.transport, copy.deepcopy(metadata))

    def source_queue(self, maxsize):
        return self.transport.decisions.queue(maxsize)

    def remember_rejection(self, resolved, reason):
        try:
            self._check(resolved.event)
        except ScopeRefusal:
            return
        self.transport.remember_rejection(resolved, reason)

    def _check(self, event):
        match = event['venueReceipt']['match']
        if (event['venue'] != 'polymarket' or event['side'] != 'BUY'
                or match['wallet'] != self.scope.wallet or match['side'] != 'BUY'
                or (event['marketId'], event['outcomeId']) != (match['marketId'], match['outcomeId'])
                or event['signalAtMs'] < self.scope.started_at_ms):
            raise ScopeRefusal('Personal execution outside the assigned scope')

    def lookup_command(self, _db, _placeholder_session, _placeholder_owner, _placeholder_command, *, event):
        event = copy.deepcopy(event)
        self._check(event)
        prior = self.transport.lookup(self.scope, event)
        if prior is None:
            self.transport.prefetch(self.scope, event)
        return prior

    def submit(self, _db, _placeholder_session, _placeholder_owner, _placeholder_command, event, estimate, guard):
        event, estimate = copy.deepcopy(event), copy.deepcopy(estimate)
        self._check(event)
        meta = self.metadata
        if not meta or (meta['condition'], meta['token'], meta['sourceTimestampMs']) != (
                event['marketId'], event['outcomeId'], event['signalAtMs']):
            raise ScopeRefusal('Personal execution metadata mismatch')
        fills = estimate['fills']
        evidence = estimate['evidence']
        if len(fills) != 1:
            raise ScopeRefusal('Only the verified single-fill profile is supported')
        fill = fills[0]
        quantity, price, fee = (exact(fill[key]) for key in ('quantity', 'price', 'cashFee'))
        gross = quantity * price
        if not (quantity > 0 and 0 < price < 1 and fee >= 0 and gross + fee <= self.scope.fixed_budget):
            raise ScopeRefusal('Personal budget or quote mismatch')
        if (exact(evidence['quantity']), exact(evidence['gross']), exact(evidence['cashFee'])) != (quantity, gross, fee):
            raise ScopeRefusal('Personal fill arithmetic mismatch')

        prepared = self.transport.prepare(self.scope, event, estimate, copy.deepcopy(meta))
        # The chain is read outside the book lock. The DB commit uses those exact bytes.
        with guard.commit_lock:
            if guard(event, estimate) is not True:
                raise ScopeRefusal('Personal quote rejected at admission')
            with self.transport.transaction(self.scope, prepared) as result:
                if guard(event, estimate) is not True:
                    raise ScopeRefusal('Personal quote rejected before commit')
        return result
