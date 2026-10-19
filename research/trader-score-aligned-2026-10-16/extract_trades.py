"""Range-read fixed calendar archive, persist only tokens in quote collection.
No final outcomes used to select assets. Public remote parquet; no credentials.
"""
import hashlib,json,time
from datetime import datetime,timezone
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parent
REV='5aa1b9d52316a8b2e789e81c8ae42c7ed532e8aa'
START=1772323200;END=1772582400
def main():
    c=duckdb.connect();c.execute('LOAD httpfs');c.execute("SET TimeZone='UTC'")
    c.execute("SET memory_limit='1GB'");c.execute('SET threads=4')
    c.read_parquet(str(ROOT/'data'/'date=*.parquet')).create_view('q')
    assets=[x[0] for x in c.execute('select distinct asset_id from q where source_ts_ms>=? and source_ts_ms<?',[START*1000,END*1000]).fetchall()]
    assert assets and all(x.isdigit() for x in assets)
    literal=','.join("'"+x+"'" for x in assets)
    manifest=[]
    for day in [1,2,3,4]:
        url=f'https://huggingface.co/datasets/TimeSeventeen/Polymarket-v1/resolve/{REV}/daily_aligned/2026_03_{day:02}.parquet'
        dest=ROOT/'data'/f'trades-2026-03-{day:02}.parquet'
        sql=f'''SELECT * FROM read_parquet('{url}') WHERE asset_id IN ({literal})
                  AND block_timestamp>={START} AND block_timestamp<{END}'''
        t=time.time()
        c.execute(f"COPY ({sql}) TO '{dest}' (FORMAT PARQUET)")
        n=c.execute('select count(*) from read_parquet(?)',[str(dest)]).fetchone()[0]
        manifest.append(dict(url=url,revision=REV,file=str(dest.relative_to(ROOT)),rows=n,
             bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
             retrieved_at=datetime.now(timezone.utc).isoformat(),seconds=time.time()-t,
             predicate=dict(asset_ids=assets,start_inclusive=START,end_exclusive=END),
             note='Derived subset via remote column/row-group reads; hash is subset, not full source file.'))
        (ROOT/'trades-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(day,n,'rows',round(time.time()-t,1),'seconds',flush=True)
if __name__=='__main__':main()
