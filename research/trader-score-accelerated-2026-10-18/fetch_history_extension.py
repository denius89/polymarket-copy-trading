"""Bounded public Q4-2023 robustness extension, not a new blind holdout.

Exact 92 daily files from a pinned dataset, independently checked against
previously saved Hugging Face LFS hashes. No account, key or trade operations.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse

BASE=Path(__file__).resolve().parent
SOURCE=BASE.parent/'trader-score-real-2026-10-16/polymarket/trade_archive-tree.json'
REVISION='5aa1b9d52316a8b2e789e81c8ae42c7ed532e8aa'


class VendorRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parsed=urlparse(newurl);host=parsed.hostname or ''
        if parsed.scheme!='https' or not any(host==x or host.endswith('.'+x) for x in ('huggingface.co','hf.co')):
            raise ValueError('nonvendor or nonHTTPS redirect refused')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    tree=json.loads(SOURCE.read_text())
    dates=[date(2023,10,1)+timedelta(days=i) for i in range(92)]
    names={'daily_aligned/'+d.strftime('%Y_%m_%d')+'.parquet' for d in dates}
    entries=[r for r in tree if r.get('path') in names]
    if len(entries)!=92 or len({r['path'] for r in entries})!=92:
        raise ValueError('exact Q4 scope missing')
    declared=sum(r['size'] for r in entries)
    if declared>8*1048576:raise ValueError('declared byte budget exceeded')
    if any(not re.fullmatch('[0-9a-f]{64}',r.get('lfs',{}).get('oid','')) for r in entries):
        raise ValueError('independent expected LFS SHA required')
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'data').mkdir()
    plan=dict(experiment='predeclared Q4 training robustness only; same February test; previously seen archive never blind holdout',
              created_at=datetime.now(timezone.utc).isoformat(),revision=REVISION,
              source_tree_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              expected_files=92,expected_bytes=declared,max_concurrency=2,
              boundaries=['2023-10-01','2024-01-01'],files=entries)
    (args.output/'fetch-plan.json').write_text(json.dumps(plan,indent=2)+'\n')

    def fetch(row):
        path=row['path'];url=f'https://huggingface.co/datasets/TimeSeventeen/Polymarket-v1/resolve/{REVISION}/{path}'
        opener=urllib.request.build_opener(VendorRedirect())
        request=urllib.request.Request(url,headers={'User-Agent':'CCT-Research-History/1.0'})
        with opener.open(request,timeout=25) as response:
            raw=response.read(row['size']+1)
        digest=hashlib.sha256(raw).hexdigest()
        if len(raw)!=row['size'] or digest!=row['lfs']['oid']:
            raise ValueError('source size/hash mismatch: '+path)
        target=args.output/'data'/Path(path).name
        with target.open('xb') as stream:stream.write(raw)
        return dict(file='data/'+target.name,url=url,revision=REVISION,bytes=len(raw),sha256=digest,
                    retrieved_at=datetime.now(timezone.utc).isoformat())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(fetch,sorted(entries,key=lambda r:r['path'])))
    (args.output/'manifest.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(dict(files=len(results),bytes=sum(x['bytes'] for x in results),all_expected_sha_verified=True)))


if __name__=='__main__':main()
