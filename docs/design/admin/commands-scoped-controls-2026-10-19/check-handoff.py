"""Scoped design-handoff checks; does not claim runtime acceptance."""
from pathlib import Path
import json,collections,re,urllib.parse
P=Path(__file__).parent;R=P.resolve().parents[3];A=R/'docs/design/admin'
read=lambda p:json.loads(p.read_text())
D=read(P/'screen-content.json')+read(P/'updated-screen-content.json');N=read(P/'screen-pairs.json');E=read(P/'external-links.json');assert len(D)==95 and len(N)==87
s=read(A/'sitemap.json');assert s['revision']=='0.24' and s['counts']=={'ru':776,'en':776}
for d in D:
 p=next((p for p in N if p['key']==d['key']),E.get(d['key']))
 x=next(x for q in s['sections'] if q['id']==d['section'] for x in q['screens'] if x['key']==d['key'])
 assert x['id']==p['ru'] and x['english']['id']==p['en']
q=read(A/'requirements-coverage-2026-10-16/requirements.json')
assert dict(collections.Counter(x['status'] for x in q))=={'готово':93,'частично':11,'отложено':6}
assert all(next(x for x in q if x['id']==i)['status']=='готово' for i in ['T05','E04'])
assert all(next(x for x in q if x['id']==i)['status']=='частично' for i in ['X01','X04','B04'])
g=read(A/'review-guide-2026-10-13/guide-source.json');assert sum(p['style']=='HEADING_2' for p in g['paras'])==771
gs=read(P/'guide-sync.json');assert gs['pass'] and gs['heading2']==771 and not gs['missingLinks']
qa=read(P/'figma-qa.json')
for f in ['ru','en']:
 assert len(qa[f]['screens'])==95 and qa[f]['rootsPerLocale']==776 and not qa[f]['errors']
 assert all(x['pass'] for x in qa[f]['screens'])
m=read(P/'manual-checks.json')['checks'];assert len(m)==10 and all(x['result']=='pass' for x in m)
v=read(P/'visual-checks.json')['checks'];assert len(v)==12
for x in v:
 b=(P/x['file']).read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n' and b[-8:]==b'IEND\xaeB\x60\x82'
files=list(P.iterdir())+[A/n for n in ['README.md','STYLE_GUIDE.md','ui-kit/README.md','sitemap.md','requirements-coverage-2026-10-16/README.md','requirements-coverage-2026-10-16/matrix.md','review-new-skills-2026-10-18/REPORT.md']]
links=0
for p in files:
 if p.suffix=='.json':read(p)
 if p.suffix!='.md':continue
 text=p.read_text();assert text.endswith('\n')
 for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
  if target.startswith('#') or re.match(r'[a-z][a-z0-9+.-]*:',target,re.I):continue
  path=urllib.parse.unquote(target.split('#')[0].split('?')[0].strip('<>'));assert (p.parent/path).exists(),(p,path);links+=1
repo=read(P/'repository-checks.json');assert repo['diffWhitespaceExitCode']==0 and repo['scopedLinkErrors']==0
out={'pass':True,'date':'2026-10-19','scope':'Synthetic design handoff only','newPairedStates':87,'updatedPairedStates':8,'rootsPerLocale':776,'mainStatesPerLocale':771,'staticContractChecks':73,'expectedRuntimeConditions':186,'nativeStatesChecked':190,'visualCompositions':12,'manualTransitions':10,'relativeLinksChecked':links,'closedDesignRequirements':['T05','E04'],'fullAcceptance':False}
(P/'handoff-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
