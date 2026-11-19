"""Additive BUY admission on the existing shared-demo SQLite; no network client."""
from contextlib import contextmanager
from datetime import datetime, timezone
from fractions import Fraction
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from zoneinfo import ZoneInfo
import pm_provenance as provenance

LEGACY=('events','sales','sell_targets','settings','settlements')
ACTIVE=('pending','held')
LEGACY_WALLETS={'polymarket':'0xde9f7f4e77a1595623ceb58e469f776257ccd43c',
                'limitless':'0x3eda6446d3f458e8ce2b9c433c59d719e331fc28'}

class Refusal(Exception): pass
class AdmissionChanged(Exception): pass
class Fenced(Exception): pass

def packed(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v): return hashlib.sha256(packed(v).encode()).hexdigest()
def now(v=None): return int(time.time()*1000) if v is None else integer(v)
def integer(v):
    if type(v) is not int or not 0<=v<2**63: raise Refusal('INVALID_INTEGER')
    return v
def text(v):
    if not isinstance(v,str) or not 1<=len(v)<=512 or any(ord(c)<32 for c in v): raise Refusal('INVALID_TEXT')
    return v
def exact(v):
    try:return provenance.q(v)
    except provenance.ProvenanceError as e:raise Refusal(str(e)) from None
def micros(v):
    v=Fraction(v)*1000000
    if v.denominator!=1:raise Refusal('NONINTEGRAL_LEGACY_MICROS')
    return integer(v.numerator)
def rows(db,sql,args=()):
    cur=db.execute(sql,args);names=[c[0] for c in cur.description]
    return [dict(zip(names,row)) for row in cur.fetchall()]
def idle(db):
    if db.in_transaction:raise RuntimeError('idle connection required')

def schema(db):
    return [dict(type=t,name=n,table=tbl,sql=s) for t,n,tbl,s in db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")]

def legacy_digest(db):
    """Logical content, including original JSON/text and fractional sale basis."""
    out={}
    for table in LEGACY:
        info=list(db.execute('PRAGMA table_info('+table+')'))
        if not info:raise Refusal('LEGACY_TABLE_MISSING')
        order=','.join('"'+c[1]+'"' for c in sorted(info,key=lambda x:x[5]) if c[5])
        if not order:order='rowid'
        h=hashlib.sha256();count=0
        for row in db.execute('SELECT * FROM '+table+' ORDER BY '+order):
            typed=[['null',None] if v is None else ['bytes',v.hex()] if isinstance(v,bytes)
                   else [type(v).__name__,str(v)] for v in row]
            h.update((packed(typed)+'\n').encode());count+=1
        out[table]={'rows':count,'sha256':h.hexdigest()}
    return out

DDL=[
'''CREATE TABLE app_buy_control(id INTEGER PRIMARY KEY CHECK(id=1), epoch INTEGER NOT NULL,
owner TEXT, admissions INTEGER NOT NULL CHECK(admissions IN(0,1)), policy_json TEXT NOT NULL,
baseline_json TEXT NOT NULL)''',
'''CREATE TABLE app_buy_signals(venue TEXT NOT NULL,execution_id TEXT NOT NULL,fingerprint TEXT NOT NULL,
source_ms INTEGER NOT NULL,first_seen_ms INTEGER NOT NULL,identity_json TEXT NOT NULL,
PRIMARY KEY(venue,execution_id))''',
'''CREATE TABLE app_buy_operations(seq INTEGER PRIMARY KEY,operation_id TEXT NOT NULL UNIQUE,
venue TEXT NOT NULL,execution_id TEXT NOT NULL,block_hash TEXT,legacy_id TEXT NOT NULL,
market TEXT NOT NULL,public_market TEXT NOT NULL,token TEXT NOT NULL,day TEXT NOT NULL,
state TEXT NOT NULL CHECK(state IN('pending','held','finalized','reverted')),
quantity INTEGER NOT NULL CHECK(quantity>0),cost INTEGER NOT NULL CHECK(cost>0),
fee INTEGER NOT NULL CHECK(fee>=0),original_json TEXT NOT NULL,body_json TEXT NOT NULL,
created_ms INTEGER NOT NULL,updated_ms INTEGER NOT NULL,legacy_seq INTEGER,
FOREIGN KEY(venue,execution_id) REFERENCES app_buy_signals(venue,execution_id),
FOREIGN KEY(legacy_seq) REFERENCES events(seq),
CHECK((state='finalized')=(legacy_seq IS NOT NULL)),
CHECK(venue='limitless' OR (venue='polymarket' AND state='finalized')))''',
'''CREATE UNIQUE INDEX app_buy_active_execution ON app_buy_operations(venue,execution_id)
WHERE state IN('pending','held','finalized')''',
'''CREATE UNIQUE INDEX app_buy_final_event ON app_buy_operations(legacy_seq) WHERE legacy_seq IS NOT NULL''',
'''CREATE TABLE app_buy_receipts(command_id TEXT PRIMARY KEY,request_json TEXT NOT NULL,result_json TEXT NOT NULL)''',
'''CREATE TABLE app_buy_transitions(seq INTEGER PRIMARY KEY,operation_id TEXT NOT NULL,
command_id TEXT NOT NULL UNIQUE,state TEXT NOT NULL,evidence_json TEXT NOT NULL,at_ms INTEGER NOT NULL,
FOREIGN KEY(operation_id) REFERENCES app_buy_operations(operation_id))'''
]

def install(db,baseline_schema,policy):
    idle(db)
    if set(policy)!={'opening','daily','market'}:raise Refusal('INVALID_POLICY')
    for v in policy.values():integer(v)
    db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
    db.execute('BEGIN IMMEDIATE')
    try:
        if schema(db)!=baseline_schema or {r['name'] for r in baseline_schema}!=set(LEGACY):
            raise Refusal('SCHEMA_BASELINE_MISMATCH')
        if db.execute('PRAGMA user_version').fetchone()[0]!=0 or db.execute('PRAGMA application_id').fetchone()[0]!=0:
            raise Refusal('SCHEMA_VERSION_MISMATCH')
        if db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise Refusal('INTEGRITY_CHECK_FAILED')
        before=legacy_digest(db)
        for statement in DDL:db.execute(statement)
        db.execute('INSERT INTO app_buy_control VALUES(1,0,NULL,0,?,?)',(packed(policy),packed(before)))
        # Every old writing path is fenced, including settlement during publication.
        fence="SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM app_buy_control WHERE id=1 AND owner=app_owner() AND epoch=app_epoch()) THEN RAISE(ABORT,'WRITER_FENCED') END;"
        for table in LEGACY+('app_buy_signals','app_buy_operations','app_buy_receipts','app_buy_transitions'):
            for action in ('INSERT','UPDATE','DELETE'):
                db.execute(f'CREATE TRIGGER app_fence_{table}_{action} BEFORE {action} ON {table} BEGIN {fence} END')
        for table in ('events','sales','settlements','settings','app_buy_signals','app_buy_receipts','app_buy_transitions'):
            for action in ('UPDATE','DELETE'):
                db.execute(f"CREATE TRIGGER app_immutable_{table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_HISTORY'); END")
        db.execute("""CREATE TRIGGER app_guard_legacy_buy BEFORE INSERT ON events
        WHEN NEW.debit>0 OR json_extract(NEW.body,'$.side')='BUY'
        BEGIN SELECT CASE WHEN app_materializing()!=1 THEN RAISE(ABORT,'LEGACY_BUY_DISABLED') END; END""")
        for table in ('sales','settlements','sell_targets'):
            for action in ('INSERT','UPDATE'):
                db.execute(f"""CREATE TRIGGER app_pending_{table}_{action} BEFORE {action} ON {table}
                WHEN EXISTS(SELECT 1 FROM app_buy_operations WHERE venue=NEW.venue AND market=NEW.market
                AND token=NEW.token AND state IN('pending','held'))
                BEGIN SELECT RAISE(ABORT,'PENDING_SCOPE_BLOCKED'); END""")
        db.execute("""CREATE TRIGGER app_guard_operation_update BEFORE UPDATE ON app_buy_operations
        WHEN app_materializing()!=1 OR OLD.state IN('finalized','reverted')
        OR NEW.operation_id!=OLD.operation_id OR NEW.original_json!=OLD.original_json
        OR NEW.body_json!=OLD.body_json OR NEW.quantity!=OLD.quantity OR NEW.cost!=OLD.cost OR NEW.fee!=OLD.fee
        OR NEW.seq!=OLD.seq OR NEW.venue!=OLD.venue OR NEW.execution_id!=OLD.execution_id
        OR NEW.block_hash IS NOT OLD.block_hash OR NEW.legacy_id!=OLD.legacy_id
        OR NEW.market!=OLD.market OR NEW.public_market!=OLD.public_market OR NEW.token!=OLD.token
        OR NEW.day!=OLD.day OR NEW.created_ms!=OLD.created_ms OR NEW.updated_ms<OLD.updated_ms
        BEGIN SELECT RAISE(ABORT,'INVALID_OPERATION_TRANSITION'); END""")
        db.execute("""CREATE TRIGGER app_guard_operation_delete BEFORE DELETE ON app_buy_operations
        BEGIN SELECT RAISE(ABORT,'IMMUTABLE_HISTORY'); END""")
        if legacy_digest(db)!=before:raise RuntimeError('legacy content changed during install')
        db.commit();return before
    except BaseException:db.rollback();raise

def claim_writer(db,owner,expected_epoch):
    idle(db);text(owner);integer(expected_epoch)
    db.execute('BEGIN IMMEDIATE')
    try:
        row=db.execute('SELECT epoch,owner FROM app_buy_control WHERE id=1').fetchone()
        if row!=(expected_epoch,None):raise Fenced('owner must first be stopped/fenced; no takeover')
        epoch=expected_epoch+1
        db.execute('UPDATE app_buy_control SET epoch=?,owner=?,admissions=1 WHERE id=1',(epoch,owner));db.commit()
        return Store(db,owner,epoch)
    except BaseException:db.rollback();raise

class Store:
    def __init__(self,db,owner,epoch):
        idle(db);self.db=db;self.owner=text(owner);self.epoch=integer(epoch);self.materializing=0
        db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
        db.create_function('app_owner',0,lambda:self.owner)
        db.create_function('app_epoch',0,lambda:self.epoch)
        db.create_function('app_materializing',0,lambda:self.materializing)
        self._fence()

    def _fence(self):
        row=self.db.execute('SELECT owner,epoch,admissions,policy_json FROM app_buy_control WHERE id=1').fetchone()
        if not row or row[:2]!=(self.owner,self.epoch):raise Fenced('WRITER_FENCED')
        return row[2],json.loads(row[3])

    @contextmanager
    def _materialize(self):
        self.materializing+=1
        try:yield
        finally:self.materializing-=1

    def stop_admissions(self):
        idle(self.db);self.db.execute('BEGIN IMMEDIATE')
        try:self._fence();self.db.execute('UPDATE app_buy_control SET admissions=0 WHERE id=1');self.db.commit()
        except BaseException:self.db.rollback();raise

    def fence(self):
        idle(self.db);self.db.execute('BEGIN IMMEDIATE')
        try:
            self._fence();self.db.execute('UPDATE app_buy_control SET admissions=0,owner=NULL,epoch=epoch+1 WHERE id=1')
            self.db.commit();return self.epoch+1
        except BaseException:self.db.rollback();raise

    def lookup_command(self,command_id,request=None,*,event=None):
        self._fence()
        row=self.db.execute('SELECT request_json,result_json FROM app_buy_receipts WHERE command_id=?',(text(command_id),)).fetchone()
        if row:
            if request is not None and row[0]!=packed(request):raise Refusal('KEY_REUSE_CONFLICT')
            if event is not None and json.loads(row[0]).get('event')!=event:raise Refusal('KEY_REUSE_CONFLICT')
            return json.loads(row[1])
        return None

    def lookup_execution(self,event):
        """Recover an immutable submit result without refreshing its observation anchors."""
        self._fence()
        venue,eid=text(event.get('venue')),text(event.get('executionId'))
        def stable(e,include_block=True):
            value={k:e[k] for k in ('venue','executionId','fingerprint','marketId','outcomeId','side','signalAtMs')}
            if e['venue']=='polymarket':
                receipt=e['venueReceipt'];f=receipt['finality']
                if receipt['source']=='polymarket-rtds-finalized-v1':
                    r=receipt['rtds']
                elif receipt['source']=='polymarket-data-api-maker-finalized-v1':
                    r=receipt['discovery']
                    value.update(discoveryProfile=r['profile'],discoveryEndpoint=r['endpoint'])
                else:raise Refusal('POLYMARKET_SOURCE_NOT_ALLOWED')
                value.update(source=receipt['source'],match=receipt['match'],
                    reported={k:r[k] for k in ('reportedQuantity','reportedPrice','transactionHash','wallet','marketId','outcomeId','side','sourceTimestampMs')})
                if include_block:value.update(blockHash=f['blockHash'],blockNumber=f['blockNumber'])
            else:
                chain=e['chain'];value['chain']={k:chain[k] for k in ('chainId','transactionHash')}
                if include_block:value['chain'].update(blockHash=chain['blockHash'],blockNumber=chain['blockNumber'],logIndex=chain['logIndex'])
            return packed(value)
        try:
            common,attempt=stable(event,False),stable(event)
            candidates=self.db.execute("""SELECT request_json,result_json FROM app_buy_receipts
                WHERE json_extract(request_json,'$.kind')='submit'
                AND json_extract(request_json,'$.event.venue')=?
                AND json_extract(request_json,'$.event.executionId')=? ORDER BY rowid""",(venue,eid))
            for request,result in candidates:
                old=json.loads(request)['event']
                if stable(old,False)!=common:raise Refusal('EXECUTION_IDENTITY_CONFLICT')
                if stable(old)==attempt:return json.loads(result)
            return None
        except (KeyError,TypeError,AttributeError):raise Refusal('INVALID_EXECUTION_LOOKUP') from None

    def _command(self,key,request,action,commit=None):
        db=self.db;idle(db);text(key);db.execute('BEGIN IMMEDIATE')
        try:
            self._fence();prior=self.lookup_command(key,request)
            if prior is not None:db.commit();return prior
            db.execute('SAVEPOINT action')
            try:result={'status':'recorded','operation':action()}
            except Refusal as e:
                db.execute('ROLLBACK TO action');result={'status':'rejected','reasonCode':str(e)}
            db.execute('RELEASE action')
            db.execute('INSERT INTO app_buy_receipts VALUES(?,?,?)',(key,packed(request),packed(result)))
            if commit and result['status']=='recorded':commit()
            else:db.commit()
            return result
        except BaseException:db.rollback();raise

    def _operation(self,oid):
        found=rows(self.db,'SELECT * FROM app_buy_operations WHERE operation_id=?',(oid,))
        if not found:raise Refusal('OPERATION_NOT_FOUND')
        return found[0]

    def lookup_reconciliation(self,command_id,operation_id,execution_id):
        """Identity-bound recovery includes a saved rejection with no operation view."""
        self._fence();op=self._operation(text(operation_id))
        if op['venue']!='limitless' or op['execution_id']!=text(execution_id):raise Refusal('RECONCILIATION_IDENTITY_CONFLICT')
        row=self.db.execute('SELECT request_json,result_json FROM app_buy_receipts WHERE command_id=?',(text(command_id),)).fetchone()
        if row:
            request=json.loads(row[0])
            if request.get('kind')!='reconcile' or request.get('operationId')!=operation_id:raise Refusal('RECONCILIATION_IDENTITY_CONFLICT')
            return json.loads(row[1])
        return None

    def _view(self,op):
        return dict(operationId=op['operation_id'],activityId=op['execution_id'],venue=op['venue'],
                    state=op['state'],quantity=op['quantity'],cost=op['cost'],fee=op['fee'],
                    createdAtMs=op['created_ms'],updatedAtMs=op['updated_ms'],legacyId=op['legacy_id'])

    def _event_row(self,body,market,day):
        with self._materialize():
            cur=self.db.execute('INSERT INTO events(venue,id,day,market,token,debit,quantity,cost,fee,body) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (body['venue'],body['id'],day,market,body['token'],body['cost']+body['fee'],body['quantity'],body['cost'],body['fee'],packed(body)))
        return cur.lastrowid

    def _transition(self,oid,key,state,evidence,at):
        self.db.execute('INSERT INTO app_buy_transitions(operation_id,command_id,state,evidence_json,at_ms) VALUES(?,?,?,?,?)',
                        (oid,key,state,packed(evidence),at))

    def legacy_guard(self,venue,market,token,kind):
        self._fence()
        if kind=='BUY':raise Refusal('LEGACY_BUY_DISABLED')
        if self.db.execute("SELECT 1 FROM app_buy_operations WHERE venue=? AND market=? AND token=? AND state IN('pending','held')",(venue,market,token)).fetchone():
            raise Refusal('PENDING_SCOPE_BLOCKED')

    def submit(self,command_id,event,estimate,public_body,aliases,latest_guard,now_ms=None):
        db=self.db;at=now(now_ms);needs_guard=False;anchor=None
        request=dict(kind='submit',event=event,estimate=estimate,publicBody=public_body,aliases=aliases)
        def action():
            nonlocal needs_guard,anchor
            enabled,policy=self._fence()
            if not enabled:raise Refusal('ADMISSIONS_STOPPED')
            if event.get('side')!='BUY' or event.get('venue') not in ('polymarket','limitless'):raise Refusal('BUY_ONLY')
            venue=event['venue'];eid=text(event['executionId']);fp=event['fingerprint']
            if not re.fullmatch('[0-9a-f]{64}',fp or ''):raise Refusal('INVALID_FINGERPRINT')
            source,first=integer(event['signalAtMs']),integer(event['firstSeenMs'])
            if source>first or first>at:raise Refusal('SOURCE_TIME_FUTURE')
            chain=event.get('chain');bh=None
            if venue=='polymarket':
                try:provenance.validate(event,at);provenance.validate_estimate(event,estimate)
                except provenance.ProvenanceError as e:raise Refusal(str(e)) from None
                tx=event['venueReceipt']['match']['transactionHash']
            else:
                if not isinstance(chain,dict) or type(chain.get('chainId')) is not int or chain['chainId']!=8453:raise Refusal('CHAIN_MISMATCH')
                bh=chain.get('blockHash');tx=chain.get('transactionHash')
                if not re.fullmatch('0x[0-9a-f]{64}',bh or '') or not re.fullmatch('0x[0-9a-f]{64}',tx or ''):raise Refusal('INVALID_CHAIN')
                integer(chain.get('blockNumber'));integer(chain.get('logIndex'))
                if chain.get('rpcBlockHashes')!=[bh,bh]:raise Refusal('RPC_DISAGREEMENT')
            if not isinstance(aliases,list) or not 1<=len(aliases)<=16 or len(set(aliases))!=len(aliases):raise Refusal('INVALID_ALIASES')
            for alias in aliases:text(alias)
            body=dict(public_body)
            for k in ('market','outcome','trader','wallet','condition','token','id','slug','recordedAt'):text(body.get(k))
            if body['venue']!=venue or body.get('side')!='BUY' or body['id']!=eid or body['token']!=event['outcomeId'] or body['condition']!=event['marketId'] or body['at']!=source//1000:
                raise Refusal('PUBLIC_BODY_BINDING')
            if body.get('tx')!=tx:raise Refusal('PUBLIC_BODY_BINDING')
            wallet=body['wallet'].lower()
            if not re.fullmatch('0x[0-9a-f]{40}',wallet):raise Refusal('INVALID_WALLET')
            if venue=='polymarket' and wallet!=event['venueReceipt']['match']['wallet']:raise Refusal('PUBLIC_BODY_BINDING')
            market=body['condition'] if wallet==LEGACY_WALLETS[venue] else body['condition']+':'+wallet
            if 'positionMarket' in body and body['positionMarket']!=market:raise Refusal('POSITION_SCOPE_MISMATCH')
            if set(estimate)!={'fills','book','evidence'} or not isinstance(estimate['evidence'],dict):raise Refusal('INVALID_ESTIMATE')
            qty=cost=fee=Fraction()
            if not isinstance(estimate['fills'],list) or not 1<=len(estimate['fills'])<=1000:raise Refusal('INVALID_FILLS')
            for fill in estimate['fills']:
                if set(fill)!={'quantity','price','cashFee'}:raise Refusal('INVALID_FILL')
                q,price,f=map(exact,(fill['quantity'],fill['price'],fill['cashFee']))
                if q<=0 or not 0<price<=1 or f<0:raise Refusal('INVALID_FILL')
                qty+=q;cost+=q*price;fee+=f
            quantity,cost,fee=micros(qty),micros(cost),micros(fee)
            if any(type(body.get(k)) is not int or body[k]!=v for k,v in [('quantity',quantity),('cost',cost),('fee',fee)]):raise Refusal('PUBLIC_MONEY_BINDING')
            identity=dict(wallet=wallet,market=market,token=body['token'],transactionHash=tx)
            prior=db.execute('SELECT fingerprint,source_ms,first_seen_ms,identity_json FROM app_buy_signals WHERE venue=? AND execution_id=?',(venue,eid)).fetchone()
            if prior:
                if (prior[0],prior[1],prior[3])!=(fp,source,packed(identity)):raise Refusal('EXECUTION_IDENTITY_CONFLICT')
                first=prior[2]
            oid=digest([venue,eid,bh])
            existing=rows(db,'SELECT * FROM app_buy_operations WHERE operation_id=?',(oid,))
            if existing:
                saved=json.loads(existing[0]['original_json'])
                if saved['estimate']!=estimate:raise Refusal('EXECUTION_INPUT_CONFLICT')
                return self._view(existing[0])
            if db.execute("SELECT 1 FROM app_buy_operations WHERE venue=? AND execution_id=? AND state IN('pending','held','finalized')",(venue,eid)).fetchone():raise Refusal('EXECUTION_ALREADY_ACTIVE_OR_FINAL')
            if not 0<=at-min(source,first)<=30000:raise Refusal('SIGNAL_EXPIRED')
            anchor=min(source,first)
            # Existing opaque legacy IDs may cover more than one on-chain execution.
            for alias in set(aliases+[eid]):
                if db.execute('SELECT 1 FROM events WHERE venue=? AND id=? UNION ALL SELECT 1 FROM sales WHERE venue=? AND id=?',(venue,alias,venue,alias)).fetchone():raise Refusal('LEGACY_EXECUTION_EXISTS')
            for oldbody, in db.execute('SELECT body FROM events e WHERE venue=? AND token=? AND NOT EXISTS(SELECT 1 FROM app_buy_operations o WHERE o.legacy_seq=e.seq)',(venue,body['token'])):
                old=json.loads(oldbody)
                if old.get('tx')==tx and (not old.get('wallet') or old['wallet'].lower()==wallet):raise Refusal('LEGACY_EXECUTION_EXISTS')
            if db.execute('SELECT 1 FROM settlements WHERE venue=? AND market=? AND token=?',(venue,market,body['token'])).fetchone():raise Refusal('MARKET_SETTLED')
            self.legacy_guard(venue,market,body['token'],'admit')
            day=datetime.fromtimestamp(at/1000,ZoneInfo('Europe/Warsaw')).date().isoformat()
            spent=db.execute('SELECT COALESCE(SUM(debit),0) FROM events').fetchone()[0]
            credits=db.execute('SELECT (SELECT COALESCE(SUM(payout),0) FROM settlements)+(SELECT COALESCE(SUM(credit),0) FROM sales)').fetchone()[0]
            reserve=db.execute("SELECT COALESCE(SUM(cost+fee),0) FROM app_buy_operations WHERE state IN('pending','held')").fetchone()[0]
            daily=db.execute('SELECT COALESCE(SUM(debit),0) FROM events WHERE day=?',(day,)).fetchone()[0]
            daily+=db.execute("SELECT COALESCE(SUM(cost+fee),0) FROM app_buy_operations WHERE day=? AND state IN('pending','held')",(day,)).fetchone()[0]
            public=body['condition'];pattern=public+':*'
            same=db.execute('SELECT COALESCE(SUM(debit),0) FROM events WHERE venue=? AND (market=? OR market GLOB ?)',(venue,public,pattern)).fetchone()[0]
            same+=db.execute("SELECT COALESCE(SUM(cost+fee),0) FROM app_buy_operations WHERE venue=? AND public_market=? AND state IN('pending','held')",(venue,public)).fetchone()[0]
            released=sum((Fraction(c)+Fraction(f) for c,f in db.execute('SELECT cost_exact,fee_exact FROM sales WHERE venue=? AND (market=? OR market GLOB ?)',(venue,public,pattern))),Fraction())
            if cost+fee>min(policy['opening']-spent+credits-reserve,policy['daily']-daily,policy['market']-same+released):raise Refusal('LIMIT')
            if latest_guard(event,estimate) is not True:raise AdmissionChanged('BOOK_NOT_CURRENT_OR_ADMISSIBLE')
            if not prior:db.execute('INSERT INTO app_buy_signals VALUES(?,?,?,?,?,?)',(venue,eid,fp,source,first,packed(identity)))
            state='finalized' if venue=='polymarket' else 'pending'
            seq=self._event_row(body,market,day) if state=='finalized' else None
            db.execute('''INSERT INTO app_buy_operations(operation_id,venue,execution_id,block_hash,legacy_id,market,public_market,token,day,state,quantity,cost,fee,original_json,body_json,created_ms,updated_ms,legacy_seq)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(oid,venue,eid,bh,eid,market,public,body['token'],day,state,quantity,cost,fee,packed(request),packed(body),at,at,seq))
            self._transition(oid,command_id,state,estimate['evidence'],at);needs_guard=True
            return self._view(self._operation(oid))
        def commit():
            if not needs_guard:db.commit();return
            with latest_guard.commit_lock:
                self._fence()
                if not 0<=now(now_ms)-anchor<=30000:raise AdmissionChanged('SIGNAL_EXPIRED')
                if latest_guard(event,estimate) is not True:raise AdmissionChanged('BOOK_NOT_CURRENT_OR_ADMISSIBLE')
                db.commit()
        return self._command(command_id,request,action,commit)

    def reconcile(self,command_id,operation_id,decision,now_ms=None):
        at=now(now_ms);db=self.db
        request=dict(kind='reconcile',operationId=operation_id,decision=decision)
        def action():
            op=self._operation(operation_id)
            if op['venue']!='limitless':raise Refusal('NOT_BASE_PENDING')
            if set(decision)!={'state','rpcBlockHashes','executionPresent','finalized','evidence'} or not isinstance(decision['evidence'],dict):raise Refusal('INVALID_DECISION')
            target=decision['state'];hashes=decision['rpcBlockHashes']
            if target not in ('held','finalized','reverted') or type(decision['executionPresent']) is not bool or type(decision['finalized']) is not bool:raise Refusal('INVALID_DECISION')
            if op['state'] in ('finalized','reverted'):
                if target!=op['state']:raise Refusal('TERMINAL_STATE_CONFLICT')
                return self._view(op)
            if at<op['updated_ms']:raise Refusal('NONMONOTONIC_DECISION_TIME')
            if target!='held':
                if not isinstance(hashes,list) or len(hashes)!=2 or hashes[0]!=hashes[1] or not re.fullmatch('0x[0-9a-f]{64}',hashes[0] or ''):raise Refusal('RPC_DISAGREEMENT')
                if target=='finalized' and (hashes[0]!=op['block_hash'] or not decision['executionPresent'] or not decision['finalized']):raise Refusal('FINALITY_NOT_PROVEN')
                if target=='reverted' and (hashes[0]==op['block_hash'] or decision['executionPresent']):raise Refusal('REORG_NOT_PROVEN')
            seq=op['legacy_seq']
            if target=='finalized':seq=self._event_row(json.loads(op['body_json']),op['market'],op['day'])
            with self._materialize():
                db.execute('UPDATE app_buy_operations SET state=?,updated_ms=?,legacy_seq=? WHERE operation_id=?',(target,at,seq,operation_id))
            self._transition(operation_id,command_id,target,decision['evidence'],at)
            return self._view(self._operation(operation_id))
        return self._command(command_id,request,action)

    def pending_operations(self):
        self._fence()
        result=[]
        for o in rows(self.db,"SELECT * FROM app_buy_operations WHERE state IN('pending','held') ORDER BY seq"):
            original=json.loads(o['original_json'])
            result.append(dict(operationId=o['operation_id'],state=o['state'],event=original['event'],
                               estimate=original['estimate'],publicBody=original['publicBody'],aliases=original['aliases']))
        return result

    def snapshot_overlay(self):
        own=not self.db.in_transaction
        if own:self.db.execute('BEGIN')
        try:
            operations=rows(self.db,"""SELECT * FROM app_buy_operations o WHERE seq=(SELECT MAX(i.seq)
                FROM app_buy_operations i WHERE i.venue=o.venue AND i.execution_id=o.execution_id) ORDER BY seq DESC""")
            reserve=0;network=[];scopes=[]
            for o in operations:
                if o['state']=='finalized':continue
                body=json.loads(o['body_json']);pending=o['state'] in ACTIVE
                network.append(dict(id=o['legacy_id'],venue=o['venue'],trader=body['trader'],market=body['market'],
                  outcome=body['outcome'],recordedAt=body['recordedAt'],status='pending' if pending else 'reverted',
                  quantity=o['quantity'],cost=o['cost'],fee=o['fee']))
                if pending:
                    reserve+=o['cost']+o['fee'];scopes.append([o['venue'],o['market'],o['token']])
            result=dict(reserved=reserve,networkPurchases=network,pendingScopes=scopes)
            if own:self.db.commit()
            return result
        except BaseException:
            if own:self.db.rollback()
            raise

def consistent_backup(source_path,destination_path):
    """Operator calls only; never copy a live main file ignoring its journal/WAL."""
    target=Path(destination_path)
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    src=sqlite3.connect(Path(source_path).resolve().as_uri()+'?mode=ro',uri=True)
    dst=sqlite3.connect(target)
    try:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:raise RuntimeError('backup integrity failed')
        logical=legacy_digest(dst)
        return dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),legacy=logical)
    finally:dst.close();src.close()

@contextmanager
def process_lock(database_path):
    """Hold for the whole unified writer lifetime, including recovery and maintenance."""
    path=str(Path(database_path).resolve())+'.app-buy-writer.lock'
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)

def audit(db,policy=None):
    """Read-only exact reconciliation in one SQLite snapshot; no marking/settlement."""
    own=not db.in_transaction
    if own:db.execute('BEGIN')
    try:
        installed=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_buy_control'").fetchone() is not None
        if installed:
            current=json.loads(db.execute('SELECT policy_json FROM app_buy_control WHERE id=1').fetchone()[0])
            if policy is not None and policy!=current:raise Refusal('POLICY_MISMATCH')
            policy=current
        if not isinstance(policy,dict) or set(policy)!={'opening','daily','market'}:raise Refusal('POLICY_REQUIRED')
        for v in policy.values():integer(v)
        if db.execute('PRAGMA foreign_key_check').fetchall():raise Refusal('FOREIGN_KEY_CHECK_FAILED')
        groups={};spent=0
        for venue,market,token,debit,qty,cost,fee in db.execute('SELECT venue,market,token,debit,quantity,cost,fee FROM events'):
            for v in (debit,qty,cost,fee):integer(v)
            if debit!=cost+fee or (debit==0 and qty!=0):raise Refusal('LEGACY_EVENT_MONEY_MISMATCH')
            spent+=debit
            if debit:
                key=(venue,market,token);g=groups.setdefault(key,[0,Fraction(),Fraction()])
                g[0]+=qty;g[1]+=cost;g[2]+=fee
        credits=0;realized=Fraction()
        for venue,market,token,qty,cost,fee,credit in db.execute('SELECT venue,market,token,quantity,cost_exact,fee_exact,credit FROM sales'):
            integer(qty);integer(credit);cost,fee=Fraction(cost),Fraction(fee)
            key=(venue,market,token)
            if key not in groups or min(cost,fee)<0:raise Refusal('LEGACY_SALE_BASIS_MISMATCH')
            g=groups[key];g[0]-=qty;g[1]-=cost;g[2]-=fee
            if min(g)<0:raise Refusal('LEGACY_NEGATIVE_REMAINDER')
            credits+=credit;realized+=credit-cost-fee
        closed=set()
        for venue,market,token,payout in db.execute('SELECT venue,market,token,payout FROM settlements'):
            integer(payout);key=(venue,market,token)
            if key not in groups:raise Refusal('LEGACY_SETTLEMENT_BASIS_MISSING')
            closed.add(key);credits+=payout;realized+=payout-groups[key][1]-groups[key][2]
        positions=[];basis=Fraction()
        for key,g in sorted(groups.items()):
            if key in closed:continue
            if not g[0] and (g[1] or g[2]):raise Refusal('EMPTY_POSITION_WITH_BASIS')
            if g[0]:
                basis+=g[1]+g[2]
                positions.append(dict(venue=key[0],market=key[1],token=key[2],quantity=g[0],costExact=str(g[1]),feeExact=str(g[2])))
        reserve=0;states={}
        if installed:
            for op in rows(db,'SELECT * FROM app_buy_operations ORDER BY seq'):
                states[op['state']]=states.get(op['state'],0)+1
                if op['state'] in ACTIVE:reserve+=op['cost']+op['fee']
                if op['state']=='finalized':
                    row=db.execute('SELECT venue,id,market,token,quantity,cost,fee,debit FROM events WHERE seq=?',(op['legacy_seq'],)).fetchone()
                    expected=(op['venue'],op['legacy_id'],op['market'],op['token'],op['quantity'],op['cost'],op['fee'],op['cost']+op['fee'])
                    if row!=expected:raise Refusal('MATERIALIZATION_MISMATCH')
        cash=policy['opening']-spent+credits
        if cash-reserve<0 or cash+basis!=policy['opening']+realized:raise Refusal('CASH_BASIS_CONSERVATION_FAILED')
        result=dict(legacy=legacy_digest(db),policy=policy,legacyCash=cash,reserved=reserve,available=cash-reserve,
                    confirmedBasisExact=str(basis),realizedPnlExact=str(realized),positions=positions,journalStates=states,
                    conservation=True)
        if own:db.commit()
        return result
    except BaseException:
        if own:db.rollback()
        raise
