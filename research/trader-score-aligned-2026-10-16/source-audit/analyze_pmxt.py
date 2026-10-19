"""Audit one bounded PMXT row group. Snapshot-only $5 capacity, no fill claim."""
import json,hashlib,bisect,statistics,sys
from pathlib import Path
from collections import Counter,defaultdict
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parent
P=ROOT/('pmxt-hf' if '--hf' in sys.argv else '.')
f=P/'pmxt-bounded-rowgroup.parquet';tab=pq.read_table(f);rows=tab.to_pylist();ids=set(); snaps=defaultdict(list);counts=Counter();levels=[];lags=[];crossed=0;bad=0;stale_clock=0;capacity=[]
for row in rows:
 x=json.loads(row['data']);typ=row['update_type'];counts[typ]+=1;token=x.get('token_id');ids.add(token)
 ts=row['timestamp_received'].timestamp();lags.append((row['timestamp_created_at']-row['timestamp_received']).total_seconds())
 if typ=='book_snapshot':
  asks=sorted((float(a),float(b)) for a,b in x.get('asks',[]) if float(a)>0 and float(b)>0)
  bids=sorted(((float(a),float(b)) for a,b in x.get('bids',[]) if float(a)>0 and float(b)>0),reverse=True)
  if asks and bids and bids[0][0]>asks[0][0]:crossed+=1
  levels.append((len(bids),len(asks)));available=sum(a*b for a,b in asks);left=5.;qty=0.
  for price,size in asks:
   use=min(left,price*size);qty+=use/price;left-=use
   if left<=1e-9:break
  rec={'ts':ts,'best_ask':asks[0][0] if asks else None,'ask_notional':available,'fits_5_usd':left<=1e-9,'vwap_5_usd':5/qty if qty and left<=1e-9 else None,'asks_levels':len(asks)}
  snaps[token].append(rec);capacity.append(rec)
for vv in snaps.values():vv.sort(key=lambda r:r['ts'])
trades=[]
for p in sorted((ROOT.parent/'data').glob('trades-*.parquet')):trades.extend(pq.read_table(p,columns=['asset_id','block_timestamp','taker_direction','price']).to_pylist())
matched=[t for t in trades if t['asset_id'] in ids];near=[];primary=Counter()
for t in matched:
 if t['taker_direction']!='BUY':continue
 ss=snaps.get(t['asset_id'],[]);times=[x['ts'] for x in ss]
 for delay in [.5,2,5]:
  for shift in [-1,0,1]:
   target=t['block_timestamp']+delay+shift;j=bisect.bisect_right(times,target)-1
   if j<0:continue
   snap=ss[j];age=target-snap['ts']
   if age<=1:
    key=f'delay={delay},shift={shift}'
    primary[key+':matched']+=1;primary[key+':capacity_pass']+=int(snap['fits_5_usd'])
 j=bisect.bisect_right(times,t['block_timestamp'])-1
 if j<0:continue
 snap=ss[j];age=t['block_timestamp']-snap['ts']
 if age<=180:near.append({'asset_id':t['asset_id'],'trade_ts':t['block_timestamp'],'snapshot_age_seconds':age,**snap})
summary={'source_url':json.loads((P/'pmxt-bounded-summary.json').read_text())['url'],'source_rowgroup':json.loads((P/'pmxt-bounded-summary.json').read_text())['rowgroup'],'raw_rows':len(rows),'events':dict(counts),'tokens':len(ids),'snapshot_tokens':len(snaps),'received_min':min(r['timestamp_received'] for r in rows).isoformat(),'received_max':max(r['timestamp_received'] for r in rows).isoformat(),'created_minus_received_seconds':{'min':min(lags),'median':statistics.median(lags),'max':max(lags),'negative':sum(x<0 for x in lags)},'snapshot_levels':{'median_bids':statistics.median(x[0] for x in levels),'median_asks':statistics.median(x[1] for x in levels)},'crossed_snapshots':crossed,'snapshots_fit_5_usd':sum(x['fits_5_usd'] for x in capacity),'snapshot_count':len(capacity),'trade_subset_rows':len(trades),'trade_subset_matching_asset_rows':len(matched),'buys_with_preceding_snapshot_age_lte180s':len(near),'primary_age1s_delay_and_clock_sensitivity':dict(primary),'conditional_snapshot_capacity_pass':sum(x['fits_5_usd'] for x in near),'local_parquet_bytes':f.stat().st_size,'local_parquet_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'limitations':['One row group chosen for minimum byte size, not a random sample or complete time window.','Snapshot price/capacity does not prove execution; unobserved updates/latency and one rowgroup omit other groups.','180 seconds is diagnostic join only, not an execution staleness rule.','No inter-snapshot reconstruction admitted: sample contains gaps and excludes other rowgroups.','timestamp_created_at source meaning requires collector verification; do not assume exchange time.']}
(P/'pmxt-capacity-audit.json').write_text(json.dumps(summary,indent=2)+'\n');(P/'pmxt-token-ids.json').write_text(json.dumps(sorted(x for x in ids if x),indent=2)+'\n');(P/'pmxt-conditional-trade-snapshot-joins.json').write_text(json.dumps(near[:100],indent=2)+'\n');print(json.dumps(summary,indent=2))
