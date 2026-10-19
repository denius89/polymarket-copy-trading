import unittest
import preliminary_compare as m
CUT=1706745600

def row(wallet,condition,edge,when,resolved):
 return dict(wallet=wallet,condition_id=condition,price=.5,y=.5+edge,block_timestamp=when,resolved_ts=resolved)

class ComparisonTests(unittest.TestCase):
 def fixture(self):
  rows=[]
  for wallet,edge in [('a',.4),('b',.3),('c',.2),('d',.1)]:
   rows += [row(wallet,f'train-{wallet}-{i}',edge,CUT-300000,CUT-200000) for i in range(3)]
  rows += [row(w,f'future-{w}',.1,CUT+10000,CUT+20000) for w in ['b','c','d']]
  return rows
 def test_missing_future_does_not_rerank(self):
  x=m.experiment(self.fixture(),set(),reps=30)
  self.assertEqual(x['top_k'],1)
  self.assertEqual(x['models']['mean_edge']['observed_future_wallets'],0)
  self.assertIsNone(x['models']['mean_edge']['conditional_mean_edge_per_share'])
  self.assertEqual(x['models']['mean_edge']['full_selected_missing_edge_bounds'],[-1,1])
 def test_future_label_not_training(self):
  rows=self.fixture()+[row('z',f'z-{i}',.49,CUT-300000,CUT+1) for i in range(3)]
  self.assertEqual(m.experiment(rows,set(),reps=1)['train_eligible_wallets'],4)
 def test_embargo_controls_eligibility(self):
  rows=[row('a',str(i),.2,CUT-300000,CUT-1) for i in range(3)]
  self.assertEqual(m.experiment(rows,set(),lag_h=24,reps=1)['train_eligible_wallets'],0)
  self.assertEqual(m.experiment(rows,set(),lag_h=0,reps=1)['train_eligible_wallets'],1)
 def test_global_condition_purge(self):
  rows=self.fixture()
  x=m.experiment(rows,{'future-b','future-c','future-d'},reps=1)
  self.assertEqual(x['test_conditions'],0)
 def test_bounds_include_missing(self):
  rows=self.fixture()+[row('a','future-a',.2,CUT+1,CUT+2)]
  x=m.experiment(rows,set(),reps=1)['models']['mean_edge']
  self.assertAlmostEqual(x['full_selected_missing_edge_bounds'][0],.2)
  self.assertAlmostEqual(x['full_selected_missing_edge_bounds'][1],.2)
 def test_expenses_not_evaluated(self):
  self.assertNotIn('ce',m.score([row('a',str(i),.2,0,1) for i in range(3)]))

if __name__=='__main__':unittest.main()
