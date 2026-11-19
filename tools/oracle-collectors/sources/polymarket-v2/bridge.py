"""Shared-demo bridge. No personal PG, no venue writes, no hidden database init."""
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import ExitStack
import copy
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
from queue import Queue, Empty, Full
import sqlite3
import tempfile
import threading
import time
import datetime as dt
from zoneinfo import ZoneInfo

import legacy_worker as legacy
from book_engine import GateSkip
import pm_provenance as rtds_provenance
from follow_policy import LABELS, NEW_LIMITLESS, approved_follows, label as follow_label

WARSAW = ZoneInfo('Europe/Warsaw')
VENUES = frozenset(('polymarket','limitless'))

class BridgeRefusal(Exception): pass
class WriterUnavailable(Exception): pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def exact(value):
    if not isinstance(value,dict) or set(value)!={'n','d'}: raise BridgeRefusal('INVALID_Q')
    result=Fraction(int(value['n']),int(value['d']))
    if value!={'n':str(result.numerator),'d':str(result.denominator)}: raise BridgeRefusal('INVALID_Q')
    return result


def micros(value):
    result=exact(value)*1_000_000
    if result.denominator!=1 or not 0<=result.numerator<=2**53-1: raise BridgeRefusal('MICRO_PRECISION')
    return result.numerator


def command_for(event):
    block=event['chain']['blockHash'] if event['venue']=='limitless' else None
    return 'buy:'+digest([event['venue'],event['executionId'],block])


def metadata_check(metadata,venue,event=None):
    m=copy.deepcopy(metadata)
    required={'venue','wallet','slug','condition','token','outcomeTitle','marketTitle','sourceTimestampMs'}
    if not required<=set(m) or m['venue']!=venue or venue not in VENUES: raise BridgeRefusal('SOURCE_METADATA')
    if not isinstance(m['wallet'],str) or (venue,m['wallet'].lower()) not in LABELS: raise BridgeRefusal('FOLLOW_SCOPE')
    if not all(isinstance(m[k],str) and 0<len(m[k])<=1000 for k in ('slug','condition','token','outcomeTitle','marketTitle')):
        raise BridgeRefusal('SOURCE_METADATA')
    if type(m['sourceTimestampMs']) is not int: raise BridgeRefusal('SOURCE_METADATA')
    m['wallet']=m['wallet'].lower()
    if event is not None:
        if (event['venue'],event['side'],event['marketId'],event['outcomeId'],event['signalAtMs']) != (venue,'BUY',m['condition'],m['token'],m['sourceTimestampMs']):
            raise BridgeRefusal('SOURCE_BINDING')
        if venue=='polymarket' and event['venueReceipt']['match']['wallet']!=m['wallet']: raise BridgeRefusal('SOURCE_BINDING')
    return m


def public_body(metadata,event,estimate,now_ms):
    m=metadata_check(metadata,event['venue'],event)
    evidence=estimate['evidence']
    quantity,cost,fee=(micros(evidence[k]) for k in ('quantity','gross','cashFee'))
    if quantity<=0 or cost<=0 or cost+fee>legacy.BUY: raise BridgeRefusal('BUY_BUDGET')
    # Decimal is UI-only. Exact amounts and price fills remain in private estimate.
    with localcontext() as context:
        context.prec=40
        price=format(Decimal(cost)/Decimal(quantity),'f')
    chain=event['chain']
    tx=chain['transactionHash'] if chain else event['venueReceipt']['match']['transactionHash']
    body=dict(id=event['executionId'],venue=event['venue'],side='BUY',wallet=m['wallet'],
              at=event['signalAtMs']//1000,slug=m['slug'],condition=m['condition'],token=m['token'],
              market=m['marketTitle'],outcome=m['outcomeTitle'],trader=follow_label(event['venue'],m['wallet']),
              recordedAt=dt.datetime.fromtimestamp(now_ms/1000,dt.UTC).isoformat(),quantity=quantity,
              cost=cost,fee=fee,price=price,tx=tx,
              day=dt.datetime.fromtimestamp(now_ms/1000,WARSAW).date().isoformat())
    body['positionMarket']=legacy.position_market(body)
    aliases=[event['executionId']]
    if event['venue']=='polymarket':
        raw=tx+':'+m['token']
        aliases+=[raw if m['wallet']==legacy.LEGACY_WALLETS[event['venue']] else m['wallet']+':'+raw]
    extra=m.get('legacyIds',[])
    if not isinstance(extra,list) or len(extra)>8 or any(not isinstance(x,str) or not 0<len(x)<=256 for x in extra):
        raise BridgeRefusal('LEGACY_ALIASES')
    return body,sorted(set(aliases+extra))


def verify_limitless(metadata,event,estimate):
    """Reuse pinned pure receipt decoder; never perform an RPC from the writer."""
    import source
    proof=estimate['evidence'].get('sourceProof')
    if not isinstance(proof,dict):raise BridgeRefusal('BASE_SOURCE_PROOF_REQUIRED')
    log,receipt=proof.get('sourceLog'),proof.get('sourceReceipt')
    if not isinstance(log,dict) or not isinstance(receipt,dict):raise BridgeRefusal('BASE_SOURCE_PROOF_REQUIRED')
    chain=event['chain'];topics=log['topics'];values=source.words(log['data'])
    market=source.Market('limitless',event['marketId'],event['outcomeId'],metadata['wallet'],metadata['slug'],log['address'].lower())
    if (log.get('removed') or len(topics)!=4 or topics[0]!=source.MATCH or
        topics[2]!=source.address_topic(market.wallet) or topics[3]!=f'0x{int(market.token):064x}' or
        len(values)!=8 or values[0]!=0 or min(values[2:4])<=0 or
        log['transactionHash']!=chain['transactionHash'] or log['blockHash']!=chain['blockHash'] or
        int(log['blockNumber'],16)!=chain['blockNumber'] or int(log['logIndex'],16)!=chain['logIndex'] or
        not source.receipt_matches(log,receipt,market)):
        raise BridgeRefusal('BASE_SOURCE_BINDING')
    fields=[chain['transactionHash'],topics[1],market.fee_module,market.wallet.lower(),
            market.market,market.token,'BUY',*values[:5]]
    fp=hashlib.sha256(json.dumps(fields,separators=(',',':')).encode()).hexdigest()
    if event['executionId']!=f"base:8453:{chain['transactionHash']}:{topics[1]}" or event['fingerprint']!=fp:
        raise BridgeRefusal('BASE_SOURCE_IDENTITY')


class BoundAdapter:
    """Compatibility with private closed route; scope is shared feed, never a login."""
    def __init__(self,runtime,venue,metadata=None):
        self.runtime,self.venue,self.metadata=runtime,venue,metadata
    def bind(self,metadata):
        scoped=metadata_check(metadata,self.venue)
        self.runtime.require_follow(self.venue,scoped['wallet'])
        return BoundAdapter(self.runtime,self.venue,scoped)
    def lookup_command(self,db,session_id,owner_id,command_id,request=None,*,event=None):
        if event is None: raise BridgeRefusal('EVENT_REQUIRED')
        if self.metadata is not None:metadata_check(self.metadata,self.venue,event)
        elif event['venue']!=self.venue or event['side']!='BUY':raise BridgeRefusal('SOURCE_BINDING')
        elif self.venue=='polymarket' and event['venueReceipt']['match']['wallet']!=legacy.WALLETS[self.venue].lower():raise BridgeRefusal('FOLLOW_SCOPE')
        elif self.venue=='limitless':raise BridgeRefusal('METADATA_REQUIRED')
        return self.runtime.call('lookup',command_for(event),copy.deepcopy(event))
    def submit(self,db,session_id,owner_id,command_id,event,estimate,latest_guard,now_ms=None):
        if self.metadata is None: raise BridgeRefusal('METADATA_REQUIRED')
        event,estimate=copy.deepcopy(event),copy.deepcopy(estimate)
        metadata_check(self.metadata,self.venue,event)
        return self.runtime.call('submit',command_for(event),event,estimate,copy.deepcopy(self.metadata),latest_guard)
    def pending_limitless(self):
        if self.venue!='limitless': raise BridgeRefusal('NOT_BASE')
        return self.runtime.call('pending')
    def resolve_limitless(self,execution_id,state,evidence,*,operation_id=None):
        if self.venue!='limitless': raise BridgeRefusal('NOT_BASE')
        return self.runtime.call('reconcile',execution_id,state,copy.deepcopy(evidence),operation_id)


class SharedDemoRuntime:
    """One thread/connection owns all new BUY, legacy SELL, settlement and publish."""
    def __init__(self,db_path,feed_path,storage,owner,expected_epoch,*,utc_ms=None,report=None,maintenance=True,quote_reader=None,enable_second_limitless=False):
        self.db_path,self.feed_path=Path(db_path),Path(feed_path)
        self.storage,self.owner,self.expected_epoch=storage,owner,expected_epoch
        self.utc=utc_ms or (lambda:time.time_ns()//1_000_000)
        self.report=report or (lambda value:None)
        self.maintenance=maintenance
        self.quote_reader=quote_reader
        self.follow_defs=approved_follows(enable_second_limitless)
        self.queue=Queue(maxsize=32)
        self.lifecycle_lock=threading.RLock()
        self.admission_stopped=threading.Event();self.closed=threading.Event()
        self.ready=Future();self.thread=None;self.health={v:'starting' for v in VENUES}
    def adapter(self,venue):
        if venue not in VENUES: raise BridgeRefusal('VENUE')
        return BoundAdapter(self,venue)
    def require_follow(self,venue,wallet):
        if not any(item['venue']==venue and item['wallet']==wallet.lower() for item in self.follow_defs):
            raise BridgeRefusal('FOLLOW_SCOPE')
    def following(self):return self.call('following')
    def start(self):
        if self.thread is not None: raise WriterUnavailable('ALREADY_STARTED')
        self.thread=threading.Thread(target=self._run,name='shared-demo-writer',daemon=False)
        self.thread.start();self.ready.result(timeout=10)
        return self
    def call(self,kind,*args):
        if kind=='submit' and self.admission_stopped.is_set(): raise BridgeRefusal('ADMISSIONS_STOPPED')
        result=Future()
        with self.lifecycle_lock:
            if self.closed.is_set() or self.thread is None or not self.thread.is_alive(): raise WriterUnavailable('WRITER_STOPPED')
            try:self.queue.put_nowait((kind,args,result))
            except Full:raise BridgeRefusal('WRITER_QUEUE_FULL') from None
        # No timeout-retry of a potentially committed command. The writer completes
        # every admitted future or surfaces a fatal/unknown outcome and stops.
        return result.result()
    def stop_admissions(self):
        self.admission_stopped.set()
        return self.call('stop')
    def close(self):
        if self.closed.is_set():
            if self.thread:self.thread.join(timeout=10)
            return
        self.stop_admissions()
        self.call('close')
        self.thread.join(timeout=10)
        if self.thread.is_alive():raise WriterUnavailable('WRITER_DID_NOT_STOP')
    def snapshot(self):return self.call('snapshot')
    def pending_limitless(self):return self.adapter('limitless').pending_limitless()
    def _run(self):
        db=None;active=None;resources=ExitStack()
        try:
            resources.enter_context(self.storage.process_lock(self.db_path))
            # URI mode=rw prevents silently creating/replacing the actual ledger.
            db=sqlite3.connect(self.db_path.resolve().as_uri()+'?mode=rw',uri=True,timeout=3)
            db.execute('PRAGMA synchronous=FULL')
            self.store=self.storage.claim_writer(db,self.owner,self.expected_epoch)
            self.db=db
            self._init_follows()
            self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix='legacy-public-read')
            self.quotes=self.quote_reader or legacy.PositionQuotes(self.pool)
            self.sale_poll=None;self.sale_jobs=[];self.last_poll=0;self.last_publish=0
            self.ready.set_result(True)
            while True:
                try:active=self.queue.get(timeout=.1)
                except Empty:active=None
                if active:
                    kind,args,future=active
                    try:result=self._dispatch(kind,*args)
                    except (BridgeRefusal,GateSkip,self.storage.Refusal,self.storage.AdmissionChanged) as error:future.set_exception(error)
                    else:future.set_result(result)
                    self.queue.task_done();active=None
                    if kind=='close':break
                if self.maintenance:self._tick_legacy()
        except BaseException as error:
            self.admission_stopped.set()
            if not self.ready.done():self.ready.set_exception(error)
            if active and not active[2].done():active[2].set_exception(error)
            self.report({'stage':'writer_stopped','errorType':type(error).__name__,'retry':False})
        finally:
            with self.lifecycle_lock:
                self.closed.set()
                while True:
                    try:_,_,future=self.queue.get_nowait()
                    except Empty:break
                    future.set_exception(WriterUnavailable('WRITER_STOPPED_NO_RETRY'))
            if hasattr(self,'pool'):self.pool.shutdown(wait=False,cancel_futures=True)
            if db is not None:db.close()
            resources.close()
    def _init_follows(self):
        now=(self.utc()+999)//1000
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.follow_state=[]
            for item in self.follow_defs:
                venue,wallet=item['venue'],item['wallet']
                key='started' if wallet==legacy.LEGACY_WALLETS[venue] else f'follow:{venue}:{wallet}'
                found=self.db.execute('SELECT value FROM settings WHERE name=?',(key,)).fetchone()
                if found is None:
                    if (venue,wallet)!=('limitless',NEW_LIMITLESS):raise BridgeRefusal('FOLLOW_SETTING_MISSING')
                    self.db.execute('INSERT INTO settings(name,value) VALUES(?,?)',(key,now))
                    start=now
                else:start=found[0]
                if type(start) is not int or not 0<=start<=now:raise BridgeRefusal('FOLLOW_START_INVALID')
                self.follow_state.append(dict(item,startedAt=start))
            # Disabling future BUY observation does not abandon already acquired
            # positions. A persisted approved follow remains eligible for SELL.
            self.maintenance_state=copy.deepcopy(self.follow_state)
            if not any(item['wallet']==NEW_LIMITLESS for item in self.maintenance_state):
                found=self.db.execute('SELECT value FROM settings WHERE name=?',(f'follow:limitless:{NEW_LIMITLESS}',)).fetchone()
                if found is not None:
                    if type(found[0]) is not int or not 0<=found[0]<=now:raise BridgeRefusal('FOLLOW_START_INVALID')
                    self.maintenance_state.append(dict(approved_follows(True)[-1],startedAt=found[0]))
            self.db.commit()
        except BaseException:self.db.rollback();raise
    def _dispatch(self,kind,*args):
        if kind=='following':return copy.deepcopy(self.follow_state)
        if kind=='lookup':return self.store.lookup_execution(args[1])
        if kind=='submit':
            command,event,estimate,meta,guard=args
            self.require_follow(meta['venue'],meta['wallet'])
            start=next(item['startedAt'] for item in self.follow_state if (item['venue'],item['wallet'])==(meta['venue'],meta['wallet']))
            if event['signalAtMs']<start*1000:raise BridgeRefusal('BEFORE_FOLLOW_START')
            now=self.utc();body,aliases=public_body(meta,event,estimate,now)
            parent=self
            class Guard:
                commit_lock=guard.commit_lock
                def __call__(self,retained,computed):
                    if event['venue']=='polymarket':
                        rtds_provenance.validate(retained,parent.utc())
                        rtds_provenance.validate_estimate(retained,estimate)
                    else:verify_limitless(meta,retained,estimate)
                    return guard(retained,computed)
            return self.store.submit(command,event,estimate,body,aliases,Guard(),now_ms=now)
        if kind=='pending':
            result=[]
            for item in self.store.pending_operations():
                e=item['event'];chain=e['chain']
                result.append(dict(operationId=item['operationId'],executionId=e['executionId'],event=e,
                    sourceEvent=dict(transaction=chain['transactionHash'],blockNumber=chain['blockNumber'],
                                     blockHash=chain['blockHash'],logIndex=chain['logIndex']),
                    sourceProof=item['estimate']['evidence'].get('sourceProof')))
            return result
        if kind=='reconcile':
            execution,state,evidence,operation=args
            if state not in ('finalized','reverted','held'):raise BridgeRefusal('BASE_DECISION_STATE')
            def receipt_key(op):
                fields=[op,state]
                if state=='held':fields.append(digest(evidence))
                return 'reconcile:'+digest(fields)
            if operation is not None:
                if not isinstance(operation,str) or not 0<len(operation)<=256:raise BridgeRefusal('BASE_OPERATION_ID')
                saved=self.store.lookup_reconciliation(receipt_key(operation),operation,execution)
                if saved is not None:return saved
            rows=[x for x in self.store.pending_operations() if x['event']['executionId']==execution and
                  (operation is None or x['operationId']==operation)]
            if len(rows)!=1:raise BridgeRefusal('PENDING_OPERATION_NOT_UNIQUE')
            operation=rows[0]['operationId']
            chain=rows[0]['event']['chain']
            providers=evidence.get('providers')
            if not isinstance(providers,list) or len(providers)!=2 or len(set(providers))!=2:raise BridgeRefusal('BASE_PROVIDERS')
            checked=evidence.get('checkedAtMs')
            if type(checked) is not int or not rows[0]['event']['firstSeenMs']<=checked<=self.utc():raise BridgeRefusal('BASE_CHECK_TIME')
            if not evidence.get('evidenceRef'):raise BridgeRefusal('BASE_EVIDENCE')
            finalized=False
            if state=='finalized':
                heights=evidence.get('finalizedHeights')
                finalized=(isinstance(heights,list) and len(heights)==2 and all(type(n) is int and n>=chain['blockNumber'] for n in heights))
                if not finalized or evidence.get('receiptMatchesOriginal') is not True:raise BridgeRefusal('BASE_FINALITY_NOT_PROVEN')
            if state=='reverted' and evidence.get('receiptPresent') is not False:raise BridgeRefusal('BASE_REORG_NOT_PROVEN')
            decision=dict(state=state,rpcBlockHashes=evidence.get('rpcBlockHashes'),
                          executionPresent=evidence.get('receiptMatchesOriginal') is True if state=='finalized' else evidence.get('receiptPresent') is True,
                          finalized=finalized,evidence=evidence)
            return self.store.reconcile(receipt_key(operation),operation,decision,now_ms=self.utc())
        if kind=='stop':return self.store.stop_admissions()
        if kind=='snapshot':return self._snapshot()
        if kind=='legacy_sale':
            event,result=args
            if event.get('side')!='SELL':raise BridgeRefusal('LEGACY_BUY_DISABLED')
            if not any((item['venue'],item['wallet'])==(event['venue'],event['wallet'].lower()) for item in self.maintenance_state):raise BridgeRefusal('FOLLOW_SCOPE')
            self.store.legacy_guard(event['venue'],legacy.position_market(event),event['token'],'sale')
            return legacy.record(self.db,event,result)
        if kind=='close':
            self._publish()
            return self.store.fence()
        raise BridgeRefusal('UNKNOWN_WRITER_OPERATION')
    def _snapshot(self):
        outer=self
        class PendingSafeQuotes:
            def read(self,key,event):
                if any(tuple(s)==tuple(key) for s in outer.store.snapshot_overlay()['pendingScopes']):return None
                return outer.quotes.read(key,event)
        base=legacy.position_snapshot(self.db,dict(self.health),PendingSafeQuotes())
        extra=self.store.snapshot_overlay()
        base['reserved']=extra['reserved'];base['networkPurchases']=extra['networkPurchases']
        base['following']=[dict(venue=item['venue'],trader=item['label']) for item in self.follow_state]
        base['available']-=extra['reserved']
        if base['available']<0:raise BridgeRefusal('NEGATIVE_AVAILABLE')
        return base
    def _publish(self):
        state=self._snapshot();self.feed_path.parent.mkdir(parents=False,exist_ok=True)
        name=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',dir=self.feed_path.parent,delete=False) as f:
                name=f.name;json.dump(state,f,ensure_ascii=False,allow_nan=False)
                f.flush();os.fchmod(f.fileno(),0o644);os.fsync(f.fileno())
            os.replace(name,self.feed_path)
            directory=os.open(self.feed_path.parent,os.O_RDONLY)
            try:os.fsync(directory)
            finally:os.close(directory)
        finally:
            if name:Path(name).unlink(missing_ok=True)
        return state
    def _tick_legacy(self):
        now=time.monotonic()
        if self.sale_poll is None and not self.sale_jobs and now-self.last_poll>=5:
            def read_sales():
                out=[]
                for item in self.maintenance_state:
                    venue,wallet=item['venue'],item['wallet']
                    try:
                        rows=legacy.poly_signals() if venue=='polymarket' else legacy.limitless_signals(wallet)
                        out.append((venue,wallet,[e for e in rows if e.get('side')=='SELL'],None))
                    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as error:out.append((venue,wallet,[],type(error).__name__))
                return out
            self.sale_poll=self.pool.submit(read_sales);self.last_poll=now
        if self.sale_poll is not None and self.sale_poll.done():
            polled=self.sale_poll.result()
            for venue in VENUES:self.health[venue]='unavailable' if any(error for v,_,_,error in polled if v==venue) else 'ok'
            for venue,source_wallet,rows,error in polled:
                for event in reversed(rows):
                    event=copy.deepcopy(event)
                    wallet=event['wallet'].lower()
                    if wallet!=source_wallet:continue
                    key='started' if wallet==legacy.LEGACY_WALLETS[venue] else f'follow:{venue}:{wallet}'
                    start=self.db.execute('SELECT value FROM settings WHERE name=?',(key,)).fetchone()
                    if start is None:raise BridgeRefusal('FOLLOW_SETTING_MISSING')
                    if event['at']<start[0]:continue
                    if wallet!=legacy.LEGACY_WALLETS[venue]:event['id']=wallet+':'+event['id']
                    if self.db.execute('SELECT 1 FROM events WHERE venue=? AND id=? UNION ALL SELECT 1 FROM sales WHERE venue=? AND id=?',(venue,event['id'],venue,event['id'])).fetchone():continue
                    if any(e['venue']==venue and e['id']==event['id'] for e,_ in self.sale_jobs):continue
                    if not 0<=time.time()-event['at']<=30:
                        legacy.record(self.db,event,{'reason':'signal_age'});continue
                    if not self.db.execute('SELECT 1 FROM events WHERE venue=? AND market=? AND debit>0 AND json_extract(body,\'$.outcome\')=? LIMIT 1',(venue,legacy.position_market(event),event['outcome'])).fetchone():
                        legacy.record(self.db,event,{'reason':'no_position'});continue
                    self.sale_jobs.append((event,self.pool.submit(legacy.evaluate_sell,event)))
            self.sale_poll=None
        # Preserve chain ordering across a complete batch, not completion order
        # of concurrent public quote/proof reads.
        ready=[]
        if self.sale_jobs and all(job.done() for _,job in self.sale_jobs):
            ready=[(event,job.result()) for event,job in self.sale_jobs]
            self.sale_jobs=[]
        ready.sort(key=lambda pair:(pair[0]['at'],pair[1].get('sequence',(0,0))))
        for event,result in ready:
            scope=(event['venue'],legacy.position_market(event),event['token'])
            if scope in {tuple(s) for s in self.store.snapshot_overlay()['pendingScopes']}:
                result={'reason':'network_pending'}
            legacy.record(self.db,event,result)
        if now-self.last_publish>=5:self._publish();self.last_publish=now
