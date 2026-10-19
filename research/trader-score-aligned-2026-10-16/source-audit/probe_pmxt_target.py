from pathlib import Path
import json,pyarrow.parquet as pq
BASE=Path(__file__).resolve().parent
# Reuse only bounded range reader, no side-effecting probe main.
ns={'__file__':str(BASE/'probe_pmxt_hf.py')};exec((BASE/'probe_pmxt_hf.py').read_text().split('r=Remote();')[0],ns)
ns['P']=BASE/'pmxt-target';ns['P'].mkdir(exist_ok=True)
ns['URL']=ns['URL'].replace('T00.parquet','T05.parquet');ns['SIZE']=520897053
r=ns['Remote']();f=pq.ParquetFile(r)
target='0xef76d0023b2bd8b15cbe0c33f570160722144b6b981c09c5881ac02dcfbfd880'
candidates=[]
for i in range(f.num_row_groups):
 g=f.metadata.row_group(i);st=g.column(2).statistics;tm=g.column(0).statistics
 if st and st.min<=target<=st.max:
  candidates.append({'id':i,'rows':g.num_rows,'compressed_bytes':sum(g.column(j).total_compressed_size for j in range(g.num_columns)),'min_time':tm.min.isoformat(),'max_time':tm.max.isoformat(),'min_market':st.min,'max_market':st.max})
(ns['P']/'candidate-rowgroups.json').write_text(json.dumps({'url':ns['URL'],'size':ns['SIZE'],'target_condition':target,'rule':'earliest UTC-day selected BTC market, no outcome or PnL used','candidates':candidates},indent=2));print(json.dumps(candidates,indent=2),flush=True)
import pyarrow as pa,pyarrow.compute as pc
inventory=[]
for c in candidates:
 ids=f.read_row_group(c['id'],columns=['market_id']);n=pc.sum(pc.equal(ids['market_id'],target)).as_py() or 0
 inventory.append({'id':c['id'],'target_rows':n})
print('inventory',inventory,flush=True)
(ns['P']/'target-inventory.json').write_text(json.dumps(inventory,indent=2))
choices=[]
for item in inventory:
 if not item['target_rows']:continue
 t=f.read_row_group(item['id'],columns=['market_id','timestamp_received','update_type']); t=t.filter(pc.equal(t['market_id'],target)); rr=t.to_pylist()
 lo=min(x['timestamp_received'].timestamp() for x in rr);hi=max(x['timestamp_received'].timestamp() for x in rr)
 choices.append((0 if lo<=1772343703<=hi else 1,abs(hi-1772343703),item['id'],len(rr),lo,hi))
choices.sort();print('choices',choices,flush=True)
gid=choices[0][2]
t=f.read_row_group(gid);subset=t.filter(pc.equal(t['market_id'],target));pq.write_table(subset,ns['P']/'target-events.parquet')
import hashlib
j={'url':ns['URL'],'source_file_size':ns['SIZE'],'rowgroup':gid,'rowgroup_rows':t.num_rows,'target_rows':subset.num_rows,'target_condition':target,'selected_on':'earliest diagnostic covered trade, deterministic nearest candidate rowgroup, no PnL read','bytes_transferred_current_run':r.used,'range_requests':r.calls,'derived_file':'target-events.parquet','derived_bytes':(ns['P']/'target-events.parquet').stat().st_size,'derived_sha256':hashlib.sha256((ns['P']/'target-events.parquet').read_bytes()).hexdigest()}
(ns['P']/'target-manifest.json').write_text(json.dumps(j,indent=2));print(j,flush=True)
