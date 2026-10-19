"""Pinned Q4 extended-training robustness. Not independent holdout."""
import json
from pathlib import Path
import preliminary_compare as m
R=Path(__file__).resolve().parent

def main():
 out=R/'extension-results.json';paired=R/'primary-paired-results.json'
 if out.exists() or paired.exists():raise SystemExit('Refusing overwrite')
 rows,groups,entries,funnel=m.load(True)
 result={'kind':'longer-training-retrospective-robustness','strict_asof_copier_outcomes':0,'financial_winner':None,'funnel':funnel,
 'lineage':{'config_sha256':m.sha(R/'extension-config.json'),'code_sha256':m.sha(R/'preliminary_compare.py'),'runner_sha256':m.sha(Path(__file__)),'inputs':entries},
 'primary':m.experiment(rows,groups,train_start=1696118400),
 'sensitivities':{'minimum_n5':m.experiment(rows,groups,train_start=1696118400,min_n=5),'embargo_168h':m.experiment(rows,groups,train_start=1696118400,lag_h=168)}}
 out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 rows2,g2,e2,f2=m.load(False);primary=m.experiment(rows2,g2)
 paired.write_text(json.dumps({'kind':'Additional paired descriptive interval for unchanged primary experiment','config_sha256':m.sha(R/'comparison-config.json'),'code_sha256':m.sha(R/'preliminary_compare.py'),'primary':primary},indent=2,allow_nan=False)+'\n')
 for name,x in [('extension',result['primary']),('primary_paired',primary)]:
  print(name, x['train_eligible_wallets'],x['top_k'],x['test_conditions'],x['paired_shrinkage_minus_mean'])
  for model,v in x['models'].items():print(model,v['observed_future_wallets'],v['conditional_mean_edge_per_share'],v['full_selected_missing_edge_bounds'])
if __name__=='__main__':main()
