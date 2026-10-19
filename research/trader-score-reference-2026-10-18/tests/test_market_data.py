import importlib
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from market_data import (D, EvidenceError, Snapshot, parse_book, parse_json,
    displayed_buy_capacity,select_snapshot,sha256_file,verify_manifest_files)

class BookTests(unittest.TestCase):
    def good(self):return parse_book({'bids':[['0.4','10']],'asks':[['0.5','10']]})
    def test_exact_decimal_and_two_level_oracle(self):
        b=parse_book(parse_json('{"bids":[],"asks":[[0.4,5],[0.6,5]]}'))
        c=displayed_buy_capacity(b,D('5'))
        self.assertEqual((c.status,c.gross_spent,c.quantity,c.vwap),('covered',D(5),D(10),D('.5')))
        self.assertEqual(c.evidence_class,'displayed_snapshot_capacity_only')
    def test_decimal_not_binary_tolerance(self):
        b=parse_book({'bids':[],'asks':[['0.1','0.1']]})
        self.assertEqual(displayed_buy_capacity(b,D('.01')).status,'covered')
        self.assertEqual(displayed_buy_capacity(b,D('.010000000000000000000000000001')).status,'insufficient')
    def test_full_amount_and_price_cap(self):
        c=displayed_buy_capacity(parse_book({'bids':[],'asks':[['.4','5'],['.6','5']]}),D(5),D('.5'))
        self.assertEqual((c.status,c.gross_spent,c.quantity),('insufficient',D(2),D(5)))
    def test_missing_not_empty(self):
        for payload in [{'bids':[]},{'asks':[]},{'asks':None,'bids':[]}]:
            c=displayed_buy_capacity(parse_book(payload),D(5))
            self.assertEqual(c.status,'unknown');self.assertIsNone(c.gross_spent)
        c=displayed_buy_capacity(parse_book({'bids':[],'asks':[]}),D(5))
        self.assertEqual((c.status,c.gross_spent),('insufficient',D(0)))
    def test_malformed_fail_closed(self):
        for levels in [[[D('.5')]],[[D('.5'),'unknown']],[[D('.5'),-1]],[[float('nan'),1]],[[D('.5'),float('inf')]],[[True,1]],[[0,5]],[[D('.5'),1],[D('.5'),2]]]:
            with self.subTest(levels=levels):
                b=parse_book({'bids':[],'asks':levels});self.assertEqual(b.status,'invalid')
                self.assertEqual(displayed_buy_capacity(b,D(5)).status,'unknown')
    def test_crossed(self):
        self.assertEqual(parse_book({'bids':[['.6',10]],'asks':[['.5',10]]}).errors,('crossed',))
    def test_nonfinite_json_rejected(self):
        for raw in ['{"asks":NaN}','{"x":Infinity}','[]','invalid']:
            with self.assertRaises(EvidenceError):parse_json(raw)
    def test_invalid_request(self):
        for amount in [D(0),D(-1),D('NaN'),None]:
            self.assertEqual(displayed_buy_capacity(self.good(),amount).status,'unknown')
    def test_exact_tie_no_fallback(self):
        ss=[Snapshot('a',D(8),self.good()),Snapshot('a',D(9),self.good())]
        self.assertEqual(select_snapshot(ss,D(9),D(2)).reason,'exact_arrival_tie')
    def test_invalid_latest_no_fallback(self):
        ss=[Snapshot('a',D(8),self.good()),Snapshot('a',D(9),parse_book({'bids':[]}))]
        self.assertEqual(select_snapshot(ss,D('9.5'),D(2)).reason,'invalid_latest_group')
    def test_mixed_invalid_group_permutation_invariant(self):
        invalid=parse_book({'bids':[['.4',10],['.3',-10]],'asks':[['.5',10]]})
        ss=[Snapshot('a',D(9),self.good()),Snapshot('a',D(9),invalid)]
        for order in itertools.permutations(ss):
            self.assertEqual(select_snapshot(order,D('9.5'),D(1)).reason,'invalid_latest_group')
    def test_conflicting_latest_permutation_invariant(self):
        different=parse_book({'bids':[['.4',10]],'asks':[['.6',10]]})
        ss=[Snapshot('a',D(9),self.good()),Snapshot('a',D(9),different)]
        for order in itertools.permutations(ss):
            self.assertEqual(select_snapshot(order,D('9.5'),D(1)).reason,'conflicting_latest_group')
    def test_equivalent_duplicate_allowed_but_not_counted_as_fills(self):
        ss=[Snapshot('a',D(9),self.good())]*2
        self.assertEqual(select_snapshot(ss,D('9.5'),D(1)).status,'eligible')
    def test_stale_future_and_mixed_token(self):
        ss=[Snapshot('a',D(9),self.good())]
        self.assertEqual(select_snapshot(ss,D(8),D(1)).reason,'no_prior_snapshot')
        self.assertEqual(select_snapshot(ss,D(11),D(1)).reason,'stale_latest_snapshot')
        ss.append(Snapshot('b',D(9),self.good()))
        self.assertEqual(select_snapshot(ss,D(10),D(1)).reason,'mixed_token_scope')
    def test_precision_of_snapshot_times(self):
        ss=[Snapshot('a',D('9.000001'),self.good())]
        self.assertEqual(select_snapshot(ss,D('9.000002'),D(1)).status,'eligible')

class ProvenanceTests(unittest.TestCase):
    def test_integrity_and_file_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'a';p.write_bytes(b'123')
            e={'file':'a','bytes':3,'sha256':sha256_file(p)}
            self.assertEqual(len(verify_manifest_files(root,[e],['a'])),1)
            for entries,expected in [([e,e],['a']),([e],['a','b']),([e],[]),([dict(e,bytes=4)],['a']),([dict(e,sha256='f'*64)],['a'])]:
                with self.assertRaises(EvidenceError):verify_manifest_files(root,entries,expected)
            p.write_bytes(b'124')
            with self.assertRaises(EvidenceError):verify_manifest_files(root,[e],['a'])
    def test_outside_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'outside';p.write_bytes(b'x');base=root/'inside';base.mkdir()
            e={'file':'../outside','bytes':1,'sha256':sha256_file(p)}
            with self.assertRaises(EvidenceError):verify_manifest_files(base,[e],['../outside'])
    def test_safe_import_no_io(self):
        with patch.object(Path,'read_text',side_effect=AssertionError('read on import')),patch.object(Path,'write_text',side_effect=AssertionError('write on import')):
            module=importlib.import_module('analyze_recorded');importlib.reload(module)
    def test_schema_is_checked(self):
        import duckdb
        import analyze_recorded
        c=duckdb.connect();c.execute('CREATE TABLE x(asset_id VARCHAR,price DOUBLE)')
        analyze_recorded.require_schema(c,'x',{'asset_id':'VARCHAR','price':'DOUBLE'})
        for schema in [{'asset_id':'BIGINT'},{'missing':'VARCHAR'}]:
            with self.assertRaises(EvidenceError):analyze_recorded.require_schema(c,'x',schema)
        with self.assertRaises(EvidenceError):analyze_recorded.exact_schema(c,'x',{'asset_id':'VARCHAR'})
    def test_existing_output_rejected_without_writes(self):
        import analyze_recorded
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EvidenceError):analyze_recorded.run(Path(tmp),Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()),[])


class FirstBucketTests(unittest.TestCase):
    def test_ambiguous_bucket_excluded_and_bounds_not_tie_selected(self):
        import duckdb
        import analyze_recorded
        rows=[('w','c','a',100,'BUY',.4,5,'YES','YES'),
              ('w','c','a',100,'BUY',.6,5,'YES','YES'),
              ('w','c','a',101,'BUY',.1,5,'YES','YES'),
              ('single','c','a',100,'BUY',.5,5,'YES','YES')]
        for order in [rows,list(reversed(rows))]:
            c=duckdb.connect()
            c.execute('CREATE TABLE hindsight(taker VARCHAR,condition_id VARCHAR,asset_id VARCHAR,block_timestamp BIGINT,taker_direction VARCHAR,price DOUBLE,usdc_amount DOUBLE,outcome_label VARCHAR,winning_outcome_label VARCHAR)')
            c.executemany('INSERT INTO hindsight VALUES (?,?,?,?,?,?,?,?,?)',order)
            report,bounds=analyze_recorded.hindsight_diagnostic(c)
            self.assertEqual(report['summary']['wallet_condition_groups'],2)
            self.assertEqual(report['summary']['multiple_row_buckets'],1)
            self.assertEqual(report['summary']['ambiguous_economic_buckets'],1)
            self.assertEqual(report['summary']['strict_single_row_buckets'],1)
            self.assertEqual(sum(r['observations'] for r in report['strict_single_row_price_bands']),1)
            ambiguous=next(r for r in bounds if r['selection_status']=='ambiguous_economic_values')
            self.assertEqual((ambiguous['price_lower'],ambiguous['price_upper']),(.4,.6))
            self.assertAlmostEqual(ambiguous['payoff_price_lower'],.4)
            self.assertAlmostEqual(ambiguous['payoff_price_upper'],.6)
            self.assertEqual(ambiguous['bucket_time'],100)

if __name__=='__main__':unittest.main()
