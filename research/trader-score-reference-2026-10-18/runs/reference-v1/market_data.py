"""Fail-closed recorded-book primitives. Decimal arithmetic; no execution or IO on import.

A covered displayed snapshot does not prove an order fill, availability at arrival,
fees, queue priority, or permission to release a reserve.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
import bisect
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping

D = Decimal

class EvidenceError(ValueError):
    """Inputs cannot support a qualified run; no success artifact may be published."""


def decimal_value(value: object) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise EvidenceError('not_numeric')
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise EvidenceError('not_numeric') from exc
    if not result.is_finite():
        raise EvidenceError('nonfinite')
    return result


def parse_json(raw: str) -> dict:
    def bad_constant(value):
        raise EvidenceError('nonfinite_json_constant:' + value)
    try:
        obj = json.loads(raw, parse_float=Decimal, parse_int=Decimal,
                         parse_constant=bad_constant)
    except (ValueError, TypeError) as exc:
        raise EvidenceError('invalid_json') from exc
    if not isinstance(obj, dict):
        raise EvidenceError('json_object_required')
    return obj


@dataclass(frozen=True)
class BookEvidence:
    status: str
    errors: tuple[str, ...]
    bids: tuple[tuple[Decimal, Decimal], ...] = ()
    asks: tuple[tuple[Decimal, Decimal], ...] = ()


def parse_book(payload: Mapping | object) -> BookEvidence:
    """Missing side is invalid; explicitly empty side is valid empty liquidity."""
    if not isinstance(payload, Mapping):
        return BookEvidence('invalid', ('object_required',))
    errors: set[str] = set()
    sides = {}
    for side in ('bids', 'asks'):
        if side not in payload:
            errors.add('missing_' + side)
            continue
        levels = payload[side]
        if not isinstance(levels, (list, tuple)):
            errors.add('malformed_' + side)
            continue
        seen = set()
        good = []
        for pair in levels:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                errors.add('malformed_level')
                continue
            try:
                price, size = map(decimal_value, pair)
            except EvidenceError as exc:
                errors.add(str(exc))
                continue
            if price < 0 or price > 1 or (side == 'asks' and price == 0):
                errors.add('invalid_price')
            if size < 0:
                errors.add('negative_size')
            if price in seen:
                errors.add('duplicate_price')
            seen.add(price)
            # Zero size is a valid absent level, but does not erase validation errors.
            if size > 0:
                good.append((price, size))
        sides[side] = tuple(sorted(good, reverse=side == 'bids'))
    if errors:
        return BookEvidence('invalid', tuple(sorted(errors)))
    bids, asks = sides['bids'], sides['asks']
    if bids and asks and bids[0][0] > asks[0][0]:
        return BookEvidence('invalid', ('crossed',))
    return BookEvidence('valid', (), bids, asks)


@dataclass(frozen=True)
class CapacityEvidence:
    status: str  # covered / insufficient / unknown; NEVER an execution status
    gross_spent: Decimal | None
    quantity: Decimal | None
    vwap: Decimal | None
    reason: str
    evidence_class: str = 'displayed_snapshot_capacity_only'


def displayed_buy_capacity(book: BookEvidence, gross_notional: Decimal,
                           max_price: Decimal | None = None) -> CapacityEvidence:
    if book.status != 'valid':
        return CapacityEvidence('unknown', None, None, None, 'invalid_book')
    try:
        target = decimal_value(gross_notional)
        cap = None if max_price is None else decimal_value(max_price)
    except EvidenceError:
        return CapacityEvidence('unknown', None, None, None, 'invalid_request')
    if target <= 0 or (cap is not None and not (0 < cap <= 1)):
        return CapacityEvidence('unknown', None, None, None, 'invalid_request')
    # Precision is calculation policy, not a venue quantity/tick rounding policy.
    with localcontext() as ctx:
        ctx.prec = 50
        left, qty = target, D(0)
        for price, size in book.asks:
            if cap is not None and price > cap:
                break
            spent = min(left, price * size)
            qty += spent / price
            left -= spent
            if left == 0:
                return CapacityEvidence('covered', target, qty, target / qty,
                                        'snapshot_levels_cover_gross_notional')
        # These are available snapshot amounts, not partial fills.
        spent = target - left
        return CapacityEvidence('insufficient', spent, qty,
                                spent / qty if qty else None,
                                'snapshot_levels_do_not_cover_full_gross_notional')


@dataclass(frozen=True)
class Snapshot:
    token: str
    available: Decimal
    book: BookEvidence


@dataclass(frozen=True)
class Selection:
    status: str
    reason: str
    snapshot: Snapshot | None = None


def select_snapshot(records: Iterable[Snapshot], arrival: Decimal,
                    max_age: Decimal) -> Selection:
    """Single-token ASOF. No older fallback for tied, invalid, or conflicting latest."""
    snapshots = list(records)
    try:
        target, age_limit = decimal_value(arrival), decimal_value(max_age)
        if age_limit < 0 or not snapshots:
            return Selection('unknown', 'invalid_age_or_no_snapshot')
        times = [decimal_value(s.available) for s in snapshots]
    except EvidenceError:
        return Selection('unknown', 'invalid_timestamp')
    if len({s.token for s in snapshots}) != 1:
        return Selection('unknown', 'mixed_token_scope')
    groups = {}
    for snapshot, timestamp in zip(snapshots, times):
        groups.setdefault(timestamp, []).append(snapshot)
    keys = sorted(groups)
    index = bisect.bisect_right(keys, target) - 1
    if index < 0:
        return Selection('unknown', 'no_prior_snapshot')
    latest = keys[index]
    if latest == target:
        return Selection('unknown', 'exact_arrival_tie')
    group = groups[latest]
    if any(s.book.status != 'valid' for s in group):
        return Selection('unknown', 'invalid_latest_group')
    if len({s.book for s in group}) > 1:
        return Selection('unknown', 'conflicting_latest_group')
    if target - latest > age_limit:
        return Selection('unknown', 'stale_latest_snapshot')
    # All economic book values are equal; representative choice cannot change result.
    return Selection('eligible', 'unambiguous_fresh_snapshot',
                     Snapshot(group[0].token, latest, group[0].book))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest_files(base: Path, entries: list[dict],
                          expected_files: Iterable[str]) -> list[dict]:
    """Exact file-list/bytes/hash verification; paths must remain within base.

    expected_files is an independently supplied run scope, not inferred from entries.
    Schema verification belongs to the reader, before producing analytical output.
    """
    base = base.resolve()
    expected = list(expected_files)
    if len(expected) != len(set(expected)):
        raise EvidenceError('duplicate_expected_file')
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise EvidenceError('manifest_list_required')
    names = [e.get('file') for e in entries]
    if any(not isinstance(n, str) for n in names) or len(names) != len(set(names)):
        raise EvidenceError('duplicate_or_invalid_manifest_file')
    if set(names) != set(expected):
        raise EvidenceError('manifest_file_scope_mismatch')
    verified = []
    for entry in sorted(entries, key=lambda x: x['file']):
        path = (base / entry['file']).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise EvidenceError('missing_or_outside_file:' + entry['file'])
        size = entry.get('bytes')
        digest = entry.get('sha256')
        if type(size) is not int or size < 0 or not isinstance(digest, str) or len(digest) != 64:
            raise EvidenceError('invalid_manifest_evidence:' + entry['file'])
        if path.stat().st_size != size or sha256_file(path) != digest:
            raise EvidenceError('integrity_mismatch:' + entry['file'])
        verified.append({'file': entry['file'], 'bytes': size, 'sha256': digest})
    return verified
