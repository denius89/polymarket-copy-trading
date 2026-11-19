"""Project shared ledger and UI publication without source frames or credentials."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

LEDGER = Path('/var/lib/shadow-e99162d8-public-paper-ledger/state/ledger.sqlite')
FEED = Path('/opt/shadow-polygon/.browser-e2e.e99162d8/gateway/distributions/app/demo-venue-data/snapshot.json')
BACKUP = Path('/var/lib/shadow-e99162d8-public-paper-ledger/integration-backups/prebuy20261117/ledger.sqlite')


def read_only(path):
    db = sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=3)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('ATTACH DATABASE ? AS preserved',(BACKUP.as_uri()+'?mode=ro',))
    db.execute('BEGIN')
    return db


def proof(db, feed):
    version = db.execute('SELECT epoch,admissions FROM app_buy_control WHERE id=1').fetchone()
    rows = db.execute('SELECT operation_id,venue,execution_id,legacy_id,state,quantity,cost,fee,created_ms,updated_ms,legacy_seq,original_json,body_json FROM app_buy_operations ORDER BY seq').fetchall()
    feed_events = {row['id']:row for row in feed.get('events',[])}
    feed_pending = {row['id']:row for row in feed.get('networkPurchases',[])}
    operations = []
    selected = [row for venue in ('polymarket','limitless') for row in [item for item in rows if item['venue']==venue][:12]]
    for row in selected:
        retained = json.loads(row['original_json'])
        event, estimate = retained['event'], retained['estimate']
        chain = event.get('chain')
        states = []
        for state,at,details in db.execute('SELECT state,at_ms,evidence_json FROM app_buy_transitions WHERE operation_id=? ORDER BY seq',(row['operation_id'],)):
            evidence = json.loads(details)
            states.append({'state':state,'atMs':at,**{key:evidence[key] for key in (
                'rpcBlockHashes','finalizedHeights','receiptMatchesOriginal','checkedAtMs','evidenceRef') if key in evidence}})
        body = json.loads(row['body_json'])
        idem = row['legacy_id']
        materialized = db.execute('SELECT count(*),COALESCE(SUM(debit),0) FROM events WHERE venue=? AND id=?',(row['venue'],idem)).fetchone()
        operations.append({'id':hashlib.sha256(row['operation_id'].encode()).hexdigest(),'venue':row['venue'],
            'state':row['state'],'market':body['market'],'outcome':body['outcome'],'amountMicros':[row[k] for k in ('quantity','cost','fee')],
            'sourceAtMs':event['signalAtMs'],'firstSeenMs':event['firstSeenMs'],'createdAtMs':row['created_ms'],
            'blockNumber':chain['blockNumber'] if chain else event['venueReceipt']['finality']['blockNumber'],
            'bookVersion':estimate['book']['hashOrVersion'],'bookReceivedAtMs':estimate['book']['receivedAtMs'],
            'materializedCount':materialized[0],'materializedDebit':materialized[1],
            'published':('event' if idem in feed_events else feed_pending.get(idem,{}).get('status')),
            'transitions':states})
    debit=db.execute('SELECT COALESCE(SUM(debit),0) FROM events').fetchone()[0]
    credits=db.execute('SELECT (SELECT COALESCE(SUM(credit),0) FROM sales)+(SELECT COALESCE(SUM(payout),0) FROM settlements)').fetchone()[0]
    reserve=sum(row['cost']+row['fee'] for row in rows if row['state'] in {'held','pending'})
    missing = {table:db.execute(f'SELECT count(*) FROM (SELECT * FROM preserved.{table} EXCEPT SELECT * FROM main.{table})').fetchone()[0]
               for table in ('events','settings','settlements','sales')}
    return {'epoch':version[0],'admissions':bool(version[1]),'operationCount':len(rows),'operations':operations,
            'missingLegacyRows':missing,
            'balances':{'confirmed':200_000_000-debit+credits,'reserved':reserve,'available':200_000_000-debit+credits-reserve},
            'feed':{'updatedAt':feed['updatedAt'],'available':feed['available'],'reserved':feed.get('reserved'),
                    'positions':len(feed['positions']),'settlements':len(feed['settlements']),'sales':len(feed['sales'])}}


if __name__=='__main__':
    with closing(read_only(LEDGER)) as connection:
        print(json.dumps(proof(connection,json.loads(FEED.read_text())),ensure_ascii=False,separators=(',',':')))
