"""Private local RTDS-only route; finalized before delay/book/financial recording."""
import copy
import time

from book_engine import BookGate, GateSkip, Signal, quote
from resolver import Resolved, sha


class RtdsBookGate(BookGate):
    def accept_resolved(self, resolved, provenance_validator):
        if not isinstance(resolved, Resolved) or sha(resolved.event) != resolved.event_sha:
            raise GateSkip('RESOLVED_PROOF_CHANGED')
        event = resolved.event
        if event['venueReceipt']['evidenceRef'] != sha(resolved.evidence):
            raise GateSkip('SOURCE_EVIDENCE_CHANGED')
        provenance_validator(event, self.utc())
        final_ns = int(event['venueReceipt']['finality']['checkedMonotonicNs'])
        if not resolved.first_ns <= final_ns <= self.clock():
            raise GateSkip('FINALITY_TIME_INVALID')
        signal = Signal(copy.deepcopy(event), (event['venue'], event['marketId'], event['outcomeId']),
                        resolved.first_ns, resolved.age_at_first_ms, self.clock())
        self.check_age(signal)
        return signal

    def accept_signal(self, *args, **kwargs):
        raise GateSkip('RTDS_ONLY_RESOLVED_ROUTE_REQUIRED')


def execute_resolved(ledger, provenance_validator, db, gate, resolved, *, session_id, owner_id,
                     command_id, policy, delay_ms, delay_evidence, budget=None, sell_quantity=None,
                     wait=time.sleep):
    """Only BOOK_CHANGED after a confirmed rollback recomputes; unknown DB errors propagate."""
    original = ledger.lookup_command(db, session_id, owner_id, command_id, event=resolved.event)
    if original is not None:
        return original
    signal = gate.accept_resolved(resolved, provenance_validator)
    if type(delay_ms) is not int or not 0 <= delay_ms <= 30000 or not delay_evidence:
        raise GateSkip('EXECUTION_DELAY_UNPROVEN')
    gate.check_age(signal)
    if delay_ms:
        wait(delay_ms/1000)
    window = gate.begin(signal, delay_ms, delay_evidence)
    book = gate.wait_candidate(window)
    while True:
        estimate = quote(book, signal.event['side'], policy, budget=budget, sell_quantity=sell_quantity)
        estimate['evidence'].update(sourceProof=copy.deepcopy(resolved.evidence),
                                    waitStartedMonotonicNs=str(window.start_ns),
                                    firstObservedMonotonicNs=str(signal.first_ns),
                                    ageAtFirstObservationMs=signal.age_ms,
                                    finalityBeforeBook=True)
        base_guard = gate.guard(window, book)

        class Guard:
            commit_lock = base_guard.commit_lock

            def __call__(self, event, retained):
                provenance_validator(event, gate.utc())
                f = event['venueReceipt']['finality']
                if book.received_ns <= int(f['checkedMonotonicNs']) or book.received_ms < f['checkedAtMs']:
                    raise GateSkip('BOOK_PRECEDES_FINALITY')
                if sha(retained['evidence']['sourceProof']) != sha(resolved.evidence):
                    raise GateSkip('SOURCE_EVIDENCE_CHANGED')
                return base_guard(event, retained)

        try:
            return ledger.submit(db, session_id, owner_id, command_id, signal.event, estimate, Guard())
        except GateSkip as error:
            if error.reason != 'BOOK_CHANGED':
                raise
            book = gate.wait_candidate(window, recompute=True)
