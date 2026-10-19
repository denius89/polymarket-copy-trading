"""Independent bounded checks; reads saved inputs, writes only this review directory."""
import argparse, ast, collections, hashlib, json, math
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=OUT/'check-post-retirement.json')
args=parser.parse_args()
if args.output.resolve()==(OUT/'data-replay-checks.json').resolve():
 raise SystemExit('The original review baseline is read-only; choose a new output filename.')
if args.output.exists():
 raise SystemExit('Refusing to overwrite an existing check output.')
old=ROOT/'research/trader-score-aligned-2026-10-16'
real=ROOT/'research/trader-score-real-2026-10-16'
c=duckdb.connect();c.execute("SET TimeZone='UTC'");c.execute("SET memory_limit='1GB'");c.execute('SET threads=2')
c.read_parquet(str(real/'polymarket/trade_archive/*.parquet')).create_view('t')
def query(sql):
 cur=c.execute(sql);return [dict(zip([x[0] for x in cur.description],r)) for r in cur.fetchall()]
r={'scope':'Saved snapshots only; no new financial model or replay execution','duckdb_version':duckdb.__version__}
r['actual_calendar_bounds']=query('''select min(block_timestamp) first_s,max(block_timestamp) last_s,
 count(*) filter(where block_timestamp<1704067200) before_jan1,
 count(*) filter(where block_timestamp>=1709251200) after_march1 from t''')
c.execute('''CREATE VIEW valid AS SELECT * FROM t WHERE taker_direction='BUY' AND price>0 AND price<1
 AND outcome_label IS NOT NULL AND winning_outcome_label IS NOT NULL''')
c.execute('''CREATE VIEW earliest AS SELECT * FROM valid QUALIFY block_timestamp=min(block_timestamp)
 OVER(PARTITION BY lower(taker),condition_id)''')
r['first_buy_ties']=query('''SELECT count(*) wallet_condition_groups,
 count(*) filter(where n>1) groups_with_multiple_earliest_rows,
 count(*) filter(where economic_versions>1) groups_with_ambiguous_earliest_economic_values,
 count(*) filter(where prices>1) groups_with_multiple_prices,
 count(*) filter(where outcomes>1) groups_with_multiple_outcomes,
 sum(n) earliest_rows FROM (SELECT lower(taker),condition_id,count(*) n,
 count(distinct struct_pack(asset:=asset_id,price:=price,notional:=usdc_amount)) economic_versions,
 count(distinct price) prices,count(distinct outcome_label) outcomes FROM earliest GROUP BY 1,2)''')
for direction in ['ASC','DESC']:
 r['tie_order_'+direction]=query(f'''WITH first_buys AS (SELECT * FROM valid QUALIFY row_number() OVER
 (PARTITION BY lower(taker),condition_id ORDER BY block_timestamp,asset_id {direction},price {direction},usdc_amount {direction})=1)
 SELECT case when price<.1 then '0.00-0.10' when price<.5 then '0.10-0.50' when price<.9 then '0.50-0.90' else '0.90-1.00' end band,
 count(*) n,avg(price) mean_price,avg(case when outcome_label=winning_outcome_label then 1.0 else 0.0 end) win_fraction,
 avg(case when outcome_label=winning_outcome_label then 1.0 else 0.0 end-price) payoff_minus_price
 FROM first_buys GROUP BY 1 ORDER BY 1''')
r['first_after_metadata_filter']=query('''WITH a AS(SELECT lower(taker) w,condition_id,min(block_timestamp) earliest_any
 FROM t WHERE taker_direction='BUY' AND price>0 AND price<1 GROUP BY 1,2),b AS(SELECT lower(taker) w,condition_id,min(block_timestamp) earliest_valid FROM valid GROUP BY 1,2)
 SELECT count(*) represented_groups,count(*) filter(where earliest_valid>earliest_any) first_changed_by_metadata_filter FROM a JOIN b USING(w,condition_id)''')
# The executable entrypoint was retired on 18 October. Read its byte-preserved
# archive to reproduce historical failures, never the new safe retirement guard.
# AST extraction avoids executing the archived analyzer or overwriting its outputs.
p=old/'source-audit/analyze_pmxt_target.2026-10-16.py.txt'
tree=ast.parse(p.read_text()); funcs=[x for x in tree.body if isinstance(x,ast.FunctionDef)]
ns={'math':math};exec(compile(ast.Module(body=funcs,type_ignores=[]),str(p),'exec'),ns)
r['snapshot_fail_closed_fixtures']=[]
for name,x in [('malformed_pair',{'bids':[], 'asks':[[.5]]}),('nonnumeric_size',{'bids':[], 'asks':[[.5,'unknown']]}),('missing_asks',{'bids':[[.4,10]]})]:
 item={'case':name,'validation_errors':ns['validate_snapshot'](x)}
 try: b=ns['book'](x);item['book_result']=b;item['capacity']=ns['capacity'](b)
 except Exception as e:item['book_exception']=type(e).__name__+': '+str(e)
 r['snapshot_fail_closed_fixtures'].append(item)
valid={'bids':[[.4,10]],'asks':[[.5,10]]};bad={'bids':[[.4,10],[.3,-10]],'asks':[[.5,10]]}
def snap(x):
 b=ns['book'](x)
 return {'invalid':bool(ns['validate_snapshot'](x)),'book_signature':hashlib.sha256(json.dumps(b,sort_keys=True).encode()).hexdigest(),**ns['capacity'](b)}
gg=[snap(valid),snap(bad)]
selected={**gg[0],'conflicting':len({s['book_signature'] for s in gg})>1}
r['same_signature_invalid_tie']={'group_invalid_flags':[s['invalid'] for s in gg],'selected_invalid':selected['invalid'],'conflicting':selected['conflicting'],'fits_5_usd':selected['fits_5_usd'],'passes_current_invalid_and_conflict_checks':not selected['invalid'] and not selected['conflicting']}
# Check existing saved derived provenance, but do not mistake this for automatic checks inside old scripts.
r['input_hash_checks']=[]
for manifest,base in [(old/'trades-manifest.json',old),(old/'quotes-manifest.json',old),(real/'polymarket/manifest.json',real/'polymarket')]:
 entries=json.loads(manifest.read_text())
 r['input_hash_checks'].append({'manifest':str(manifest.relative_to(ROOT)),'files':len(entries),'all_match':all(hashlib.sha256((base/e['file']).read_bytes()).hexdigest()==e['sha256'] for e in entries)})
m=json.loads((old/'source-audit/pmxt-target/target-manifest.json').read_text())
pq=old/'source-audit/pmxt-target'/m['derived_file']
r['pmxt_derived_integrity_now']={'bytes_match':pq.stat().st_size==m['derived_bytes'],'sha_matches':hashlib.sha256(pq.read_bytes()).hexdigest()==m['derived_sha256']}
# Hash review targets including code; this report never edits them.
r['audited_code_sha256']={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [p,old/'analyze_alignment.py',real/'analyze_public.2026-10-16.py.txt',old/'extract_trades.py']}
r['historical_source_note']='Archived 16 October code reproduces historical defects; executable entrypoints are now retirement guards. Original review baseline preserved.'
args.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
print(json.dumps(r,indent=2,allow_nan=False))
