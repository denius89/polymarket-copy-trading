import copy
import unittest

from audit_snapshot import audit

T='2026-11-04T12:00:00.000Z'
DEADLINE='2026-11-04T12:00:10.000Z'
EXPIRY='2026-11-04T12:05:00.000Z'


def complete_fixture():
    # Independent sanitized projection: actual provider bytes are neither needed nor represented.
    completion={'kind':'login_completed','completion':{'authContextId':'ctx','authOperationId':'totp','loginId':'login','realm':'user','completedAt':T}}
    stage={'kind':'auth_step_required','stage':'totp_verification','challengeId':'challenge','challengeIssuedAt':T,'challengeExpiresAt':EXPIRY}
    results=[{'context_id':'ctx','operation_id':'email','action':'C02','login_id':None,'result':stage,'resolved_at':T,'valid':True},
             {'context_id':'ctx','operation_id':'totp','action':'AUTH_TOTP_VERIFY','login_id':'login','result':completion,'resolved_at':T,'valid':True}]
    return {'schema':'v00-upstream-snapshot-v1','actor_id':'actor','current_factor':'factor','failures':0,'paused_until':None,
        'gate':{'epoch':1,'open':True,'clock_trusted':True},
        'contexts':[{'id':'ctx','stage':'completed','factor_version':'factor','email_challenge_id':'email-challenge',
                     'totp_challenge_id':'challenge','totp_issued_at':T,'totp_expires_at':EXPIRY}],
        'admissions':[{'id':op+'-admission','context_id':'ctx','operation_id':op,'action':action,
                       'executor_id':'executor-'+op,'epoch':1,'captured_at':T,'deadline_at':DEADLINE}
                      for op,action in [('email','C02'),('totp','AUTH_TOTP_VERIFY')]],
        'results':results,
        'steps':[{'factor_version':'factor','step':step,'context_id':'ctx','operation_id':'totp'} for step in [153567,153569]],
        'plans':[{'context_id':'ctx','operation_id':'totp','admission_id':'totp-admission','action':'AUTH_TOTP_VERIFY','transaction_id':123}],
        'generations':[{'id':'generation','family':'recovery','state':'consumed','issued_at':T,'issuing_txid':90}],
        'email_outcomes':[{'seal_id':'seal','admission_id':'email-admission','generation_id':'generation','family':'recovery',
                           'sealed_at':T,'consumption_txid':100,'outcome_txid':100,'provider_session_id':'provider-session','observed_at':T}],
        'audit':[{'ordinal':i,'context_id':'ctx','operation_id':op,'kind':kind,'recorded_at':T}
                 for i,op,kind in [(1,'email','email_stage'),(2,'totp','completion')]],
        'dependency':{'actor_id':'actor','contexts':[{'id':'ctx','completed_login_id':'login','completed_operation_id':'totp'}],
            'results':[{'context_id':'ctx','operation_id':'totp','login_id':'login','resolved_at':T,'valid':True,'result':copy.deepcopy(completion)}],
            'logins':[{'id':'login','context_id':'ctx','operation_id':'totp','completed_at':T,'credential_present':True,
                       'secret_row_present':True,'secret_present':True,'closed_at':None,'close_reason':None,'erased_at':None}],
            'plans':1}}


class IndependentProjection(unittest.TestCase):
    def test_complete_chain(self):
        result=audit(complete_fixture())
        self.assertEqual(result['verdict'],'pass')
        self.assertEqual(result['counts']['full_logins'],1)

    def test_producer_valid_flag_cannot_hide_broken_links(self):
        mutations=[lambda s:s['dependency']['logins'][0].update(operation_id='other'),
                   lambda s:s['plans'][0].update(admission_id='email-admission'),
                   lambda s:s['steps'][0].update(operation_id='email'),
                   lambda s:s['email_outcomes'][0].update(outcome_txid=999),
                   lambda s:s['generations'][0].update(state='replaced'),
                   lambda s:s['dependency']['logins'][0].update(credential_present=False),
                   lambda s:s['admissions'][1].update(deadline_at=EXPIRY)]
        for mutate in mutations:
            sample=complete_fixture(); mutate(sample)
            self.assertEqual(audit(sample)['verdict'],'fail')

    def test_legal_cipher_erasure_retains_login(self):
        sample=complete_fixture()
        sample['dependency']['logins'][0].update(secret_present=False,erased_at=T,closed_at=T,close_reason='first_confirmation')
        self.assertEqual(audit(sample)['verdict'],'pass')
        sample['dependency']['logins'][0]['secret_row_present']=False
        self.assertEqual(audit(sample)['verdict'],'fail')

    def test_missing_email_stage_and_duplicate_steps(self):
        sample=complete_fixture(); sample['results'].pop(0)
        self.assertEqual(audit(sample)['verdict'],'fail')
        sample=complete_fixture(); sample['steps'].append(copy.deepcopy(sample['steps'][0]))
        self.assertEqual(audit(sample)['verdict'],'fail')

    def test_extra_sensitive_top_level_and_malformed_projection(self):
        sample=complete_fixture(); sample['ciphertext']='must-not-be-here'
        self.assertEqual(audit(sample)['verdict'],'fail')
        self.assertEqual(audit(None)['verdict'],'fail')

    def test_no_data_is_explicit(self):
        sample=complete_fixture()
        for key in ['contexts','admissions','results','steps','plans','generations','email_outcomes','audit']:
            sample[key]=[]
        sample['dependency'].update(contexts=[],results=[],logins=[],plans=0)
        report=audit(sample)
        self.assertEqual(report['verdict'],'pass')
        self.assertEqual(report['counts']['full_logins'],0)
        self.assertIn('zero rows are no-data, not behavioral coverage',report['limits'])

    def test_millisecond_projection_is_truncation_not_tolerance(self):
        sample=complete_fixture(); sample['results'][1]['resolved_at']='2026-11-04T12:00:00.000999Z'
        self.assertEqual(audit(sample)['verdict'],'pass')
        sample['results'][1]['resolved_at']='2026-11-04T12:00:00.001000Z'
        self.assertEqual(audit(sample)['verdict'],'fail')

    def test_logout_exact_target_and_audit(self):
        sample=complete_fixture(); dep=sample['dependency']
        dep['logins'][0]['revoked_at']=T
        dep['logout_contexts']=[{'id':'logout-ctx','target_login_id':'login'}]
        dep['logout_results']=[{'context_id':'logout-ctx','operation_id':'logout-op','target_login_id':'login','confirmed_at':T,'valid':True}]
        dep['audit']=[{'kind':'logout_confirmed','operation_id':'logout-op','login_id':'login','recorded_at':T}]
        self.assertEqual(audit(sample)['verdict'],'pass')
        dep['audit'][0]['login_id']='other-login'
        self.assertEqual(audit(sample)['verdict'],'fail')


if __name__=='__main__':
    unittest.main()
