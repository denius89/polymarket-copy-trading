import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL(p,import.meta.url)),json=p=>JSON.parse(read(p));
const map=json('../sitemap.json'),pairs=json('screen-pairs.json'),trace=json('manual-checks.json');
assert.ok(Number(map.revision)>=0.29);assert.equal(map.sections.flatMap(s=>s.screens).length,878);assert.deepEqual(map.counts,{ru:888,en:888});assert.equal(pairs.length,26);
const ev=(x,vars)=>{if(x.type==='VARIABLE_ALIAS')return vars[x.value.id];if(x.type!=='EXPRESSION')return x.value;const a=x.value.expressionArguments.map(v=>ev(v,vars));switch(x.value.expressionFunction){case'EQUALS':return a[0]===a[1];case'NOT_EQUAL':return a[0]!==a[1];case'AND':return a.every(Boolean);default:throw Error(x.value.expressionFunction);}};
function run(actions,vars){const destinations=[];for(const a of actions){if(a.type==='SET_VARIABLE')vars[a.variableId]=ev(a.variableValue,vars);else if(a.type==='NODE')destinations.push(a.destinationId);else if(a.type==='CONDITIONAL'){const b=a.conditionalBlocks.find(b=>!b.condition||ev(b.condition,vars));if(b)destinations.push(...run(b.actions,vars));}}return destinations;}
let combinations=0;
for(const locale of ['ru','en']){
 const d=json('native-filter-'+locale+'.json'),n=json('native-readback-'+locale+'.json'),latest=json('native-final-readback-'+locale+'.json');
 assert.equal(latest.rootFrames,888);assert.equal(latest.roots.length,26);assert.equal(latest.menus.length,5);
 for(const pair of pairs){const row=latest.roots.find(x=>x.key===pair.key);assert.equal(row.id,pair[locale]);assert.ok(row.mainWithinFrame);assert.deepEqual(row.fonts,['Inter']);assert.ok(row.bindings>0);assert.equal(row.imagePaintCount,0);assert.deepEqual(n.roots.find(x=>x.key===pair.key).ownerNavigationLeaks,[]);assert.ok(map.sections.find(s=>s.id===pair.section).screens.some(s=>s.id===pair.ru&&s.english.id===pair.en));assert.ok(trace.some(t=>t.ax.includes('container '+locale.toUpperCase()+' · '+pair.key+' ·')),pair.key+' missing browser observation '+locale);}
 const result=locale==='ru'?'3445:70297':'3445:202693',empty=pairs.find(x=>x.key==='users-current-empty')[locale],invalid=pairs.find(x=>x.key==='users-period-invalid')[locale];
 const menus=d.menus;assert.equal(menus.length,5);
 for(let a=0;a<3;a++)for(let b=0;b<3;b++)for(let c=0;c<3;c++)for(let e=0;e<3;e++)for(let f=0;f<3;f++){
  const indexes=[a,b,c,e,f],vars={};indexes.forEach((v,i)=>vars[d.variables.draft[i].id]=menus[i].options[v]);d.variables.applied.forEach(v=>vars[v.id]='unchanged');
  const destinations=run(d.applyReactions.flatMap(r=>r.actions),vars);const match=a!==2&&b!==2&&c!==2&&e!==2&&f===0;
  assert.deepEqual(destinations,[f===2?invalid:match?result:empty]);
  d.variables.applied.forEach((v,i)=>assert.equal(vars[v.id],f===2?'unchanged':menus[i].options[indexes[i]]));combinations++;
 }
 assert.equal(d.previousActions.length,6);
 for(const action of d.previousActions){const key=action.conditionalBlocks[0].condition.value.expressionArguments[1].value;const destination=action.conditionalBlocks[0].actions[0].destinationId;assert.deepEqual(run(d.previousActions,{[d.priorSelection.id]:key}),[destination]);}
 for(const menu of latest.menus){assert.ok(menu.buttons.filter(b=>b.types.includes('SET_VARIABLE')&&b.types.includes('CLOSE')).length>=3);assert.ok(menu.buttons.some(b=>b.types.includes('CLOSE')&&!b.types.includes('SET_VARIABLE')));assert.equal(menu.dismiss[0].actions[0].type,'CLOSE');}
 const text=key=>JSON.stringify(latest.roots.find(x=>x.key===key));
 assert.ok(text('incident-feed-closed').includes('INC-DEMO-04'));assert.ok(text('incident-feed-closed').includes(locale==='ru'?'версия 4':'revision 4'));assert.ok(text('incident-order-close-blocked').includes('$12'));assert.ok(text('incident-order-close-conflict').includes(locale==='ru'?'версия 8':'revision 8'));
 assert.ok(text('support-page2-1060').includes('TKT-1060'));assert.ok(text('support-page2-1060').includes(locale==='ru'?'Мина Али':'Mina Ali'));assert.ok(!JSON.stringify(latest.roots.find(x=>x.key==='support-page2-1060').rows).includes('TKT-1042')); assert.ok(text('support-page2-1027').includes('TKT-1027'));assert.ok(text('support-page2-1027').includes(locale==='ru'?'Карим Саид':'Karim Said'));
 assert.ok(text('sessions-needs-attention').includes('S-DEMO-002'));assert.ok(!text('sessions-needs-attention').includes('S-DEMO-001'));
 for(const suffix of ['initial returns unfiltered users','stale snapshot preserved'])assert.ok(trace.some(t=>t.label==='CANCEL '+locale.toUpperCase()+' '+suffix&&t.ax.includes('container '+locale.toUpperCase()+' · '+(suffix.startsWith('stale')?'users-current-stale':'users')+' ·')));
}
const g=json('guide-sync.json');assert.equal(g.screenCards,878);assert.equal(g.uniqueCardNumbers,878);assert.equal(g.allLinkRuns,1802);for(const key of ['readbackVerified','newCardsVerified','newLinksVerified','allPriorCardNumbersRetained','countsVerified'])assert.equal(g[key],true);
const manifest=json('manifest.json');for(const item of [...manifest.screenshots,manifest.browserTrace]){const b=read(item.file);assert.equal(crypto.createHash('sha256').update(b).digest('hex'),item.sha256);}
assert.equal(combinations,486);assert.equal(manifest.fullManualAcceptance,false);assert.equal(manifest.realOperationsVerified,false);
console.log('Verified 26 native pairs, observed browser states, 486 prepared filter combinations against native actions, 12 previous-selection routes, menu closures, retained entities and guide readback. Runtime/full acceptance not claimed.');
