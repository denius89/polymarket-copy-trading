import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const j=p=>JSON.parse(fs.readFileSync(new URL(p,import.meta.url),'utf8'));
const pairs=j('state-pairs.json'),ru=j('native-language-ru.json'),en=j('native-language-en.json');
assert.equal(pairs.length,33);
const val=(x,v)=>x.type==='VARIABLE_ALIAS'?v[x.value.id]:x.type==='EXPRESSION'?(()=>{const a=x.value.expressionArguments.map(y=>val(y,v));if(x.value.expressionFunction==='EQUALS')return a[0]===a[1];throw Error(x.value.expressionFunction);})():x.value;
function run(as,v){const dest=[];for(const a of as){if(a.type==='SET_VARIABLE')v[a.variableId]=val(a.variableValue,v);else if(a.type==='NODE')dest.push(a.destinationId);else if(a.type==='CONDITIONAL'){const b=a.conditionalBlocks.find(b=>!b.condition||val(b.condition,v));if(b)dest.push(...run(b.actions,v));}else throw Error('Unexpected action '+a.type);}return dest;}
const actions={ru:ru.reactions[0].actions,en:en.reactions[0].actions};let checks=0;
for(const from of ['ru','en']){const to=from==='ru'?'en':'ru';assert.equal(actions[from].filter(a=>a.type==='SET_VARIABLE').length,33);for(const p of pairs){const values=p.ru.type==='BOOLEAN'?[false,true]:p.values[from];for(let i=0;i<values.length;i++){const v={};for(const q of pairs){v[q[from].id]=q[from].initial;v[q[to].id]=q.ru.type==='BOOLEAN'?!q[to].initial:'STALE-DESTINATION';}v[p[from].id]=values[i];const dest=run(actions[from],v);assert.deepEqual(dest,[from==='ru'?'2155:79633':'2155:19891']);let expected=p.ru.type==='BOOLEAN'?values[i]:(p.values[to][i]??p.values[to][0]);assert.equal(v[p[to].id],expected,p.name+' '+from+' '+String(values[i]));run(actions[to],v);const canonical=p.name.endsWith('session snapshot/2')&&from==='en'&&i===2?p.values.en[0]:values[i];assert.equal(v[p[from].id],canonical,p.name+' round trip');checks++;}}}
const migration=j('migration.json');assert.equal(migration.enFrameCount,888);assert.equal(migration.combinedRootFrames,1776);assert.equal(migration.reactionNodesChecked,6649);assert.equal(migration.reactionNodesRestored,0);assert.equal(migration.sourceRemainingFrames,0);
const n=j('navigation-migration.json').batches;assert.equal(n.length,19);assert.equal(n.reduce((a,b)=>a+b.rootsChecked,0),1776);assert.equal(n.reduce((a,b)=>a+b.convertedURLs,0),5950);
const master=j('menu-migration.json');assert.equal(master.variantCount,12);assert.equal(master.parentId,'1981:29');assert.equal(master.convertedURLs,68);
const resume=j('resume-readback.json');for(const l of ['ru','en']){const c=resume.config[l];const rows=resume.rows.filter(r=>r.locale===l);assert.ok(rows.length>=1);const menu=rows.find(r=>r.name==='Menu · users');assert.ok(menu);for(const [key,id]of Object.entries(c.targets))assert.deepEqual(run(menu.reactions[0].actions,{[c.view.id]:key}),[id]);}
const live=j('final-readback.json');assert.equal(live.sharedFrames,1776);assert.equal(live.formerEnglishFrames,0);assert.equal(live.switches.length,6);assert.ok(live.switches.every(x=>x.native&&x.resetInteractiveComponents&&!x.hasURL&&x.sameAsReference));assert.equal(live.adminInternalURLs,0);assert.equal(live.invalidDestinations,0);
const map=j('../sitemap.json');assert.ok(Number(map.revision)>=0.31);assert.equal(map.sections.flatMap(s=>s.screens).length,878);assert.ok(map.counts.ru>=888&&map.counts.en>=888);
const guide=j('guide-sync.json');assert.ok(guide.tailRetained&&guide.introVerified);assert.equal(guide.linksAfter,1802);assert.equal(guide.screenCards,878);
const trace=j('manual-checks.json');for(const [label,key,text] of [
 ['FINAL EN new email and ended sessions','sessions-other-revoked','elena.new@demo.example'],
 ['FINAL RU new email and ended sessions','sessions-other-revoked','elena.new@demo.example'],
 ['FINAL EN draft retained','users-filter-form','Demo Noor'],
 ['FINAL EN applied retained','users-filter-result','Demo Noor'],
 ['FINAL RU applied round trip','users-filter-result','Demo Noor']
]){const t=trace.findLast(t=>t.label===label);assert.ok(t&&t.ax.includes(' · '+key+' ·')&&t.ax.includes(text),label);}
const manifest=j('manifest.json');for(const f of manifest.files)assert.equal(crypto.createHash('sha256').update(fs.readFileSync(new URL(f.file,import.meta.url))).digest('hex'),f.sha256);assert.equal(trace.length,manifest.observations);
console.log('Verified '+checks+' state transfers/round trips, native language/menu routes, shared-page inventory, guide retention and selected browser paths. No production or complete role acceptance.');
