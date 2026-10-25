'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const listeners={};const element={innerHTML:'',textContent:'',focus(){},setAttribute(){}};
const c=vm.createContext({structuredClone,Intl,Date,Set,document:{documentElement:{},activeElement:null,querySelector:s=>s==='.tooltip'?null:element,addEventListener:(type,fn)=>(listeners[type]??=[]).push(fn)},window:{scrollTo(){}}});
for(const f of ['account-fixtures.js','account.js','support.js','feedback.js','incidents.js','reconciliation.js','trading.js','emergency.js','finance.js','platforms.js','app.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+f,'utf8'),c);
const read=s=>vm.runInContext(s,c);read('render=()=>{}');
let checks=0;const ok=(code,expected=true)=>{assert.equal(read(code),expected,code);checks++;};
for(const role of ['ownerA','ownerB','lead','ops','limited','marketing','audit']){
 read(`state.role=${JSON.stringify(role)}; account=newAccount(state.role); state.response='success'; state.locale='ru'; state.route='order'; state.userId='U-DEMO-002'; state.sessionId='S-DEMO-002'; state.q='Noor'; state.selected=new Set(['U-DEMO-002']); account.draft='Учебное имя';state.locale='en';`);
 ok("account.draft==='Учебное имя'&&state.userId==='U-DEMO-002'&&state.selected.has('U-DEMO-002')");
 ok("accountRole()===actor().en.split(' · ').slice(2).join(' · ')");
 read("accountAction('session-end',{dataset:{session:'laptop'}});closeAccountDialog()");ok('account.otherSessions.length',2);
 read("state.response='unknown';accountAction('session-end',{dataset:{session:'laptop'}});accountAction('end-confirm',{});closeAccountDialog();accountAction('session-end',{dataset:{session:'mobile'}})");
 ok("account.pendingEnd==='laptop'&&account.endTarget==='laptop'");read("accountAction('end-confirm',{})");ok('account.otherSessions.length',2);read("accountAction('end-refresh',{})");ok("account.otherSessions.join(',')",'mobile');ok('account.logged');
 read("account=newAccount(state.role);state.response='error';accountAction('session-end',{dataset:{session:'all'}});accountAction('end-confirm',{})");ok('account.otherSessions.length',2);ok('!!account.error');read("accountAction('end-confirm',{})");ok('account.otherSessions.length',0);
 read("account=newAccount(state.role);state.response='success';accountAction('keys-start',{});accountAction('auth-pass',{});accountAction('key-next',{});accountAction('key-next',{})");ok('account.step',role.startsWith('owner')?3:5);
 if(role.startsWith('owner')){read("accountAction('same-key',{})");ok('account.step',3);ok('!!account.error');read("accountAction('key-next',{});accountAction('key-next',{})");}
 read("accountAction('key-next',{})");ok('account.otherSessions.length',0);ok('account.logged');
 read("account=newAccount(state.role);accountAction('codes-start',{});accountAction('auth-pass',{});accountAction('codes-generate',{})");ok('account.codesShown');read('closeAccountDialog()');ok('account.codesShown',false);
 read("account=newAccount(state.role);account.emailDraft='<b>x</b>@example.com';accountAction('email-continue',{})");ok('!!account.error');ok('account.pendingEmail',null);
 read("account.pendingEmail='<b>x</b>@example.com'");ok("accountDetails().includes('&lt;b&gt;x&lt;/b&gt;@example.com')");ok("accountDetails().includes('<b>x</b>')",false);
 read("account=newAccount(state.role);accountAction('recovery-start',{})");ok('account.logged',false);ok('state.route','recovery');read("accountAction('recovery-proof',{});account.step=5;accountAction('key-next',{})");ok('account.recoveryDone');ok('account.logged',false);
}
read("state.role='limited';account=newAccount('limited');state.locale='en'");ok("filtered().every(u=>u.id==='U-DEMO-002')");ok('fmt(160)','No access');
read("state.role='marketing';account=newAccount('marketing')");ok('filtered().length',0);
read("state.role='audit';account=newAccount('audit')");ok('fmt(160)','No access');
console.log(JSON.stringify({checks,status:'pass',roles:7,scope:'in-memory account transitions; no server authentication proof'}));
