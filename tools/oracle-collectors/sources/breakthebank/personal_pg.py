"""Private PostgreSQL transport for an enrolled paper-buy stream."""
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from threading import Event, Lock, local
from time import monotonic
from uuid import UUID, uuid4, uuid5

from psycopg import OperationalError, connect
from psycopg.errors import QueryCanceled, SerializationFailure
from psycopg.types.json import Jsonb

from guarded_source import ScopeRefusal, exact
from personal_decisions import DecisionGuard
from personal_range import ingest_envelope, read_range, timestamp, utc_ms
from personal_source import market_binding, normalized_candidate, normalized_proof_fill, provenance
from resolver import Skip
from rtds_provenance import ProvenanceError

READ_SCOPE = 'SELECT polygon.personal_quote_scope_v1(%s::uuid)'
ISSUE = 'SELECT polygon.personal_quote_issue_v1(%s::jsonb)'
INGEST = 'SELECT polygon.live_activity_ingest(%s::jsonb)'
APPLY = 'SELECT polygon.personal_quote_apply_v1(%s::uuid,%s::text)'
LOOKUP = 'SELECT polygon.personal_quote_lookup_v1(%s::uuid,%s::text)'
STOP = 'SELECT polygon.live_activity_stop(%s::jsonb)'
CAP_WRITE_TRANSACTION = """
SELECT CASE WHEN remaining_ms > 5000
       THEN set_config('transaction_timeout', remaining_ms::text, true) END
FROM (
  SELECT floor(extract(epoch FROM
    (to_timestamp(%s::double precision / 1000) - clock_timestamp())) * 1000)::bigint AS remaining_ms
) AS deadline
"""
EXACT_REFUSALS = {
    'TAKER_FEE_PROFILE_UNPROVEN_FOR_MAKER_SOURCE': 'fee_profile_unavailable',
    'FEE_ZERO_UNPROVEN': 'fee_profile_unavailable',
    'FEE_ROUNDING_UNPROVEN': 'fee_profile_unavailable',
    'FEE_ROUNDING_INDETERMINATE': 'fee_profile_unavailable',
    'BOOK_AGE': 'book_stale',
    'SIGNAL_EXPIRED': 'signal_expired',
}


class IdleIngestCanceled(RuntimeError):
    """PostgreSQL canceled the ingest statement before COMMIT was requested."""


class UnresolvedResult(RuntimeError):
    """The original key must be investigated before the worker restarts."""

    def __init__(self, key, kind='purchase'):
        super().__init__(key)
        self.kind = kind


def command_id(session, execution, purpose):
    # Old accounting decoders require the UUID v4 variant on the wire.
    return str(UUID(bytes=uuid5(UUID(session), execution + ':' + purpose).bytes, version=4))


def call(db, query, *parameters):
    return db.execute(query, parameters).fetchone()[0]


def result(reply, stage):
    if not isinstance(reply, dict) or reply.get('http') != 200 or not isinstance(reply.get('result'), dict):
        raise ScopeRefusal(stage)
    return reply['result']


@dataclass(frozen=True)
class PreparedBuy:
    cursor: dict
    quote: dict
    envelope: dict


class PgTransport:
    def __init__(self, rpc, writer_service, issuer_service, window=None):
        self.rpc = rpc
        self.writer = writer_service
        self.issuer = issuer_service
        self.write_lock = Lock()
        self.prefetched = local()
        self.halted = Event()
        self.idle_statement_canceled = False
        self.window = window
        self.decisions = DecisionGuard()

    def remember_rejection(self, resolved, reason):
        disposition = EXACT_REFUSALS.get(reason)
        if disposition is None:
            return
        event = resolved.event
        if disposition == 'signal_expired' and utc_ms() - event['signalAtMs'] < 30_000:
            return
        try:
            receipt = event['venueReceipt']
            provenance(event).validate(event, receipt['finality']['checkedAtMs'])
            log = normalized_proof_fill(event, resolved.evidence)
        except (Skip, ProvenanceError, ValueError, KeyError, IndexError, TypeError):
            return
        self.decisions.remember(log, disposition, receipt['evidenceRef'])

    def check_write(self):
        if self.window is not None:
            self.window.check_write()

    @contextmanager
    def connection(self, service, *, mutation=False, idle_ingest=False):
        # Service names resolve only through the operator's protected local
        # service/pass files. No URL, credentials or statements in diagnostics.
        statement_timeout_ms = 5000 if idle_ingest else 2500
        with connect(service=service, connect_timeout=2,
                     options=f'-c statement_timeout={statement_timeout_ms} -c lock_timeout=1000') as db:
            db.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
            if mutation and self.window is not None:
                self.check_write()
                if call(db, CAP_WRITE_TRANSACTION, self.window.cutoff_ms) is None:
                    raise Skip('PERSONAL_WINDOW_CLOSING')
            yield db

    def read(self, query, *parameters):
        for attempt in range(2):
            try:
                with self.connection(self.writer) as db:
                    return call(db, query, *parameters)
            except SerializationFailure as error:
                if error.sqlstate != '40001' or error.diag.sqlstate != '40001':
                    raise
                if attempt:
                    raise Skip('PERSONAL_BUY_READ_SERIALIZATION_ROLLBACK') from None

    def cursor(self, session):
        return result(self.read(READ_SCOPE, session), 'Personal cursor refused')

    def scoped(self, scope, cursor):
        if (cursor['sessionId'], cursor['streamId'], cursor['settingsId'], cursor['wallet'],
                exact(cursor['fixedBudget'])) != (scope.session_id, scope.assignment_id, scope.settings_revision_id,
                                                 scope.wallet, scope.fixed_budget):
            raise ScopeRefusal('Personal cursor changed scope')
        if cursor['status'] != 'observing':
            raise ScopeRefusal('Personal stream is not observing')
        start = cursor['personalStart']
        if scope.wallet == '0xf0318c32136c2db7fec88b84869aee6a1106c80c':
            if (not isinstance(start, dict) or set(start) != {'chainId', 'number', 'hash', 'evidenceSha256'}
                    or start['chainId'] != 137 or not re.fullmatch(r'0|[1-9][0-9]{0,18}', start['number'])
                    or not re.fullmatch(r'0x[0-9a-f]{64}', start['hash'])
                    or not re.fullmatch(r'[0-9a-f]{64}', start['evidenceSha256'])):
                raise ScopeRefusal('Personal activation boundary missing or invalid')
        elif start is not None:
            raise ScopeRefusal('Unexpected personal activation boundary')

    def lookup(self, scope, event):
        reply = self.read(LOOKUP, scope.session_id, event['executionId'])
        if reply == {'http': 202, 'status': 'unknown'}:
            return None
        return self.receipt(result(reply, 'Personal lookup refused'), scope.session_id)

    @staticmethod
    def receipt(body, session_id):
        if body.get('sessionId') != session_id or body.get('kind') != 'settle':
            raise ScopeRefusal('Unexpected personal settlement receipt')
        return dict(status='recorded', receipt=body)

    def prefetch(self, scope, event):
        self.prefetched.data = None
        now_ms = utc_ms()
        expires = event['signalAtMs'] + 30_000
        if self.window is not None:
            self.check_write()
            expires = min(expires, self.window.cutoff_ms)
        deadline = monotonic() + min(8, (expires - now_ms) / 1000)
        if deadline <= monotonic():
            raise Skip('PERSONAL_QUOTE_EXPIRED')
        cursor = self.cursor(scope.session_id)
        self.scoped(scope, cursor)
        if event['signalAtMs'] < timestamp(cursor['boundAt']).timestamp() * 1000:
            raise Skip('PERSONAL_PREBIND')
        proof_block = event['venueReceipt']['finality']['blockNumber']
        start = cursor['personalStart']
        if start and proof_block <= int(start['number']):
            raise Skip('PERSONAL_BEFORE_ACTIVATION')
        chain_range = read_range(self.rpc, cursor, target_number=proof_block, deadline=deadline)
        binding = market_binding(event, deadline - monotonic())
        self.prefetched.data = (scope.session_id, event['executionId'], cursor, chain_range, binding)

    def prepare(self, scope, event, estimate, meta):
        data = self.prefetched.data
        if not data or data[:2] != (scope.session_id, event['executionId']):
            raise ScopeRefusal('Missing personal prefetch')
        cursor, chain_range, binding = data[2:]
        if (binding['marketTitle'], binding['outcome']) != (meta['marketTitle'], meta['outcomeTitle']):
            raise Skip('PERSONAL_MARKET_CHANGED')
        now_ms = utc_ms()
        normalized = normalized_candidate(event, estimate, now_ms)
        if [entry for entry in chain_range[1] if entry == normalized] != [normalized]:
            raise Skip('PERSONAL_TARGET_RECEIPT_CHANGED')
        execution = event['executionId']
        expires = event['signalAtMs'] + 30_000
        if self.window is not None:
            self.check_write()
            expires = min(expires, self.window.cutoff_ms)
        quote = dict(sessionId=scope.session_id, assignmentId=scope.assignment_id,
                     settingsId=scope.settings_revision_id, executionId=execution, event=event, estimate=estimate,
                     normalizedLog=normalized, expectedVersion=cursor['version'],
                     expiresAtMs=expires)
        for key in ('observationId', 'reserveId', 'settleId', 'reserveCommandId', 'settleCommandId',
                    'intentId', 'fillId', 'confirmationId'):
            quote[key] = command_id(scope.session_id, execution, key)
        envelope = ingest_envelope(cursor, chain_range, command_id(scope.session_id, execution, 'ingest'),
                                   quote=quote, binding=binding, now_ms=utc_ms())
        return PreparedBuy(cursor, quote, envelope)

    @contextmanager
    def transaction(self, scope, prepared):
        quote = prepared.quote
        sid, execution = scope.session_id, quote['executionId']
        with self.write_lock:
            if self.halted.is_set():
                if self.idle_statement_canceled:
                    raise Skip('PERSONAL_WRITE_FENCED')
                raise ScopeRefusal('Personal writer awaits reconciliation')
            prior = self.lookup(scope, quote['event'])
            if prior is not None:
                yield prior
                return
            if self.cursor(sid) != prepared.cursor:
                raise Skip('PERSONAL_CURSOR_ADVANCED')
            self.check_write()
            try:
                with self.connection(self.issuer, mutation=True) as db:
                    self.check_write()
                    issued = call(db, ISSUE, Jsonb(quote))
                    if issued != {key: quote[key] for key in ('reserveId', 'observationId')}:
                        raise ScopeRefusal('Personal quote issuer returned a different identity')
                    self.check_write()
                with self.connection(self.writer, mutation=True) as db:
                    current = result(call(db, READ_SCOPE, sid), 'Personal writer scope unavailable')
                    self.scoped(scope, current)
                    if current != prepared.cursor:
                        raise ScopeRefusal('Personal writer cursor advanced during preparation')
                    self.check_write()
                    ingested = result(call(db, INGEST, Jsonb(prepared.envelope)), 'Personal ingest refused')
                    operation = prepared.envelope['request']['ingest']
                    if (ingested.get('kind'), ingested.get('sessionId'), ingested.get('operationId')) != (
                            'ingest', sid, operation['operationId']):
                        raise ScopeRefusal('Personal ingest did not accept the prepared range')
                    self.check_write()
                    applied = result(call(db, APPLY, sid, execution), 'Personal purchase refused')
                    if applied.get('commandId') != quote['settleCommandId']:
                        raise ScopeRefusal('Unexpected personal command receipt')
                    yield self.receipt(applied, sid)
                    self.check_write()
                    if utc_ms() >= quote['expiresAtMs']:
                        raise ScopeRefusal('Personal quote expired before commit')
            except OperationalError:
                # Never resubmit after a lost response.
                self.halted.set()
                raise UnresolvedResult(execution) from None

    def advance_idle(self, scope):
        self.check_write()
        cursor = self.cursor(scope.session_id)
        self.scoped(scope, cursor)
        deadline = monotonic() + 8
        if self.window is not None:
            deadline = min(deadline, self.window.deadline)
        chain_range = read_range(self.rpc, cursor, deadline=deadline)
        if chain_range is None:
            return
        with self.write_lock, self.decisions.lock:
            if self.halted.is_set():
                raise ScopeRefusal('Personal writer awaits reconciliation')
            self.check_write()
            now = utc_ms()
            self.decisions.observe(chain_range[1], now)
            envelope = ingest_envelope(
                cursor, chain_range, str(uuid4()), now_ms=now,
                close_buy=lambda log: self.decisions.evidence(log, now))
            if envelope is None:
                return
            try:
                with self.connection(self.writer, mutation=True, idle_ingest=True) as db:
                    current = result(call(db, READ_SCOPE, scope.session_id), 'Personal checkpoint unavailable')
                    if current != cursor:
                        return
                    self.check_write()
                    try:
                        applied = result(call(db, INGEST, Jsonb(envelope)), 'Personal idle ingest refused')
                    except QueryCanceled as error:
                        if error.sqlstate != '57014' or error.diag.sqlstate != '57014':
                            raise
                        self.idle_statement_canceled = True
                        self.halted.set()
                        raise IdleIngestCanceled(envelope['request']['ingest']['operationId']) from None
                    if applied.get('kind') != 'ingest':
                        raise ScopeRefusal('Personal idle ingest blocked')
                    self.check_write()
                self.decisions.retire(int(envelope['request']['ingest']['finalized']['number']))
            except OperationalError:
                self.halted.set()
                if self.window is None:
                    raise ScopeRefusal('Personal ingest needs checkpoint reconciliation') from None
                raise UnresolvedResult(envelope['request']['ingest']['operationId'], 'ingest') from None

    def finish(self, scope, status, cutoff_ms):
        """Close observation after collectors join; this operation never issues a quote."""
        sid, operation = scope.session_id, str(uuid4())
        with self.write_lock:
            try:
                with self.connection(self.writer) as db:
                    cursor = result(call(db, READ_SCOPE, sid), 'Personal stop scope unavailable')
                    if cursor['status'] == status:
                        return
                    self.scoped(scope, cursor)
                    evidence = json.dumps({'status': status, 'cutoffMs': cutoff_ms, 'checkpoint': cursor['checkpoint']},
                                          sort_keys=True, separators=(',', ':')).encode()
                    request = {'sessionId': sid, 'runId': cursor['runId'], 'operationId': operation,
                               'status': status, 'evidenceSha256': sha256(evidence).hexdigest()}
                    receipt = result(call(db, STOP, Jsonb({'session_id': sid, 'request': request})),
                                     'Personal stop refused')
                    if (receipt.get('sessionId'), receipt.get('operationId'), receipt.get('status')) != (sid, operation, status):
                        raise ScopeRefusal('Unexpected personal stop receipt')
            except OperationalError:
                raise UnresolvedResult(operation, 'stop') from None
