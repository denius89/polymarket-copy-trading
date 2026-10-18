"""Cross-file design evidence checks; no runtime acceptance implied."""
from pathlib import Path
import json, collections, re, urllib.parse
P=Path(__file__).parent; R=P.resolve().parents[3]; A=R/'docs/design/admin'
load=lambda p:json.loads(p.read_text())
pairs=load(P/'screen-pairs.json'); data=load(P/'screen-content.json')
assert len(pairs)==len(data)==42
s=load(A/'sitemap.json');assert s['revision']=='0.23' and s['counts']=={'ru':689,'en':689}
for p in pairs:
    sec=next(x for x in s['sections'] if x['id']==p['section'])
    x=next(x for x in sec['screens'] if x['key']==p['key'])
    assert x['id']==p['ru'] and x['english']['id']==p['en']
q=load(A/'requirements-coverage-2026-10-16/requirements.json')
assert dict(collections.Counter(x['status'] for x in q))=={'готово':91,'частично':13,'отложено':6}
assert all(next(x for x in q if x['id']==i)['status']=='готово' for i in ['D02','D03','L03'])
assert all(next(x for x in q if x['id']==i)['status']=='частично' for i in ['T05','E04','X01','X04','B04'])
g=load(A/'review-guide-2026-10-13/guide-source.json')
assert sum(x['style']=='HEADING_2' for x in g['paras'])==684
gs=load(P/'guide-sync.json')
assert gs['cards']==684 and gs['missingHeadings']==gs['missingLinks']==0 and gs['verifiedNewLinks']==84
qa=load(P/'figma-qa.json')
for locale in ['ru','en']:
    assert not qa[locale]['errors'] and len(qa[locale]['screens'])==42 and qa[locale]['rootsPerLocale']==689
    assert qa[locale]['fontFamilies']==['Inter']
    assert all(not s['placeholder'] and not s['images'] and len(s['header'])==3 for s in qa[locale]['screens'])
    assert {x['id'] for x in qa[locale]['screens']}=={p[locale] for p in pairs}
m=load(P/'manual-checks.json')['checks']
assert len(m)>=5 and all(x['result']=='pass' for x in m)
assert {x['locale'] for x in m}=={'ru','en'}
files=list(P.iterdir())+[A/n for n in ['README.md','STYLE_GUIDE.md','ui-kit/README.md','sitemap.md','requirements-coverage-2026-10-16/README.md','requirements-coverage-2026-10-16/matrix.md','review-new-skills-2026-10-18/REPORT.md']]+[R/'docs'/n for n in ['115_admin_console_technical_specification_2026-10-09.md','118_admin_console_figma_design_brief_2026-10-09.md']]
links=0;images=[]
for p in files:
    if p.suffix=='.json':load(p)
    if p.suffix=='.md':
        text=p.read_text();assert text.endswith('\n')
        if p.parent==P: assert not any(l.endswith((' ','\t')) for l in text.splitlines())
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            if target.startswith('#') or re.match(r'[a-z][a-z0-9+.-]*:',target,re.I):continue
            path=urllib.parse.unquote(target.split('#')[0].split('?')[0].strip('<>'))
            # This output is generated only after the checks below pass.
            if (p.parent/path).resolve()==(P/'handoff-checks.json').resolve(): continue
            assert (p.parent/path).exists(),(str(p),path)
            links+=1
    if p.suffix=='.png':
        b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n' and b[-8:]==b'IEND\xaeB`\x82'
        images.append(p.name)
assert len(images)==6
repo=load(P/'repository-checks.json')
repo_ok=repo['diffWhitespaceExitCode']==0 and repo['scopedLinkErrors']==0
out={'pass':repo_ok,'scope':'Static synthetic design handoff, not product acceptance','pairedStates':42,'rootsPerLocale':689,'mainStatesPerLocale':684,'nativeVisibleLinks':sum(x['links'] for loc in qa.values() for x in loc['screens']),'manualTransitions':len(m),'relativeLinksChecked':links,'images':sorted(images),'coverageClosed':['D02','D03','L03'],'improvedNotClosed':['T05','E04'],'fullAcceptance':False}
(P/'handoff-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
assert repo_ok, 'Re-run repository check after creating this report; no false pass is recorded'
