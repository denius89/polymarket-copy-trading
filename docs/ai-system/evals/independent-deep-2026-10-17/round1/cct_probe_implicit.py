from pathlib import Path
import subprocess,json,re
root=Path('/private/tmp/cct-deep-vb6rjvhh/discovery');probe=root/'implicit-probe';probe.mkdir(exist_ok=True)
prompt='Прочитай case.md и подготовь краткую рамку текущего поручения: что допустимо сделать сейчас, какие основания актуальны и что ещё неизвестно. Ничего не меняй и не обращайся к сети. Только материалы текущей папки.'
cmd=['codex','-a','never','exec','--ephemeral','--json','--ignore-user-config','--skip-git-repo-check','-s','read-only','-C',str(root/'replica'),prompt]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
(probe/'trace.jsonl').write_text(r.stdout);(probe/'stderr.log').write_text(r.stderr);(probe/'prompt.txt').write_text(prompt)
events=[]
for line in r.stdout.splitlines():
 try:events.append(json.loads(line))
 except json.JSONDecodeError:pass
print(json.dumps({'returncode':r.returncode,'event_types':list(dict.fromkeys(e.get('type') for e in events)),'items':[{k:v for k,v in e.get('item',{}).items() if k in ['type','command','name']} for e in events if 'item' in e],'usage':[e.get('usage') for e in events if e.get('usage')]},ensure_ascii=False,indent=2))
