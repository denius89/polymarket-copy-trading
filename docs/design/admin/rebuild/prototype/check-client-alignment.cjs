const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
let html='';
const node={textContent:'',set innerHTML(v){html=v},get innerHTML(){return html},setAttribute(){},focus(){},insertAdjacentHTML(){},getBoundingClientRect(){return {bottom:0}},scrollHeight:0,clientHeight:0};
const c={structuredClone,Intl,Set,Date,console,document:{addEventListener(){},querySelector(s){return s==='.tooltip'?null:node},documentElement:{}},window:{scrollTo(){},scrollY:0}};
vm.createContext(c);
for(const f of ['account-fixtures.js','account.js','support.js','feedback.js','incidents.js','reconciliation.js','trading.js','emergency.js','finance.js','own-withdrawal.js','platforms.js','content.js','management.js','staff-security.js','technical-mode.js','app.js','client-view.js'])
 vm.runInContext(fs.readFileSync(path.join(__dirname,f),'utf8').replace(['app.js','client-view.js'].includes(f)?/render\(\);\s*$/:/$^/,''),c);
const run=s=>vm.runInContext(s,c);run('render=()=>{}');
let n=0;const ok=(s,label)=>{assert.ok(run(s),label);n++;};
ok('users.every(u=>u.sessions.length<=1)','single current session globally');
ok('users.flatMap(u=>u.sessions).length===23','correct current session count');
ok('users.some(u=>u.sessions.some(s=>s.venue==="Polymarket"))&&users.some(u=>u.sessions.some(s=>s.venue==="Limitless"))','both venues retained');
for(const role of ['ownerA','ownerB','lead','ops','limited','marketing','audit'])for(const locale of ['ru','en']){
 run(`state.role='${role}';state.locale='${locale}';state.route='order';state.userId='U-DEMO-002';state.sessionId='S-DEMO-002';state.q='Noor';state.page=2;account=newAccount(state.role);technical=newTechnical();clientView.active=false;`);
 const allowed=['ownerA','ownerB','lead','ops'].includes(role);
 ok(`clientOpen('U-DEMO-002')===${allowed}`,'preview does not broaden assignment');
 if(!allowed)continue;
 const before=run('JSON.stringify(state)');
 for(const route of ['order','help','support','profile','notifications']){
  run(`clientNavigate('${route}')`);
  ok(`clientView.uid==='U-DEMO-002'&&clientView.sid==='S-DEMO-002'&&state.role==='${role}'`,'client and staff identities remain separate');
 }
 run("clientView.locale=clientView.locale==='ru'?'en':'ru';clientBack()");
 ok("clientView.route==='order'",'auxiliary return restores source order');
 ok(`state.locale==='${locale}'`,'client locale does not overwrite employee locale');
 ok('clientSession().reserved===20&&clientTrade().c.fill===null','unknown keeps reserve and unknown fill');
 ok("clientOrder().includes(clientAmount(null))&&!clientOrder().includes('Confirmed fill: $0')",'unknown not rendered as known zero');
 run('clientReturnAdmin()');
 assert.equal(run('JSON.stringify(state)'),before);n++;
}
run("state.role='ownerA';state.locale='ru';state.route='order';state.userId='U-DEMO-005';state.sessionId='S-DEMO-005';account=newAccount('ownerA');support=newSupport();technical=newTechnical();trading=newTrading();");
for(const key of ['partial','late','cancelled','full']){
 run(`tradingChoose('${key}');clientOpen('U-DEMO-005')`);
 ok(`clientTrade().key==='${key}'`,'shared selected snapshot');
 ok("clientSession().id===sharedClientCases['U-DEMO-005'].sid",'shared session identity');
 ok('clientSession().reserved===tradingCurrent().reserve','client/admin reserve projection matches');
 ok('clientSession().positionsCost===tradingCurrent().position','client/admin position cost matches');
 ok('clientSession().available+clientSession().reserved+clientSession().positionsCost===200','confirmed snapshot conservation');
 run('clientReturnAdmin()');
}
run("state.userId='U-DEMO-002';state.sessionId='S-DEMO-002';support.id='T-101';support.mode='note';supportCurrent().note='PRIVATE STAFF NOTE';supportSend();support.mode='reply';supportCurrent().reply='Public original response';support.fixture='unknown';supportSend();clientOpen('U-DEMO-002');");
ok('clientPublicThread().id==="T-101"&&clientPublicThread().sid==="S-DEMO-002"','shared conversation identity');
ok('clientPublicThread().messages.length===0','unknown public send not shown as confirmed');
ok("!JSON.stringify(clientPublicThread()).includes('PRIVATE STAFF NOTE')",'internal note does not leak');
run("clientReturnAdmin();support.fixture='success';supportAction('check');clientOpen('U-DEMO-002')");
ok("clientPublicThread().messages.length===1&&clientPublicThread().messages[0].id==='T-101-M2'",'confirmed original public message shown once');
ok("!JSON.stringify(clientPublicThread()).includes('STAFF-')",'employee identifiers excluded from public projection');
ok("clientThreadPage().includes('Public original response')&&!clientThreadPage().includes('PRIVATE STAFF NOTE')",'actual client conversation rendering');
run("clientReturnAdmin();finance=newFinance();finance.policies['vip:U-DEMO-002']={history:[{version:2,status:'published',effective:'2026-10-01T12:00',value:'0.5',extra:{intentVIP:'assign',duration:'indefinite'}}]};clientOpen('U-DEMO-002');");
ok('clientTerms().vip&&clientTerms().version===2&&clientTerms().fee===0','published VIP does not activate paid tariff');
ok('clientTerms().futureRate==="0.5"','same version and individual future rate');
run("clientView.route='order';clientNavigate('profile');clientView.locale='en';clientBack()");
ok("clientView.route==='order'&&clientView.locale==='en'&&clientView.sid==='S-DEMO-002'",'language and object preserved');
run("clientReturnAdmin();technical.phase='pending';clientOpen('U-DEMO-002')");
ok("!clientNavigate('profile')&&!clientAction('pause',{})",'shutdown pending already blocks client changes');
run('clientRender()');
assert.ok(html.includes('Сервис временно недоступен')&&!html.includes('client-bottom')&&!html.includes('data-client="pause"'));n++;
run("technical.phase='active';clientRender()");
assert.ok(html.includes('Сервис временно недоступен'));n++;
run("technical.phase='restored';clientRender()");
ok('clientTrade().c.fill===null&&clientSession().reserved===20','restoration does not replay unknown order or release reserve');
run("clientReturnAdmin();state.userId='U-DEMO-001';state.sessionId='S-DEMO-001';clientOpen('U-DEMO-001');clientAction('pause',{});clientNavigate('profile');clientView.locale='en';clientBack()");
ok('clientSession().manualPaused===true','manual pause survives auxiliary navigation');
run('clientReturnAdmin()');
ok("findSession().manualPaused===true&&state.role==='ownerA'",'client pause visible in the same admin session');
run("account.logged=false");
ok("!clientOpen('U-DEMO-002')",'signed out cannot preview');
console.log(JSON.stringify({assertions:n,status:'pass',scope:'Shared in-memory client/admin projection and contextual returns; no backend/authentication assertion'}));
