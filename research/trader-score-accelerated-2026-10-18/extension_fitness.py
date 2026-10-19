"""Independent immutable hash, schema and timestamp audit of Q4 source extension."""
from pathlib import Path
import hashlib,json,sys
from datetime import date,timedelta,datetime,timezone
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 import duckdb
 c=duckdb.connect();c.execute("SET TimeZone='UTC'")
 folder=HERE/'q4-extension';manifest=json.loads((folder/'manifest.json').read_text());plan=json.loads((folder/'fetch-plan.json').read_text())
 names=[f'data/{date(2023,10,1)+timedelta(days=i):%Y_%m_%d}.parquet' for i in range(92)]
 assert sorted(e['file'] for e in manifest)==sorted(names)
 assert sorted(str(p.relative_to(folder)) for p in (folder/'data').glob('*.parquet'))==sorted(names)
 lfs={Path(e['path']).name:e['lfs']['oid'] for e in plan['files']}
 base=REPO/'research/trader-score-real-2026-10-16/polymarket/trade_archive'
 schema=c.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(base/'2024_01_01.parquet')]).fetchall()
 expected=[(v[0],v[1]) for v in schema]
 reports=[]
 for e in manifest:
  p=folder/e['file'];h=sha(p)
  assert p.stat().st_size==e['bytes'] and h==e['sha256']==lfs[p.name]
  actual=[(v[0],v[1]) for v in c.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(p)]).fetchall()]
  assert actual==expected
  stats=c.execute('''SELECT count(*),min(block_timestamp),max(block_timestamp),count(DISTINCT condition_id),
   count(*) FILTER(WHERE block_timestamp IS NULL OR condition_id IS NULL OR taker IS NULL) FROM read_parquet(?)''',[str(p)]).fetchone()
  fileday=date.fromisoformat(p.stem.replace('_','-'));lo=int(datetime.combine(fileday,datetime.min.time(),timezone.utc).timestamp())
  outside=c.execute('SELECT count(*) FROM read_parquet(?) WHERE block_timestamp<? OR block_timestamp>=?',[str(p),lo,lo+86400]).fetchone()[0]
  reports.append(dict(file=e['file'],sha256=h,bytes=e['bytes'],rows=stats[0],first_event_seconds=stats[1],last_event_seconds=stats[2],conditions=stats[3],missing_identity=stats[4],outside_filename_UTC_day=outside))
 c.read_parquet([str(folder/e['file']) for e in manifest]).create_view('q4')
 count=c.execute('SELECT count(*),count(DISTINCT condition_id),count(DISTINCT lower(taker)),min(block_timestamp),max(block_timestamp) FROM q4').fetchone()
 feb29=c.execute('SELECT min(block_timestamp),max(block_timestamp) FROM read_parquet(?)',[str(base/'2024_02_29.parquet')]).fetchone()
 out={'version':'extension-fitness-v3','result_kind':'Q4_source_extension_fitness_not_copier_return','files':92,'bytes':sum(e['bytes'] for e in manifest),'rows':count[0],'conditions':count[1],'takers':count[2],'first_event_seconds':count[3],'last_event_seconds':count[4],'missing_identity_rows':sum(e['missing_identity'] for e in reports),'out_of_filename_UTC_day_rows':sum(e['outside_filename_UTC_day'] for e in reports),'strict_standard_H30_paths':0,'verified_label_observation_times':0,'checks':{'sha256_matches_manifest_and_pinned_lfs':True,'exact_24_field_schema_matches_existing':True,'all_92_expected_files_present_no_extra_parquet':True},'base_last_file_actual_range':{'2024_02_29.parquet':list(feb29)},'partition_note':'Check actual timestamps rather than infer day boundaries from README UTC+8 claim; observed per-file UTC scope is measured here, not assumed completeness. No row-continuity proof.','file_reports':reports,'lineage':{'code_sha256':sha(Path(__file__)),'manifest_sha256':sha(folder/'manifest.json'),'fetch_plan_sha256':sha(folder/'fetch-plan.json')}}
 with (HERE/'extension-fitness-v3.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in out.items() if k!='file_reports'},indent=2))
if __name__=='__main__':run()
