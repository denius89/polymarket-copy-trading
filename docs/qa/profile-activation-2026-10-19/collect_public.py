"""Bounded public read-only diagnostics; no wallet, signing or private API."""
import asyncio,datetime,hashlib,json,time,urllib.request,urllib.error
from pathlib import Path
import websockets,socketio

OUT=Path(__file__).resolve().parent/'evidence'
REQ=[]

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def get(name,url,save=True):
    start=time.time_ns();mono=time.monotonic_ns();rec={'id':name,'url':url,'sentAt':now(),'sentUnixNs':start}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'CCT-public-activation-audit/1.0'}),timeout=8) as resp:
            body=resp.read(3000000);data=json.loads(body,parse_float=str)
            rec.update(httpStatus=resp.status,headers={k:resp.headers[k] for k in ['Date','Age','Cache-Control'] if resp.headers.get(k)},sourceSHA256=hashlib.sha256(body).hexdigest())
    except urllib.error.HTTPError as e:rec['httpStatus']=e.code;data=None
    except Exception as e:rec['errorType']=type(e).__name__;data=None
    rec.update(receivedUnixNs=time.time_ns(),receivedAt=now(),rttMs=(time.monotonic_ns()-mono)/1e6)
    if save and data is not None:
        f=OUT/(name+'.json');f.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');rec['artifact']=f.name
    REQ.append(rec);return data


def projection(row,venue):
    fields=(['id','version','conditionId','clobTokenIds','positionIds','feesEnabled','feeSchedule','negRisk'] if venue=='polymarket'
            else ['id','slug','tradeType','venue','tokens','collateralToken','status','metadata','settings'])
    d={k:row.get(k) for k in fields}
    if venue=='limitless':
        d['metadata']={k:(d['metadata'] or {}).get(k) for k in ['fee','takerDelayMs']}
        d['settings']={k:(d['settings'] or {}).get(k) for k in ['takerDelayMs','minSize']}
    return d


def discover():
    chosen=[];polys=[];limrows=[]
    url='https://gamma-api.polymarket.com/markets/keyset?active=true&closed=false&limit=25'
    data=get('poly-discovery-0',url,False)
    rows=data.get('markets',[]) if isinstance(data,dict) else (data or [])
    polys=[projection(x,'polymarket') for x in rows]
    for version in ['v1','v2']:
        row=next((r for r in polys if r['version']==version),None)
        if row:
            ids=row['positionIds'] if version=='v2' else row['clobTokenIds']
            if isinstance(ids,str):ids=json.loads(ids)
            if ids:
                label='polymarket-'+version;asset=str(ids[0]);book=get(label+'-book','https://clob.polymarket.com/book?token_id='+asset)
                market=get(label+'-market','https://clob.polymarket.com/clob-markets/'+row['conditionId'])
                chosen.append({'id':label,'venue':'polymarket','assetId':asset,'conditionId':row['conditionId'],'bookAvailable':book is not None})
    # One bounded page, no claim of exhaustive venue discovery.
    data=get('limitless-discovery','https://api.limitless.exchange/markets/active?limit=25&page=1',False)
    limrows=[projection(x,'limitless') for x in (data or {}).get('data',[])]
    for family in ['legacy','collateral']:
        row=next((r for r in limrows if r['tradeType']=='clob' and ((r.get('venue') or {}).get('feeModuleType')=='COLLATERAL')==(family=='collateral')),None)
        if row:
            label='limitless-'+family;book=get(label+'-book','https://api.limitless.exchange/markets/'+row['slug']+'/orderbook')
            chosen.append({'id':label,'venue':'limitless','marketSlug':row['slug'],'yesToken':(row['tokens'] or {}).get('yes'),'bookAvailable':book is not None,'metadata':row['metadata'],'settings':row['settings'],'venueData':row['venue']})
    (OUT/'discovery-projection.json').write_text(json.dumps({'polymarket':polys,'limitless':limrows,'selected':chosen},indent=2)+'\n')
    return chosen

async def capture(p):
    summary={'profile':p,'sessions':[]}
    for attempt,duration in enumerate([25,15]):
        s={'attempt':attempt,'startedAt':now(),'generation':attempt,'frameCount':0,'bookCount':0};t=time.monotonic();path=OUT/(p['id']+'-session-'+str(attempt)+'.jsonl')
        with path.open('w') as f:
            def record(d):
                row={'receivedAt':now(),'receiveMonotonicNs':time.monotonic_ns(),'payload':d}
                f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush();s['frameCount']+=1
                if d.get('event_type')=='book' or 'orderbook' in d:s['bookCount']+=1
                if 'firstFrameMs' not in s:s['firstFrameMs']=(time.monotonic()-t)*1000
            try:
                if p['venue']=='polymarket':
                    async with websockets.connect('wss://ws-subscriptions-clob.polymarket.com/ws/market',open_timeout=8) as ws:
                        await ws.send(json.dumps({'assets_ids':[p['assetId']],'type':'market'}));end=time.monotonic()+duration
                        while time.monotonic()<end and s['frameCount']<500:
                            try:raw=await asyncio.wait_for(ws.recv(),timeout=min(5,max(.1,end-time.monotonic())))
                            except asyncio.TimeoutError:
                                await ws.send('PING');continue
                            if raw=='PONG':continue
                            d=json.loads(raw,parse_float=str)
                            for x in d if isinstance(d,list) else [d]:
                                if isinstance(x,dict):record(x)
                else:
                    client=socketio.AsyncClient(reconnection=False)
                    @client.on('orderbookUpdate',namespace='/markets')
                    async def update(data):
                        if s['frameCount']<500:record(data)
                    @client.on('system',namespace='/markets')
                    async def system(data):s.setdefault('system',[]).append(data)
                    try:
                        await client.connect('https://ws.limitless.exchange',transports=['websocket'],namespaces=['/markets'],wait_timeout=8)
                        await client.emit('subscribe_market_prices',{'marketSlugs':[p['marketSlug']]},namespace='/markets')
                        await asyncio.sleep(duration)
                    finally:
                        if client.connected:await client.disconnect()
                s['outcome']='completed_bounded_capture'
            except Exception as e:s.update(outcome='not_verified',errorType=type(e).__name__)
        s.update(durationMs=int((time.monotonic()-t)*1000),artifact=path.name,frameCapReached=s['frameCount']>=500);summary['sessions'].append(s)
        print(p['id'],attempt,s['frameCount'],s['outcome'],flush=True)
    return summary

async def clock_samples():
    samples=[]
    for i in range(8):
        d=await asyncio.to_thread(get,'polymarket-time-'+str(i),'https://clob.polymarket.com/time',False)
        samples.append({'value':d,'requestId':'polymarket-time-'+str(i)})
        await asyncio.sleep(.17)
    return samples

async def main():
    OUT.mkdir(exist_ok=True)
    if (OUT/'run.json').exists():raise RuntimeError('preserve prior run; choose new evidence directory')
    profiles=discover();start=now()
    results=await asyncio.gather(*(capture(p) for p in profiles),clock_samples())
    out={'startedAt':start,'finishedAt':now(),'scope':'bounded unauthenticated market data; two controlled sessions per observed family, full relevant frames until cap; not production acceptance','streams':results[:-1],'clockSamples':results[-1],'requests':REQ}
    for rec in REQ:
        if rec.get('artifact'):rec['artifactSHA256']=hashlib.sha256((OUT/rec['artifact']).read_bytes()).hexdigest()
    for p in out['streams']:
        for s in p['sessions']:s['artifactSHA256']=hashlib.sha256((OUT/s['artifact']).read_bytes()).hexdigest()
    (OUT/'run.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':asyncio.run(main())
