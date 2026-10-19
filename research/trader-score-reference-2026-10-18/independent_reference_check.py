"""Independent controlled-ledger checks. No engine import; expected money is manual.
This is an open engineering regression suite, not a blind statistical holdout.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parent
ORACLE_SHA256 = '42bf8af63b97d8e81e6c6898f71095c1d4b408b285f3a8d97b82c9cb5c8c5974'
CHECKS = []

def check(name, condition, detail=''):
    CHECKS.append({'check': name, 'passed': bool(condition), 'detail': detail if not condition else ''})

def eq(name, actual, expected):
    check(name, D(str(actual)) == D(str(expected)), f'{actual} != {expected}')

def statecheck(name, state, expected):
    aliases = {'reserve':'cash_reserve'}
    for key in ('cash','reserve','available','daily_spent','daily_pending'):
        if key in expected:
            eq(name+':'+key, state[aliases.get(key,key)], expected[key])
    for key, field in [('quantity','quantity'),('cost','cost_basis')]:
        if key in expected:
            eq(name+':'+key, sum((D(x[field]) for x in state['positions'].values()),D(0)), expected[key])
    if 'current_day' in expected:
        check(name+':day',state['current_day']==expected['current_day'])
    for token, position in expected.get('positions',{}).items():
        for field, value in position.items():
            eq(name+':'+token+':'+field,state['positions'].get(token,{}).get(field,'0'),value)
    if 'sell_reserved_quantity' in expected:
        eq(name+':sell_reserve',state['positions']['A']['reserved_sell_quantity'],expected['sell_reserved_quantity'])
    if 'prior_day_spent' in expected:
        eq(name+':prior_day_spent',state['daily_used_all'].get('2026-03-28','0'),expected['prior_day_spent'])

def conservation(name,result):
    for i,row in enumerate(result['trace']):
        s=row['state'];prefix=f'{name}:row{i}'
        eq(prefix+':cash_less_reserve',D(s['cash'])-D(s['cash_reserve']),s['available'])
        eq(prefix+':reserve_components',D(s['gross_buy_reserve'])+D(s['expense_reserve']),s['cash_reserve'])
        eq(prefix+':daily_gross',D(s['daily_spent'])+D(s['daily_pending'])+D(s['daily_available']),'30')
        check(prefix+':nonnegative',all(D(s[k])>=0 for k in ('cash','available','cash_reserve','daily_available')))
        for token,p in s['positions'].items():
            eq(prefix+':lot_qty:'+token,sum((D(l['quantity']) for l in p['lots']),D(0)),p['quantity'])
            eq(prefix+':lot_cost:'+token,sum((D(l['cost_basis']) for l in p['lots']),D(0)),p['cost_basis'])

def utc(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))

def iso(value):
    return value.isoformat().replace('+00:00','Z')

def intent(name, token='A', at='2026-03-28T12:00:02Z', side='BUY'):
    t=utc(at)
    return dict(event_id=name,kind='intent',received_at=iso(t),order_id=name,token=token,side=side,
      observed_at=iso(t-timedelta(seconds=2)),source_at=iso(t-timedelta(seconds=3)),
      fee_cap='0.10',fee_evidence='controlled_fixture_not_venue_tariff',
      max_price='0.52' if side=='BUY' else None,min_price='0.58' if side=='SELL' else None,
      leader_before='100',leader_sold='25',books=[dict(token=token,
      available_at=iso(t-timedelta(seconds=.5)),source_at=iso(t-timedelta(seconds=.6)),
      payload={'asks':[['0.50' if side=='BUY' else '0.62','100']], 'bids':[['0.49' if side=='BUY' else '0.60','100']]})])

def fill(order, at, qty='10',price='0.50',gross='5',name=None,executed=None):
    return dict(event_id=name or order+'_fill',kind='fill',received_at=at,order_id=order,
      executed_at=executed or iso(utc(at)-timedelta(seconds=.25)),quantity=qty,price=price,gross=gross,
      confirmation='authoritative_controlled_fixture')

def terminal(order, at, gross='5', outcome='filled',fee='0.05'):
    return dict(event_id=order+'_terminal',kind='terminal',received_at=at,order_id=order,
      confirmed_gross_total=gross,outcome=outcome,fee_actual=fee,confirmation='authoritative_controlled_fixture')

def tick(name,at):return dict(event_id=name,kind='tick',received_at=at)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--actual',type=Path,default=BASE/'reference-output.json');args=parser.parse_args()
    original=json.loads((BASE/'reference-input.json').read_text())
    oracle_path=BASE/'expected-ledger.json';oracle=json.loads(oracle_path.read_text())
    check('frozen_manual_oracle_sha256',hashlib.sha256(oracle_path.read_bytes()).hexdigest()==ORACLE_SHA256)
    actual=json.loads(args.actual.read_text())
    primary={x['stage']:x for x in oracle['primary_checkpoints'] if x['stage']!='initial'}
    for row in actual['trace']:statecheck('primary:'+row['event_id'],row['state'],primary[row['event_id']])
    check('primary_event_count',len(actual['trace'])==23)
    check('primary_no_incidents',not actual['incidents'])
    conservation('primary',actual)
    for valuation in actual['valuations']:
        expected=oracle['valuations'][valuation['event_id']]
        status='known' if valuation['status']=='known_under_controlled_fixture' else valuation['status']
        check('valuation_status:'+valuation['event_id'],status==expected['status'])
        for key in ('equity','pnl'):
            if expected[key] is None:check('valuation_null:'+key,valuation[key] is None)
            else:eq('valuation:'+key,valuation[key],expected[key])
    check('H30_zero',actual['full_historical_30_day_outcomes']==0)
    check('comparison_disabled',actual['model_comparison_permitted'] is False)
    check('depth_never_fill_flag',actual['source_to_fill_inference'] is False)
    cases=[]
    with tempfile.TemporaryDirectory(prefix='independent-reference-') as temp:
        def run(name,events):
            doc=deepcopy(original);doc['events']=deepcopy(events)
            for i,e in enumerate(doc['events']):e['sequence']=i+1
            ip=Path(temp)/(name+'.json');op=Path(temp)/(name+'-out.json');ip.write_text(json.dumps(doc))
            proc=subprocess.run([sys.executable,str(BASE/'reference_replay.py'),'--input',str(ip),'--standard',str(BASE/'copier-standard.json'),'--output',str(op)],capture_output=True,text=True)
            if proc.returncode:raise AssertionError(name+': '+proc.stderr)
            result=json.loads(op.read_text());cases.append(name);conservation(name,result);return result
        # Exactly four $5 buys reach cost cap $20; a fifth is skipped in full.
        events=[]
        for i in range(5):
            t=utc('2026-03-28T12:00:02Z')+timedelta(seconds=10*i);order='p'+str(i)
            events.append(intent(order,at=iso(t)))
            if i<4:events.extend([fill(order,iso(t+timedelta(seconds=1))),terminal(order,iso(t+timedelta(seconds=2)))])
        r=run('repeat_buy_position_cap',events)
        statecheck(cases[-1],r['final'],dict(cash='179.80',reserve='0',available='179.80',quantity='40',cost='20',daily_spent='20'))
        check(cases[-1]+':skip',r['trace'][-1]['decision']=='skipped:position_limit')
        r=run('pending_position_cap',[intent('p'+str(i),at=iso(utc('2026-03-28T12:00:02Z')+timedelta(seconds=10*i))) for i in range(5)])
        statecheck(cases[-1],r['final'],dict(cash='200',reserve='20.40',available='179.60',quantity='0',cost='0',daily_pending='20'))
        check(cases[-1]+':skip',r['trace'][-1]['decision']=='skipped:position_limit')
        events=[]
        for i in range(7):
            t=utc('2026-03-28T12:00:02Z')+timedelta(seconds=10*i);order='d'+str(i)
            events.append(intent(order,token='T'+str(i),at=iso(t)))
            if i<6:events.extend([fill(order,iso(t+timedelta(seconds=1))),terminal(order,iso(t+timedelta(seconds=2)))])
        r=run('daily_gross_excludes_fees',events)
        statecheck(cases[-1],r['final'],dict(cash='169.70',reserve='0',available='169.70',quantity='60',cost='30',daily_spent='30'))
        check(cases[-1]+':skip',r['trace'][-1]['decision']=='skipped:daily_limit')
        first=intent('a');full=fill('a','2026-03-28T12:00:03Z');term=terminal('a','2026-03-28T12:00:04Z')
        r=run('unknown_cancel_request_midnight',[first,dict(event_id='u',kind='unknown',received_at='2026-03-28T12:00:03Z',order_id='a'),dict(event_id='c',kind='cancel_request',received_at='2026-03-28T12:00:04Z',order_id='a'),tick('day','2026-03-28T23:00:00Z')])
        statecheck(cases[-1],r['final'],dict(cash='200',reserve='5.10',available='194.90',daily_spent='0',daily_pending='5',quantity='0'))
        r=run('full_fill_retains_fee',[first,full]);statecheck(cases[-1],r['final'],dict(cash='195',reserve='.10',available='194.90'))
        # Duplicate delivery in two valid receipt placements preserves the same manual endpoint.
        for slot in ('before_terminal','after_terminal'):
            duplicate=deepcopy(full);duplicate['received_at']='2026-03-28T12:00:03.5Z' if slot=='before_terminal' else '2026-03-28T12:00:05Z'
            events=[first,full,duplicate,term] if slot=='before_terminal' else [first,full,term,duplicate]
            r=run('duplicate_'+slot,events);statecheck(cases[-1],r['final'],dict(cash='194.95',reserve='0',quantity='10',cost='5',daily_spent='5'))
            check(cases[-1]+':no_incident',not r['incidents'])
        conflict=deepcopy(full);conflict.update(received_at='2026-03-28T12:00:03.5Z',quantity='8',gross='4')
        r=run('conflicting_identity_then_reconcile',[first,full,conflict,term,intent('blocked',token='B',at='2026-03-28T12:00:08Z')])
        statecheck(cases[-1],r['final'],dict(cash='194.95',reserve='0',quantity='10',cost='5'))
        check(cases[-1]+':blocked',r['final']['risk_blocked'] and r['trace'][-1]['decision']=='skipped:risk_quarantine')
        # Each invalid pre-intent fact independently produces no order/reserve.
        for label,mutate in [
          ('unknown_fee',lambda e:e.update(fee_cap=None)),
          ('missing_price',lambda e:e.update(max_price=None)),
          ('future_book',lambda e:e['books'][0].update(available_at='2026-03-28T12:00:03Z')),
          ('stale_source',lambda e:e['books'][0].update(source_at='2026-03-28T12:00:00Z')),
          ('exact_book_tie',lambda e:e['books'][0].update(available_at=e['received_at'])),
          ('empty_depth',lambda e:e['books'][0]['payload'].update(asks=[]))]:
            e=deepcopy(first);mutate(e);r=run(label,[e]);statecheck(label,r['final'],dict(cash='200',reserve='0',quantity='0'))
            check(label+':no_order',not r['final']['orders'])
        # Full execution after partial/cancel request still counts all confirmed fills.
        p=fill('a','2026-03-28T12:00:03Z',qty='4',gross='2',name='part')
        f=fill('a','2026-03-28T12:00:04Z',qty='6',gross='3',name='rest')
        t=terminal('a','2026-03-28T12:00:05Z')
        r=run('cancel_race_full_confirmation',[first,p,f,t]);statecheck(cases[-1],r['final'],dict(cash='194.95',reserve='0',quantity='10',cost='5'))
        check(cases[-1]+':status',r['final']['orders']['a']['status']=='filled_cancel_too_late')
        # Invalid confirmations quarantine atomically; reserve remains.
        for label,mutate in [('overfill',lambda e:e.update(quantity='12',gross='6')),('future_fill',lambda e:e.update(executed_at='2026-03-28T12:00:04Z')),('preintent_fill',lambda e:e.update(executed_at='2026-03-28T12:00:01Z')),('wrong_units',lambda e:e.update(gross='4')),('price_cap',lambda e:e.update(quantity='5',price='1',gross='5'))]:
            f=deepcopy(full);mutate(f);r=run(label,[first,f]);statecheck(label,r['final'],dict(cash='200',reserve='5.10',quantity='0',cost='0'))
            check(label+':incident',r['final']['risk_blocked'])
        r=run('terminal_mismatch',[first,p,terminal('a','2026-03-28T12:00:04Z',gross='5',outcome='cancelled_remainder')])
        statecheck(cases[-1],r['final'],dict(cash='198',reserve='3.10',quantity='4',cost='2'));check(cases[-1]+':blocked',r['final']['risk_blocked'])
        r=run('terminal_unknown_fee',[first,full,terminal('a','2026-03-28T12:00:04Z',fee=None)])
        statecheck(cases[-1],r['final'],dict(cash='195',reserve='.10',available='194.90'))
        # Independently expected execution-day split: received after midnight, executed after it.
        events=deepcopy(original['events'][:8]);events[-1]['executed_at']='2026-03-28T23:00:01Z'
        r=run('late_new_day_execution',events);statecheck(cases[-1],r['final'],dict(cash='197',reserve='2.10',daily_spent='1',daily_pending='2'))
        eq(cases[-1]+':previous_day',r['final']['daily_used_all']['2026-03-28'],'2')
        # Spring and autumn resets follow IANA local midnight, not fixed 24h or repeated hour.
        r=run('fall_dst',[tick('start','2026-10-24T22:00:00Z'),tick('first02','2026-10-25T00:30:00Z'),tick('second02','2026-10-25T01:30:00Z'),tick('next','2026-10-25T23:00:00Z')])
        for row in r['trace'][:3]:
            check('fall:day:'+row['event_id'],row['state']['current_day']=='2026-10-25')
            check('fall:reset:'+row['event_id'],utc(row['state']['next_reset_utc'])==utc('2026-10-25T23:00:00Z'))
        check('fall:next_day',r['final']['current_day']=='2026-10-26')
        spring=next(x for x in actual['trace'] if x['event_id']=='midnight')
        check('spring:23hour_reset',utc(spring['state']['next_reset_utc'])==utc('2026-03-29T22:00:00Z'))
        # A sell requires known leader inventory; fractions apply only to confirmed owned shares.
        sell=intent('sell',side='SELL',at='2026-03-28T12:00:08Z');sell['leader_before']=None
        r=run('sell_unknown_inventory',[first,full,term,sell]);statecheck(cases[-1],r['final'],dict(cash='194.95',reserve='0',quantity='10',cost='5'))
        check(cases[-1]+':skip',r['trace'][-1]['decision']=='skipped:leader_inventory_unknown')
    summary=dict(scope='controlled independent manual and adversarial accounting checks; not historical or statistical model validation',primary_events=23,adversarial_cases=cases,assertions=len(CHECKS),passed=sum(x['passed'] for x in CHECKS),failed=[x for x in CHECKS if not x['passed']],oracle_sha256=ORACLE_SHA256,actual_file=args.actual.name,
      reviewed_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/'reference_replay.py',BASE/'market_data.py',BASE/'copier-standard.json',args.actual]})
    print(json.dumps(summary,indent=2));return 1 if summary['failed'] else 0

if __name__=='__main__':sys.exit(main())
