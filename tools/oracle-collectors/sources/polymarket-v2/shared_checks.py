"""Report the shared-demo audit as counts and invariant checks only."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

ROOT=Path('/var/lib/shadow-e99162d8-public-paper-ledger')
LEDGER=ROOT/'state/ledger.sqlite'
BACKUP=ROOT/'integration-backups/prebuy20261117/ledger.sqlite'
FEED=Path('/opt/shadow-polygon/.browser-e2e.e99162d8/gateway/distributions/app/demo-venue-data/snapshot.json')


def check(db, feed):
    epoch,admissions=db.execute('SELECT epoch,admissions FROM app_buy_control WHERE id=1').fetchone()
    retained={table:db.execute(f'SELECT count(*) FROM (SELECT * FROM preserved.{table} EXCEPT SELECT * FROM main.{table})').fetchone()[0]==0
              for table in ('events','settings','settlements','sales','sell_targets')}
    counts={}
    for venue,state,count in db.execute('SELECT venue,state,count(*) FROM app_buy_operations GROUP BY venue,state'):
        if venue not in ('polymarket','limitless') or state not in ('pending','held','finalized','reverted'):
            raise RuntimeError('invalid venue or state in the shared ledger')
        counts.setdefault(venue,{})[state]=count
    materialized=db.execute('''SELECT count(*) FROM app_buy_operations o LEFT JOIN events e ON e.seq=o.legacy_seq
        WHERE o.state='finalized' AND (e.seq IS NULL OR e.venue<>o.venue OR e.id<>o.legacy_id
         OR e.debit<>o.cost+o.fee OR e.quantity<>o.quantity OR e.cost<>o.cost OR e.fee<>o.fee)''').fetchone()[0]==0
    expected_credits=db.execute('SELECT COALESCE(SUM(payout),0)+(SELECT COALESCE(SUM(credit),0) FROM sales) FROM settlements').fetchone()[0]
    spent=db.execute('SELECT COALESCE(SUM(debit),0) FROM events').fetchone()[0]
    reserved=db.execute("SELECT COALESCE(SUM(cost+fee),0) FROM app_buy_operations WHERE state IN ('pending','held')").fetchone()[0]
    published_ids={item['id'] for item in feed.get('events',[])}
    published_pending={item['id'] for item in feed.get('networkPurchases',[]) if item['status']=='pending'}
    milestones={}
    for operation,venue,identifier,original,block_hash in db.execute("""SELECT operation_id,venue,legacy_id,original_json,block_hash FROM app_buy_operations WHERE state='finalized' ORDER BY seq"""):
        if venue in milestones and milestones[venue]['published']:
            continue
        event=json.loads(original)['event']
        transition=db.execute("SELECT state,evidence_json FROM app_buy_transitions WHERE operation_id=? ORDER BY seq",(operation,)).fetchall()
        data={'published':identifier in published_ids,'transitionOrder':[name for name,_ in transition]}
        if venue=='polymarket':
            data['source']=event['venueReceipt']['source']
        else:
            evidence=json.loads(transition[-1][1])
            height=event['chain']['blockNumber']
            heads=evidence.get('finalizedHeights')
            data['independentBaseFinality']=evidence.get('rpcBlockHashes')==[block_hash,block_hash] and (
                isinstance(heads,list) and len(heads)==2 and all(type(head) is int and head>=height for head in heads)) and evidence.get('receiptMatchesOriginal') is True
        milestones[venue]=data
    return {'epoch':epoch,'admissions':bool(admissions),'counts':counts,'legacyRowsPreserved':retained,
            'finalizedLedgerLinksVerified':materialized,
            'publishedBalanceReconciled':feed.get('available')==200_000_000+expected_credits-spent-reserved and feed.get('reserved')==reserved,
            'publishedPendingCount':len(published_pending),'milestones':milestones}


if __name__=='__main__':
    with closing(sqlite3.connect(LEDGER.as_uri()+'?mode=ro',uri=True,timeout=3)) as database:
        database.execute('PRAGMA query_only=ON')
        database.execute('ATTACH DATABASE ? AS preserved',(BACKUP.as_uri()+'?mode=ro',))
        database.execute('BEGIN')
        print(json.dumps(check(database,json.loads(FEED.read_text())),ensure_ascii=False))
