"""Check an observed blocking graph, not a claimed sleep or overlapping HTTP time.

No SQL/network. Relation lock alone does not prove the exact held actor row;
operator holder setup and independent-actor progress remain separate evidence.
"""
import json
import sys


def audit_locks(value):
    def need(condition):
        if not condition:
            raise ValueError('invalid evidence')

    try:
        need(type(value) is dict and set(value) == {'observation','holder_pid','waiter_pids'})
        s=value['observation'];holder=value['holder_pid'];waiters=value['waiter_pids']
        need(s['schema']=='v00-upstream-lock-observation-v1')
        need(type(holder) is int and holder>0 and type(waiters) is list and len(waiters)==2)
        need(all(type(p) is int and p>0 and p!=holder for p in waiters) and len(set(waiters))==2)
        backends={r['pid']:r for r in s['backends']}
        need(len(backends)==len(s['backends']) and holder in backends and len(backends)<=32)
        need(backends[holder]['state']=='idle in transaction')
        need(backends[holder]['blocking_pids']==[])
        need(any(l['pid']==holder and l['granted'] is True and l['relation']=='v00_session.actors'
                   and l['mode']=='RowShareLock' for l in s['locks']))

        def reaches_holder(pid,seen):
            if pid==holder:return True
            if pid in seen or pid not in backends:return False
            return any(reaches_holder(p,seen|{pid}) for p in backends[pid]['blocking_pids'])

        for pid in waiters:
            a=backends[pid]
            need(a['state']=='active' and a['wait_event_type']=='Lock')
            need(a['wait_event'] in {'transactionid','tuple'})
            need(any(l['pid']==pid and l['granted'] is False and l['locktype'] in {'transactionid','tuple'} for l in s['locks']))
            need(reaches_holder(pid,set()))
        return {'schema':'v00-upstream-lock-review-v1','observed_wait_verdict':'pass','waiters':2,
                'limits':['exact actor binding requires operator holder setup','independent actor completion before release is separate evidence',
                          'one observed wait graph is not universal deadlock freedom'],'errors':[]}
    except (AssertionError,KeyError,TypeError,ValueError):
        return {'schema':'v00-upstream-lock-review-v1','observed_wait_verdict':'fail','errors':['missing-or-invalid-blocking-evidence']}


if __name__=='__main__':
    try:
        with open(sys.argv[1],encoding='utf-8') as stream:report=audit_locks(json.load(stream))
    except (OSError,ValueError,IndexError):
        report={'observed_wait_verdict':'fail','errors':['unreadable-input']}
    print(json.dumps(report))
    raise SystemExit(0 if report['observed_wait_verdict']=='pass' else 1)
