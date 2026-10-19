"""Precision/order sensitivity only; not a validated reconstruction or fill replay."""
from pathlib import Path
import json,collections,duckdb
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
P=ROOT/'research/trader-score-aligned-2026-10-16/source-audit/pmxt-target/target-events.parquet'
c=duckdb.connect();c.execute("SET memory_limit='1GB'");c.execute('SET threads=2');c.read_parquet(str(P)).create_view('e')
c.execute("create view x as select *,json_extract_string(data,'$.token_id') token,try_cast(json_extract_string(data,'$.timestamp') as DOUBLE) jt,greatest(epoch(timestamp_received),epoch(timestamp_created_at)) avail from e")
def q(sql):
 z=c.execute(sql);return [dict(zip([d[0] for d in z.description],r)) for r in z.fetchall()]
r={'status':'unvalidated_ordering_sensitivity_not_primary_result','clock_note':'JSON timestamp closely follows received clock; no claim of exchange sequence or information available to product'}
r['json_vs_received']=q('select count(*) n_rows,min(jt-epoch(timestamp_received)) min_s,max(jt-epoch(timestamp_received)) max_s,median(jt-epoch(timestamp_received)) median_s,count(*) filter(where abs(jt-epoch(timestamp_received))<0.001) within_1ms from x')
r['json_vs_created']=q('select min(jt-epoch(timestamp_created_at)) min_s,max(jt-epoch(timestamp_created_at)) max_s,median(jt-epoch(timestamp_created_at)) median_s from x')
for name,pred,group in [('availability_all','true','token,avail'),('availability_snapshot',"update_type='book_snapshot'",'token,avail'),('both_parquet_clocks_all','true','token,timestamp_received,timestamp_created_at')]:
 r[name]=q(f'''select count(*) n_groups,count(*) filter(where n>1) tied,
 count(*) filter(where n>1 and jt_n>1) finer_timestamp_distinguishes,
 count(*) filter(where n>1 and jt_n=n) all_finer_timestamps_distinct
 from (select {group},count(*) n,count(distinct jt) jt_n from x where {pred} group by {group})''')
def replay(order):
 state={};z=collections.Counter();examples=[];max_best_delta=0.;max_quantity_delta=0.;min_nonzero_quantity_delta=None
 for rec in c.execute(f'select data from x order by {order}').fetchall():
  d=json.loads(rec[0]);token=d['token_id']
  if d['update_type']=='book_snapshot':
   b={side:{float(p):float(n) for p,n in d[side] if float(n)>0} for side in ['bids','asks']}
   if token in state:
    old=state[token];z['comparisons']+=1
    same=old==b;top=lambda y:(max(y['bids'],default=None),min(y['asks'],default=None))
    z['same_depth']+=same;z['same_top']+=top(old)==top(b)
    if not same:
     missing=sum(len(set(old[side]) ^ set(b[side])) for side in ['bids','asks'])
     qdiff=[abs(old[side][p]-b[side][p]) for side in ['bids','asks'] for p in set(old[side]) & set(b[side]) if old[side][p]!=b[side][p]]
     diffs=[abs(a-bb) for a,bb in zip(top(old),top(b)) if a is not None and bb is not None]
     db=max(diffs,default=0.)
     max_best_delta=max(max_best_delta,db);max_quantity_delta=max(max_quantity_delta,max(qdiff,default=0.))
     if qdiff:min_nonzero_quantity_delta=min(min_nonzero_quantity_delta or min(qdiff),min(qdiff))
     z['mismatch_with_missing_or_added_price_levels']+=bool(missing)
     z['mismatch_quantity_only']+=not missing
     z['quantity_only_all_deltas_le_1e_6']+=bool(not missing and qdiff and max(qdiff)<=1e-6)
     z['top_difference_gt_1e_6']+=db>1e-6
     if len(examples)<3:
      changed=[{'side':side,'price':p,'old_size':old[side].get(p),'new_size':b[side].get(p)} for side in ['bids','asks'] for p in sorted(set(old[side]) | set(b[side])) if old[side].get(p)!=b[side].get(p)]
      examples.append({'token':token,'jt':d['timestamp'],'old_top':top(old),'new_top':top(b),'changed_levels':changed})
   state[token]=b
  elif d['update_type']=='price_change' and token in state:
   side={'BUY':'bids','SELL':'asks'}.get(d.get('change_side'));p=float(d['change_price']);n=float(d['change_size'])
   if side:
    if n>0:state[token][side][p]=n
    else:state[token][side].pop(p,None)
 return {'counts':dict(z),'max_best_price_absolute_delta':max_best_delta,'max_quantity_absolute_delta':max_quantity_delta,'min_nonzero_quantity_absolute_delta':min_nonzero_quantity_delta,'tick_size_verified':False,'first_mismatches':examples}
r['replay_json_timestamp_order']=replay('jt')
r['demonstration_event_group']=q("select token,update_type,jt,epoch(timestamp_received) received_s,epoch(timestamp_created_at) created_s from x where avail>1772343006.97 and avail<1772343007 order by token,jt")
(OUT/'pmxt-precision-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
