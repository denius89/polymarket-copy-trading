'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
const path=__dirname,model=JSON.parse(fs.readFileSync(path+'/model.json','utf8'));
const common=fs.readFileSync(path+'/common.js','utf8');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
new AsyncFunction('MODEL','JOB',common+fs.readFileSync(path+'/screens.js','utf8'));
const vars={};for(const k of ['canUsers','limited','venue','day','statusFilter','search',...model.cases.map(c=>'show/'+c.key)])vars[k]={id:k,resolvedType:['canUsers','limited'].includes(k)||k.startsWith('show/')?'BOOLEAN':k==='day'?'FLOAT':'STRING'};
const source=common.slice(common.indexOf('const literal='),common.indexOf('const colors='))+common.slice(common.indexOf('function rowCondition'),common.indexOf('function resetFilters'))+'\nresult=MODEL.cases.map(c=>({key:c.key,condition:rowCondition(c)}));';
const ctx={MODEL:model,vars,result:null};vm.runInNewContext(source,ctx);
function evalData(d,state){if(d.type==='VARIABLE_ALIAS')return state[d.value.id];if(d.type!=='EXPRESSION')return d.value;const a=d.value.expressionArguments.map(x=>evalData(x,state));switch(d.value.expressionFunction){case'EQUALS':return a[0]===a[1];case'AND':return a.every(Boolean);case'OR':return a.some(Boolean);case'NOT':return!a[0];default:throw Error('Unknown expression');}}
let checked=0;
for(const role of model.roles)for(const venue of ['all','Polymarket','Limitless'])for(const day of [0,17,18,19,20,21,22,23])for(const statusFilter of ['all','unknown','partial','stale'])for(const search of ['all','noor','orion','robin']){
 const state={canUsers:role.users,limited:role.limited,venue,day,statusFilter,search};
 const actual=ctx.result.filter(x=>evalData(x.condition,state)).map(x=>x.key);
 const expected=model.cases.filter(c=>role.users&&(!role.limited||c.key==='noor')&&(venue==='all'||c.venue===venue)&&(day===0||c.day===day)&&(statusFilter==='all'||c.status===statusFilter)&&(search==='all'||c.key===search)).map(c=>c.key);
 assert.deepEqual(actual,expected);checked++;
}
assert.equal(model.roles.filter(r=>r.key.startsWith('owner')).length,2);
assert.deepEqual(model.roles.slice(0,2).map(r=>[r.users,r.money,r.limited]),[[true,true,false],[true,true,false]]);
for(const c of model.cases)if(c.available!==null)assert.equal(c.available+c.reserve+c.cost,200);
const partial=model.cases.find(c=>c.status==='partial');assert.equal(partial.filled+partial.remaining,partial.requested);assert.equal(partial.reserve,partial.remaining);
assert.equal(model.cases.find(c=>c.status==='unknown').filled,null);
assert.equal(model.roles.find(r=>r.key==='marketing').users,false);
assert.equal(model.roles.find(r=>r.key==='audit').money,false);
console.log(JSON.stringify({filterCombinations:checked,syntax:'pass',roleBoundaries:'pass',moneyFixtures:'pass',note:'Tests the emitted expression logic; not a browser or server authorization test.'}));
