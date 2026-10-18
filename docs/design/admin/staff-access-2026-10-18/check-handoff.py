"""Static handoff consistency only. Native and manual evidence have separate limits."""
from pathlib import Path
import json,re,csv,collections,urllib.parse
P=Path(__file__).parent;R=P.resolve().parents[3];A=R/'docs/design/admin';load=lambda p:json.loads(p.read_text())
D=load(P/'screen-content.json');pairs=load(P/'screen-pairs.json');assert len(D)==len(pairs)==29
assert len({x['ru'] for x in pairs})==len({x['en'] for x in pairs})==29
s=load(A/'sitemap.json');assert s['revision']=='0.22' and s['counts']=={'ru':647,'en':647};assert sum(len(x['screens']) for x in s['sections'])==642
for p in pairs:
 sec=next(x for x in s['sections'] if x['id']==p['section']);x=next(x for x in sec['screens'] if x['key']==p['key']);assert x['id']==p['ru'] and x['english']['id']==p['en']
q=load(A/'requirements-coverage-2026-10-16/requirements.json');assert dict(collections.Counter(x['status'] for x in q))=={'готово':88,'частично':15,'отсутствует':1,'отложено':6}
assert all(next(x for x in q if x['id']==id)['status']=='готово' for id in ['G06','B02','A02']);assert next(x for x in q if x['id']=='X01')['status']=='частично'
g=load(A/'review-guide-2026-10-13/guide-source.json');assert sum(x['style']=='HEADING_2' for x in g['paras'])==642
assert load(P/'guide-sync.json')['cards']==642 and load(P/'guide-sync.json')['missingParagraphs']==0
qa=load(P/'figma-qa.json')
for locale in ['ru','en']:
 assert not qa[locale]['errors'] and len(qa[locale]['screens'])==29 and qa[locale]['rootsPerLocale']==647
 assert qa[locale]['fontFamilies']==['Inter'] and all(not s['placeholder'] and not s['images'] for s in qa[locale]['screens'])
 assert {x['id'] for x in qa[locale]['screens']}=={p[locale] for p in pairs}
assert sum(x['visibleLinks'] for loc in qa.values() for x in loc['screens'])==298
m=load(P/'manual-checks.json')['checks'];assert len(m)==18 and all(x['result']=='pass' for x in m);assert collections.Counter(x['locale'] for x in m)=={'ru':12,'en':6}
with (P/'sample-access-export.csv').open(newline='') as f:
 rows=list(csv.reader(f));assert len(rows)==3 and len(rows[0])==6 and all(len(r)==6 for r in rows)
 assert all(r[-2:]==['Polymarket','demo'] for r in rows[1:]);assert not any('0x' in c or '$' in c for r in rows for c in r)
files=list(P.iterdir())+[A/n for n in ['README.md','STYLE_GUIDE.md','ui-kit/README.md','sitemap.md','requirements-coverage-2026-10-16/README.md','requirements-coverage-2026-10-16/matrix.md','review-new-skills-2026-10-18/REPORT.md']]+[R/'docs'/n for n in ['115_admin_console_technical_specification_2026-10-09.md','118_admin_console_figma_design_brief_2026-10-09.md']]
links=0;images=[]
for p in files:
 if p.suffix=='.json':load(p)
 if p.suffix=='.md':
  text=p.read_text();assert text.endswith('\n');assert p.parent!=P or not any(l.endswith((' ','\t')) for l in text.splitlines())
  for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
   if target.startswith('#') or re.match(r'[a-z][a-z0-9+.-]*:',target,re.I):continue
   path=urllib.parse.unquote(target.split('#')[0].split('?')[0].strip('<>'));assert (p.parent/path).exists(),(str(p),path);links+=1
 if p.suffix=='.png':
  b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n' and b[-8:]==b'IEND\xaeB`\x82';images.append(p.name)
assert len(images)==7
repo=load(P/'repository-checks.json');assert repo['diffWhitespaceExitCode']==0 and repo['scopedLinkErrors']==0
out={'pass':True,'scope':'Static synthetic design handoff, not product authorization','pairedStates':29,'rootsPerLocale':647,'mainStatesPerLocale':642,'nativeVisibleLinks':298,'manualTransitions':18,'relativeLinksChecked':links,'images':sorted(images),'coverageClosed':['G06','B02','A02'],'fullAcceptance':False}
(P/'handoff-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
