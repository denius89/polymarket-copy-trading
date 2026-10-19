"""Bounded additional public discovery; never infer absence from a sample."""
import asyncio,json
from collect_public import OUT,REQ,get,projection,capture

async def main():
    if (OUT/'alternate-discovery.json').exists():raise RuntimeError('preserve prior evidence')
    poly=get('polymarket-newest','https://gamma-api.polymarket.com/markets/keyset?closed=false&limit=25&order=id&ascending=false',False)
    prows=[projection(x,'polymarket') for x in (poly or {}).get('markets',[])]
    limrows=[]
    for page in [2,3]:
        rows=get('limitless-page-'+str(page),'https://api.limitless.exchange/markets/active?limit=25&page='+str(page),False)
        limrows += [projection(x,'limitless') for x in (rows or {}).get('data',[])]
    selected=[]
    row=next((r for r in prows if r['version']=='v2' and r.get('positionIds')),None)
    if row:
        asset=str(row['positionIds'][0]);label='polymarket-v2'
        book=get(label+'-book','https://clob.polymarket.com/book?token_id='+asset)
        get(label+'-market','https://clob.polymarket.com/clob-markets/'+row['conditionId'])
        selected.append({'id':label,'venue':'polymarket','assetId':asset,'conditionId':row['conditionId'],'bookAvailable':book is not None})
    row=next((r for r in limrows if r['tradeType']=='clob' and (r.get('venue') or {}).get('feeModuleType')=='COLLATERAL'),None)
    if row:
        label='limitless-collateral';book=get(label+'-book','https://api.limitless.exchange/markets/'+row['slug']+'/orderbook')
        selected.append({'id':label,'venue':'limitless','marketSlug':row['slug'],'yesToken':(row['tokens'] or {}).get('yes'),'bookAvailable':book is not None,'metadata':row['metadata'],'venueData':row['venue']})
    streams=await asyncio.gather(*(capture(p) for p in selected))
    (OUT/'alternate-discovery.json').write_text(json.dumps({'polymarket':prows,'limitless':limrows,'selected':selected,'streams':streams,'requests':REQ},indent=2)+'\n')
    print({'polyV2Observed':sum(r['version']=='v2' for r in prows),'collateralObserved':sum((r.get('venue') or {}).get('feeModuleType')=='COLLATERAL' for r in limrows),'profilesCaptured':[p['id'] for p in selected]})
if __name__=='__main__':asyncio.run(main())
