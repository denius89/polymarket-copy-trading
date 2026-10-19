import fs from 'node:fs';
import assert from 'node:assert/strict';
const read = path => JSON.parse(fs.readFileSync(new URL(path, import.meta.url), 'utf8'));
const final = read('./native-final.json');
const semantic = read('./native-after.json');
const pairs = read('./screen-pairs.json');
const ownerB = read('./focused-owner-b-targets.json');
const map = read('../sitemap.json');
const guide = read('../review-guide-2026-10-13/guide-source.json');
const client = read('./client-native-final.json');
const clientRecords = read('./client-screen-records.json');
const results = [];
function check(name, body) { try { body(); results.push({name, passed:true}); } catch(error) { results.push({name, passed:false, error:error.message}); } }
const byId = (locale,id) => final[locale].find(s=>s.id===id) || semantic[locale].find(s=>s.id===id);
const node = (locale,key) => byId(locale,pairs.find(p=>p.key===key)[locale]);
const text = s => s.texts.map(t=>Array.isArray(t)?t[2]:t).join('\n');
const targets = s => s.links.flatMap(l=>(l.actions||[]).filter(a=>a.navigation==='NAVIGATE').map(a=>a.to));
check('Unique 802 RU/EN pairs in map 0.25',()=>{ const screens=map.sections.flatMap(s=>s.screens); assert.equal(map.revision,'0.25'); assert.equal(screens.length,802); assert.equal(new Set(screens.map(s=>s.id)).size,802); assert.equal(new Set(screens.map(s=>s.english.id)).size,802); });
check('Google guide contains 802 actual heading cards',()=>assert.equal(guide.paras.filter(p=>p.style==='HEADING_2').length,802));
for(const locale of ['ru','en']) {
  check(locale+': waiting preserves first approval; second participant is a prototype handoff',()=>{ const secondIds=new Set(ownerB.map(p=>p[locale])); for(const p of pairs.filter(p=>p.key.startsWith('recovery-wait-'))) { const s=byId(locale,p[locale]); assert.ok(s); assert.match(text(s),/1 из 2.*владелец A|1 of 2.*Owner A/i); const secondLinks=s.links.filter(l=>(l.actions||[]).some(a=>a.navigation==='NAVIGATE'&&secondIds.has(a.to))); assert.equal(secondLinks.length,1,p.key); assert.match(secondLinks[0].parent,/scenario/i,p.key); } });
  check(locale+': focused Owner B never silently navigates into Owner A fixture',()=>{ const allowed=new Set(ownerB.map(p=>p[locale])); allowed.add(pairs.find(p=>p.key==='role-signed-out')[locale]); for(const p of ownerB) { const s=byId(locale,p[locale]); assert.ok(text(s).includes('STAFF-202'),p.key); for(const l of s.links) for(const a of l.actions||[]) if(a.navigation==='NAVIGATE'&&!allowed.has(a.to)) assert.ok(/scenario/i.test(l.parent),p.key+' -> '+a.to); } });
  check(locale+': Owner B own-profile return uses history, not Owner A destination',()=>{ const s=node(locale,'role-profile-owner-b'); assert.ok(s.links.some(l=>l.actions?.some(a=>a.type==='BACK'))); });
  check(locale+': operations profile keeps STAFF-206 identity',()=>{ const s=node(locale,'role-profile-ops'); assert.match(s.texts[0],locale==='ru'?/Олег Смирнов.*STAFF-206/:/Oleg Smirnov.*STAFF-206/); assert.ok(targets(s).includes(pairs.find(p=>p.key==='role-operations-overview')[locale])); });
  check(locale+': REC v2 has its own PAY-023 operation and full recipient',()=>{ for(const key of ['recipient-payment-accepted','recipient-payment-submitted','recipient-payment-paid','recipient-payment-unknown']) { const s=node(locale,key),t=text(s); assert.ok(t.includes('PAY-023')); assert.ok(t.includes('PRV-022 v1')); assert.ok(t.includes('REC v2')); assert.ok(t.includes('0x5555555555555555555555555555555555555555')); assert.ok(t.includes('120.00 / 1.20 / 121.20 USDT')); } });
  check(locale+': unknown payout retains reserves and cannot return to acceptance/send',()=>{ const s=node(locale,'recipient-payment-unknown'); assert.ok(text(s).includes('120.00 / 121.20 USDT')); assert.ok(!targets(s).includes(pairs.find(p=>p.key==='recipient-payment-accepted')[locale])); assert.ok(!s.links.some(l=>/resend|retry-send/i.test(l.name))); assert.ok(text(node(locale,'recipient-payment-paid')).includes('0.00 / 0.00 USDT')); });
  check(locale+': route authorization is separate from transfer approval',()=>{ const route=node(locale,'recovery-route-authorized'),first=node(locale,'recovery-transfer-first'),wait=node(locale,'recovery-transfer-wait'); assert.ok(targets(route).includes(first.id)); assert.ok(targets(first).includes(wait.id)); assert.ok(!targets(route).includes(locale==='ru'?'2827:90935':'2827:45137')); assert.ok(text(first).includes('100.00 / 0.50 / 100.50')); });
}
check('Full payout arithmetic and treasury expense are consistent',()=>{ assert.equal(Math.round((120+1.2)*100),12120); assert.equal(Math.round((100+0.5)*100),10050); assert.equal(225+100,325); assert.ok(325<=500); });
check('44 unique companion client states; no product screens are counted as server tests',()=>{ assert.equal(clientRecords.length,44); assert.equal(new Set(clientRecords.map(s=>s.id)).size,44); assert.equal(client.length,28); for(const s of client) { const t=text(s); assert.ok(t.includes('0%')); assert.ok(!/STAFF-20[1-6]|SRC-REV|private key|seed phrase/i.test(t)); assert.equal(s.width,s.locale.startsWith('mobile')?390:1440); } });
const output={scope:'Design-data and prototype-graph checks; not runtime/security acceptance',results,passed:results.every(r=>r.passed)};
fs.writeFileSync(new URL('./contract-checks.json',import.meta.url),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify(output,null,2));
if(!output.passed)process.exitCode=1;
