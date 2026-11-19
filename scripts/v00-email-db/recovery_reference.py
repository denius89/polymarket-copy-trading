"""Independent integer-UTC rolling-window oracle; no DB, secrets or network."""
from datetime import datetime,timedelta,timezone


def micros(value):
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.utcoffset()!=timedelta(0):raise ValueError('UTC required')
    delta=d-datetime(1970,1,1,tzinfo=timezone.utc)
    return (delta.days*86400+delta.seconds)*1000000+delta.microseconds


def decide(now,history,*,available=True,clock_trusted=True,scope_present=True):
    if not available or not clock_trusted or not scope_present:
        return {'http':503,'insert':False}
    t=micros(now);past=[micros(x) for x in history]
    if any(x>t for x in past):return {'http':503,'insert':False}
    active=sorted(x for x in past if t-60000000<x<=t)
    return {'http':429 if len(active)>=3 else 201,'insert':len(active)<3,'active':len(active),
            'earliest_slot_at_us':active[0]+60000000 if len(active)>=3 else None}


def bracket(lower,upper,history,**flags):
    if micros(lower)>micros(upper):raise ValueError('reversed clock bracket')
    a,b=decide(lower,history,**flags),decide(upper,history,**flags)
    if a['http']!=b['http']:
        return {'verdict':'inconclusive','reason':'window-boundary-inside-bracket','lower':a,'upper':b}
    return {'verdict':'decidable','http':a['http'],'lower':a,'upper':b}
