"""Verify frozen source inputs and independently quantify conditional proxy fitness.
No fills, fees, money trajectories or score values are inferred. No network IO.
"""
from pathlib import Path
import hashlib, importlib.util, json, sys
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
REF=REPO/'research/trader-score-reference-2026-10-18'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(c,q):
    x=c.execute(q); return [dict(zip([v[0] for v in x.description],r)) for r in x.fetchall()]
def run():
    import duckdb
    sys.path.insert(0,str(REF))
    import analyze_recorded
    c=duckdb.connect(); c.execute("SET TimeZone='UTC'")
    _, verification=analyze_recorded.verify_inputs(REPO,c)
    manifest=REPO/'research/trader-score-aligned-2026-10-16/quotes-manifest.json'
    quote_entries=json.loads(manifest.read_text())
    from market_data import verify_manifest_files
    quotes=verify_manifest_files(manifest.parent,quote_entries,[e['file'] for e in quote_entries])
    c.execute('''CREATE VIEW meta AS SELECT condition_id,
        count(DISTINCT winning_outcome_label) winner_versions,
        count(DISTINCT resolved_at) resolution_versions,
        count(*) FILTER(WHERE winning_outcome_label IS NULL OR resolved_at IS NULL) missing_metadata_rows
        FROM hindsight GROUP BY condition_id''')
    c.execute('''CREATE VIEW first_bucket AS SELECT *,lower(taker) wallet FROM hindsight
      WHERE taker_direction='BUY' AND taker IS NOT NULL AND condition_id IS NOT NULL
      QUALIFY block_timestamp=min(block_timestamp) OVER(PARTITION BY lower(taker),condition_id)''')
    c.execute('''CREATE VIEW bucket_counts AS SELECT wallet,condition_id,count(*) n FROM first_bucket GROUP BY 1,2''')
    c.execute('''CREATE VIEW usable AS SELECT b.*,
        CASE WHEN outcome_label=winning_outcome_label THEN 1.0 ELSE 0.0 END -price edge
        FROM first_bucket b JOIN bucket_counts k USING(wallet,condition_id)
        JOIN meta m USING(condition_id) WHERE k.n=1 AND m.winner_versions=1 AND m.resolution_versions=1
        AND m.missing_metadata_rows=0 AND b.asset_id IS NOT NULL AND isfinite(price) AND price>0 AND price<1
        AND outcome_label IS NOT NULL AND winning_outcome_label IS NOT NULL AND resolved_at IS NOT NULL
        AND to_timestamp(block_timestamp)<resolved_at AND resolution_status='resolved' ''')
    overview=rows(c,'''SELECT count(*) row_count,count(DISTINCT condition_id) conditions,
      count(DISTINCT lower(taker)) takers,min(block_timestamp) first_event_seconds,max(block_timestamp) last_event_seconds,
      count(*) FILTER(WHERE resolved_at IS NULL) no_resolution_time,
      count(*) FILTER(WHERE winning_outcome_label IS NULL) no_winning_label FROM hindsight''')[0]
    buckets=rows(c,'''SELECT count(*) wallet_condition_buckets,sum(n) first_second_rows,
      count(*) FILTER(WHERE n=1) singleton_buckets,count(*) FILTER(WHERE n>1) excluded_tied_buckets FROM bucket_counts''')[0]
    usable=rows(c,'''SELECT count(*) observations,count(DISTINCT wallet) wallets,count(DISTINCT condition_id) conditions,
        min(block_timestamp) first_event_seconds,max(block_timestamp) last_event_seconds FROM usable''')[0]
    metadata=rows(c,'''SELECT count(*) conditions,
      count(*) FILTER(WHERE winner_versions<>1 OR resolution_versions<>1 OR missing_metadata_rows>0) excluded_conditions FROM meta''')[0]
    splits=[]
    for lag in [0,24,168]:
        c.execute(f'''CREATE OR REPLACE VIEW train AS SELECT * FROM usable
            WHERE block_timestamp>=1704067200 AND block_timestamp<1706745600
            AND resolved_at+INTERVAL '{lag} hours'<TIMESTAMPTZ '2024-02-01T00:00:00Z' ''')
        c.execute('''CREATE OR REPLACE VIEW future AS SELECT * FROM usable WHERE block_timestamp>=1706745600
            AND block_timestamp<1709251200 AND condition_id NOT IN (SELECT condition_id FROM hindsight WHERE block_timestamp>=1704067200 AND block_timestamp<1706745600)''')
        c.execute('''CREATE OR REPLACE VIEW counts AS SELECT wallet,count(DISTINCT condition_id) n FROM train GROUP BY wallet''')
        for minimum in [3,5]:
            val=rows(c,f'''SELECT count(*) observations,count(DISTINCT wallet) wallets,count(DISTINCT condition_id) conditions
                FROM future WHERE wallet IN(SELECT wallet FROM counts WHERE n>={minimum})''')[0]
            val.update({'label_lag_hours':lag,'minimum_training_conditions':minimum,
                'training_observations':c.execute('SELECT count(*) FROM train').fetchone()[0],
                'training_wallets':c.execute(f'SELECT count(*) FROM counts WHERE n>={minimum}').fetchone()[0]})
            splits.append(val)
    qual=REF/'recorded-qualification-v2/recorded-qualification.json'
    old=json.loads(qual.read_text())
    out={'version':'history-fitness-v2','created_at':datetime.now(timezone.utc).isoformat(),
      'result_kind':'source_fitness_and_conditional_proxy_not_copier_returns',
      'archive':overview,'first_bucket':buckets,'metadata':metadata,'conditional_usable_rows':usable,
      'temporal_group_splits':splits,'group_barrier':'Exclude every condition in all January raw rows from February evaluation; stronger than v1 resolved-training-only purge','strict_standard_H30_paths':0,'verified_label_observation_times':0,
      'proxy_target':'binary eventual payout minus leader fill price per share, equal wallet-condition; not money PnL/return',
      'assumption':'Retrospective resolved_at plus embargo only approximates label availability; no recorded known_at.',
      'limitations':['Convenience resolved Standard Binary v1 universe; survivor/metadata selection not removed',
        'First second singleton is one observed source row, not proved economic signal ID',
        'Outcome conditions can share event or underlying risk; condition grouping does not prove independence',
        'Historical source already explored: new config freeze does not create untouched holdout',
        'Proxy omits copied execution, fees, sizing, exits, cash reserves and30day wealth'],
      'checks':{'all_frozen_input_hashes_verified':True,'no_price_tie_chronology':True,
        'invalid_first_row_no_later_fallback':True,'strict_label_availability_not_claimed':True},
      'input_verification':verification,'quote_input_verification':quotes,
      'lineage':{'history_fitness.py':sha(Path(__file__)),str(qual.relative_to(REPO)):sha(qual),
        str(manifest.relative_to(REPO)):sha(manifest)},
      'previous_pmxt_mismatch_counts':old['events']}
    target=HERE/'history_fitness-v2.json'
    if target.exists(): raise FileExistsError('immutable result exists; inspect or use a versioned run')
    target.write_text(json.dumps(out,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['input_verification','quote_input_verification']},indent=2))
if __name__=='__main__':run()
