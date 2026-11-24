"""Use the stock Polymarket quote route for a previously staged delivery."""
from contextlib import contextmanager
from dataclasses import dataclass
from time import monotonic, sleep

from psycopg import OperationalError
from psycopg.errors import SerializationFailure
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from book_engine import GateSkip
from guarded_source import ScopeRefusal, SessionCollectorAdapter
from personal_pg import APPLY, ISSUE, ConfirmedBookRollback, UnresolvedResult, call, command_id, read_call, result
from personal_range import timestamp, utc_ms
from personal_source import market_binding, normalized_candidate, normalized_proof_fill, provenance
from resolver import Skip

CLAIM = 'SELECT demo_delivery.claim_polygon_quote(%s::uuid,%s::jsonb)'
ACK = 'SELECT demo_delivery.acknowledge_polygon_result(%s::bigint,%s::uuid,%s::uuid)'
REFUSE_BOOK = 'SELECT demo_delivery.complete_polygon_refusal(%s::uuid,%s::bigint,%s::uuid,%s::text)'


@dataclass(frozen=True)
class QueuedQuote:
    quote: dict
    job: dict


class QueuedQuoteTransport:
    def __init__(self, base, resolved):
        self.base = base
        self.resolved = resolved
        self.write_lock = base.write_lock
        self.prepared = None

    def lookup(self, scope, event):
        return self.base.lookup(scope, event)

    def lookup_scope(self, scope, event):
        return self.base.lookup_scope(scope, event)

    def prefetch(self, scope, event, cursor=None, *, lookup_ms=None):
        self.prepared = None
        if event != self.resolved.event:
            raise ScopeRefusal('Queue candidate changed after confirmation')
        provenance(event).validate(event, utc_ms())
        log = normalized_proof_fill(event, self.resolved.evidence)
        if cursor is None:
            prior, cursor = self.base.lookup_scope(scope, event)
            if prior is not None:
                return prior
        self.base.scoped(scope, cursor)
        remaining = (event['signalAtMs'] + 30_000 - utc_ms()) / 1000
        if remaining <= 0:
            raise Skip('PERSONAL_QUOTE_EXPIRED')
        binding = market_binding(event, min(remaining, 3))
        started = monotonic()
        deadline = started + max(0, min(7, (event['signalAtMs'] + 30_000 - utc_ms()) / 1000 - 3))
        while True:
            with self.base.connection(self.base.writer) as db:
                job = read_call(db, CLAIM, scope.session_id, Jsonb(log))
            if job:
                break
            if monotonic() + 0.25 > deadline:
                raise Skip('POLYGON_QUEUE_NOT_READY')
            sleep(0.25)
        self.prepared = (log, cursor['version'], binding, job)
        self.claim_ms = round((monotonic() - started) * 1000)

    def prepare(self, scope, event, estimate, meta):
        if self.prepared is None:
            raise ScopeRefusal('Missing canonical Polygon lease')
        log, version, binding, job = self.prepared
        if normalized_candidate(event, estimate, utc_ms()) != log:
            raise Skip('PERSONAL_TARGET_RECEIPT_CHANGED')
        if (binding['marketTitle'], binding['outcome']) != (meta['marketTitle'], meta['outcomeTitle']):
            raise Skip('PERSONAL_MARKET_CHANGED')

        execution = event['executionId']
        expires = min(event['signalAtMs'] + 30_000,
                      int(timestamp(job['expiresAt']).timestamp() * 1000))
        if self.base.window is not None:
            self.base.check_write()
            expires = min(expires, self.base.window.cutoff_ms)
        quote = dict(sessionId=scope.session_id, assignmentId=scope.assignment_id,
                     settingsId=scope.settings_revision_id, executionId=execution, event=event, estimate=estimate,
                     normalizedLog=log, expectedVersion=version, expiresAtMs=expires,
                     observationId=job['observationId'])
        for key in ('reserveId', 'settleId', 'reserveCommandId', 'settleCommandId', 'intentId', 'fillId', 'confirmationId'):
            quote[key] = command_id(scope.session_id, execution, key)
        return QueuedQuote(quote, job)

    def finish_book_refusal(self, scope, reason):
        if reason != 'BOOK_WAIT_TIMEOUT' or self.prepared is None:
            return False
        job = self.prepared[3]
        self.base.check_write()
        try:
            with self.base.connection(self.base.writer, mutation=True) as db:
                return read_call(db, REFUSE_BOOK, scope.session_id, job['signalId'], job['lease'], 'book_unavailable')
        except (SerializationFailure, OperationalError, Skip):
            # A later iteration can reconcile a committed refusal or expire the lease.
            return False

    @contextmanager
    def transaction(self, scope, prepared):
        quote, job = prepared.quote, prepared.job
        sid, execution = scope.session_id, quote['executionId']
        with self.write_lock:
            if self.base.halted.is_set():
                raise ScopeRefusal('Personal writer awaits reconciliation')
            self.base.check_write()
            if utc_ms() >= quote['expiresAtMs']:
                raise Skip('PERSONAL_QUOTE_EXPIRED')
            with self.base.tracking('purchase', execution):
                try:
                    with self.base.connection(self.base.issuer, mutation=True) as db:
                        issued = call(db, ISSUE, Jsonb(quote))
                        if issued != {key: quote[key] for key in ('reserveId','observationId')}:
                            raise ScopeRefusal('Personal quote issuer returned a different identity')
                    with self.base.connection(self.base.writer, mutation=True) as db:
                        call(db, "SELECT set_config('demo_delivery.polygon_lease',%s,true)", job['lease'])
                        applied = result(call(db, APPLY, sid, execution), 'Polygon queued purchase refused')
                        receipt = self.base.receipt(applied, sid)
                        if receipt['status'] != 'recorded' or applied.get('commandId') != quote['settleCommandId']:
                            raise ScopeRefusal('Unexpected Polygon queued purchase receipt')
                        if call(db, ACK, job['signalId'], sid, job['lease']) is not True:
                            raise Skip('POLYGON_QUEUE_LEASE_LOST')
                        try:
                            yield receipt
                        except GateSkip as error:
                            db.rollback()
                            if db.info.transaction_status != TransactionStatus.IDLE:
                                raise UnresolvedResult(execution) from None
                            raise ConfirmedBookRollback('POLYGON_QUEUE_BOOK_REFUSED') from error
                        self.base.check_write()
                        if utc_ms() >= quote['expiresAtMs']:
                            raise Skip('PERSONAL_QUOTE_EXPIRED')
                except SerializationFailure as error:
                    if error.sqlstate != '40001':
                        raise
                    raise Skip('PERSONAL_BUY_SERIALIZATION_ROLLBACK') from None
                except (OperationalError, UnresolvedResult):
                    self.base.halted.set()
                    raise UnresolvedResult(execution) from None


def queued_quote_adapter(scope, transport, resolved):
    """Called after the normal source resolver and before opening the quote window."""
    return SessionCollectorAdapter(scope, QueuedQuoteTransport(transport, resolved))
