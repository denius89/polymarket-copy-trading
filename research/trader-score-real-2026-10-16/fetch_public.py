"""Download a fixed, small public research slice, never accounts/credentials.

Selection fixed before inspecting outcome statistics: all Standard Binary files
for Jan-Feb 2024; OpenMarket demo quote/metadata files for schema QA only.
"""
import concurrent.futures
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'polymarket'
REPOS = [('TimeSeventeen/Polymarket-v1', '5aa1b9d52316a8b2e789e81c8ae42c7ed532e8aa'),
         ('gregyoung14/openmarket-btc-polymarket', '74502466d1a7cef56395bfd8d0b465fbebc849cf')]


def get(url):
    with urllib.request.urlopen(url, timeout=40) as r:
        return r.read()


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for repo, rev in REPOS:
        subdir = 'trade_archive' if repo == REPOS[0][0] else 'quote_sample'
        tree_path = '/daily_aligned' if subdir == 'trade_archive' else ''
        tree_url = f'https://huggingface.co/api/datasets/{repo}/tree/{rev}{tree_path}?limit=1000'
        raw = get(tree_url)
        (ROOT/f'{subdir}-tree.json').write_bytes(raw)
        tree = json.loads(raw)
        chosen = [x for x in tree if x['type'] == 'file' and
                  (x['path'].startswith(('daily_aligned/2024_01_', 'daily_aligned/2024_02_'))
                   if subdir == 'trade_archive' else x['path'] in ['polymarket_ticks_ms.parquet', 'market_meta.parquet'])]
        assert sum(x['size'] for x in chosen) < 20_000_000
        for x in chosen:
            jobs.append((repo, rev, subdir, x['path'], x.get('lfs', {}).get('oid')))
        jobs.append((repo, rev, subdir, 'README.md', None))
    def download(job):
        repo, rev, subdir, path, expected = job
        url = f'https://huggingface.co/datasets/{repo}/resolve/{rev}/{path}'
        dest = ROOT/subdir/Path(path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = get(url)
        sha = hashlib.sha256(raw).hexdigest()
        if expected:
            assert sha == expected, path
        dest.write_bytes(raw)
        return dict(url=url, dataset=repo, revision=rev, file=str(dest.relative_to(ROOT)),
                    bytes=len(raw), sha256=sha, retrieved_at=datetime.now(timezone.utc).isoformat())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        manifest = list(pool.map(download, jobs))
    (ROOT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(files=len(manifest), bytes=sum(x['bytes'] for x in manifest)),indent=2))


if __name__ == '__main__':
    main()
