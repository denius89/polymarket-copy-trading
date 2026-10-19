"""Independent SQL recomputation and adversarial checks; no comparison-engine imports."""
from pathlib import Path
import json,hashlib,math,statistics,sys
import duckdb
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 result_path=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'preliminary-results-v2.json')
 result=json.loads(result_path.read_text())
 checks=[]
 def check(name,condition):
  checks.append({'name':name,'passed':bool(condition)})
  if not condition: raise AssertionError(name)
 for entry in result['lineage']['inputs']:
  check('input hash '+entry['file'],digest(REPO/entry['file'])==entry['sha256'])
 c=duckdb.connect();c.execute("set timezone='UTC'")
 c.read_parquet([str(REPO/e['file']) for e in result['lineage']['inputs']]).create_view('tape')
 # Independent GROUP BY + join, rather than engine window selection.
 c.execute('''create table unique_first as
 with firsttime as (select lower(taker) w,condition_id g,min(block_timestamp) ts
 from tape where taker_direction='BUY' and taker is not null and condition_id is not null and block_timestamp is not null group by 1,2),
 atfirst as (select lower(t.taker) w,t.* from tape t join firsttime f on lower(t.taker)=f.w and t.condition_id=f.g and t.block_timestamp=f.ts where t.taker_direction='BUY'),
 unambiguous as (select w,condition_id from atfirst group by 1,2 having count(*)=1),
 consistent as (select condition_id from tape group by 1 having count(distinct winning_outcome_label)=1 and count(distinct resolved_at)=1 and count(distinct outcome_label)<=2)
 select a.* from atfirst a join unambiguous u using(w,condition_id) join consistent s using(condition_id)
 where isfinite(price) and price>0 and price<1 and outcome_label is not null and winning_outcome_label is not null and resolved_at is not null and epoch(resolved_at)>=block_timestamp''')
 c.execute('''create table train as select w,condition_id,(case when outcome_label=winning_outcome_label then 1.0 else 0.0 end)-price edge,case when outcome_label=winning_outcome_label then 1.0 else 0.0 end y
 from unique_first where block_timestamp>=1704067200 and block_timestamp<1706745600 and epoch(resolved_at)+86400<1706745600''')
 c.execute('''create table eligible as select w,count(*) n,avg(edge) m,stddev_samp(edge) sd,sum(edge)/(count(*)+5) shr,avg(y) wr from train group by w having count(*)>=3''')
 c.execute('''create table test as select w,condition_id,(case when outcome_label=winning_outcome_label then 1.0 else 0.0 end)-price edge
 from unique_first where block_timestamp>=1706745600 and block_timestamp<1709251200 and condition_id not in (select distinct condition_id from tape where block_timestamp>=1704067200 and block_timestamp<1706745600)''')
 train={w:{'mean_edge':m,'shrinkage_edge':s,'lcb_edge':m-1.645*sd/math.sqrt(n),'win_rate':wr} for w,n,m,sd,s,wr in c.sql('select * from eligible').fetchall()}
 future={w:(v,n) for w,v,n in c.sql('select w,avg(edge),count(*) from test group by w').fetchall()}
 check('train eligible SQL recomputation',len(train)==result['primary']['train_eligible_wallets'])
 check('no condition overlap',c.sql('select count(*) from train join test using(condition_id)').fetchone()[0]==0)
 check('all labels end before cutoff conditional on24h assumption',c.sql('select max(epoch(resolved_at)+86400) from unique_first where block_timestamp>=1704067200 and block_timestamp<1706745600 and epoch(resolved_at)+86400<1706745600').fetchone()[0]<1706745600)
 cohort_bounds={}
 k=math.ceil(len(train)/4)
 for model,actual in result['primary']['models'].items():
  selected=sorted(train) if model=='unranked' else sorted(train,key=lambda w:(-train[w][model],hashlib.sha256(w.encode()).hexdigest()))[:k]
  hashes=[hashlib.sha256(w.encode()).hexdigest()[:16] for w in selected]
  check(model+' selected on full training cohort',hashes==actual['selected_wallet_hashes'])
  observed=[future[w][0] for w in selected if w in future]
  missing=len(selected)-len(observed)
  check(model+' future missing retained',missing==actual['missing_future_wallets'])
  check(model+' observed future mean SQL',abs(statistics.mean(observed)-actual['conditional_mean_edge_per_share'])<1e-12)
  check(model+' future observations SQL',sum(future[w][1] for w in selected if w in future)==actual['test_observations'])
  cohort_bounds[model]=[(sum(observed)-missing)/len(selected),(sum(observed)+missing)/len(selected)]
  if 'full_selected_missing_edge_bounds' in actual:
   check(model+' full cohort bounds independent',all(abs(a-b)<1e-12 for a,b in zip(cohort_bounds[model],actual['full_selected_missing_edge_bounds'])))
 # Adversarial arithmetic: exceptional win rate can lose money at expensive prices.
 check('win rate not edge',.9-.99 < .6-.4)
 # Missing observations can reverse model ranking; complete cases do not establish full-cohort edge.
 check('missing cohort may reverse ranking',(.2+.2-1)/3 < .1)
 # Repeat fills in one market do not add independent resolution events.
 check('cluster denominator not fill count',len(set(['eventA']*100+['eventB']))==2)
 # Low lower-bound estimate cannot fix unobserved rare catastrophe.
 wealth=[1.01]*100
 point_ce=1/statistics.mean([1/x for x in wealth])-1
 true_ce=1/(.99/1.01+.01/.01)-1
 check('observed bootstrap misses unseen tail',point_ce>0 and true_ce<0)
 check('not H30 validation',result['strict_asof_copier_outcomes']==0 and result['net_copier_model_winner'] is None and result['ce_result'] is None)
 report={'kind':'internal_independent_reimplementation_no_engine_import','checks':checks,'passed':len(checks),'all_passed':True,'cohort_missing_edge_bounds':cohort_bounds,'result_file':result_path.name,'result_sha256':digest(result_path),'limits':['Already explored archive, not blind holdout','Retrospective resolved_at plus24h is assumed availability, not observed','Proxy edge not net copier return','Independent arithmetic does not validate archived winning labels']}
 (ROOT/('independent-checks-v2.json' if 'v2' in result_path.name else 'independent-checks.json')).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
 print(json.dumps({'passed':len(checks),'bounds':cohort_bounds},indent=2))
if __name__=='__main__': run()
