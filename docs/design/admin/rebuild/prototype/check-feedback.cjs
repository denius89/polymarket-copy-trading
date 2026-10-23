'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const c={structuredClone,Set,Date,console,document:{addEventListener(){},querySelector(){return {textContent:'',innerHTML:'',setAttribute(){},focus(){}}},documentElement:{}},window:{scrollTo(){}}};vm.createContext(c);
for(const f of ['account-fixtures.js','account.js','support.js','feedback.js','incidents.js','reconciliation.js','app.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,f),'utf8').replace(f==='app.js'?/render\(\);\s*$/:/$^/,''),c);
const run=s=>vm.runInContext(s,c);run('render=()=>{}');let n=0;const ok=(s,label)=>{assert.ok(run(s),label);n++;};
for(const role of ['ownerA','ownerB','lead','ops','limited','marketing','audit']){
 run(`state.role='${role}';account=newAccount(state.role);support=newSupport();feedback=newFeedback();`);
 const write=['ownerA','ownerB','lead','ops'].includes(role);
 ok(`feedbackRows().length===${role==='marketing'?0:role==='limited'?1:3}`,'visibility '+role);
 run("feedback.id='FB-102';");ok(`Boolean(feedbackCurrent())===${!['marketing','limited'].includes(role)}`,'scope gate');
 run("feedback.id='FB-101';feedback.draft={status:'reviewed',category:'idea',assignee:'STAFF-206',version:1};feedbackSave();");ok(`feedback.records[0].status==='${write?'reviewed':'new'}'`,'write gate');ok("support.records[0].status==='waiting_support'&&support.records[0].messages.length===0",'independent support');
 run("feedbackAction('choose');if(feedback.link)feedback.link.ticket='T-102';feedbackAction('link');");ok("feedback.records[0].ticket===null",'wrong context rejected');
 run("feedbackAction('choose');if(feedback.link)feedback.link.ticket='T-101';feedbackAction('link');feedbackAction('link');");ok(`feedback.records[0].ticket===${write?"'T-101'":'null'}`,'matching link rights');if(write){ok("feedback.records[0].events.filter(e=>e.label[0].startsWith('Добавлена связь')).length===1",'deduplicated link');ok("support.records.length===3&&support.records[0].messages.length===0",'no ticket creation/no send');}
 const original="feedbackFixtures[0].body";run("state.locale='en';");ok(`feedback.records[0].body===${original}`,'original language');
 run("feedback.records[0].note='PRIVATE_NOTE';feedbackAction('note');");ok(`feedback.records[0].notes.length===${write?1:0}`,'note rights');
 if(!write&&role!=='marketing')ok("!feedbackDetail().includes('PRIVATE_NOTE')&&!feedbackDetail().includes('feedback-note-form')",'private note hidden');
 run("account.logged=false;");ok("feedbackRows().length===0&&!feedbackCurrent()",'logged out gate');
}
run("state.role='lead';account=newAccount(state.role);support=newSupport();feedback=newFeedback();feedbackAction('open',{dataset:{id:'FB-101'}});feedback.draft.status='reviewed';feedback.records[0].note='draft';feedbackAction('conflict');feedbackSave();");ok("feedback.error&&feedback.records[0].status==='new'&&feedback.records[0].note==='draft'",'conflict preserves version and note');
run("feedbackAction('discard');feedbackAction('open',{dataset:{id:'FB-101'}});feedback.draft.category='idea';feedbackAction('back');feedbackAction('open',{dataset:{id:'FB-102'}});feedbackAction('open',{dataset:{id:'FB-101'}});");ok("feedback.draft.category==='idea'",'per-item draft survives list and another item');
run("feedbackSave();feedbackAction('choose');feedback.link.ticket='T-101';feedbackAction('link');feedbackAction('ticket',{dataset:{id:'FB-101'}});");ok("state.route==='ticket'&&support.id==='T-101'&&feedback.returnFromTicket&&state.role==='lead'",'support route retains actor');
run("feedbackAction('return');");ok("state.route==='feedbackItem'&&feedback.id==='FB-101'",'return exact item');
run("feedback.id='FB-103';feedbackAction('choose');");ok("feedback.link===null&&!feedbackDetail().includes('data-feedback=\"user\"')",'missing context not invented');
run("feedback.q='cannot tell';");ok("feedbackRows().length===1",'original search');run("feedback.q='no match';");ok("feedbackRows().length===0",'empty');
run("feedback.q='';feedback.status='new';feedback.category='other';");ok("feedbackRows().length===1&&feedbackRows()[0].id==='FB-103'",'composed filters');run("feedback.from='2026-10-23';");ok("feedbackRows().length===0",'date intersects filters');
run("feedback=newFeedback();feedback.records[0].body='<img src=x onerror=alert(1)>';");ok("feedbackDetail().includes('&lt;img')&&!feedbackDetail().includes('<img src=x')",'escape original');

run("feedback=newFeedback();feedbackAction('open',{dataset:{id:'FB-101'}});feedback.draft.status='reviewed';feedbackAction('conflict');feedback.records[0].note='independent note';feedbackAction('note');feedbackSave();");ok("feedback.error&&feedback.records[0].status==='new'&&feedback.records[0].notes.length===1",'note cannot rebase stale processing');
run("feedbackAction('choose');feedback.link.ticket='T-101';feedbackAction('link');feedbackSave();");ok("feedback.error&&feedback.records[0].status==='new'&&feedback.records[0].ticket==='T-101'",'link cannot rebase stale processing');
console.log(JSON.stringify({assertions:n,result:'pass',roles:7,scope:'synthetic in-memory transitions, not server authorization'}));
