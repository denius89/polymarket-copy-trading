import subprocess,json,re
from pathlib import Path
roots=[Path('/Users/denisfedko/.codex/.chatgpt-projects/g-p-6ab3bea8f0208191ada58dd99e906e49'),Path('/Users/denisfedko/.codex/.chatgpt-projects/g-p-6ab3bea8f0208191ada58dd99e906e49/polymarket-copy-trading'),Path('/private/tmp/cct-deep-vb6rjvhh/discovery/replica')]
results=[]
for root in roots:
 r=subprocess.run(['codex','debug','prompt-input','Skill discovery inspection only'],cwd=root,capture_output=True,text=True)
 if r.returncode:results.append({'cwd':str(root),'returncode':r.returncode,'error':r.stderr[-300:]});continue
 data=json.loads(r.stdout)
 def strings(x):
  if isinstance(x,str):yield x
  elif isinstance(x,list):
   for v in x:yield from strings(v)
  elif isinstance(x,dict):
   for v in x.values():yield from strings(v)
 lines=[line for t in strings(data) for line in t.splitlines() if re.search(r'^- cct-[\w-]+:',line)]
 results.append({'cwd':str(root),'returncode':0,'discovered_cct_skill_lines':lines,'count':len(lines)})
Path('/private/tmp/cct-deep-vb6rjvhh/discovery/metadata-before.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps([{'cwd':v['cwd'],'count':v.get('count'),'error':v.get('error')} for v in results],ensure_ascii=False,indent=2))
