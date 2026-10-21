import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL(p,import.meta.url)),j=p=>JSON.parse(read(p));
const map=j('../sitemap.json'), inv=j('native-inventory.json');
const pairs=map.sections.flatMap(s=>s.screens), main=pairs.flatMap(x=>[x.id,x.english.id]);
assert.equal(pairs.length,878);assert.equal(new Set(main).size,1756);
assert.equal(inv.rootIds.length,1788);assert.equal(new Set(inv.rootIds).size,1788);
assert.ok(main.every(id=>inv.rootIds.includes(id)));
const extras=inv.rootIds.filter(id=>!main.includes(id));assert.equal(extras.length,32);
assert.ok(map.roleLocaleServiceOverlays.every(x=>extras.includes(x.id)));
assert.deepEqual(map.counts,{ru:894,en:894});assert.equal(map.figma.sharedPageRootFrames,1788);
const targets={'3484:208575':'2185:21842','3484:208743':'2185:21842','3484:209563':'2188:85045','3484:209731':'2188:85045'};
assert.equal(inv.returns.length,4);for(const n of inv.returns){assert.ok(targets[n.id]);assert.deepEqual(n.reactions.flatMap(r=>r.actions).map(a=>[a.type,a.destinationId]),[['NODE',targets[n.id]]]);}
const menu=j('native-menu-readback.json');assert.equal(menu.length,82);assert.ok(menu.every(x=>x.hasSupport&&x.selected.length===1&&x.selected[0].name==='Role menu · ADM-09/support'));
const req=j('../requirements-coverage-2026-10-16/requirements.json'), counts={};for(const r of req)counts[r.status]=(counts[r.status]||0)+1;
assert.deepEqual(counts,{'готово':96,'частично':8,'отложено':6});for(const id of ['U01','H04','B04'])assert.equal(req.find(r=>r.id===id).status,'готово');
assert.deepEqual(j('../requirements-coverage-2026-10-16/current-status.json').counts,counts);
const trace=j('manual-checks.json'), last=label=>{const t=trace.findLast(x=>x.label===label);assert.ok(t,label);return t.ax;};
for(const [label,locale,key]of [
['OPS EN card-profile-page2 verified','EN','support-page2'],
['OPS RU page 2 after card locale switch verified','RU','support-page2'],
['MARKETING EN filtered verified','EN','content-filtered'],
['MARKETING RU card verified','RU','content-missing'],
['NORA EN filtered verified','EN','feedback-filtered'],
['NORA RU filtered verified','RU','feedback-filtered'],
['AUDIT EN list verified','EN','access-audit-read'],
['AUDIT RU denial retained verified','RU','access-export-denied'],
['LIMITED EN assigned context verified','EN','access-support-limited'],
['LIMITED RU assigned user retained verified','RU','access-user-limited'],
['OWNER B EN exact review confirmed','EN','partner-rule-review-b'],
['OWNER B RU exact review confirmed','RU','partner-rule-review-b'],
['OWNER A RU applied filter verified','RU','users-filter-result'],
['OWNER A RU card-selection verified','RU','users-filter-result']
])assert.ok(last(label).includes('container '+locale+' · '+key+' ·'),label);
assert.ok(last('LIMITED RU assigned user retained verified').includes('ASG-DEMO-41'));
assert.ok(last('AUDIT RU denial retained verified').includes('Экспорт'));
const manifest=j('manifest.json');assert.equal(manifest.observations,trace.length);
for(const x of manifest.files)assert.equal(crypto.createHash('sha256').update(read(x.file)).digest('hex'),x.sha256);
console.log('Verified current 878 pairs / 1788 root IDs, four explicit support returns, reconciled 110 requirements and selected browser chains for seven contexts. Full product/runtime acceptance not claimed.');
