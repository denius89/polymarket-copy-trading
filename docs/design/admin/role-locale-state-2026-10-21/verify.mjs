import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL(p,import.meta.url)),j=p=>JSON.parse(read(p));
const roles=j('roles.json'),native=j('native-readback.json'),entries=j('native-entry-writes.json'),build=j('native-build.json'),map=j('../sitemap.json');
assert.equal(roles.length,6);assert.equal(roles.reduce((n,r)=>n+r.origins.length,0),280);
assert.equal(native.rows.length,12);assert.equal(native.sharedRootFrames,1788);assert.equal(build.proof.length,12);
const variableIds=roles.flatMap(r=>Object.values(r.vars));assert.equal(new Set(variableIds).size,30);
const roleOrigins=new Map();for(const r of roles)for(const o of r.origins){assert.ok(o.key.includes('/'));assert.ok(!roleOrigins.has(o.key),'Origins must belong to one assignment');roleOrigins.set(o.key,r.key);}
assert.equal(entries.batches.length,12);assert.equal(entries.batches.reduce((n,b)=>n+b.proof.length,0),1120);
for(const b of entries.batches)for(const e of b.proof){const role=roles[e.index];assert.equal(role.key,roleOrigins.get(e.key));assert.ok(e.prefixRetained);assert.equal(e.assignments,5);assert.ok(Object.values(role.profile).includes(e.profileTarget));}
let returnCases=0;for(const row of native.rows){const role=roles.find(r=>r.key===row.role),lang=row.locale,other=lang==='ru'?'en':'ru';assert.equal(row.profile,role.profile[lang]);assert.deepEqual(row.fontFamilies,['Inter']);assert.ok(row.rootHeight>=row.contentBottom);assert.ok(row.languagePrefixMatches);assert.equal(row.languageDestination.destinationId,role.profile[other]);assert.equal(row.languageDestination.type,'NODE');assert.equal(row.languageDestination.navigation,'NAVIGATE');assert.equal(row.languageDestination.resetInteractiveComponents,true);assert.deepEqual(row.sameLanguageActions,[{type:'CLOSE'}]);assert.deepEqual(row.dismissActions,[{type:'CLOSE'}]);assert.equal(row.triggerAction.navigation,'OVERLAY');assert.equal(row.triggerAction.destinationId,row.overlay);assert.equal(row.hasOriginBinding.id,role.vars.hasOrigin);assert.equal(row.contextBinding.id,role.vars[lang+'_title']);assert.ok(row.returnContract);assert.deepEqual(row.returns,role.origins.map(o=>[o.key,o[lang]]));assert.equal(new Map(row.returns).get('UNKNOWN-CALLER'),undefined);returnCases+=row.returns.length;
 const initial=build.proof.find(p=>p.role===row.role&&p.locale===lang);const normalize=rows=>rows.filter(r=>r.name!=='Table column headings').map(r=>({name:r.name,props:r.props}));assert.deepEqual(normalize(row.identity),normalize(initial.identity));assert.ok(!row.header.some(s=>/STAFF-201/.test(s)));
}
assert.equal(returnCases,560);assert.equal(map.revision,'0.32');assert.deepEqual(map.counts,{ru:894,en:894});assert.equal(map.sections.flatMap(s=>s.screens).length,878);assert.equal(map.roleLocaleServiceOverlays.length,12);
const trace=j('manual-checks.json');const expected=[
 ['OWNER B','role-profile-owner-b','partner-rule-review-b','STAFF-202'],
 ['OPS','role-profile-ops','ops-note-saved','STAFF-206'],
 ['LIMITED','role-profile-limited','limited-reply-sent','STAFF-203'],
 ['MARKETING','role-profile-marketing','marketing-draft-saved','STAFF-204'],
 ['AUDIT','role-profile-audit','access-export-denied','STAFF-205'],
 ['NORA OPS','role-profile-nora-operations','feedback-resolved','STAFF-203']
];
for(const [label,profile,work,staff]of expected){const name=label==='OWNER B'?'OWNER B profile EN retains role':label+' EN profile';const p=trace.findLast(t=>t.label===name);assert.ok(p&&p.ax.includes('container EN · '+profile+' ·')&&p.ax.includes(staff),name);for(const l of ['EN','RU']){const name=label+' '+l+(l==='EN'?' work retained':' work round trip');const t=trace.findLast(t=>t.label===name);assert.ok(t&&t.ax.includes('container '+l+' · '+work+' ·'),name);}}
for(const label of ['NORA OPS EN work retained','NORA OPS RU work round trip'])assert.ok(trace.findLast(t=>t.label===label).ax.includes('TKT-1042'));
for(const label of ['SAME LANGUAGE closes in same role','DISMISS language menu retains role'])assert.ok(trace.findLast(t=>t.label===label).ax.includes('container RU · role-profile-nora-operations ·'));
const direct=trace.findLast(t=>t.label==='DIRECT EN role preserved without caller');assert.ok(direct.ax.includes('ASG-DEMO-41')&&direct.ax.includes('Open your profile from a work screen'));assert.ok(!/\d+ (button|link) Back to work screen/.test(direct.ax));
const guide=j('guide-sync.json');assert.equal(guide.screenCards,878);assert.equal(guide.uniqueCardNumbers,878);assert.equal(guide.linkRuns,1802);assert.equal(guide.profileChecksUpdated,6);assert.ok(guide.allPriorLinksRetained&&guide.introVerified);
const manifest=j('manifest.json');for(const f of manifest.files)assert.equal(crypto.createHash('sha256').update(read(f.file)).digest('hex'),f.sha256);assert.equal(trace.length,manifest.observations);
console.log('Verified 12 role profiles, 1120 profile entries, 560 assignment-scoped returns, 6 RU/EN browser round trips and direct-entry/close behavior. No runtime authorization or full product acceptance.');
