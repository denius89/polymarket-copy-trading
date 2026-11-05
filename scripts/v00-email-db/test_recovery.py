"""Offline independent-oracle/mutation tests; these do not execute PostgreSQL."""
import copy
import unittest

from audit_recovery import audit, delta, Invalid
from recovery_reference import decide, bracket, micros
from test_audit_snapshot import fixture as email_fixture, t


def completed_email():
    s=email_fixture(False)
    s['context'].update(stage='completed',actor_id='actor')
    s['generations'][0]['state']='consumed'
    s['challenges'][0]['consumed_by_operation_id']='verify'
    s['admissions'].append({'id':'a2','context_id':'ctx','operation_id':'verify','action':'C02','challenge_id':'challenge','captured_at':t(5),'deadline_at':t(15)})
    result={'kind':'login_completed','completion':{'authContextId':'ctx','authOperationId':'verify','loginId':'login','realm':'user','completedAt':t(8)}}
    s['results'].append({'context_id':'ctx','operation_id':'verify','action':'C02','valid':True,'historical_http_status':200,'result':result,'resolved_at':t(9),'login_id':'login'})
    s['verifies']=[{'id':'verify-dispatch','admission_id':'a2','challenge_id':'challenge','generation_id':'generation','provider_user_id':'provider'}]
    s['consumptions']=[{'dispatch_id':'verify-dispatch','provider_user_id':'provider','provider_txid':2}]
    s['verify_observations']=[{'dispatch_id':'verify-dispatch','provider_txid':2}]
    s['plans']=[{'operation_id':'verify','admission_id':'a2'}]
    s['audit'].append({'operation_id':'verify','kind':'completion','recorded_at':t(9)})
    login={'id':'login','context_id':'ctx','operation_id':'verify','completed_at':t(8),'expires_at':t(8+30*86400),'idle_expires_at':t(8+7*86400),
           'credential_present':True,'secret_row_present':True,'secret_present':True,'closed_at':None,'close_reason':None,'erased_at':None}
    s['dependency']={'actor_id':'actor','results':[{'context_id':'ctx','operation_id':'verify','result':copy.deepcopy(result),'login_id':'login','resolved_at':t(9)}],
                     'logins':[login],'contexts':[{'id':'ctx','completed_login_id':'login','completed_operation_id':'verify'}]}
    return s


def fixture(times=(20,), attempts=True, uses=True):
    s={'schema':'v00-email-recovery-snapshot-v1','context_id':'ctx','email':completed_email(),
       'scope':{'context_id':'ctx','environment':'v00-d03-07','purpose':'user/login/cookie_recovery','limit_count':3,'window_seconds':60,'created_at':t(0)},
       'admissions':[],'attempts':[],'uses':[],'replay_guards':[]}
    for i,at in enumerate(times):
        token='token'+str(i)
        s['admissions'].append({'admission_token':token,'context_id':'ctx','operation_id':'verify','action':'C02','executor_id':'executor'+str(i),
             'admitted_epoch':1,'request_started_at':t(at-1),'admitted_at':t(at),'deadline_at':t(at+4),'row_sha256':str(i)*64})
        if attempts:s['attempts'].append({'admission_token':token,'target_pid':100+i,'target_txid':1000+i,'sealed_at':t(at+.1)})
        if uses:s['uses'].append({'admission_token':token,'target_pid':100+i,'target_txid':1000+i,'entered_at':t(at+.2)})
    return s


class ReferenceTests(unittest.TestCase):
    def test_three_slots_and_denial(self):
        for count in range(4):self.assertEqual(decide(t(30),[t(20+i) for i in range(count)])['http'],201 if count<3 else 429)

    def test_exact_microsecond_boundary_and_single_slot(self):
        history=[t(20),t(30),t(40)]
        self.assertEqual(decide(t(79.999999),history)['http'],429)
        self.assertEqual(decide(t(80),history)['active'],2)
        self.assertEqual(decide(t(80.000001),history+[t(80)])['http'],429)
        self.assertEqual(micros(t(80))-micros(t(79.999999)),1)

    def test_unavailable_untrusted_missing_future(self):
        for flag in ('available','clock_trusted','scope_present'):
            self.assertEqual(decide(t(30),[],**{flag:False}),{'http':503,'insert':False})
        self.assertEqual(decide(t(30),[t(31)])['http'],503)

    def test_bracket_is_not_equality_proof(self):
        history=[t(20),t(30),t(40)]
        self.assertEqual(bracket(t(79),t(81),history)['verdict'],'inconclusive')
        self.assertEqual(bracket(t(78),t(79),history)['http'],429)
        self.assertEqual(bracket(t(80),t(81),history)['http'],201)
        with self.assertRaises(ValueError):bracket(t(81),t(80),history)
        with self.assertRaises(ValueError):micros('2026-11-04T00:00:00+01:00')


class AuditTests(unittest.TestCase):
    def test_valid_three_and_legal_fourth_after_boundary(self):
        for times in ((),(20,),(20,30,40),(20,30,40,80)):
            self.assertEqual(audit(fixture(times))['verdict'],'pass')

    def test_subject_rollback_keeps_attempt_and_quota(self):
        s=fixture(uses=False)
        self.assertEqual(audit(s)['verdict'],'pass')
        self.assertEqual(audit(s)['attempts'],1)
        self.assertEqual(audit(s)['committed_uses'],0)

    def test_unknown_quota_commit_has_admission_no_attempt(self):
        self.assertEqual(audit(fixture(attempts=False,uses=False))['verdict'],'pass')

    def test_four_inside_window_rejected(self):
        self.assertEqual(audit(fixture((20,30,40,79.999999)))['verdict'],'fail')

    def test_scope_policy_and_deadline_mutations(self):
        mutations=[lambda s:s.update(scope=None),lambda s:s['scope'].update(limit_count=4),
          lambda s:s['scope'].update(created_at=t(1)),lambda s:s['scope'].update(environment='other'),
          lambda s:s['admissions'][0].update(context_id='other'),lambda s:s['admissions'][0].update(deadline_at=t(25)),
          lambda s:s['admissions'][0].update(admitted_at=t(25)),lambda s:s['admissions'][0].update(executor_proof_digest='secret'),
          lambda s:s['admissions'][0].update(row_sha256='bad')]
        for f in mutations:
            with self.subTest(mutation=f):
                s=fixture();f(s);self.assertEqual(audit(s)['verdict'],'fail')

    def test_foreign_missing_duplicate_or_late_attempt_use(self):
        mutations=[lambda s:s['attempts'][0].update(admission_token='other'),lambda s:s['attempts'][0].update(target_txid=0),
          lambda s:s['attempts'][0].update(sealed_at=t(24)),lambda s:s['uses'][0].update(target_txid=1001),
          lambda s:s['uses'][0].update(entered_at=t(24)),lambda s:s['attempts'].clear(),
          lambda s:s['uses'].append(copy.deepcopy(s['uses'][0])),lambda s:s['admissions'][0].update(operation_id='other')]
        for f in mutations:
            with self.subTest(mutation=f):
                s=fixture();f(s);self.assertEqual(audit(s)['verdict'],'fail')

    def test_duplicate_transaction_pair_rejected(self):
        s=fixture((20,30));s['attempts'][1].update(target_pid=100,target_txid=1000)
        self.assertEqual(audit(s)['verdict'],'fail')

    def test_original_bundle_still_required(self):
        s=fixture();s['email']['dependency']['logins'][0]['secret_row_present']=False
        self.assertEqual(audit(s)['verdict'],'fail')

    def test_replay_guard_requires_original_completion(self):
        s=fixture();s['replay_guards']=[{'target_txid':2000,'context_id':'ctx','operation_id':'verify','used_at':t(22)}]
        self.assertEqual(audit(s)['verdict'],'pass')
        s['replay_guards'][0]['operation_id']='send'
        self.assertEqual(audit(s)['verdict'],'fail')

    def test_history_delta_does_not_refund_or_rewrite(self):
        a=fixture((20,));b=fixture((20,30))
        self.assertEqual(delta(a,b),{'admissions':1,'attempts':1,'uses':1})
        with self.assertRaises(Invalid):delta(b,a)
        b=copy.deepcopy(a);b['admissions'][0]['row_sha256']='f'*64
        with self.assertRaises(Invalid):delta(a,b)

    def test_malformed_projection_does_not_echo_secret(self):
        for s in (None,{}, {'secret':'DO-NOT-ECHO'}):
            report=audit(s);self.assertEqual(report['verdict'],'fail');self.assertNotIn('DO-NOT-ECHO',str(report))


if __name__=='__main__':unittest.main()
