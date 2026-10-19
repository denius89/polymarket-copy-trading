"""Exploratory leader-price outcome-edge diagnostic. NOT copier return or score validation."""
from pathlib import Path
import datetime as dt
import hashlib,json,math,random,statistics,sys
import duckdb
ROOT=Path(__file__).resolve().parent
DATA=ROOT.parent/'trader-score-real-2026-10-16'/'polymarket'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mean(xs):return sum(xs)/len(xs) if xs else None
def quantile(a,p):
 a=sorted(a);return a[min(len(a)-1,int((len(a)-1)*p))] if a else None

def load(extension=False):
 manifest=json.loads((DATA/'manifest.json').read_text());entries=[]
 files=sorted((DATA/'trade_archive').glob('*.parquet'))
 for p in files:
  e=next(x for x in manifest if x['file']==str(p.relative_to(DATA)))
  assert sha(p)==e['sha256'],p
  entries.append({'file':str(p.relative_to(ROOT.parent.parent)),'sha256':sha(p),'bytes':p.stat().st_size})
 assert len(files)==60
 if extension:
  extra=json.loads((ROOT/'q4-extension/manifest.json').read_text())
  assert len(extra)==92
  for e in extra:
   p=ROOT/'q4-extension'/e['file'];assert sha(p)==e['sha256'];files.append(p)
   entries.append({'file':str(p.relative_to(ROOT.parent.parent)),'sha256':sha(p),'bytes':p.stat().st_size})
 c=duckdb.connect();c.execute("SET TimeZone='UTC'")
 c.read_parquet([str(p) for p in files]).create_view('raw')
 # Earliest timestamp is computed before any price/label/metadata validity filter.
 c.execute('''create table firsts as with base as (
 select *,lower(taker) wallet,min(block_timestamp) over(partition by lower(taker),condition_id) first_ts
 from raw where taker_direction='BUY' and taker is not null and condition_id is not null and block_timestamp is not null),
 earliest as (select *, count(*) over(partition by wallet,condition_id) bucket_rows from base where block_timestamp=first_ts)
 select *,cast(case when outcome_label=winning_outcome_label then 1 else 0 end as double) y
 from earliest''')
 # A market with conflicting winner/asset-outcome mappings cannot be rescued by arbitrary row selection.
 c.execute('''create table valid_conditions as select condition_id from raw group by condition_id
 having count(distinct winning_outcome_label)=1 and count(distinct resolved_at)=1
 and count(distinct outcome_label)<=2''')
 cur=c.execute('''select wallet,condition_id,block_timestamp,price,y,epoch(resolved_at) resolved_ts
 from firsts where bucket_rows=1 and isfinite(price) and price>0 and price<1
 and outcome_label is not null and winning_outcome_label is not null
 and resolved_at is not null and epoch(resolved_at)>=block_timestamp
 and condition_id in (select * from valid_conditions) order by wallet,condition_id''')
 rows=[dict(zip([d[0] for d in cur.description],r)) for r in cur.fetchall()]
 all_jan={r[0] for r in c.execute('select distinct condition_id from raw where block_timestamp>=? and block_timestamp<1706745600',[1696118400 if extension else 1704067200]).fetchall()}
 funnel={'raw_rows':c.execute('select count(*) from raw').fetchone()[0],
 'wallet_condition_groups':c.execute('select count(distinct (wallet,condition_id)) from firsts').fetchone()[0],
 'ambiguous_first_second_groups':c.execute('select count(distinct (wallet,condition_id)) from firsts where bucket_rows>1').fetchone()[0],
 'valid_unique_first_observations':len(rows),'january_condition_universe':len(all_jan)}
 return rows,all_jan,entries,funnel

def score(rows):
 edges=[r['y']-r['price'] for r in rows];m=mean(edges);n=len(edges)
 return {'win_rate':mean([r['y'] for r in rows]),'mean_edge':m,'shrinkage_edge':sum(edges)/(n+5),
 'lcb_edge':m-1.645*statistics.stdev(edges)/math.sqrt(n)}

def experiment(rows,jan_conditions,lag_h=24,min_n=3,priceband=False,overlap=False,reps=2000,train_start=1704067200):
 train={};test={};start,cut,end=train_start,1706745600,1709251200
 for r in rows:
  if priceband and not .1<=r['price']<=.9:continue
  if start<=r['block_timestamp']<cut and r['resolved_ts']+lag_h*3600<cut:train.setdefault(r['wallet'],[]).append(r)
  if cut<=r['block_timestamp']<end and (overlap or r['condition_id'] not in jan_conditions):test.setdefault(r['wallet'],[]).append(r)
 eligible=sorted(w for w,v in train.items() if len(v)>=min_n)
 scores={w:score(train[w]) for w in eligible};k=math.ceil(len(eligible)/4)
 ranking={m:sorted(eligible,key=lambda w:(-scores[w][m],hashlib.sha256(w.encode()).hexdigest()))[:k]
 for m in ['win_rate','mean_edge','shrinkage_edge','lcb_edge']}
 ranking['unranked']=eligible
 # Ranking is frozen on ALL training-eligible wallets, never conditioned on future presence.
 def value(ws,weights=None):
  vals=[]
  for w in ws:
   obs=test.get(w,[])
   if weights is None:
    if obs:vals.append(mean([r['y']-r['price'] for r in obs]))
   else:
    den=sum(weights.get(r['condition_id'],0) for r in obs)
    if den:vals.append(sum((r['y']-r['price'])*weights.get(r['condition_id'],0) for r in obs)/den)
  return mean(vals)
 baseline=value(eligible);result={'label_embargo_hours':lag_h,'minimum_training_conditions':min_n,'price_band_sensitivity':priceband,
 'allows_condition_overlap':overlap,'train_eligible_wallets':len(eligible),'top_k':k,
 'train_conditions':len({r['condition_id'] for w in eligible for r in train[w]}),
 'test_conditions':len({r['condition_id'] for w in eligible for r in test.get(w,[])}),'models':{}}
 conds=sorted({r['condition_id'] for w in eligible for r in test.get(w,[])})
 rng=random.Random(20261018);boot={m:[] for m in ranking};paired=[]
 # Poisson(1) weights on shared conditions. This interval is descriptive, not population inference.
 def poisson():
  n=0;p=1.
  while p>math.exp(-1):n+=1;p*=rng.random()
  return n-1
 for _ in range(reps):
  weights={g:poisson() for g in conds};base=value(eligible,weights)
  for m,ws in ranking.items():
   v=value(ws,weights)
   if v is not None and base is not None:boot[m].append(v-base)
  a,b=value(ranking['shrinkage_edge'],weights),value(ranking['mean_edge'],weights)
  if a is not None and b is not None:paired.append(a-b)
 for m,ws in ranking.items():
  observed=[w for w in ws if test.get(w)];v=value(ws)
  result['models'][m]={'selected_wallets':len(ws),'observed_future_wallets':len(observed),
   'missing_future_wallets':len(ws)-len(observed),'future_coverage':len(observed)/len(ws) if ws else None,
   'test_conditions':len({r['condition_id'] for w in observed for r in test[w]}),
   'test_observations':sum(len(test[w]) for w in observed),
   'conditional_mean_edge_per_share':v,'difference_vs_unranked':v-baseline if v is not None and baseline is not None else None,
   'descriptive_cluster_interval_95':[quantile(boot[m],.025),quantile(boot[m],.975)],
   'full_selected_missing_edge_bounds':[(sum(mean([r['y']-r['price'] for r in test[w]]) for w in observed)-(len(ws)-len(observed)))/len(ws),(sum(mean([r['y']-r['price'] for r in test[w]]) for w in observed)+(len(ws)-len(observed)))/len(ws)] if ws else [None,None],
   'selected_wallet_hashes':[hashlib.sha256(w.encode()).hexdigest()[:16] for w in ws]}
 result['paired_shrinkage_minus_mean']={'point':value(ranking['shrinkage_edge'])-value(ranking['mean_edge']) if value(ranking['shrinkage_edge']) is not None and value(ranking['mean_edge']) is not None else None,'descriptive_cluster_interval_95':[quantile(paired,.025),quantile(paired,.975)],'note':'Same condition weights; fixed selections; differing observed wallet subsets remain'}
 result['random_top_k']={'expected_edge_conditional_on_future_observation':baseline,'sampling_variance':'not estimated; expected value alone does not describe random subset risk'}
 return result

def main():
 output=ROOT/'preliminary-results-v2.json'
 if output.exists():raise SystemExit('Refusing to overwrite previous result')
 config=json.loads((ROOT/'comparison-config.json').read_text())
 rows,jan,entries,funnel=load()
 result={'kind':'exploratory_conditional_eventual_leader_price_edge_diagnostic','strict_asof_copier_outcomes':0,
 'net_copier_model_winner':None,'ce_result':None,'cash_control':'No trade has zero per-share gross payoff; no wealth scale is asserted and not a forecast validation',
 'revision':'v2 adds full-selected missing future outcome bounds; same frozen protocol and ranking',
 'fees':'unknown: edge is before expenses by definition; no net return is computed',
 'availability':'Assumed resolved_at+embargo; publication/observed_at absent, not established asof',
 'lineage':{'protocol_sha256':sha(ROOT/'comparison-config.json'),'code_sha256':sha(Path(__file__)),'duckdb_version':duckdb.__version__,'inputs':entries},
 'funnel':funnel,'primary':experiment(rows,jan),
 'sensitivities':{'minimum_n5':experiment(rows,jan,min_n=5),'price_10_90':experiment(rows,jan,priceband=True),
 'embargo_0h':experiment(rows,jan,lag_h=0),'embargo_168h':experiment(rows,jan,lag_h=168),
 'overlap_allowed_not_independent':experiment(rows,jan,overlap=True)}}
 output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print(json.dumps({'funnel':funnel,'primary':{k:v for k,v in result['primary'].items() if k!='models'},
 'models':{k:{a:b for a,b in v.items() if a!='selected_wallet_hashes'} for k,v in result['primary']['models'].items()}},indent=2))
if __name__=='__main__':main()
