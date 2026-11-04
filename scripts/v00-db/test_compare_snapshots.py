import copy
import unittest

from compare_snapshots import compare


class RestoreComparisonTests(unittest.TestCase):
    def setUp(self):
        self.source = {'profile':'v00-db-snapshot-v1','wal_lsn':'0/100','tables':{
            name:[] for name in ['actors','factors','contexts','challenges','totp_results','used_steps',
                                'email_confirmations','email_outcomes','email_seals_redacted','provider_observations']},
            'integrity':{'used_step_wrong_result':0,'success_step_count_mismatch':0,
                         'outcome_wrong_txid':0,'confirmation_wrong_user':0,'outcome_missing_provider_session':0}}
        self.source['tables']['used_steps'] = [{'factor_version':'synthetic-version','step':153567}]

    def test_metadata_change_is_not_row_loss(self):
        restored = copy.deepcopy(self.source)
        restored['wal_lsn'] = '0/200'
        restored['is_recovery'] = True
        self.assertEqual(compare(self.source,restored)['verdict'],'pass')

    def test_loss_and_extra_consumption_fail(self):
        for rows in [[], self.source['tables']['used_steps'] + [{'factor_version':'synthetic-version','step':153569}]]:
            restored = copy.deepcopy(self.source)
            restored['tables']['used_steps'] = rows
            self.assertEqual(compare(self.source,restored)['verdict'],'fail')

    def test_absent_table_and_corrupt_parent_fail(self):
        restored = copy.deepcopy(self.source)
        del restored['tables']['email_outcomes']
        self.assertEqual(compare(self.source,restored)['verdict'],'fail')
        restored = copy.deepcopy(self.source)
        restored['integrity']['outcome_wrong_txid'] = 1
        self.assertEqual(compare(self.source,restored)['verdict'],'fail')

    def test_empty_table_not_behavioral_pass(self):
        report = compare(self.source,self.source)
        row = next(x for x in report['checks'] if x['criterion']=='email_outcomes')
        self.assertEqual(row['detail']['behavioral_coverage'],'no_data')


if __name__ == '__main__':
    unittest.main()
