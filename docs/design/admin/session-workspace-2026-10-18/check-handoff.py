"""Static package consistency; native evidence and manual passes remain separately scoped."""
from pathlib import Path
import json,re,collections,urllib.parse
P=Path(__file__).parent;R=P.resolve().parents[3];A=R/'docs/design/admin';load=lambda p:json.loads(p.read_text())
pairs=load(P/'screen-pairs.json');data=load(P/'screen-content.json');assert len(pairs)==len(data)==17
assert len({x['ru'] for x in pairs})==len({x['en'] for x in pairs})==17
s=load(A/'sitemap.json');assert s['revision']=='0.21' and s['counts']=={'ru':618,'en':618}
sec=next(x for x in s['sections'] if x['id']=='ADM-03');assert len(sec['screens'])==53
for p in pairs:
 item=next(x for x in sec['screens'] if x['key']==p['key']);assert item['id']==p['ru'] and item['english']['id']==p['en']
assert sum(len(x['screens']) for x in s['sections'])==613
q=load(A/'requirements-coverage-2026-10-16/requirements.json');assert dict(collections.Counter(x['status'] for x in q))=={'готово':85,'частично':18,'отсутствует':1,'отложено':6}
assert next(x for x in q if x['id']=='S04')['status']=='готово'
g=load(A/'review-guide-2026-10-13/guide-source.json');assert sum(p['style']=='HEADING_2' for p in g['paras'])==613
native=load(P/'figma-qa.json');assert not native['ru']['errors'] and not native['en']['errors']
for lang in ['ru','en']:
 assert len(native[lang]['screens'])==17 and native[lang]['rootsPerLocale']==618
 assert all(not x['placeholder'] for x in native[lang]['screens'])
 assert {x['id'] for x in native[lang]['screens']}=={x[lang] for x in pairs}
assert len(native['ru']['links'])==len(native['en']['links'])==127
files=list(P.glob('*'))+[R/'docs'/n for n in ['PROJECT_STATE.md','ROADMAP.md','README.md','115_admin_console_technical_specification_2026-10-09.md','118_admin_console_figma_design_brief_2026-10-09.md']]+[A/n for n in ['README.md','sitemap.md','STYLE_GUIDE.md','ui-kit/README.md','review-new-skills-2026-10-18/REPORT.md','requirements-coverage-2026-10-16/README.md','requirements-coverage-2026-10-16/matrix.md']]
checkedLinks=0;pngs=[]
for p in files:
 if p.suffix=='.json':load(p)
 if p.suffix=='.md':
  txt=p.read_text();assert txt.endswith('\n');assert p.parent!=P or not any(l.endswith(' ') or l.endswith('\t') for l in txt.splitlines()),str(p)
  for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',txt):
   if target.startswith('#'):continue
   if re.match(r'[a-z][a-z0-9+.-]*:',target,re.I):
    if 'figma.com/proto/' in target:assert urllib.parse.urlsplit(target).path.split('/')[2]=='lxPP2um7FvIbt02K8eeH4T' and not re.search(r'\s',target),(p,target)
    continue
   target=urllib.parse.unquote(target.split('#')[0].split('?')[0].strip('<>'));assert (p.parent/target).exists(),(str(p),target);checkedLinks+=1
 if p.suffix=='.png':
  b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n' and b[-8:]==b'IEND\xaeB`\x82',str(p);pngs.append(p.name)
assert len(pngs)==7,pngs
out={'date':'2026-10-18','pass':True,'scope':'Static design handoff only','pairedStates':17,'rootsPerLocale':618,'mainStatesPerLocale':613,'nativeActionLinks':254,'relativeLinksChecked':checkedLinks,'pngs':sorted(pngs),'notChecked':['server authorization and accounting','real API support','all role/RU/EN paths','client and mobile UI','runtime accessibility']}
(P/'handoff-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
