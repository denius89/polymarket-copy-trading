"""Bounded synthetic accounting reference, not a venue client or historical replay.

Import has no file/network effects. Decimal amounts must arrive as strings/integers.
Book capacity admits an intent; only explicit authoritative fixture confirmations
change cash/lots. No recorded-data-to-fill conversion is provided.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from market_data import Snapshot, parse_book, select_snapshot, displayed_buy_capacity

D = Decimal
ZERO = D('0')

class ReferenceError(ValueError):
    pass


def amount(value):
    if isinstance(value, (float, bool)) or value is None:
        raise ReferenceError('exact_decimal_required')
    try:
        result = D(value)
    except Exception as exc:
        raise ReferenceError('invalid_decimal') from exc
    if not result.is_finite():
        raise ReferenceError('nonfinite_decimal')
    return result


def stamp(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception as exc:
        raise ReferenceError('invalid_timestamp') from exc
    if dt.tzinfo is None:
        raise ReferenceError('timezone_required')
    return dt.astimezone(timezone.utc)


def seconds(dt):
    delta = dt - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return D(delta.days * 86400 + delta.seconds) + D(delta.microseconds) / D(1000000)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def strings(obj):
    if isinstance(obj, Decimal):
        return format(obj, 'f')
    if isinstance(obj, dict):
        return {k: strings(v) for k, v in obj.items()}
    if isinstance(obj, (tuple, list)):
        return [strings(v) for v in obj]
    return obj


def validate_config(config, standard):
    expected = {
        'initial_cash': standard['opening']['virtual_cash'],
        'fixed_buy': standard['sizing']['amount'],
        'position_cap': standard['sizing']['position_cap_cost_basis_plus_pending'],
        'daily_cap': standard['sizing']['daily_buy_gross_cap'],
        'timezone': standard['sizing']['session_zone'],
        'latency_seconds': standard['signals']['decision_delay_seconds'],
        'max_signal_age_seconds': standard['signals']['maximum_signal_age_seconds'],
        'max_book_age_seconds': standard['market_data']['max_book_age_seconds'],
        'cash_quantum': standard['controlled_fixture_binding']['collateral_quantum'],
        'share_quantum': standard['controlled_fixture_binding']['share_quantum'],
        'target_horizon_days': standard['target']['target_horizon_calendar_days'],
    }
    for key, value in expected.items():
        if str(config.get(key)) != str(value):
            raise ReferenceError('standard_config_mismatch:' + key)
    if config.get('initial_positions') != {} or config.get('venue') != 'PolymarketV1':
        raise ReferenceError('unsupported_opening_or_venue')
    if amount(config['cash_quantum']) <= 0 or amount(config['share_quantum']) <= 0:
        raise ReferenceError('invalid_quantum')


class Replay:
    def __init__(self, config):
        self.cfg = deepcopy(config)
        self.zone = ZoneInfo(config['timezone'])
        self.cash = amount(config['initial_cash'])
        self.orders = {}
        self.lots = {}
        self.daily = {}
        self.seen = {}
        self.trace = []
        self.valuations = []
        self.incidents = []
        self.risk_blocked = False
        self.now = None
        self.sequence = 0
        self.fees_paid = ZERO
        self.gross_bought = ZERO
        self.gross_sold = ZERO
        self.settlement_cash = ZERO

    def day(self, dt):
        return dt.astimezone(self.zone).date().isoformat()

    def position(self, token):
        lots = self.lots.get(token, [])
        return sum((x['quantity'] for x in lots), ZERO), sum((x['cost_basis'] for x in lots), ZERO)

    def pending(self, token=None):
        return sum((o['target_gross'] - o['filled_gross'] for o in self.orders.values()
                    if not o['terminal'] and o['side'] == 'BUY' and (token is None or o['token'] == token)), ZERO)

    def fee_reserve(self):
        return sum((o['fee_cap'] for o in self.orders.values() if not o['terminal']), ZERO)

    def reserved_qty(self, token):
        return sum((o['target_quantity'] - o['filled_quantity'] for o in self.orders.values()
                    if not o['terminal'] and o['side'] == 'SELL' and o['token'] == token), ZERO)

    def state(self):
        pending, fees = self.pending(), self.fee_reserve()
        current = self.day(self.now)
        local = self.now.astimezone(self.zone)
        midnight = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), self.zone)
        return dict(cash=self.cash, gross_buy_reserve=pending, expense_reserve=fees,
                    cash_reserve=pending+fees, available=self.cash-pending-fees,
                    current_day=current, local_time=local.isoformat(), next_reset_utc=midnight.astimezone(timezone.utc).isoformat(),
                    daily_spent=self.daily.get(current, ZERO), daily_pending=pending,
                    daily_available=amount(self.cfg['daily_cap'])-self.daily.get(current, ZERO)-pending,
                    daily_used_all=self.daily.copy(), fees_paid=self.fees_paid,
                    gross_bought=self.gross_bought, gross_sold=self.gross_sold,
                    settlement_cash=self.settlement_cash, risk_blocked=self.risk_blocked,
                    positions={t: dict(quantity=self.position(t)[0],cost_basis=self.position(t)[1],
                                       pending_buy=self.pending(t), reserved_sell_quantity=self.reserved_qty(t),
                                       lots=deepcopy(ls)) for t,ls in self.lots.items()},
                    orders=deepcopy(self.orders))

    def book(self, event, token):
        snapshots = []
        for b in event.get('books', []):
            if b.get('token') != token:
                continue
            available = stamp(b['available_at'])
            source = stamp(b['source_at'])
            if source > available:
                return None, 'invalid_book_clock'
            # Old source data freshly delivered is still old. Keep it invalid,
            # so selection cannot fall back to an older valid snapshot.
            payload = parse_book(b.get('payload'))
            if self.now >= available and seconds(self.now)-seconds(source) > amount(self.cfg['max_book_age_seconds']):
                payload = parse_book(None)
            snapshots.append(Snapshot(token, seconds(available), payload))
        chosen = select_snapshot(snapshots, seconds(self.now), amount(self.cfg['max_book_age_seconds']))
        return (chosen.snapshot.book, chosen.reason) if chosen.status == 'eligible' else (None, chosen.reason)

    def bid_value(self, book, qty, minimum=ZERO):
        left, total = qty, ZERO
        for price, size in book.bids:
            if price < minimum:
                continue
            take = min(left, size)
            total += take * price
            left -= take
            if left == 0:
                return total
        return None

    def intent(self, e):
        if self.risk_blocked:
            return 'skipped:risk_quarantine'
        side, token = e['side'], e['token']
        if side not in ('BUY','SELL'):
            raise ReferenceError('unsupported_side')
        if e['order_id'] in self.orders:
            raise ReferenceError('order_id_reused')
        observed, source = stamp(e['observed_at']), stamp(e['source_at'])
        if seconds(self.now)-seconds(observed) != amount(self.cfg['latency_seconds']):
            return 'skipped:decision_time_not_observed_plus_latency'
        if source > observed or seconds(self.now)-seconds(source) > amount(self.cfg['max_signal_age_seconds']):
            return 'skipped:signal_time_unknown_or_stale'
        if e.get('fee_cap') is None or not e.get('fee_evidence'):
            return 'skipped:unknown_expenses'
        fee = amount(e['fee_cap'])
        if fee < 0:
            raise ReferenceError('negative_fee_cap')
        cq = amount(self.cfg['cash_quantum'])
        fee = (fee/cq).to_integral_value(rounding=ROUND_CEILING)*cq
        bound_name = 'max_price' if side=='BUY' else 'min_price'
        if e.get(bound_name) is None:
            return 'skipped:missing_price_boundary'
        bound = amount(e[bound_name])
        if not ZERO < bound <= 1:
            return 'skipped:invalid_price_boundary'
        book, reason = self.book(e,token)
        if book is None:
            return 'skipped:'+reason
        available = self.cash-self.pending()-self.fee_reserve()
        if side == 'BUY':
            gross = amount(self.cfg['fixed_buy'])
            capacity = displayed_buy_capacity(book,gross,max_price=bound)
            if capacity.status != 'covered':
                return 'skipped:'+capacity.status+'_full_buy_depth'
            if gross+fee > available:
                return 'skipped:budget_with_expenses'
            if self.position(token)[1]+self.pending(token)+gross > amount(self.cfg['position_cap']):
                return 'skipped:position_limit'
            if self.daily.get(self.day(self.now),ZERO)+self.pending()+gross > amount(self.cfg['daily_cap']):
                return 'skipped:daily_limit'
            qty = None
        else:
            if e.get('leader_before') is None or e.get('leader_sold') is None:
                return 'skipped:leader_inventory_unknown'
            before, sold = amount(e['leader_before']),amount(e['leader_sold'])
            if before<=0 or sold<=0 or sold>before:
                return 'skipped:leader_reduction_unknown'
            if self.reserved_qty(token)>0 or self.pending(token)>0:
                return 'skipped:position_reconciliation_pending'
            quantum = amount(self.cfg['share_quantum'])
            qty = (self.position(token)[0]*sold/before/quantum).to_integral_value(rounding=ROUND_FLOOR)*quantum
            if qty <= 0:
                return 'skipped:no_tracked_quantity'
            gross = self.bid_value(book,qty,bound)
            if gross is None:
                return 'skipped:insufficient_full_sell_depth'
            if fee>available:
                return 'skipped:budget_for_sell_expenses'
        self.orders[e['order_id']] = dict(side=side,token=token,target_gross=gross,
                    target_quantity=qty,filled_gross=ZERO,filled_quantity=ZERO,fee_cap=fee,
                    fee_actual=None,terminal=False,status='admitted',decision_at=e['received_at'],
                    price_boundary=bound,cancel_requested=False,remaining_cancelled=ZERO)
        return 'admitted:no_fill_generated'

    def reduce_lots(self,token,qty):
        total=self.position(token)[0]
        if qty>total:
            raise ReferenceError('sell_exceeds_tracked_lots')
        sq,cq=amount(self.cfg['share_quantum']),amount(self.cfg['cash_quantum'])
        remaining=qty
        active=[x for x in self.lots[token] if x['quantity']>0]
        # Explicit engineering allocation: proportional floors then last-lot remainder.
        allocations=[(x['quantity']*qty/total/sq).to_integral_value(rounding=ROUND_FLOOR)*sq for x in active]
        residual=qty-sum(allocations,ZERO)
        for i in reversed(range(len(active))):
            extra=min(residual,active[i]['quantity']-allocations[i]);allocations[i]+=extra;residual-=extra
        if residual:
            raise ReferenceError('lot_allocation_incomplete')
        for lot,take in zip(active,allocations):
            old=lot['quantity']
            reduction=lot['cost_basis'] if take==old else (lot['cost_basis']*take/old/cq).to_integral_value(rounding=ROUND_HALF_EVEN)*cq
            lot['quantity']-=take;lot['cost_basis']-=reduction

    def fill(self,e):
        o=self.orders[e['order_id']]
        if o['terminal']:
            raise ReferenceError('fill_after_terminal_requires_reconciliation')
        if e.get('confirmation')!='authoritative_controlled_fixture':
            raise ReferenceError('unverified_fill')
        when=stamp(e['executed_at'])
        if when>self.now or when<stamp(o['decision_at']):
            raise ReferenceError('invalid_fill_time')
        qty,price,gross=amount(e['quantity']),amount(e['price']),amount(e['gross'])
        if qty<=0 or price<=0 or price>1 or gross<=0 or qty*price!=gross:
            raise ReferenceError('invalid_fill_units')
        if qty%amount(self.cfg['share_quantum']) or gross%amount(self.cfg['cash_quantum']):
            raise ReferenceError('fill_not_native_fixture_units')
        if o['side']=='BUY':
            if price>o['price_boundary'] or o['filled_gross']+gross>o['target_gross']:
                raise ReferenceError('buy_fill_exceeds_authorized_intent')
            self.cash-=gross;self.gross_bought+=gross
            day=self.day(when);self.daily[day]=self.daily.get(day,ZERO)+gross
            self.lots.setdefault(o['token'],[]).append(dict(lot_id=e['event_id'],order_id=e['order_id'],
                               quantity=qty,cost_basis=gross,source='tracked_copy',executed_at=e['executed_at']))
        else:
            if price<o['price_boundary'] or o['filled_quantity']+qty>o['target_quantity']:
                raise ReferenceError('sell_fill_exceeds_authorized_intent')
            self.reduce_lots(o['token'],qty);self.cash+=gross;self.gross_sold+=gross
        o['filled_gross']+=gross;o['filled_quantity']+=qty
        complete=(o['filled_gross']==o['target_gross']) if o['side']=='BUY' else o['filled_quantity']==o['target_quantity']
        if complete:
            o['status']='full_fill_awaiting_terminal_fee';return 'confirmed_full_fill:fee_bound_retained'
        o['status']='partial_cancel_requested';o['cancel_requested']=True
        return 'confirmed_partial_fill:cancel_requested_not_confirmed'

    def terminal(self,e):
        o=self.orders[e['order_id']]
        if o['terminal']:
            raise ReferenceError('second_terminal_requires_reconciliation')
        if e.get('confirmation')!='authoritative_controlled_fixture' or e.get('fee_actual') is None:
            return 'unknown:terminal_confirmation_or_expense_missing'
        if amount(e['confirmed_gross_total'])!=o['filled_gross']:
            raise ReferenceError('terminal_cumulative_fill_mismatch')
        fee=amount(e['fee_actual'])
        if fee<0 or fee>o['fee_cap'] or fee%amount(self.cfg['cash_quantum']):
            raise ReferenceError('terminal_fee_outside_bound_or_quantum')
        if o['filled_gross']==0 and fee!=0:
            raise ReferenceError('unsupported_fixture_unfilled_expense')
        complete=(o['filled_gross']==o['target_gross']) if o['side']=='BUY' else o['filled_quantity']==o['target_quantity']
        if e['outcome']=='filled' and not complete:
            raise ReferenceError('terminal_filled_but_remaining')
        if e['outcome'] not in ('filled','cancelled_remainder'):
            raise ReferenceError('unsupported_terminal_outcome')
        if complete and e['outcome']=='cancelled_remainder':
            raise ReferenceError('cancel_conflicts_with_full_fill')
        o['remaining_cancelled']=o['target_gross']-o['filled_gross'] if o['side']=='BUY' else o['target_quantity']-o['filled_quantity']
        self.cash-=fee;self.fees_paid+=fee;o['fee_actual']=fee;o['terminal']=True
        o['status']='filled_cancel_too_late' if complete and o['cancel_requested'] else e['outcome']
        return 'terminal_confirmed:remaining_and_expense_reserve_released'

    def settlement(self,e):
        if stamp(e['known_at'])>self.now:
            return 'unknown:resolution_not_known_at_cutoff'
        if e.get('confirmation')!='authoritative_controlled_fixture' or e.get('fee_actual') is None:
            return 'unknown:settlement_unverified'
        token=e['token']
        if any(o['token']==token and not o['terminal'] for o in self.orders.values()):
            return 'unknown:orders_not_reconciled'
        payout,fee=amount(e['payout_per_token']),amount(e['fee_actual'])
        if not ZERO<=payout<=1 or fee<0:
            raise ReferenceError('invalid_payout_or_fee')
        qty=self.position(token)[0]
        if qty==0:
            return 'no_tracked_position_to_settle'
        proceeds=qty*payout
        self.cash+=proceeds-fee;self.settlement_cash+=proceeds;self.fees_paid+=fee
        for lot in self.lots[token]:lot['quantity']=ZERO;lot['cost_basis']=ZERO
        return 'settled_from_known_fixture_confirmation'

    def valuation(self,e):
        value=dict(event_id=e['event_id'],status='unknown',equity=None,pnl=None,reason=None)
        if self.risk_blocked or any(not o['terminal'] for o in self.orders.values()):
            value['reason']='unresolved_order_or_incident'
        elif e.get('exit_fee_per_position') is None or not e.get('fee_evidence'):
            value['reason']='unknown_exit_expenses'
        else:
            fee=amount(e['exit_fee_per_position'])
            if fee<0:raise ReferenceError('invalid_exit_fee')
            liquidation=ZERO
            for token in self.lots:
                qty=self.position(token)[0]
                if qty==0:continue
                book,reason=self.book(e,token)
                if book is None:value['reason']=token+':'+reason;break
                proceeds=self.bid_value(book,qty)
                if proceeds is None:value['reason']=token+':insufficient_exit_depth';break
                liquidation+=proceeds-fee
            if value['reason'] is None:
                value.update(status='known_under_controlled_fixture',equity=self.cash+liquidation,
                             pnl=self.cash+liquidation-amount(self.cfg['initial_cash']),
                             reason='marked_only_no_cash_or_lot_mutation')
        self.valuations.append(value)
        return 'valuation:'+value['status']

    def apply(self,e):
        kind=e['kind']
        if kind=='intent':return self.intent(e)
        if kind=='fill':return self.fill(e)
        if kind=='terminal':return self.terminal(e)
        if kind=='unknown':
            o=self.orders[e['order_id']]
            if o['terminal']:raise ReferenceError('unknown_after_terminal')
            o['status']='unknown';return 'unknown:all_existing_reserves_retained'
        if kind=='cancel_request':
            o=self.orders[e['order_id']]
            if o['terminal']:raise ReferenceError('cancel_after_terminal')
            o['cancel_requested']=True;o['status']='cancel_requested';return 'cancel_requested:no_release'
        if kind=='settlement':return self.settlement(e)
        if kind=='valuation':return self.valuation(e)
        if kind=='tick':return 'clock_only'
        raise ReferenceError('unsupported_event_kind')

    def invariants(self):
        if self.cash<0 or self.cash-self.pending()-self.fee_reserve()<0:
            raise ReferenceError('negative_cash_or_available')
        expected=amount(self.cfg['initial_cash'])-self.gross_bought+self.gross_sold+self.settlement_cash-self.fees_paid
        if self.cash!=expected:
            raise ReferenceError('cash_conservation_failed')
        for token in self.lots:
            qty,cost=self.position(token)
            if qty<0 or cost<0 or self.reserved_qty(token)>qty:
                raise ReferenceError('lot_conservation_failed')
            if cost+self.pending(token)>amount(self.cfg['position_cap']):
                raise ReferenceError('position_cap_failed')
        if self.daily.get(self.day(self.now),ZERO)+self.pending()>amount(self.cfg['daily_cap']):
            raise ReferenceError('daily_cap_failed')

    def run(self,events):
        for e in events:
            now=stamp(e['received_at'])
            if type(e.get('sequence')) is not int or e['sequence']<=self.sequence or (self.now and now<self.now):
                raise ReferenceError('receipt_sequence_or_time_not_monotonic')
            self.now=now;self.sequence=e['sequence']
            identity=e['event_id'];payload={k:v for k,v in e.items() if k not in ('sequence','received_at')}
            h=digest(payload)
            if identity in self.seen:
                if self.seen[identity]==h:decision='duplicate:no_economic_mutation'
                else:
                    decision='conflict:quarantined_no_economic_mutation';self.risk_blocked=True
                    self.incidents.append(dict(event_id=identity,reason='conflicting_event_id',sequence=self.sequence))
            else:
                self.seen[identity]=h
                checkpoint=deepcopy((self.cash,self.orders,self.lots,self.daily,self.valuations,self.fees_paid,
                                     self.gross_bought,self.gross_sold,self.settlement_cash))
                try:
                    decision=self.apply(e);self.invariants()
                except (ReferenceError,KeyError,TypeError,ValueError) as exc:
                    (self.cash,self.orders,self.lots,self.daily,self.valuations,self.fees_paid,
                     self.gross_bought,self.gross_sold,self.settlement_cash)=checkpoint
                    self.risk_blocked=True;decision='incident:'+str(exc)
                    self.incidents.append(dict(event_id=identity,reason=str(exc),sequence=self.sequence))
            self.trace.append(dict(event_id=identity,sequence=self.sequence,kind=e['kind'],received_at=e['received_at'],
                                   decision=decision,state=self.state()))
        return dict(trace=self.trace,final=self.state(),valuations=self.valuations,incidents=self.incidents)


def run_fixture(document,standard=None):
    if standard is None:
        raise ReferenceError('explicit_frozen_standard_required')
    if document.get('evidence_class')!='controlled_synthetic_accounting_fixture_not_historical_backtest':
        raise ReferenceError('only_explicit_controlled_fixture_supported')
    validate_config(document['config'],standard)
    if not document.get('events'):
        raise ReferenceError('events_required')
    with localcontext() as ctx:
        ctx.prec=50
        engine=Replay(document['config']);result=engine.run(document['events'])
    result.update(evidence_class=document['evidence_class'],standard_id=standard['standard_id'],
                  input_canonical_sha256=digest(document),config_canonical_sha256=digest(document['config']),
                  standard_canonical_sha256=digest(standard),full_historical_30_day_outcomes=0,
                  model_comparison_permitted=False,source_to_fill_inference=False,
                  arithmetic='Decimal precision 50; explicit fixture quanta; authoritative fill units',
                  first_received_at=document['events'][0]['received_at'],last_received_at=document['events'][-1]['received_at'])
    return strings(result)


def main():
    parser=argparse.ArgumentParser();base=Path(__file__).resolve().parent
    parser.add_argument('--input',type=Path,default=base/'reference-input.json')
    parser.add_argument('--standard',type=Path,default=base/'copier-standard.json')
    parser.add_argument('--output',type=Path,default=base/'reference-output.json')
    args=parser.parse_args()
    document=json.loads(args.input.read_text());standard=json.loads(args.standard.read_text())
    result=run_fixture(document,standard)
    files=[args.input,args.standard,Path(__file__),base/'market_data.py']
    result['manifest']=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
    # Identical reruns verify an immutable artifact; changed inputs/code use a new output path.
    encoded=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    if args.output.exists() and args.output.read_text()!=encoded:
        raise ReferenceError('immutable_output_exists_choose_new_path')
    args.output.write_text(encoded)
    print(json.dumps(dict(output=str(args.output),trace_events=len(result['trace']),incidents=result['incidents'],
                         final_cash=result['final']['cash'],valuations=result['valuations']),indent=2))

if __name__=='__main__':
    main()
