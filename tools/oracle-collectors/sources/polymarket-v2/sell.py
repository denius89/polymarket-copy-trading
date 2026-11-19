"""Public receipts only. Reconstruct the lead trader's pre-sale token balance."""
import json
import re
from fractions import Fraction
from urllib.request import Request, urlopen

CHAINS = {
    'polymarket': ('polygon.drpc.org', '0x4d97dcd97ec945f40cf65f87097ace5ea0476045'),
    'limitless': ('base.drpc.org', '0xc9c98965297bc527861c898329ee280632b76e18'),
}
SINGLE = '0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62'
BATCH = '0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb'

def rpc(host, method, *params):
    body = json.dumps({'id':1,'jsonrpc':'2.0','method':method,'params':params}).encode()
    req = Request(f'https://{host}', data=body,
                  headers={'Content-Type':'application/json','User-Agent':'Shadow-read-only-market-check/1'})
    with urlopen(req,timeout=4) as response:
        reply=json.loads(response.read(2_000_001))
    return reply['result']

def transfer_amount(log, token):
    data=log['data'][2:]
    if not re.fullmatch(r'[0-9a-fA-F]+',data) or len(data)%64:
        raise ValueError('invalid transfer')
    words=[int(data[i:i+64],16) for i in range(0,len(data),64)]
    if log['topics'][0]==SINGLE and len(words)==2:
        return words[1] if words[0]==token else 0
    if log['topics'][0]==BATCH and len(words)>=4:
        i,j=words[0]//32,words[1]//32
        if words[0]!=64 or words[1]%32 or not 2<=i<j<len(words):
            raise ValueError('invalid batch offsets')
        count=words[i]
        if j!=i+count+1 or words[j]!=count or j+count+1!=len(words):
            raise ValueError('invalid batch lengths')
        return sum(n for t,n in zip(words[i+1:j],words[j+1:]) if t==token)
    raise ValueError('invalid transfer kind')

def sale_fraction(event):
    host,contract=CHAINS[event['venue']]
    wallet=event['wallet'].lower()
    account='0x'+wallet[2:].rjust(64,'0')
    token=int(event['token'])
    tx=event['tx']
    receipt=rpc(host,'eth_getTransactionReceipt',tx)
    if receipt['status']!='0x1' or receipt['transactionHash'].lower()!=tx.lower():
        raise ValueError('invalid sale receipt')
    h=receipt['blockHash']
    block=receipt['blockNumber']
    sequence=int(receipt['transactionIndex'],16)
    header=rpc(host,'eth_getBlockByNumber',block,False)
    if header['hash']!=h or int(rpc(host,'eth_blockNumber'),16)<=int(block,16):
        raise ValueError('sale not confirmed')
    calldata='0x00fdd58e'+account[2:]+format(token,'064x')
    previous=rpc(host,'eth_call',{'to':contract,'data':calldata},
                 {'blockHash':header['parentHash'],'requireCanonical':True})
    pre=int(previous,16)
    logs={}
    for topics in ([ [SINGLE,BATCH],None,account ],[ [SINGLE,BATCH],None,None,account ]):
        entries=rpc(host,'eth_getLogs',{'blockHash':h,'address':contract,'topics':topics})
        for log in entries:
            if log.get('removed') or log['blockHash']!=h or log['address'].lower()!=contract:
                raise ValueError('noncanonical token transfer')
            logs[log['logIndex']]=log
    sold=0
    for log in logs.values():
        n=int(log['transactionIndex'],16)
        if n>sequence:
            continue
        _,_,sender,recipient=log['topics']
        if sender==recipient:
            continue
        amount=transfer_amount(log,token)
        if n<sequence:
            pre+=amount if recipient==account else -amount
        elif amount:
            if log['transactionHash'].lower()!=tx.lower() or recipient==account:
                raise ValueError('mixed movement in sale')
            sold+=amount
    if sold<=0 or sold>pre or sold!=event['reportedQuantity']:
        raise ValueError('sale quantity is not explained by the receipt')
    return Fraction(sold,pre),(int(block,16),sequence)
