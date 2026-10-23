'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const context={structuredClone,Set,console,document:{addEventListener(){},querySelector(){return {textContent:'',innerHTML:'',insertAdjacentHTML(){},setAttribute(){},focus(){}}},documentElement:{}},window:{scrollTo(){}}};vm.createContext(context);
for(const f of ['account-fixtures.js','account.js','support.js','feedback.js','incidents.js','app.js']){let s=fs.readFileSync(path.join(__dirname,f),'utf8');if(f==='app.js')s=s.replace(/render\(\);\s*$/,'');vm.runInContext(s,context);}
const run=s=>vm.runInContext(s,context);let n=0;function ok(s,label){assert.ok(run(s),label);n++;}
for(const role of ['ownerA','ownerB','lead','ops','limited','marketing','audit']){
 run(`state.role='${role}';state.locale='ru';account=newAccount(state.role);support=newSupport();`);
 ok(`supportRows().length===${role==='marketing'?0:role==='limited'?1:3}`,'scope '+role);
 run("support.id='T-102';");ok(`Boolean(supportCurrent())===${!['marketing','limited'].includes(role)}`,'cross user '+role);
 run("support.id='T-101';support.records[0].reply='Не повторять отправку';support.records[0].note='Внутренняя проверка';state.locale='en';");ok("support.records[0].reply==='Не повторять отправку'&&support.records[0].note==='Внутренняя проверка'",'locale preserves text');
 const write=['ownerA','ownerB','lead','ops'].includes(role);
 run("support.fixture='unknown';supportSend();");ok(`Boolean(support.records[0].pending)===${write}`,'write gate '+role);
 if(write){ok("support.records[0].messages.length===0&&support.records[0].pending.status==='unknown'",'unknown not sent');run("support.fixture='success';supportSend();");ok("support.records[0].messages.length===0",'unknown cannot resend');run("support.fixture='unknown';supportAction('check',{});supportAction('check',{});supportAction('check',{});");ok("support.records[0].pending.status==='unknown'&&support.records[0].messages.length===0",'repeated checks remain unknown');run("support.fixture='success';supportAction('check',{});supportAction('check',{});");ok("support.records[0].messages.length===1&&support.records[0].messages[0].kind==='reply'",'one confirmed reply');ok("support.records[0].status==='waiting_support'",'reply not status');run("support.mode='note';supportSend();");ok("support.records[0].messages.length===2&&support.records[0].messages[1].kind==='note'",'separate internal note');ok("support.records[0].messages.every(m=>m.author.includes(actor().id))",'author identity');
 run("support=newSupport();support.records[0].reply='retry';support.fixture='failed';supportSend();var firstId=support.records[0].pending.id;support.fixture='success';supportSend();");ok("support.records[0].messages[0].id===firstId",'retry identity');run("support=newSupport();supportSend();");ok("support.error&&support.records[0].messages.length===0",'empty validation');
 run("support.records[0].reply='<img src=x onerror=alert(1)>';supportSend();");ok("supportTicket().includes('&lt;img')&&!supportTicket().includes('<img src=x')",'escape message');
 }
 run("support.q='no results';");ok("supportRows().length===0",'empty filter');run("support.q='';support.venue='Limitless';");ok(`supportRows().length===${role==='marketing'||role==='limited'?0:2}`,'venue scope');
 run("account.logged=false;");ok("supportRows().length===0&&!supportCurrent()",'logout closes data');
}
run("state.role='audit';account=newAccount(state.role);support=newSupport();support.records[0].messages.push({kind:'note',body:'PRIVATE_NOTE',author:'demo',id:'N1'});");ok("!supportTicket().includes('PRIVATE_NOTE')&&!supportTicket().includes('support-compose')",'notes excluded from readonly projection');
run("state.role='lead';account=newAccount(state.role);support=newSupport();support.assignee='mine';");ok("supportRows().length===1&&supportRows()[0].id==='T-103'",'assigned to me');
console.log(JSON.stringify({assertions:n,result:'pass',roles:7}));
