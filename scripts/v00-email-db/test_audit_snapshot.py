import copy
import datetime
import unittest

from audit_snapshot import audit


def t(seconds):
    return (datetime.datetime(2026, 11, 4, tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=seconds)).isoformat()


def fixture(wrong=True):
    accepted = {'kind':'email_dispatch_accepted','acceptedAt':t(3),'challengeId':'challenge','resendNotBeforeAt':t(63)}
    rejected = {'kind':'verification_rejected','reasonCode':'AUTH_VERIFICATION_FAILED'}
    value = {'schema':'v00-email-entry-snapshot-v1',
        'context':{'id':'ctx','created_at':t(0),'expires_at':t(1800),'stage':'email_verification',
                   'actor_id':None,'failures':int(wrong),'paused_until':None},
        'material':{'cipher_present':True,'reveal_until':t(1800)},'directory_enabled':True,
        'gate':{'epoch':1,'open':True,'clock_trusted':True},
        'admissions':[{'id':'a1','context_id':'ctx','operation_id':'send','action':'C01','captured_at':t(0),'deadline_at':t(10)}],
        'results':[{'context_id':'ctx','operation_id':'send','action':'C01','valid':True,'historical_http_status':202,'result':accepted,'resolved_at':t(4),'login_id':None}],
        'challenges':[{'id':'challenge','context_id':'ctx','send_admission_id':'a1','dispatch_id':'dispatch','generation_id':'generation',
                       'issued_at':t(2),'expires_at':t(602),'replaced_by_id':None,'consumed_by_operation_id':None}],
        'sends':[{'id':'dispatch','admission_id':'a1','provider_user_id':'provider','before_generation_id':None,'sealed_at':t(1)}],
        'send_observations':[{'dispatch_id':'dispatch','generation_id':'generation','observed_at':t(3),'accepted_at':t(3)}],
        'verifies':[],'consumptions':[],'verify_observations':[],'negative_proofs':[],'plans':[],'steps':[],
        'audit':[{'operation_id':'send','kind':'email_dispatch_accepted','recorded_at':t(4)}],
        'address_sends':[{'dispatch_id':'dispatch'}], 'dependency':None,
        'generations':[{'id':'generation','user_id':'provider','family':'recovery','issued_at':t(2),'state':'issued'}]}
    if wrong:
        value['admissions'].append({'id':'a2','context_id':'ctx','operation_id':'wrong','action':'C02','challenge_id':'challenge','captured_at':t(5),'deadline_at':t(15)})
        value['results'].append({'context_id':'ctx','operation_id':'wrong','action':'C02','valid':True,'historical_http_status':401,'result':rejected,'resolved_at':t(6),'login_id':None})
        value['negative_proofs'].append({'admission_id':'a2','context_id':'ctx','operation_id':'wrong','challenge_id':'challenge','generation_id':'generation','kind':'live_mismatch','checked_at':t(6)})
        value['audit'].append({'operation_id':'wrong','kind':'verification_rejected','recorded_at':t(6)})
    return value


class IndependentEmailAudit(unittest.TestCase):
    def test_send_and_proven_wrong(self):
        report = audit(fixture())
        self.assertEqual(report['verdict'], 'pass')
        self.assertEqual(report['coverage']['negative_proofs'], 1)
        self.assertEqual(report['coverage']['verify_dispatches'], 0)

    def test_producer_flag_does_not_hide_bad_sources(self):
        mutations = [lambda s:s['send_observations'][0].update(generation_id='other'),
                     lambda s:s['negative_proofs'][0].update(operation_id='send'),
                     lambda s:s['negative_proofs'][0].update(generation_id='other'),
                     lambda s:s['challenges'][0].update(expires_at=t(603)),
                     lambda s:s['admissions'][1].update(deadline_at=t(16)),
                     lambda s:s['context'].update(actor_id='premature'),
                     lambda s:s['audit'].pop()]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                value=fixture(); mutate(value)
                self.assertEqual(audit(value)['verdict'],'fail')

    def test_counter_cannot_change_without_original_proof(self):
        value=fixture(); value['context']['failures']=2
        self.assertEqual(audit(value)['verdict'],'fail')
        value=fixture(False); value['context']['failures']=1
        self.assertEqual(audit(value)['verdict'],'fail')

    def test_expired_code_has_no_counter(self):
        value=fixture()
        value['context']['failures']=0
        value['admissions'][1].update(captured_at=t(603),deadline_at=t(613))
        value['results'][1]['resolved_at']=t(604)
        value['audit'][1]['recorded_at']=t(604)
        value['negative_proofs'][0].update(kind='expired_current',checked_at=t(604))
        self.assertEqual(audit(value)['verdict'],'pass')
        value['context']['failures']=1
        self.assertEqual(audit(value)['verdict'],'fail')

    def test_negative_with_network_seal_rejected(self):
        value=fixture(); value['verifies'].append({'id':'verify','admission_id':'a2','challenge_id':'challenge','generation_id':'generation'})
        self.assertEqual(audit(value)['verdict'],'fail')

    def test_unknown_send_is_not_accepted(self):
        value=fixture(False)
        for key in ('results','challenges','send_observations','audit'):
            value[key]=[]
        value['context']['stage']='ready'
        report=audit(value)
        self.assertEqual(report['verdict'],'pass')
        self.assertEqual(report['coverage']['unresolved'],1)
        self.assertEqual(report['coverage']['results'],{})
        value['results']=copy.deepcopy(fixture(False)['results'])
        self.assertEqual(audit(value)['verdict'],'fail')

    def test_duplicate_proof_and_malformed_input_fail_closed(self):
        value=fixture(); value['negative_proofs'].append(copy.deepcopy(value['negative_proofs'][0]))
        self.assertEqual(audit(value)['verdict'],'fail')
        for value in (None,{}, {'secret':'DO-NOT-ECHO'}):
            report=audit(value)
            self.assertEqual(report['verdict'],'fail')
            self.assertNotIn('DO-NOT-ECHO',str(report))

    def test_complete_chain_requires_dependency_material_and_matching_witness(self):
        value=fixture(False)
        value['context'].update(stage='completed',actor_id='actor')
        value['generations'][0]['state']='consumed'
        value['challenges'][0]['consumed_by_operation_id']='verify'
        value['admissions'].append({'id':'a2','context_id':'ctx','operation_id':'verify','action':'C02','challenge_id':'challenge','captured_at':t(5),'deadline_at':t(15)})
        result={'kind':'login_completed','completion':{'authContextId':'ctx','authOperationId':'verify','loginId':'login','realm':'user','completedAt':t(8)}}
        value['results'].append({'context_id':'ctx','operation_id':'verify','action':'C02','valid':True,'historical_http_status':200,'result':result,'resolved_at':t(9),'login_id':'login'})
        value['verifies']=[{'id':'verify-dispatch','admission_id':'a2','challenge_id':'challenge','generation_id':'generation','provider_user_id':'provider'}]
        value['consumptions']=[{'dispatch_id':'verify-dispatch','provider_user_id':'provider','provider_txid':2}]
        value['verify_observations']=[{'dispatch_id':'verify-dispatch','provider_txid':2}]
        value['plans']=[{'operation_id':'verify','admission_id':'a2'}]
        value['audit'].append({'operation_id':'verify','kind':'completion','recorded_at':t(9)})
        login={'id':'login','context_id':'ctx','operation_id':'verify','completed_at':t(8),'expires_at':t(8+30*86400),'idle_expires_at':t(8+7*86400),
               'credential_present':True,'secret_row_present':True,'secret_present':True,'closed_at':None,'close_reason':None,'erased_at':None}
        value['dependency']={'actor_id':'actor','results':[{'context_id':'ctx','operation_id':'verify','result':copy.deepcopy(result),'login_id':'login','resolved_at':t(9)}],
                             'logins':[login],'contexts':[{'id':'ctx','completed_login_id':'login','completed_operation_id':'verify'}]}
        self.assertEqual(audit(value)['verdict'],'pass')
        for mutate in [lambda s:s['dependency']['logins'][0].update(secret_row_present=False),
                       lambda s:s['dependency']['contexts'][0].update(completed_operation_id='other'),
                       lambda s:s['verify_observations'][0].update(provider_txid=3),
                       lambda s:s['dependency']['logins'][0].update(expires_at=t(9+30*86400))]:
            damaged=copy.deepcopy(value); mutate(damaged)
            self.assertEqual(audit(damaged)['verdict'],'fail')


if __name__=='__main__':
    unittest.main()
