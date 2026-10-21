import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL(p,import.meta.url)),j=p=>JSON.parse(read(p));
const idx=j('card-index.json'),desc=j('descriptions.json'),proof=j('guide-sync.json'),changes=j('change-summary.json'),native=j('figma-readback.json'),map=j('../sitemap.json');
assert.equal(idx.length,878);assert.equal(new Set(idx.map(x=>x.number)).size,878);assert.equal(new Set(idx.flatMap(x=>[x.ru,x.en])).size,1756);
for(const row of idx){assert.equal(row.headingStyle,'HEADING_2');assert.ok(map.sections.flatMap(s=>s.screens).some(x=>x.id===row.ru&&x.english.id===row.en));for(const [id,url]of [[row.ru,row.urlRU],[row.en,row.urlEN]]){assert.ok(url.includes('node-id='+id.replace(':','-')));assert.ok(url.includes('starting-point-node-id='+id.replace(':','-')));assert.ok(!url.includes('page-id=1981-30'));}}
assert.equal(desc.length,120);assert.equal(native.rows.length,120);assert.equal(native.special.length,5);assert.ok(native.rows.every(x=>!x.truncated));
for(const row of desc){assert.ok(idx.some(x=>x.number===row.number&&x.ru===row.id&&x.en===row.en));assert.ok(native.rows.some(x=>x.number===row.number&&x.id===row.id));assert.ok(row.description.length>60);assert.ok(read('UPDATED_CARDS.md').toString().includes(row.description));}
assert.equal(changes.rewrittenLinks.length,53);for(const x of changes.rewrittenLinks)assert.equal(x.url,x.old.replace('page-id=1981-30','page-id=1981-29'));
assert.equal(changes.requestCount,348);assert.ok(changes.guardedWriteSucceeded);assert.equal(changes.figmaWritten,false);
assert.equal(proof.screenCards,878);assert.equal(proof.totalLinkRuns,1804);assert.equal(proof.descriptionsVerified,120);assert.equal(proof.genericParagraphs,0);assert.equal(proof.staleEnglishPageLinks,0);assert.deepEqual(proof.oldVersionClaims,[]);
for(const key of ['allPriorNumbersRetained','titlesRetained','cardHeadingsPreserved','cardPairsMatchMap','newP19Present'])assert.equal(proof[key],true);
const intro=read('INTRO.md').toString();for(const phrase of ['0.32','878','894','0.4.21','24 часа','Клиенты → Пользователи','двух разных владельцев'])assert.ok(intro.includes(phrase),phrase);
const registry=j('../review-guide-2026-10-13/google-doc.json');assert.equal(registry.links,1804);assert.equal(registry.currentVerification,'../guide-refresh-2026-10-21/guide-sync.json');
for(const f of j('manifest.json').files)assert.equal(crypto.createHash('sha256').update(read(f.file)).digest('hex'),f.sha256);
console.log('Verified retained 878 cards and 1756 screen IDs, 120 descriptions against Figma readback, 53 normalized links, 1804 native link runs and current rules. No full prototype or runtime acceptance.');
