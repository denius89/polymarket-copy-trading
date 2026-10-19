"""Bounded public range audit; hard 20 MB transfer cap; no execution/trading."""
import io,json,urllib.request,urllib.error,hashlib,time
from pathlib import Path
import pyarrow.parquet as pq
P=Path(__file__).resolve().parent
URL='https://dl.pendulumflow.com/pmxt/v1/polymarket_orderbook_2026-03-01T00.parquet'
SIZE=621439015
class Remote(io.RawIOBase):
 def __init__(self): self.pos=0; self.used=0; self.calls=[]
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,off,whence=0):
  self.pos=off if whence==0 else self.pos+off if whence==1 else SIZE+off
  return self.pos
 def read(self,n=-1):
  if n<0:n=SIZE-self.pos
  n=min(n,SIZE-self.pos)
  if not n:return b''
  if self.used+n>20_000_000:raise RuntimeError(f'20MB cap: used={self.used},next={n}')
  a=self.pos;b=a+n-1
  parts=[]
  for start in range(a,b+1,512000):
   end=min(b,start+511999)
   cache=P/'pmxt-range-cache'/f'{start}-{end}.bin';cache.parent.mkdir(exist_ok=True)
   if cache.exists(): part=cache.read_bytes()
   else:
    req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{end}'})
    for attempt in range(5):
     try:
      time.sleep(2 if attempt==0 else 5*attempt)
      with urllib.request.urlopen(req,timeout=45) as response:
       assert response.status==206,(response.status,dict(response.headers))
       part=response.read(end-start+2);assert len(part)==end-start+1
      cache.write_bytes(part);break
     except (urllib.error.HTTPError,TimeoutError) as e:
      if (hasattr(e,'code') and e.code not in (429,503,520,502,504)) or attempt==4:raise
      print('backoff',str(e),attempt,flush=True)
    self.used+=len(part)
   parts.append(part)
  raw=b''.join(parts);self.pos+=n;self.calls.append({'start':a,'end':b,'bytes':n,'sha256':hashlib.sha256(raw).hexdigest()})
  return raw
r=Remote();f=pq.ParquetFile(r)
meta={'url':URL,'size':SIZE,'schema':str(f.schema_arrow),'rows':f.metadata.num_rows,'row_groups':f.num_row_groups,'groups':[]}
for i in range(f.num_row_groups):
 g=f.metadata.row_group(i);meta['groups'].append({'id':i,'rows':g.num_rows,'columns':[{'name':g.column(j).path_in_schema,'bytes':g.column(j).total_compressed_size,'stats':str(g.column(j).statistics)} for j in range(g.num_columns)]})
(P/'pmxt-parquet-metadata.json').write_text(json.dumps(meta,indent=2));print(json.dumps({k:v for k,v in meta.items() if k!='groups'},indent=2),flush=True)
print('first groups',[(g['id'],g['rows'],sum(c['bytes'] for c in g['columns'])) for g in meta['groups'][:5]],flush=True)
gid=min(range(f.num_row_groups),key=lambda i:sum(c['bytes'] for c in meta['groups'][i]['columns']))
g=f.read_row_group(gid);pq.write_table(g,P/'pmxt-bounded-rowgroup.parquet'); rows=g.to_pylist();examples=[];counts={}
for row in rows:
 typ=row['update_type'];counts[typ]=counts.get(typ,0)+1
 if len(examples)<4 and typ=='book_snapshot':
  x={k:(v.isoformat() if hasattr(v,'isoformat') else v) for k,v in row.items()};x['data']=json.loads(x['data']);examples.append(x)
(P/'pmxt-bounded-summary.json').write_text(json.dumps({'url':URL,'rowgroup':gid,'rows':len(rows),'event_counts':counts,'examples':examples,'bytes_transferred':r.used,'range_requests':r.calls},indent=2));print('sample',gid,len(rows),counts,'bytes',r.used,flush=True)
