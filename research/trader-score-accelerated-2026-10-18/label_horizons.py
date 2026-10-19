"""Additional descriptive future label horizon; never moves protocol boundaries."""
import json,statistics
from pathlib import Path
import preliminary_compare as m
R=Path(__file__).resolve().parent
out=R/'label-horizons.json'
if out.exists():raise SystemExit('Refusing overwrite')
results={}
for extended in [False,True]:
 rows,groups,entries,funnel=m.load(extended)
 train={}
 for r in rows:
  if (1696118400 if extended else 1704067200)<=r['block_timestamp']<1706745600 and r['resolved_ts']+86400<1706745600:train.setdefault(r['wallet'],[]).append(r)
 eligible={w for w,rs in train.items() if len(rs)>=3}
 future=[r for r in rows if r['wallet'] in eligible and 1706745600<=r['block_timestamp']<1709251200 and r['condition_id'] not in groups]
 days=[(r['resolved_ts']-r['block_timestamp'])/86400 for r in future]
 results['extension' if extended else 'primary']={'observations':len(days),'min_days':min(days) if days else None,'median_days':statistics.median(days) if days else None,'max_days':max(days) if days else None,'fraction_resolved_within30d':sum(x<=30 for x in days)/len(days) if days else None,'resolved_after_March1':sum(r['resolved_ts']>=1709251200 for r in future),'latest_resolution_utc':__import__('datetime').datetime.fromtimestamp(max(r['resolved_ts'] for r in future),__import__('datetime').timezone.utc).isoformat() if future else None}
out.write_text(json.dumps({'kind':'future eventual-label horizon diagnostic','code_sha256':m.sha(Path(__file__)),'loader_sha256':m.sha(R/'preliminary_compare.py'),'results':results},indent=2)+'\n')
print(json.dumps(results,indent=2))
