"""Adversarial fixtures for causal quote joins, not a synthetic score backtest."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import duckdb
import analyze_alignment as analysis

def main():
    original_root=analysis.ROOT
    with tempfile.TemporaryDirectory(prefix='score-alignment-test-') as tmp:
        root=Path(tmp);(root/'data').mkdir();c=duckdb.connect();base=analysis.START+10000
        c.execute('''CREATE TABLE trades(asset_id VARCHAR,block_timestamp BIGINT,price DOUBLE,
          taker_direction VARCHAR,maker VARCHAR,taker VARCHAR,usdc_amount DOUBLE,
          fee_usdc DOUBLE,condition_id VARCHAR,winning_outcome_label VARCHAR)''')
        cases=[('good','BUY'),('good','SELL'),('future','BUY'),('stale','BUY'),
               ('invalid_latest','BUY'),('conflict','BUY'),('tie','BUY'),('null','BUY'),('absent','BUY')]
        c.executemany('INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?)',[
          (asset,base//1000,.5,side,'maker','taker',5,None,asset,'FUTURE_LABEL_MUST_NOT_BE_USED')
          for asset,side in cases])
        manifest=[]
        def entry(p, **kwargs):
            return dict(file=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),**kwargs)
        for day in [1,2,3,4]:
            p=root/'data'/f'trades-2026-03-{day:02}.parquet'
            c.execute(f"COPY (SELECT * FROM trades WHERE {'true' if day==1 else 'false'}) TO '{p}' (FORMAT PARQUET)")
            manifest.append(entry(p,rows=len(cases) if day==1 else 0,predicate={'asset_ids':list({a for a,s in cases})}))
        c.execute('''CREATE TABLE quotes(asset_id VARCHAR,source_ts_ms BIGINT,ingest_ts_ms BIGINT,
            best_bid DOUBLE,best_ask DOUBLE,event_type VARCHAR)''')
        quotes=[('good',base+400,.4,.6),('good',base+1900,.4,.6),('good',base+4900,.4,.6),
          ('future',base+501,.4,.6),('stale',base-2000,.4,.6),
          ('invalid_latest',base,.4,.6),('invalid_latest',base+400,.7,.6),
          ('conflict',base+400,.4,.6),('conflict',base+400,.3,.7),
          ('tie',base+500,.4,.6),('null',base+400,None,.6)]
        c.executemany('INSERT INTO quotes VALUES (?,?,?,?,?,?)',[
          (asset,ts,ts+10,bid,ask,'price_change') for asset,ts,bid,ask in quotes])
        p=root/'data/date=2026-03-01.parquet'
        c.execute(f"COPY quotes TO '{p}' (FORMAT PARQUET)")
        (root/'quotes-manifest.json').write_text(json.dumps([entry(p)]))
        (root/'trades-manifest.json').write_text(json.dumps(manifest))
        try:
            analysis.ROOT=root
            with contextlib.redirect_stdout(io.StringIO()): analysis.main()
            result=json.loads((root/'alignment-results.json').read_text())
            first=result['funnels'][0]
            assert first['all_subset_rows']==9
            assert first['asof_present']==7, 'A future quote must not be used'
            assert first['fresh']==6, 'Stale quotes must remain unknown'
            assert first['fresh_valid']==4, 'Invalid latest quote must not fall back to an older valid quote'
            assert first['conflicting_bbo']==1 and first['exact_timestamp_ties']==1
            assert first['eligible']==2
            assert result['common_complete_case_rows']==2
            assert result['quotes']['missing_bbo_rows']==1
            assert result['quotes']['invalid_bbo_rows']==2, 'NULL must count as invalid'
            for group in result['comparisons'][1]['groups']:
                assert group['rows']==1 and abs(group['adverse_cents_median']-10)<1e-10
            assert all(x['unknown_or_invalid_fee_rows']>0 for x in result['partial_trade_legs'])
            assert result['model_verdict']=='comparison_blocked_by_horizon_and_data'
            # A mutated input must fail verification rather than enter analysis.
            with p.open('ab') as f: f.write(b'changed')
            try: analysis.main()
            except AssertionError: pass
            else: raise AssertionError('Input integrity mismatch was not rejected')
        finally: analysis.ROOT=original_root
    print('PASS: future/stale/invalid/conflicting/tied/NULL quotes; both sides; common cohort; missing fees; data integrity; score gate.')

if __name__=='__main__': main()
