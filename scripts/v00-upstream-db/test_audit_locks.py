import copy
import unittest

from audit_locks import audit_locks


def graph():
    return {'holder_pid':1,'waiter_pids':[2,3],'observation':{'schema':'v00-upstream-lock-observation-v1',
        'observed_at':'2000-01-01T00:00:00Z','backends':[
            {'pid':1,'state':'idle in transaction','blocking_pids':[]},
            {'pid':2,'state':'active','wait_event_type':'Lock','wait_event':'transactionid','blocking_pids':[1]},
            {'pid':3,'state':'active','wait_event_type':'Lock','wait_event':'tuple','blocking_pids':[2]}],
        'locks':[{'pid':1,'granted':True,'relation':'v00_session.actors','mode':'RowShareLock'},
                 {'pid':2,'granted':False,'locktype':'transactionid'},
                 {'pid':3,'granted':False,'locktype':'tuple'}]}}


class ObservedLocks(unittest.TestCase):
    def test_transitive_chain(self):
        self.assertEqual(audit_locks(graph())['observed_wait_verdict'],'pass')

    def test_http_overlap_cannot_replace_lock_evidence(self):
        for mutate in [lambda x:x['observation']['locks'].pop(),
                       lambda x:x['observation']['backends'][2].update(wait_event_type='Client'),
                       lambda x:x['observation']['backends'][2].update(blocking_pids=[]),
                       lambda x:x['observation']['backends'][2].update(blocking_pids=[3]),
                       lambda x:x.update(waiter_pids=[2,2])]:
            x=copy.deepcopy(graph());mutate(x)
            self.assertEqual(audit_locks(x)['observed_wait_verdict'],'fail')

    def test_no_id_output(self):
        r=audit_locks(graph())
        self.assertNotIn('holder_pid',r)
        self.assertIn('independent actor completion before release is separate evidence',r['limits'])


if __name__=='__main__':unittest.main()
