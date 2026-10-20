import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL(p,import.meta.url));
const json=p=>JSON.parse(read(p));
const map=json('../sitemap.json'),pairs=json('screen-pairs.json'),specs=json('screen-specs.json');
const coverage=json('coverage.json'),manifest=json('manifest.json'),trace=json('manual-checks.json');
const all=map.sections.flatMap(s=>s.screens);
assert.ok(Number(map.revision)>=0.28);assert.ok(all.length>=852);assert.ok(map.counts.ru>=857&&map.counts.en>=857);assert.equal(pairs.length,27);
assert.equal(manifest.uiKitVersion,'0.4.21');assert.equal(manifest.visualKitChanged,false);assert.equal(manifest.fullManualAcceptance,false);assert.equal(manifest.realOperationsVerified,false);
// A named design root proves the observed screen. Its controls can legitimately
// include a "Loading example" action; that is not the viewer loading placeholder.
const rendered=trace.filter(t=>t.ax.length>500&&/container (RU|EN) · /.test(t.ax));
for(const locale of ['ru','en']){
 const d=json('native-readback-'+locale+'.json'),p=json('native-polish-'+locale+'.json');
 assert.equal(d.rootFrames,857);assert.equal(d.roots.length,27);
 const get=key=>d.roots.find(r=>r.key===key);
 for(const pair of pairs){
  const n=get(pair.key),s=specs.find(s=>s.key===pair.key);assert.equal(n.id,pair[locale]);
  assert.ok(all.some(a=>a.id===pair.ru&&a.english.id===pair.en));
  assert.ok(n.fonts.every(f=>f==='Inter'));assert.ok(n.bindings>0);assert.equal(n.imagePaintCount,0);
  assert.ok(n.actor.includes(s.role==='ops'?'STAFF-206':'STAFF-201'),pair.key+' actor');
  if(s.role==='ops')assert.deepEqual(p.proof.find(r=>r.key===pair.key).ownerLinks,[],pair.key+' owner navigation');
  assert.ok(rendered.some(t=>t.ax.includes('container '+locale.toUpperCase()+' · '+pair.key+' ·')),pair.key+' '+locale+' missing rendered browser observation');
 }
 const text=key=>JSON.stringify(get(key));
 for(const venue of ['pm','ll']){
  const x=text('connection-diagnostics-'+venue);assert.ok(x.includes('CONN-'+venue.toUpperCase()+'-01'));assert.ok(x.includes('WebSocket'));
  assert.ok(x.includes(locale==='ru'?'Не предоставлен':'Not provided'));assert.ok(x.includes(locale==='ru'?'не ноль':'not zero'));
 }
 assert.ok(text('session-period-ended').includes(locale==='ru'?'Новые покупки':'New buys'));
 assert.ok(text('session-final-blocked').includes(locale==='ru'?'Новая сессия / сброс':'New session / reset'));
 assert.ok(text('session-dust').includes('0.003'));assert.ok(text('session-dust').includes('0.01'));
 assert.ok(text('session-budget-history').includes('FLOW-DEMO-01'));assert.ok(text('session-budget-history').includes('FLOW-DEMO-02'));
 assert.ok(text('session-budget-summary').includes(locale==='ru'?'Баланс изменён':'Balance changed'));
 assert.ok(text('session-signal-revisions').includes(locale==='ru'?'Версия размера: 12':'Sizing revision: 12'));
 assert.ok(text('session-signal-revisions').includes(locale==='ru'?'Версия ограничений: 14':'Admission revision: 14'));
 assert.equal(get('users-filter-form').fields.length,5);assert.equal(get('users-filter-form').records.length,0);
 for(const key of ['users-filter-result','incident-reopened-queue','staff-invited-list'])assert.equal(get(key).records.length,1,key+' entity list');
 assert.ok(text('user-related-support').includes('TKT-NOOR-DEMO-01'));assert.ok(!text('user-related-support').includes('USR-1007'));
 for(const key of ['support-position-context','support-order-context','support-event-context'])assert.ok(text(key).includes('USR-1007'));
 assert.ok(text('support-event-context').includes(locale==='ru'?'Не создавалась':'None created'));
 assert.ok(text('incident-reopened').includes('EVID-DEMO-04'));assert.ok(text('incident-reopened').includes('$12'));
 const final=get('incident-reopened');assert.ok(final.actions.some(a=>a.actions.some(x=>x.target===pairs.find(p=>p.key==='incident-reopened-queue')[locale])));
 assert.ok(text('staff-invite-activated').includes('STAFF-207'));assert.ok(text('staff-invite-activated').includes(locale==='ru'?'Нет роли и области':'No role or scope'));
 assert.ok(get('staff-invite-activated').actions.some(a=>a.actions.some(x=>x.target===pairs.find(p=>p.key==='staff-invited-list')[locale])));
 const help=json('native-help-'+locale+'.json').final;assert.equal(help.isError,false);
 const follow=json('native-followup-'+locale+'.json');assert.equal(follow.isError,false);
 const fp=JSON.parse(follow.content.find(x=>x.type==='text').text);
 assert.equal(fp.target,pairs.find(p=>p.key==='incident-reopened-queue')[locale]);
 assert.equal(fp.reactions[0].actions[0].destinationId,fp.target);
 const hp=JSON.parse(help.content.find(x=>x.type==='text').text).proof;assert.equal(hp.length,2);
 for(const h of hp){assert.equal(h.width,44);assert.equal(h.height,44);assert.ok(h.fills.some(f=>f.type==='SOLID'&&f.boundVariables?.color));assert.equal(h.reactions[0].actions[0].type,'CLOSE');}
 const labels=locale==='ru'?['HELP RU global closed and emergency context preserved','HELP RU technical close confirmed']:['HELP EN global closed verified','HELP EN technical close confirmed'];
 for(const label of labels){const t=trace.find(t=>t.label===label);assert.ok(t,label);assert.ok(!t.ax.includes(locale==='ru'?'button Закрыть подсказку':'button Close help'));assert.ok(t.ax.includes(locale==='ru'?'container RU · emergency':'container EN · emergency'));}
}
const guide=json('guide-sync.json');assert.equal(guide.screenCards,852);assert.equal(guide.newCards,27);assert.equal(guide.newLinks,54);assert.equal(guide.allLinkRuns,1750);assert.ok(guide.readbackVerified&&guide.allPriorCardNumbersRetained&&guide.newCardsVerified&&guide.newLinksVerified&&guide.countsVerified);
assert.equal(coverage.temporarySettings.viewportReset,true);assert.equal(coverage.temporarySettings.screenReaderChanged,false);assert.equal(coverage.fullStateCombinationAcceptance,false);
for(const [locale,id] of [['RU','2210:21620'],['EN','2210:82672']]){
 const t=trace.find(t=>t.label==='ORIGINAL Noor '+locale+' back preserves caller');assert.ok(t);assert.ok(t.url.includes('node-id='+id.replace(':','-')));
}
for(const shot of manifest.screenshots){const b=read(shot.file);assert.equal(crypto.createHash('sha256').update(b).digest('hex'),shot.sha256);assert.ok(b.subarray(1,4).toString()==='PNG'||b.subarray(0,3).equals(Buffer.from([255,216,255])));}
assert.equal(crypto.createHash('sha256').update(read('manual-checks.json')).digest('hex'),manifest.browserTrace.sha256);
console.log('Verified 27 paired native states and browser observations, four help closures, role boundaries, retained facts, lists and 27 new guide cards. No full-state/runtime acceptance.');
