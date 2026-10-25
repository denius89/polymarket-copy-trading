'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const handlers={},nodes=new Map();
const node=s=>{if(!nodes.has(s))nodes.set(s,{innerHTML:'',textContent:'',dataset:{},setAttribute(){},showModal(){this.open=true},focus(){},insertAdjacentHTML(){},getBoundingClientRect(){return {top:0,left:0,bottom:44,right:100,width:100,height:44}}});return nodes.get(s)};
const ctx={structuredClone,Set,console,document:{documentElement:{},activeElement:{dataset:{}},addEventListener(k,f){(handlers[k]??=[]).push(f)},querySelector(s){return s==='.tooltip'?null:node(s)}},window:{scrollY:37,scrollTo(){}},Intl,Date};vm.createContext(ctx);
for(const f of ['account-fixtures.js','account.js','support.js','feedback.js','incidents.js','reconciliation.js','trading.js','emergency.js','finance.js','app.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+f,'utf8'),ctx);
const run=s=>vm.runInContext(s,ctx);let n=0;
const ok=(s,msg)=>{assert.ok(run(s),msg);n++};
for(const role of ['ownerA','ownerB','lead','ops','limited','marketing','audit']){
 run(`accountAction('enter',{dataset:{role:'${role}'}});state.q='Noor';state.venue='Polymarket';state.page=2;state.userId='U-DEMO-002';state.sessionId='S-DEMO-002';state.selected.add('U-DEMO-002');account.draft='Synthetic draft';support.q='reserve';feedback.q='demo';incidents.q='INC';reconciliation.q='REC';`);
 const routes=role==='marketing'?['overview','profile']:['overview','users','user','session','order','profile','support','ticket','feedback','feedbackItem',...(['limited'].includes(role)?[]:['incidents','incident','reconciliation','reconciliationItem','emergency'])];
 for(const route of routes){
  run(`state.menuOpen=true;navigate('${route}');`);ok('!state.menuOpen','navigation closes mobile menu');
  const before=run('JSON.stringify([state.role,actor().id,state.q,state.venue,state.page,state.userId,state.sessionId,[...state.selected],account.draft,support.q,feedback.q,incidents.q,reconciliation.q])');
  for(const locale of ['en','ru']){run(`state.locale='${locale}';render();`);assert.equal(run('JSON.stringify([state.role,actor().id,state.q,state.venue,state.page,state.userId,state.sessionId,[...state.selected],account.draft,support.q,feedback.q,incidents.q,reconciliation.q])'),before,role+'/'+route+' context');n++;
  const html=nodes.get('#app').innerHTML;assert.ok(html.includes(run('actor().id')),'identity in shell');assert.equal((html.match(/id="main-navigation"/g)||[]).length,1,'one navigation tree');n+=2;
  if(role==='marketing'){assert.ok(!html.includes('U-DEMO-')&&!html.includes('160,00'),'no user balances');n++;}
  }
 }
 run("accountAction('logout',{dataset:{}});navigate('users');");ok("state.route==='logout'",'logout guard');
}
console.log(JSON.stringify({status:'pass',assertions:n,roles:7,locales:2,scope:'In-memory route and identity invariants; not browser layout or server authorization'}));
