import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const configs=JSON.parse(fs.readFileSync(path.join(root,'config.json'),'utf8'));
let passed=0;
for(const c of configs){
  if(process.env.CHECK_VARIANT&&process.env.CHECK_VARIANT!==c.key)continue;
  const d=JSON.parse(fs.readFileSync(path.join(root,`after-${c.key}.json`),'utf8'));
  const records=new Map(d.actions.map(n=>[n.id,n]));
  const roles=d.roles;
  const initial=(more={})=>({[c.auth]:false,[c.stage]:'before',[c.draft]:false,
    [c.v.AccountState]:'new',[c.v.DraftMode]:'none',[c.v.Origin]:'main',...more});
  function run(id,vars){
    const record=records.get(id);assert(record,`${c.key}: missing action ${id}`);
    let destination=null;
    const value=v=>v.type==='VARIABLE_ALIAS'?vars[v.value.id]:v.type==='EXPRESSION'?expression(v.value):v.value;
    function expression(e){
      if(e.expressionFunction==='EQUALS')return value(e.expressionArguments[0])===value(e.expressionArguments[1]);
      if(e.expressionFunction==='AND')return e.expressionArguments.every(value);
      if(e.expressionFunction==='NOT')return !value(e.expressionArguments[0]);
      assert.fail(`Unsupported expression ${e.expressionFunction}`);
    }
    function actions(list){for(const a of list){
      if(a.type==='SET_VARIABLE')vars[a.variableId]=value(a.variableValue);
      else if(a.type==='NODE')destination=a.destinationId;
      else if(a.type==='CONDITIONAL'){
        const block=a.conditionalBlocks.find(b=>!b.condition||value(b.condition));
        if(block)actions(block.actions);
      }else assert.fail(`Unhandled prototype action ${a.type}`);
    }}
    actions(record.actions);return destination;
  }
  const check=(fn)=>{fn();passed++;};
  check(()=>{
    const v=initial();assert.equal(run(roles.mainPrimary,v),c.email);
    assert.equal(run(roles.confirm,v),c.catalog);assert.equal(v[c.auth],true);
    assert.equal(v[c.v.AccountState],'new');
  });
  for(const mode of ['fixed','percent']){
    const review=mode==='fixed'?c.review:c.percentReview;
    const setup=mode==='fixed'?c.setup:c.percentSetup;
    check(()=>{
      const v=initial();assert.equal(run(roles[mode+'Setup'],v),review);
      assert.equal(v[c.auth],false);assert.equal(v[c.v.DraftMode],mode);
      assert.equal(run(roles[mode+'Start'],v),c.email);
      assert.equal(run(roles.confirm,v),review);
      assert.equal(v[c.v.DraftMode],mode);assert.equal(v[c.v.AccountState],'new');
      assert.equal(run(roles[mode+'Start'],v),c.launch);
      assert.equal(v[c.v.AccountState],'empty');assert.equal(v[c.v.DraftMode],'none');
    });
    check(()=>{
      const v=initial({[c.v.DraftMode]:mode,[c.v.Origin]:mode,[c.draft]:true});
      assert.equal(run(roles.emailBack,v),review);assert.equal(v[c.v.DraftMode],mode);
      assert.equal(run(roles.confirmBack,v),c.email);assert.equal(v[c.draft],true);
      assert.equal(run(roles[mode+'Edit'],v),setup);
    });
    for(const state of ['active','paused','blocked','empty','completed'])check(()=>{
      const v=initial({[c.v.AccountState]:state,[c.v.DraftMode]:mode,[c.draft]:true});
      assert.equal(run(roles.confirm,v),state==='empty'?c.empty:d.resume);
      assert.equal(v[c.v.DraftMode],mode);assert.equal(v[c.draft],true);
      assert.equal(v[c.v.AccountState],state);
      if(state==='paused')assert.equal(run(roles.resumePrimary,v),c.paused);
      if(state==='active'||state==='blocked')assert.equal(run(roles.resumePrimary,v),c.active);
      if(state==='completed')assert.equal(run(roles.resumePrimary,v),c.catalog);
    });
    for(const state of ['active','paused','blocked','empty'])check(()=>{
      const v=initial({[c.auth]:true,[c.v.AccountState]:state,[c.v.DraftMode]:mode});
      assert.equal(run(roles[mode+'Start'],v),state==='empty'?c.empty:d.resume);
      assert.equal(v[c.v.DraftMode],mode);assert.equal(v[c.v.AccountState],state);
    });
  }
  for(const error of d.errorActions||[])check(()=>{
    const v=initial({[c.v.DraftMode]:'percent',[c.v.Origin]:'percent',[c.draft]:true});
    const destination=run(error.id,v);
    assert([c.email,c.confirm].includes(destination));
    assert.equal(v[c.v.DraftMode],'percent');assert.equal(v[c.auth],false);
  });
  if(c.key==='me')for(const f of [c.review,c.percentReview])check(()=>{
    const texts=d.frames.find(n=>n.id===f).texts.map(t=>t.text);
    assert(texts.includes('New signals only. Existing orders and positions stay unchanged.'));
  });
}
console.log(`${passed} assertions passed against exported Figma actions and visible text. Not a runtime/auth or manual Present test.`);
