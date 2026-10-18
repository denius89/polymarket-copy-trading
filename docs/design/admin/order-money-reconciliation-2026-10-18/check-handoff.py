"""Static handoff checks; no app, API or monetary side effects."""
from pathlib import Path
import json,re,collections
P=Path(__file__).parent;R=P.resolve().parents[3];A=R/'docs/design/admin'
read=lambda p:json.loads(p.read_text())
pairs=read(P/'screen-pairs.json');data=read(P/'screen-content.json')
assert len(pairs)==len(data)==35
assert len({x['ru'] for x in pairs})==len({x['en'] for x in pairs})==35
s=read(A/'sitemap.json');assert s['revision']=='0.20' and s['counts']=={'ru':601,'en':601}
flat={x['key']:x for sec in s['sections'] for x in sec['screens']}
for p in pairs:assert flat[p['key']]['id']==p['ru'] and flat[p['key']]['english']['id']==p['en']
assert sum(len(x['screens']) for x in s['sections'])==596
q=read(A/'requirements-coverage-2026-10-16/requirements.json')
assert dict(collections.Counter(x['status'] for x in q))=={'готово':84,'частично':19,'отсутствует':1,'отложено':6}
g=read(A/'review-guide-2026-10-13/guide-source.json');assert sum(p['style']=='HEADING_2' for p in g['paras'])==596
structure=read(P/'figma-final-structure.json')
assert len(structure['ru']['screens'])==len(structure['en']['screens'])==35
assert not structure['ru']['errors'] and not structure['en']['errors']
assert sum(len(structure[k]['links']) for k in ['ru','en'])==164
files=list(P.glob('*'))+[R/'docs/PROJECT_STATE.md',R/'docs/ROADMAP.md',R/'docs/README.md',A/'review-new-skills-2026-10-18/REPORT.md']+[R/'docs/115_admin_console_technical_specification_2026-10-09.md',R/'docs/118_admin_console_figma_design_brief_2026-10-09.md',A/'README.md',A/'sitemap.md',A/'ui-kit/README.md',A/'requirements-coverage-2026-10-16/README.md',A/'requirements-coverage-2026-10-16/matrix.md']
links=[];pngs=[]
for p in files:
 if p.suffix=='.json':read(p)
 if p.suffix=='.md':
  for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text()):
   if re.match(r'[a-z][a-z0-9+.-]*:',target,re.I) or target.startswith('#'):continue
   target=target.split('#')[0].split('?')[0].strip('<>');assert (p.parent/target).exists(),(str(p),target);links.append(target)
 if p.suffix=='.png':
  b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n' and b[-8:]==b'IEND\xaeB`\x82',str(p);pngs.append(p.name)
out={'date':'2026-10-18','pass':True,'scope':'Static design handoff only','newPairedStates':35,'actionLinks':164,'guideCards':596,'rootCountPerLocale':601,'relativeLinksChecked':len(links),'pngs':pngs,'notChecked':['runtime ledger and idempotency','real venue capabilities','full RU/EN and role browser coverage','client UI synchronization']}
(P/'handoff-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
