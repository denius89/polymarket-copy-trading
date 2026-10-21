import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL(p,import.meta.url)),j=p=>JSON.parse(read(p));
const map=j('../sitemap.json'),trace=j('manual-checks.json');
assert.equal(map.revision,'0.30');assert.equal(map.sections.flatMap(s=>s.screens).length,878);assert.deepEqual(map.counts,{ru:888,en:888});
const val=(x,v)=>x.type==='VARIABLE_ALIAS'?v[x.value.id]:x.type==='EXPRESSION'?(()=>{const a=x.value.expressionArguments.map(x=>val(x,v));if(x.value.expressionFunction==='EQUALS')return a[0]===a[1];throw Error(x.value.expressionFunction);})():x.value;
function run(actions,v){let dest=[];for(const a of actions){if(a.type==='SET_VARIABLE')v[a.variableId]=val(a.variableValue,v);else if(a.type==='NODE')dest.push(a.destinationId);else if(a.type==='CONDITIONAL'){const b=a.conditionalBlocks.find(b=>!b.condition||val(b.condition,v));if(b)dest.push(...run(b.actions,v));}}return dest;}
const flat=as=>as.flatMap(a=>a.type==='CONDITIONAL'?flat(a.conditionalBlocks.flatMap(b=>b.actions)):[a]);
const states={feedback:'ADM-11',audit:'ADM-12'};
const id=(locale,key,section)=>{const x=map.sections.find(s=>s.id===section).screens.find(s=>s.key===key);return locale==='ru'?x.id:x.english.id;};
for(const locale of ['ru','en']){
 const account=j('native-account-'+locale+'.json'),feedback=j('native-feedback-'+locale+'.json'),fa=j('native-feedback-actions-'+locale+'.json'),audit=j('native-audit-'+locale+'.json'),native=j('native-readback-'+locale+'.json');
 assert.equal(account.modifiedRoots.length,50);assert.equal(account.linkCount,349);assert.equal(account.boundCount,50);assert.equal(account.translatedCount,locale==='ru'?27:0);
 assert.equal(native.rootFrames,888);assert.equal(native.rows.length,75);for(const r of native.rows){assert.deepEqual(r.fonts,['Inter']);assert.equal(r.imagePaints,0);}
 assert.equal(native.rows.slice(0,63).reduce((n,r)=>n+r.legacyInternalURLs,0),3);
 const urls=j('native-language-links-'+locale+'.json').flatMap(r=>r.urls);assert.equal(urls.length,3);const other=locale==='ru'?'2155-79633':'2155-19891';assert.ok(urls.every(u=>u.url.includes('node-id='+other)));
 const a=account.variables;
 const pending=account.proof.find(p=>p.key==='email-pending').actions.find(p=>p.name==='Action · email-saved');
 const vars={};assert.deepEqual(run(pending.reactions.flatMap(r=>r.actions),vars),[id(locale,'email-saved','ADM-14')]);assert.equal(vars[a.email],'elena.new@demo.example');assert.equal(vars[a.otherSessionsEnded],true);
 const security=account.proof.find(p=>p.key==='account-security');const sessions=security.actions.find(n=>n.name==='Action · my-sessions')||security.actions.find(n=>flat(n.reactions.flatMap(r=>r.actions)).some(a=>a.destinationId===id(locale,'my-sessions','ADM-14')));
 assert.ok(sessions);assert.deepEqual(run(sessions.reactions.flatMap(r=>r.actions),vars),[id(locale,'sessions-other-revoked','ADM-14')]);assert.deepEqual(run(sessions.reactions.flatMap(r=>r.actions),{[a.otherSessionsEnded]:false}),[id(locale,'my-sessions','ADM-14')]);
 const fv=feedback.variables;const v={[fv.state]:'new',[fv.link]:'no link'};
 const save=fa.find(n=>n.name==='Action · feedback-updated');assert.ok(save);run(save.actions,v);assert.equal(v[fv.state],'updated');
 const row=fa.find(n=>n.name==='Admin/Metadata row');assert.deepEqual(run(row.actions,v),[id(locale,'feedback-updated','ADM-11')]);
 const linked=fa.find(n=>n.name==='Action · feedback-linked');run(linked.actions,v);assert.equal(v[fv.state],'linked');assert.ok(v[fv.link].includes('TKT-1042'));
 const resolved=fa.find(n=>n.name==='Action · feedback-resolved');run(resolved.actions,v);assert.equal(v[fv.state],'resolved');assert.ok(v[fv.link].includes('TKT-1042'));assert.deepEqual(run(row.actions,v),[id(locale,'feedback-resolved','ADM-11')]);
 const without={[fv.state]:'new',[fv.link]:'no link'};run(save.actions,without);run(resolved.actions,without);assert.equal(without[fv.link],'no link');
 const filter=fa.find(n=>n.name==='Action · feedback-filtered');assert.deepEqual(run(filter.actions,v),[id(locale,'feedback-empty','ADM-11')]);assert.deepEqual(run(filter.actions,{[fv.state]:'new'}),[id(locale,'feedback-filtered','ADM-11')]);
 const returns=audit.proof.find(p=>p.key==='audit-entry').changes.filter(n=>flat(n.reactions.flatMap(r=>r.actions)).some(a=>a.destinationId===id(locale,'audit-filtered','ADM-12')));assert.ok(returns.length>0);
 for(const n of returns)for(const key of ['audit','audit-filtered'])assert.deepEqual(run(n.reactions.flatMap(r=>r.actions),{[audit.variable]:key}),[id(locale,key,'ADM-12')]);
 const observed=key=>trace.some(t=>t.ax.includes('container '+locale.toUpperCase()+' · '+key+' ·'));
 for(const key of ['staff-invite-form','staff-invite-pending','staff-invite-invalid','staff-invite-activated','staff-invited-list','password-change','password-error','password-reauth','password-saved','email-change','email-pending','email-saved','my-profile','sessions-other-revoked','mfa-replaced','mfa-recovery-setup','mfa-recovery-complete','admin-login','feedback-conflict','feedback-updated','feedback-linked','feedback-resolved','feedback-empty','notification-acknowledged','notification-facts','notification-unknown','notification-checked','audit-filtered','audit-entry','audit-export-failed','audit-page-2','content-rollback-review','content-rollback-pending','content-rollback-done','content-history-restored','marketing-pausing','marketing-paused','marketing-delivery-paused'])assert.ok(observed(key),locale+' '+key);
 for(const mode of ['replace','recovery'])for(const key of ['primary-prompt','primary-error','backup-ready','backup-prompt','backup-error','backup-cancelled','backup-duplicate','proof-expired'])assert.ok(observed('account-key-'+mode+'-'+key),locale+' '+mode+' '+key);
 const label=locale==='ru'?'EMAIL RU profile retains new email':'EMAIL EN account retains new email verified';const t=trace.find(t=>t.label===label);assert.ok(t&&t.ax.includes(' · my-profile · ')&&t.ax.includes('elena.new@demo.example'));
 const f=trace.find(t=>t.label==='FEEDBACK '+locale.toUpperCase()+' processed excluded from new selection');assert.ok(f&&f.ax.includes(' · feedback-empty · '));
}
const guide=j('guide-sync.json');assert.equal(guide.screenCards,878);assert.equal(guide.allLinkRuns,1802);assert.ok(guide.introVerified&&guide.allPriorCardsRetained);
const coverage=j('coverage.json');assert.equal(coverage.routes.length,10);assert.equal(coverage.fullStateCombinationAcceptance,false);assert.equal(coverage.realOperationsVerified,false);
const manifest=j('manifest.json');for(const f of [...manifest.screenshots,manifest.browserTrace])assert.equal(crypto.createHash('sha256').update(read(f.file)).digest('hex'),f.sha256);
console.log('Verified account/email/session continuity, feedback state/link retention, audit caller return, observed selected RU/EN branches and retained guide. No full-state or runtime acceptance.');
