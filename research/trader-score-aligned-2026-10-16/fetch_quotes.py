import concurrent.futures, hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO='gregyoung14/openmarket-btc-polymarket'
REV='74502466d1a7cef56395bfd8d0b465fbebc849cf'
PATHS=[f'unified/polymarket_ticks_ms/date=2026-03-{d:02}/part-000001.parquet' for d in [1,2,3]]
PATHS.insert(0,'unified/polymarket_ticks_ms/date=2026-02-28/part-000001.parquet')
PATHS+=['unified/market_meta/unpartitioned/part-000001.parquet']
def get(path):
    url=f'https://huggingface.co/datasets/{REPO}/resolve/{REV}/{path}'
    with urllib.request.urlopen(url,timeout=60) as r:raw=r.read(20_000_001)
    assert len(raw)<=20_000_000
    name=path.split('/')[-2]+'.parquet'
    dest=ROOT/'data'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    return dict(url=url,file=str(dest.relative_to(ROOT)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),retrieved_at=datetime.now(timezone.utc).isoformat())
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:manifest=list(p.map(get,PATHS))
    (ROOT/'quotes-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Downloaded quote/meta bytes:',sum(x['bytes'] for x in manifest))
