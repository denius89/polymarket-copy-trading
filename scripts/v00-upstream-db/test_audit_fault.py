import copy
import unittest

from audit_fault import audit_fault
from test_audit_snapshot import complete_fixture, T, DEADLINE


def envelope(case):
    after = complete_fixture()
    # One fresh, no-MFA existing-user email fixture, prepared before the request.
    after['current_factor'] = None
    ctx = after['contexts'][0]
    ctx.update(factor_version=None, totp_challenge_id=None, totp_issued_at=None, totp_expires_at=None)
    after['admissions'] = [after['admissions'][0]]
    after['results'] = [after['results'][1]]
    r = after['results'][0]
    r.update(operation_id='email', action='C02')
    r['result']['completion']['authOperationId'] = 'email'
    after['steps'] = []
    after['plans'][0].update(operation_id='email', action='C02', admission_id='email-admission')
    after['audit'] = [after['audit'][1]]; after['audit'][0]['operation_id'] = 'email'
    dep = after['dependency']
    dep['results'][0].update(operation_id='email', result=copy.deepcopy(r['result']))
    dep['contexts'][0]['completed_operation_id'] = 'email'
    dep['logins'][0]['operation_id'] = 'email'
    before = copy.deepcopy(after)
    for group in ['admissions', 'results', 'plans', 'audit', 'email_outcomes']:
        before[group] = []
    before['contexts'][0]['stage'] = 'email_verification'
    before['dependency'].update(results=[], logins=[], plans=0)
    before['dependency']['contexts'][0].update(completed_login_id=None, completed_operation_id=None)
    before['generations'][0]['state'] = 'issued'
    if case != 'UB10':
        for group in ['results', 'plans', 'audit']:
            after[group] = []
        after['contexts'] = copy.deepcopy(before['contexts'])
        after['dependency'] = copy.deepcopy(before['dependency'])
        if case == 'UB15':
            after['email_outcomes'][0]['observed_at'] = '2026-11-04T12:00:11.000Z'
        else:
            after['generations'][0]['state'] = 'issued'
            after['email_outcomes'][0].update(consumption_txid=None, outcome_txid=None, provider_session_id=None, observed_at=None)
    return {'schema':'v00-upstream-fault-storage-v1','case':case,'before':before,'after':after,
            'operations':[{'context_id':'ctx','operation_id':'email','action':'C02'}]}


def race(rejected=True):
    after = complete_fixture()
    other = copy.deepcopy(after['contexts'][0]); other.update(id='ctx-b',stage='totp_verification')
    after['contexts'].append(other)
    after['dependency']['contexts'].append({'id':'ctx-b','completed_login_id':None,'completed_operation_id':None})
    a = copy.deepcopy(after['admissions'][0]); a.update(id='email-b-admission', context_id='ctx-b', operation_id='email-b')
    after['admissions'].append(a)
    r = copy.deepcopy(after['results'][0]); r.update(context_id='ctx-b',operation_id='email-b')
    after['results'].append(r)
    au = copy.deepcopy(after['audit'][0]); au.update(ordinal=3,context_id='ctx-b',operation_id='email-b')
    after['audit'].append(au)
    gen = copy.deepcopy(after['generations'][0]); gen['id']='generation-b';after['generations'].append(gen)
    seal = copy.deepcopy(after['email_outcomes'][0]);seal.update(seal_id='seal-b',admission_id='email-b-admission',generation_id='generation-b',provider_session_id='provider-session-b');after['email_outcomes'].append(seal)
    before = copy.deepcopy(after)
    for group in ['admissions','results','plans','audit']:
        before[group] = [r for r in before[group] if r['operation_id'] != 'totp']
    before['steps']=[];before['contexts'][0]['stage']='totp_verification'
    before['dependency'].update(results=[],logins=[],plans=0)
    before['dependency']['contexts'][0].update(completed_login_id=None,completed_operation_id=None)
    if rejected:
        a = copy.deepcopy(after['admissions'][1]);a.update(id='loser-admission',context_id='ctx-b',operation_id='loser');after['admissions'].append(a)
        after['results'].append({'context_id':'ctx-b','operation_id':'loser','action':'AUTH_TOTP_VERIFY','login_id':None,
                                'result':{'kind':'verification_rejected','reasonCode':'AUTH_VERIFICATION_FAILED'},'valid':True,'resolved_at':T})
        after['audit'].append({'context_id':'ctx-b','operation_id':'loser','ordinal':4,'kind':'verification_rejected','recorded_at':T})
        after['failures']=1
    return {'schema':'v00-upstream-fault-storage-v1','case':'UB07','before':before,'after':after,
            'operations':[{'context_id':'ctx','operation_id':'totp','action':'AUTH_TOTP_VERIFY'},
                          {'context_id':'ctx-b','operation_id':'loser','action':'AUTH_TOTP_VERIFY'}]}


class FaultStorage(unittest.TestCase):
    def test_supported_branches(self):
        for case in ['UB04','UB10','UB15','UNKNOWN_NO_FORWARD']:
            with self.subTest(case=case):
                self.assertEqual(audit_fault(envelope(case))['storage_verdict'],'pass')
        for rejected in [True,False]:
            report = audit_fault(race(rejected))
            self.assertEqual(report['storage_verdict'],'pass', report)
            self.assertEqual(report['counts']['loser_rejection_results'],int(rejected))

    def test_unknown_cannot_be_success_or_fake_rejection(self):
        v=envelope('UB10');v['case']='UB04'
        self.assertEqual(audit_fault(v)['storage_verdict'],'fail')
        v=envelope('UB04');v['after']['failures']=1
        self.assertEqual(audit_fault(v)['storage_verdict'],'fail')

    def test_late_requires_effect_after_original_budget(self):
        v=envelope('UB15');v['after']['email_outcomes'][0]['observed_at']=T
        self.assertEqual(audit_fault(v)['storage_verdict'],'fail')
        v['after']['email_outcomes'][0]['observed_at']=DEADLINE
        self.assertEqual(audit_fault(v)['storage_verdict'],'pass')
        for invalid in [17, [], None]:
            v['after']['email_outcomes'][0]['observed_at']=invalid
            self.assertEqual(audit_fault(v)['errors'],['timestamp-type'])

    def test_replay_cannot_mutate_deadline_or_executor(self):
        for field,value in [('deadline_at','2026-11-04T12:01:10Z'),('executor_id','replacement')]:
            v=envelope('UB04');v['before']=copy.deepcopy(v['after']);v['after']['admissions'][0][field]=value
            self.assertEqual(audit_fault(v)['storage_verdict'],'fail')

    def test_race_cannot_hide_partial_steps_or_counter(self):
        v=race();v['after']['steps'][0]['operation_id']='loser'
        self.assertEqual(audit_fault(v)['storage_verdict'],'fail')
        v=race(False);v['after']['failures']=1
        self.assertEqual(audit_fault(v)['storage_verdict'],'fail')

    def test_unrelated_issuance_or_seal_rejected(self):
        v=envelope('UB04');g=copy.deepcopy(v['after']['generations'][0]);g['id']='new';v['after']['generations'].append(g)
        self.assertEqual(audit_fault(v)['storage_verdict'],'fail')
        v=race();v['after']['email_outcomes'][1]['provider_session_id']=v['after']['email_outcomes'][0]['provider_session_id']
        self.assertEqual(audit_fault(v)['storage_verdict'],'fail')

    def test_report_contains_no_identifiers_and_names_limits(self):
        v=envelope('UB04');report=audit_fault(v)
        self.assertNotIn('email-admission',str(report))
        self.assertIn('network dispatch count',report['not_proven_by_this_verifier'])
        self.assertEqual(audit_fault({'secret':'do-not-echo'})['errors'],['closed-envelope'])


if __name__ == '__main__':
    unittest.main()
