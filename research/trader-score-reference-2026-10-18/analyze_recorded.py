"""Versioned qualification of saved public data; never an executed copier backtest.

PYTHONPATH=/tmp/trader-score-python-deps python3 analyze_recorded.py --output-dir NEW_DIR
No IO on import. Old 16-Oct code/results are read-only. Output directory must be new.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal
import bisect
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from market_data import (EvidenceError, Snapshot, decimal_value, parse_json,
                         parse_book, displayed_buy_capacity, select_snapshot,
                         sha256_file, verify_manifest_files)

D = Decimal
VERSION = 'recorded-qualification-v2-2026-10-18'


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise EvidenceError('invalid_manifest:' + str(path)) from exc


def require_schema(connection, relation, required):
    actual = {r[0]: r[1] for r in connection.execute('DESCRIBE ' + relation).fetchall()}
    for name, expected in required.items():
        if actual.get(name) != expected:
            raise EvidenceError('schema_mismatch:' + relation + ':' + name)


def exact_schema(connection, relation, required):
    require_schema(connection, relation, required)
    names = {r[0] for r in connection.execute('DESCRIBE ' + relation).fetchall()}
    if names != set(required):
        raise EvidenceError('schema_field_list_mismatch:' + relation)


def table_rows(connection, sql):
    cur = connection.execute(sql)
    return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]


def verify_inputs(repo, connection):
    aligned = repo / 'research/trader-score-aligned-2026-10-16'
    real = repo / 'research/trader-score-real-2026-10-16/polymarket'
    target = aligned / 'source-audit/pmxt-target'
    manifest = read_json(target / 'target-manifest.json')
    target_entry = {'file': manifest['derived_file'], 'bytes': manifest['derived_bytes'],
                    'sha256': manifest['derived_sha256']}
    target_verified = verify_manifest_files(target, [target_entry], ['target-events.parquet'])
    trade_entries = read_json(aligned / 'trades-manifest.json')
    trade_names = [f'data/trades-2026-03-{d:02}.parquet' for d in (1, 2, 3, 4)]
    if {str(p.relative_to(aligned)) for p in (aligned/'data').glob('trades-*.parquet')} != set(trade_names):
        raise EvidenceError('unexpected_trade_input_file')
    trade_verified = verify_manifest_files(aligned, trade_entries, trade_names)
    start = date(2024, 1, 1)
    real_names = [f'trade_archive/{start+timedelta(days=d):%Y_%m_%d}.parquet' for d in range(60)]
    real_names += ['trade_archive/README.md', 'quote_sample/README.md',
                   'quote_sample/market_meta.parquet', 'quote_sample/polymarket_ticks_ms.parquet']
    if {str(p.relative_to(real)) for p in (real/'trade_archive').glob('*.parquet')} != set(real_names[:60]):
        raise EvidenceError('unexpected_hindsight_input_file')
    real_verified = verify_manifest_files(real, read_json(real/'manifest.json'), real_names)
    connection.read_parquet(str(target/'target-events.parquet')).create_view('pmxt')
    exact_schema(connection, 'pmxt', {'timestamp_received':'TIMESTAMP WITH TIME ZONE',
        'timestamp_created_at':'TIMESTAMP WITH TIME ZONE', 'market_id':'VARCHAR',
        'update_type':'VARCHAR', 'data':'VARCHAR'})
    required_trade = {'asset_id':'VARCHAR','condition_id':'VARCHAR','block_timestamp':'BIGINT',
                      'taker_direction':'VARCHAR','price':'DOUBLE','maker':'VARCHAR','taker':'VARCHAR'}
    for entry in trade_entries:
        connection.read_parquet(str(aligned/entry['file'])).create_view('one_trade', replace=True)
        require_schema(connection, 'one_trade', required_trade)
        expected = entry.get('rows')
        count = connection.execute('SELECT count(*) FROM one_trade').fetchone()[0]
        if type(expected) is not int or expected != count:
            raise EvidenceError('row_count_mismatch:' + entry['file'])
        predicate = entry.get('predicate', {})
        assets = predicate.get('asset_ids')
        if not isinstance(assets, list) or not assets or len(set(assets)) != len(assets):
            raise EvidenceError('invalid_trade_asset_scope')
        if predicate.get('start_inclusive') != 1772323200 or predicate.get('end_exclusive') != 1772582400:
            raise EvidenceError('unexpected_trade_time_scope')
        bad = connection.execute('''SELECT count(*) FROM one_trade WHERE asset_id IS NULL
            OR condition_id IS NULL OR block_timestamp IS NULL OR NOT list_contains(?,asset_id)
            OR block_timestamp < ? OR block_timestamp >= ?''',
            [assets, predicate['start_inclusive'], predicate['end_exclusive']]).fetchone()[0]
        if bad:
            raise EvidenceError('trade_scope_mismatch')
    connection.read_parquet([str(aligned/e['file']) for e in trade_entries]).create_view('aligned_trades')
    connection.read_parquet([str(real/n) for n in real_names[:60]]).create_view('hindsight')
    require_schema(connection,'hindsight',{'asset_id':'VARCHAR','condition_id':'VARCHAR',
        'block_timestamp':'BIGINT','taker_direction':'VARCHAR','price':'DOUBLE','usdc_amount':'DOUBLE',
        'taker':'VARCHAR','outcome_label':'VARCHAR','winning_outcome_label':'VARCHAR'})
    if connection.execute('SELECT count(*) FROM pmxt').fetchone()[0] != manifest['target_rows']:
        raise EvidenceError('pmxt_row_count_mismatch')
    if connection.execute('SELECT count(*) FROM pmxt WHERE market_id IS NULL OR market_id<>?',
                          [manifest['target_condition']]).fetchone()[0]:
        raise EvidenceError('pmxt_condition_mismatch')
    return manifest, {'target':target_verified, 'aligned_trades':trade_verified,
                      'hindsight_inputs':real_verified,
        'source_manifest_hashes':{str(p.relative_to(repo)):sha256_file(p) for p in
          [target/'target-manifest.json',aligned/'trades-manifest.json',real/'manifest.json']}}


def hindsight_diagnostic(connection):
    """Ambiguous first-second buckets are never asserted to be a first trade."""
    connection.execute('''CREATE VIEW valid_buys AS SELECT lower(taker) wallet,condition_id,
        asset_id,block_timestamp,price,usdc_amount,outcome_label,winning_outcome_label
        FROM hindsight WHERE taker_direction='BUY' AND isfinite(price) AND price>0 AND price<1
        AND taker IS NOT NULL AND condition_id IS NOT NULL AND asset_id IS NOT NULL
        AND outcome_label IS NOT NULL AND winning_outcome_label IS NOT NULL''')
    connection.execute('''CREATE VIEW earliest_bucket AS SELECT * FROM valid_buys QUALIFY
        block_timestamp=min(block_timestamp) OVER(PARTITION BY wallet,condition_id)''')
    connection.execute('''CREATE TABLE buckets AS SELECT wallet,condition_id,min(block_timestamp) bucket_time,
        count(*) row_count,count(DISTINCT struct_pack(asset:=asset_id,price:=price,amount:=usdc_amount,
           outcome:=outcome_label,winner:=winning_outcome_label)) economic_versions,
        min(price) price_lower,max(price) price_upper,
        min(CASE WHEN outcome_label=winning_outcome_label THEN 1.0 ELSE 0.0 END-price) payoff_price_lower,
        max(CASE WHEN outcome_label=winning_outcome_label THEN 1.0 ELSE 0.0 END-price) payoff_price_upper
        FROM earliest_bucket GROUP BY wallet,condition_id''')
    summary = table_rows(connection,'''SELECT count(*) wallet_condition_groups,
        count(*) FILTER(WHERE row_count>1) multiple_row_buckets,
        count(*) FILTER(WHERE economic_versions>1) ambiguous_economic_buckets,
        count(*) FILTER(WHERE price_lower<>price_upper) ambiguous_price_buckets,
        count(*) FILTER(WHERE row_count=1) strict_single_row_buckets,
        avg(payoff_price_lower) pooled_lower_if_arbitrary_first_row,
        avg(payoff_price_upper) pooled_upper_if_arbitrary_first_row FROM buckets''')[0]
    # One source row in a first second is a unique observed row, not independent onchain proof.
    strict = table_rows(connection,'''SELECT
        CASE WHEN e.price<.1 THEN '0.00-0.10' WHEN e.price<.5 THEN '0.10-0.50'
             WHEN e.price<.9 THEN '0.50-0.90' ELSE '0.90-1.00' END price_band,
        count(*) observations,avg(e.price) mean_price,
        avg(CASE WHEN e.outcome_label=e.winning_outcome_label THEN 1.0 ELSE 0.0 END) hindsight_win_fraction,
        avg(CASE WHEN e.outcome_label=e.winning_outcome_label THEN 1.0 ELSE 0.0 END-e.price) payoff_minus_price
        FROM earliest_bucket e JOIN buckets b USING(wallet,condition_id)
        WHERE b.row_count=1 GROUP BY 1 ORDER BY 1''')
    bounds = table_rows(connection,'''SELECT sha256(wallet) wallet_pseudonym,condition_id,bucket_time,
        row_count,economic_versions,price_lower,price_upper,payoff_price_lower,payoff_price_upper,
        CASE WHEN row_count=1 THEN 'single_observed_row' WHEN economic_versions=1
             THEN 'multiple_equivalent_rows_identity_unknown' ELSE 'ambiguous_economic_values' END selection_status
        FROM buckets ORDER BY wallet_pseudonym,condition_id''')
    return {'diagnostic_version':VERSION,'result_kind':'hindsight_first_second_bucket_diagnostic_not_pnl',
            'selection_rule':'first eligible observed second per wallet/condition; multiple source rows excluded from strict table',
            'metadata_note':'Retrospective final labels only; not information known at prediction time. Raw first event identity absent.',
            'summary':summary,'strict_single_row_price_bands':strict,
            'bounds_note':'Bounds enumerate admissible first-row payoff-price values inside each observed bucket; not confidence intervals, return or model calibration.'}, bounds


def pmxt_diagnostic(connection, manifest):
    connection.execute("""CREATE VIEW ordered_pmxt AS SELECT *,
       try_cast(json_extract_string(data,'$.timestamp') AS DECIMAL(38,15)) json_time,
       epoch_ms(timestamp_received) received_ms,epoch_ms(timestamp_created_at) created_ms
       FROM pmxt""")
    if connection.execute('SELECT count(*) FROM ordered_pmxt WHERE json_time IS NULL OR received_ms IS NULL OR created_ms IS NULL').fetchone()[0]:
        raise EvidenceError('missing_or_invalid_clock')
    state = {}; snapshots = defaultdict(list); update_times = defaultdict(list)
    counters = Counter(); errors = Counter(); tokens = set(); deltas = []
    clock_min = None; clock_max = None; lo = None; hi = None; available_hi = None
    maximum_best_difference=D(0); maximum_quantity_difference=D(0); minimum_quantity_difference=None
    query = '''SELECT data,json_time,received_ms,created_ms,market_id,update_type
               FROM ordered_pmxt ORDER BY json_time,received_ms,created_ms'''
    cursor=connection.execute(query)
    # fetchmany bounds transient memory. No raw events are written into the new output.
    while True:
        batch=cursor.fetchmany(4096)
        if not batch: break
        for raw, ordered_time, rx_ms, created_ms, condition, outer_type in batch:
            obj=parse_json(raw); token=obj.get('token_id'); typ=obj.get('update_type')
            if not isinstance(token,str) or not token.isdigit() or obj.get('market_id') != condition or typ != outer_type:
                raise EvidenceError('pmxt_identity_or_event_type_mismatch')
            if typ not in ('book_snapshot','price_change'):
                raise EvidenceError('unsupported_pmxt_event_type')
            jt=decimal_value(obj.get('timestamp'))
            if jt != ordered_time:
                raise EvidenceError('json_timestamp_precision_loss')
            received=D(rx_ms)/1000; created=D(created_ms)/1000; available=max(received,created)
            diff=jt-received; clock_min=diff if clock_min is None else min(clock_min,diff); clock_max=diff if clock_max is None else max(clock_max,diff)
            lo=received if lo is None else min(lo,received);hi=received if hi is None else max(hi,received)
            available_hi=available if available_hi is None else max(available_hi,available)
            tokens.add(token);counters[typ]+=1
            if typ=='book_snapshot':
                book=parse_book(obj)
                snapshots[token].append(Snapshot(token,available,book))
                if book.status!='valid':
                    errors.update(book.errors);state.pop(token,None);continue
                new={'bids':dict(book.bids),'asks':dict(book.asks)}
                if token in state:
                    old=state[token];counters['snapshot_comparisons']+=1
                    top=lambda b:(max(b['bids'],default=None),min(b['asks'],default=None))
                    same=old==new;same_top=top(old)==top(new)
                    counters['same_depth']+=same;counters['same_top']+=same_top
                    if not same:
                        missing=sum(len(set(old[s]) ^ set(new[s])) for s in ('bids','asks'))
                        quantities=[abs(old[s][p]-new[s][p]) for s in ('bids','asks') for p in set(old[s])&set(new[s]) if old[s][p]!=new[s][p]]
                        differences=[abs(a-b) for a,b in zip(top(old),top(new)) if a is not None and b is not None]
                        maximum_best_difference=max(maximum_best_difference,max(differences,default=D(0)))
                        maximum_quantity_difference=max(maximum_quantity_difference,max(quantities,default=D(0)))
                        if quantities:minimum_quantity_difference=min(minimum_quantity_difference or min(quantities),min(quantities))
                        counters['mismatch_with_changed_price_levels']+=bool(missing)
                        counters['mismatch_quantity_only']+=not missing
                        if len(deltas)<3:
                            deltas.append({'token':token,'json_timestamp':jt,'before_top':top(old),'after_top':top(new),
                                'changed_levels':[{'side':s,'price':p,'before':old[s].get(p),'after':new[s].get(p)} for s in ('bids','asks')
                                   for p in sorted(set(old[s])|set(new[s])) if old[s].get(p)!=new[s].get(p)]})
                state[token]=new
            else:
                update_times[token].append(available)
                side={'BUY':'bids','SELL':'asks'}.get(obj.get('change_side'))
                price=decimal_value(obj.get('change_price'));size=decimal_value(obj.get('change_size'))
                if side is None or price<0 or price>1 or size<0:
                    raise EvidenceError('invalid_price_change')
                if token in state:
                    if size>0:state[token][side][price]=size
                    else:state[token][side].pop(price,None)
    for times in update_times.values():times.sort()
    trades=connection.execute('''SELECT asset_id,block_timestamp,taker_direction FROM aligned_trades
               WHERE condition_id=? AND block_timestamp>=? AND block_timestamp<=?''',
               [manifest['target_condition'],lo,hi]).fetchall()
    if set(tokens) - {r[0] for r in connection.execute('SELECT DISTINCT asset_id FROM aligned_trades WHERE condition_id=?',[manifest['target_condition']]).fetchall()}:
        raise EvidenceError('pmxt_tokens_outside_target_trade_scope')
    selection_counts=Counter();capacity_counts=Counter();examples=[]
    for token,seconds,side in trades:
        if side!='BUY':continue
        selection_counts['buy_rows']+=1
        arrival=D(seconds)+2
        if arrival>available_hi:
            selection_counts['arrival_outside_sample']+=1;continue
        selected=select_snapshot(snapshots.get(token,[]),arrival,D(1))
        selection_counts[selected.reason]+=1
        if selected.status!='eligible':continue
        snapshot=selected.snapshot
        capacity=displayed_buy_capacity(snapshot.book,D(5))
        capacity_counts[capacity.status]+=1
        times=update_times[token]
        known_changes=bisect.bisect_right(times,arrival)-bisect.bisect_left(times,snapshot.available)
        selection_counts['tied_or_intervening_updates']+=bool(known_changes)
        selection_counts['without_known_updates']+=not known_changes
        if len(examples)<3:examples.append({'token':token,'arrival':arrival,'snapshot_available':snapshot.available,
             'known_changes_inclusive':known_changes,'displayed_snapshot_capacity':asdict(capacity)})
    selection_counts.setdefault('without_known_updates',0)
    return {'diagnostic_version':VERSION,'result_kind':'recorded_source_qualification_not_execution',
       'events':dict(counters),'snapshot_validation_errors':dict(errors),'received_min':lo,'received_max':hi,
       'json_minus_received_seconds':[clock_min,clock_max],'clock_contract_verified':False,
       'replay_ordering':'JSON timestamp precision retained; sensitivity only, not verified exchange sequence',
       'replay_mismatch_examples':deltas,'max_best_price_difference':maximum_best_difference,
       'max_quantity_difference':maximum_quantity_difference,'min_nonzero_quantity_difference':minimum_quantity_difference,
       'matching_trade_rows_in_received_interval':len(trades),'selection_2s_1s_max_age':dict(selection_counts),
       'snapshot_gross_5_capacity':dict(capacity_counts),'examples':examples,
       'copier_fill_claim':False,'copier_pnl':None,'model_verdict':'not_validated',
       'unresolved':['signal observedAt','historical collector clock contract/sequence and replay mismatch',
                     'same-period fees/rounding/price caps','leader inventory for proportional sells',
                     'own copier ledger and horizon','venue Limitless scope']} 


def json_default(value):
    if isinstance(value,Decimal):return str(value)
    raise TypeError(type(value).__name__)


def run(repo: Path, output: Path):
    # Optional dependency imported only for an explicit recorded analysis run.
    import duckdb
    if duckdb.__version__!='1.4.1':
        raise EvidenceError('duckdb_version_must_be_1.4.1')
    repo=repo.resolve(); output=output.resolve()
    protected=[repo/'research/trader-score-aligned-2026-10-16',repo/'research/trader-score-real-2026-10-16']
    if output.exists() or any(output.is_relative_to(p) for p in protected):
        raise EvidenceError('output_must_be_new_and_outside_historical_inputs')
    c=duckdb.connect();c.execute("SET TimeZone='UTC'");c.execute("SET memory_limit='1GB'");c.execute('SET threads=2')
    source,verified=verify_inputs(repo,c)
    pmxt=pmxt_diagnostic(c,source)
    hindsight,bounds=hindsight_diagnostic(c)
    result={'version':VERSION,'inputs':verified,'source_target_manifest':source,
       'runtime':{'python':sys.version,'duckdb':duckdb.__version__},
       'config':{'arrival_delay_seconds':'2','max_snapshot_age_seconds':'1','snapshot_gross_probe':'5',
                 'no_fees_or_fill_claim':True,'json_timestamp_order':'sensitivity_only'},
       'code_sha256':{p.name:sha256_file(p) for p in [Path(__file__),Path(__file__).with_name('market_data.py')]}}
    files={'recorded-qualification.json':pmxt,'first-bucket-diagnostic.json':hindsight,
           'first-bucket-bounds.json':bounds,'run-manifest.json':result}
    # Publish one complete bundle only after all computations and checks succeeded.
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.recorded-staging-',dir=output.parent))
    try:
        for name,value in files.items():
            (temporary/name).write_text(json.dumps(value,indent=2,default=json_default,allow_nan=False)+'\n')
        checks={p.name:{'bytes':p.stat().st_size,'sha256':sha256_file(p)} for p in sorted(temporary.iterdir())}
        (temporary/'output-manifest.json').write_text(json.dumps(checks,indent=2)+'\n')
        # Existing destination cannot be overwritten by rename when it contains output.
        if output.exists():raise EvidenceError('output_created_concurrently')
        os.rename(temporary,output)
    finally:
        if temporary.exists():
            import shutil
            shutil.rmtree(temporary)
    return {'output':str(output),'result_kind':pmxt['result_kind'],'events':pmxt['events'],
            'selection':pmxt['selection_2s_1s_max_age'],'first_bucket_summary':hindsight['summary']}


def main(argv=None):
    here=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=here.parents[1])
    parser.add_argument('--output-dir',type=Path,default=here/'recorded-qualification-v2')
    args=parser.parse_args(argv)
    try:
        summary=run(args.repo_root,args.output_dir)
    except (EvidenceError,OSError,KeyError) as exc:
        print(json.dumps({'status':'qualification_failed','error':str(exc)}),file=sys.stderr)
        return 2
    print(json.dumps(summary,indent=2,default=json_default));return 0


if __name__=='__main__':
    raise SystemExit(main())
