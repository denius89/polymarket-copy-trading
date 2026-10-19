from pathlib import Path
import json,subprocess,concurrent.futures,time,datetime,re,sys
BASE=Path('/private/tmp/cct-deep-vb6rjvhh'); CWD=Path('/Users/denisfedko/.codex/.chatgpt-projects/g-p-6ab3bea8f0208191ada58dd99e906e49'); OUT=BASE/'discovery/actual-parent';OUT.mkdir(exist_ok=True)
data=json.loads((BASE/'discovery-queries.json').read_text());keys=json.loads((BASE/'discovery-query-oracles.json').read_text())['oracles']
data['cases']=data['cases'][:1]
ids={r['id'] for r in data['cases']}
assert ids<=set(keys)
def run(case):
 cid=case['id'];p=OUT/cid;p.mkdir(exist_ok=True)
 prompt=case['prompt']+'\nОтветь кратко, до 150 слов. Используй только предоставленные факты и применимые локальные инструкции. Не обращайся к сети, не изменяй файлы и не выполняй внешних действий.'
 (p/'prompt.txt').write_text(prompt)
 cmd=['codex','-a','never','exec','--ephemeral','--json','--ignore-user-config','--skip-git-repo-check','-s','read-only','-C',str(CWD),prompt]
 start=time.monotonic()
 try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
 except subprocess.TimeoutExpired as e:
  (p/'trace.jsonl').write_text((e.stdout or b'').decode() if isinstance(e.stdout,bytes) else e.stdout or '')
  result={'id':cid,'status':'not_verified','reason':'timeout','seconds':time.monotonic()-start};(p/'result.json').write_text(json.dumps(result,indent=2));return result
 (p/'trace.jsonl').write_text(r.stdout);(p/'stderr.log').write_text(r.stderr)
 events=[]
 for line in r.stdout.splitlines():
  try:events.append(json.loads(line))
  except json.JSONDecodeError:pass
 loaded=set();commands=[];usage=[];messages=[]
 for event in events:
  if event.get('type')=='turn.completed':usage.append(event.get('usage'))
  item=event.get('item',{})
  if event.get('type')=='item.completed' and item.get('type')=='agent_message':messages.append(item.get('text',''))
  if event.get('type')=='item.completed' and item.get('type')=='command_execution':
   command=item.get('command','');commands.append({'command':command,'exit_code':item.get('exit_code')})
   if item.get('exit_code')==0 and re.search(r'\b(cat|sed|head|tail|read_text|Get-Content)\b',command):loaded.update(re.findall(r'(cct-[a-z0-9-]+)/SKILL\.md',command))
 oracle=keys[cid];expected=set(oracle['expected_any']);should=oracle['should_activate'];ok=bool(loaded&expected) if should else not loaded
 status=('pass' if ok else 'fail') if r.returncode==0 else 'not_verified'
 result={'id':cid,'returncode':r.returncode,'status':status,'expected_any':sorted(expected),'should_activate':should,'observed_skill_file_reads':sorted(loaded),'commands':commands,'usage':usage,'seconds':round(time.monotonic()-start,2),'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'meaning':'Observed native implicit SKILL.md read, not semantic quality or Desktop UI parity'}
 (p/'answer.md').write_text('\n\n'.join(messages)+'\n');(p/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 fs=[pool.submit(run,c) for c in data['cases']]
 for f in concurrent.futures.as_completed(fs):
  r=f.result();print(json.dumps({k:r.get(k) for k in ['id','status','observed_skill_file_reads','seconds','reason']},ensure_ascii=False),flush=True)
results=[json.loads((OUT/c['id']/'result.json').read_text()) for c in data['cases']]
(OUT/'summary.json').write_text(json.dumps({'results':results,'counts':{s:sum(r['status']==s for r in results) for s in ['pass','fail','not_verified']}},ensure_ascii=False,indent=2)+'\n')
print('COMPLETE',json.dumps({s:sum(r['status']==s for r in results) for s in ['pass','fail','not_verified']}),flush=True)
