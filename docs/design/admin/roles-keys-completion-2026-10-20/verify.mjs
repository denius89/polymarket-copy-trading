import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const read=n=>fs.readFileSync(new URL(n,import.meta.url));
const json=n=>JSON.parse(read(n));
const pairs=json('screen-pairs.json'), definitions=json('key-states.json'), map=json('../sitemap.json');
const all=map.sections.flatMap(s=>s.screens), manifest=json('manifest.json');
assert.equal(all.length,819);assert.equal(map.revision,'0.26');assert.deepEqual(map.counts,{ru:824,en:824});
assert.equal(pairs.length,21);assert.equal(definitions.length,20);
for(const p of pairs)assert.ok(all.some(s=>s.id===p.ru&&s.english.id===p.en));
for(const loc of ['ru','en']){
 const flows=json('key-readback-'+loc+'.json'), roles=json('role-readback-'+loc+'.json').records;
 const latest=json(loc+'-final.json'), visual=json(loc+'-visual-final.json'), menus=json(loc+'-menu-final.json').records;
 assert.equal(flows.length,20);assert.equal(new Set(flows.map(s=>s.id)).size,20);
 const byKey=Object.fromEntries(pairs.map(p=>[p.key,p[loc]]));
 for(const mode of ['replace','recovery']){
  const prefix='account-key-'+mode+'-';
  const end=byKey[mode==='replace'?'mfa-replaced':'mfa-recovery-complete'];
  // Only the separate backup browser-result example can lead to completion.
  const incoming=flows.flatMap(s=>s.links.filter(l=>l.to.includes(end)).map(l=>({from:s.id,name:l.name})));
  assert.deepEqual(incoming.map(x=>x.from),[byKey[prefix+'backup-prompt']]);
  assert.ok(incoming[0].name.startsWith('Prototype outcome'));
  const done=flows.find(s=>s.id===end);assert.ok(done.results.some(t=>/Проверен|Verified/.test(t)));
  for(const tail of ['primary-error','backup-error','backup-cancelled','backup-duplicate','proof-expired']){
   const f=flows.find(s=>s.id===byKey[prefix+tail]);assert.ok(f,tail);assert.ok(!f.links.some(l=>l.to.includes(end)));
  }
 }
 const recovery=pairs.filter(p=>p.mode==='recovery').map(p=>p[loc]);assert.equal(recovery.length,10);
 for(const f of flows.filter(s=>recovery.includes(s.id))){assert.deepEqual(f.recoveryNavigation,['Main content']);assert.ok(f.links.every(l=>l.to.every(t=>recovery.includes(t)||t===(loc==='ru'?'2138:9959':'2138:67538'))));}
 assert.equal(roles.length,80);assert.ok(roles.every(r=>r.ordinaryCrosses.length===0));
 assert.deepEqual(['owner-b','nora-ops','ops'].map(a=>roles.filter(r=>r.actor===a).length),[33,34,13]);
 assert.ok(roles.every(r=>r.avatarHidden||r.avatarTo===r.profile));
 assert.equal(menus.length,47);assert.ok(menus.every(m=>m.items.length===6));
 const known=new Set(all.flatMap(s=>[s.id,s.english.id]));assert.ok(menus.every(m=>m.items.every(i=>!i.to||known.has(i.to))));
 assert.equal(latest.profileBacks.length,6);assert.ok(latest.profileBacks.every(p=>p.actions.length===1&&p.actions[0].type==='BACK'));
 assert.equal(latest.hiddenInputs.length,4);assert.ok(latest.hiddenInputs.every(i=>i.visible===false));
 assert.equal(latest.icons.length,3);assert.ok(latest.icons.every(i=>i.supported&&i.value===false));
 assert.equal(visual.nora.meta,'STAFF-203');assert.equal(visual.nora.detail,loc==='ru'?'Нора Азиз':'Nora Aziz');
 assert.ok(visual.labels.filter(l=>l.to===(loc==='ru'?'2138:9959':'2138:67538')).every(l=>!/безопасност|security/i.test(l.label)));
}
const guide=json('guide-sync.json');assert.equal(guide.screenCards,819);assert.equal(guide.newCards,17);assert.equal(guide.newLinks,34);assert.equal(guide.readbackVerified,true);
for(const shot of manifest.screenshots){const b=read(shot.file);assert.equal(b.subarray(1,4).toString(),'PNG');assert.equal(crypto.createHash('sha256').update(b).digest('hex'),shot.sha256);}
for(const name of ['build-key-contexts.js','fix-role-contexts.js','finish-role-links.js'])new (Object.getPrototypeOf(async function(){}).constructor)(read(name).toString());
assert.equal(manifest.fullManualAcceptance,false);assert.equal(manifest.realAuthenticationVerified,false);
console.log('Verified native evidence: 20 key states and 80 role contexts per locale; 6 profile returns each; 819 pairs; selected screenshots. No runtime or full Present acceptance.');
