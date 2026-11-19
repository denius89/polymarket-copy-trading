// Operator-only disposable HTTP→PostgreSQL test. No SQL/admin connection in this process.
import assert from 'node:assert/strict';
import { randomBytes, randomUUID, createHmac } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { request as httpRequest } from 'node:http';
import { startPaperRuntime } from '../src/runtime.ts';

if(process.env.POLYGON_DISPOSABLE_HTTP!=='offline-http-clone')throw new Error('Explicit disposable HTTP marker required');
const [mode,dir,configPath,descriptorPath]=process.argv.slice(2);
const save=(name,value)=>writeFileSync(join(dir,name),JSON.stringify(value)+'\n',{mode:0o600,flag:'wx'});
const load=path=>JSON.parse(readFileSync(path,'utf8'));
if(mode==='prepare'){
  mkdirSync(dir,{mode:0o700});
  const key=randomBytes(32),cursor=randomBytes(32),keyId=randomBytes(16).toString('hex');
  const users=[1,2].map(ordinal=>{
    const loginId=randomUUID(),cookie=randomBytes(32).toString('base64url');
    // Independent fixture codec: never call selectedUserProof to manufacture its own expected digest.
    const mac=createHmac('sha256',key).update(Buffer.from('shadow.v00.login-verify.v1\0','ascii'));
    for(const field of ['v00-d03-07','user',loginId,'v00-test-login-cookie-v1',cookie]){
      const bytes=Buffer.from(field,'utf8'),n=Buffer.alloc(4);n.writeUInt32BE(bytes.length);mac.update(n).update(bytes);
    }
    return {ordinal,loginId,cookie,cookieDigest:mac.digest('hex')};
  });
  save('credential-key.json',{credential:{id:'credential-1',hex:key.toString('hex')}});
  save('cursor-key.json',{format:'q02-cursor-keyset-v1',enabled:true,issuerKeyId:keyId,keys:[{keyId,hex:cursor.toString('hex')}],revoked:[]});
  save('fixture-input.json',{format:'polygon-http-fixture-v1',users:users.map(({loginId,cookieDigest})=>({loginId,cookieDigest}))});
  save('private-users.json',{format:'polygon-http-private-v1',users:users.map(({ordinal,loginId,cookie})=>({ordinal,loginId,cookie}))});
  process.stdout.write('disposable_fixture_prepared=true; users=2; secrets_not_printed=true\n');
}else if(mode==='run'){
  const privateUsers=load(join(dir,'private-users.json')),descriptor=load(descriptorPath),config=load(configPath);
  assert.equal(existsSync(join(dir,'HTTP_COMPLETE')),false);assert.equal(existsSync(join(dir,'OPERATOR_OBSERVED')),false);
  assert.equal(privateUsers.format,'polygon-http-private-v1');assert.equal(descriptor.format,'polygon-http-descriptor-v1');
  assert.equal(config.ingress.mode,'direct-test');assert.equal(config.startEnabled,true);assert.equal(config.bindHost,'127.0.0.1');
  assert.equal(descriptor.users.length,2);assert.equal(privateUsers.users.length,2);
  const users=descriptor.users.map((u,i)=>{const p=privateUsers.users[i];assert.equal(u.ordinal,i+1);assert.equal(u.loginId,p.loginId);return {...u,cookie:p.cookie};});
  const runtime=await startPaperRuntime(configPath),labels=[],ids=new Set();
  const check=(label,fn)=>{fn();assert.ok(!labels.includes(label));labels.push(label);};
  async function call(user,method,path,body,changes={}){
    const bytes=body===undefined?'':JSON.stringify(body);
    const headers={Host:new URL(config.origin).host,'X-Shadow-Login-Id':user.loginId,
      Cookie:`__Host-shadow-user-login-${user.loginId}=${user.cookie}`,'Sec-Fetch-Site':'same-origin',
      ...(method==='GET'?{}:{Origin:config.origin,'Content-Type':'application/json','X-Shadow-Auth-Request':'1'}),...changes};
    return await new Promise((resolve,reject)=>{
      const req=httpRequest({host:'127.0.0.1',port:config.port,path,method,headers},res=>{
        let data='';res.setEncoding('utf8');res.on('data',x=>{data+=x;});res.on('end',()=>{
          try{assert.equal(res.headers['cache-control'],'no-store');assert.ok(res.headers['x-request-id']);
            assert.ok(!ids.has(res.headers['x-request-id']));ids.add(res.headers['x-request-id']);
            resolve({status:res.statusCode,body:JSON.parse(data)});}catch(e){reject(e);}
        });
      });req.setTimeout(7000,()=>req.destroy(new Error('HTTP test timeout')));req.on('error',reject);req.end(bytes);
    });
  }
  const get=(u,path)=>call(u,'GET',path),ver='requestSchemaVersion=v1';
  const q05=(u,type,id,actor=u.userId)=>get(u,`/api/commands/${id}?${ver}&commandType=${type}&actorRealm=user&actorId=${actor}`);
  const results=[];
  try{
    for(const u of users){
      const prefix=`user${u.ordinal}`,venue=u.ordinal===1?'polymarket':'limitless';
      let r=await get(u,`/__polygon__/identity?${ver}`);check(prefix+'_product_identity',()=>{assert.equal(r.status,200);assert.equal(r.body.userId,u.userId);});
      r=await get(u,`/api/sessions/current?${ver}`);check(prefix+'_empty_current',()=>{assert.equal(r.status,200);assert.equal(r.body.session,null);});
      const page=await get(u,`/api/traders?${ver}&venueCode=${venue}&limit=1`);
      check(prefix+'_catalog_first_page',()=>{assert.equal(page.status,200);assert.equal(page.body.items.length,1);assert.equal(typeof page.body.nextCursor,'string');});
      const next=await get(u,`/api/traders?${ver}&venueCode=${venue}&limit=1&cursor=${page.body.nextCursor}`);
      check(prefix+'_full_final_page',()=>{assert.equal(next.status,200);assert.equal(next.body.items.length,1);assert.equal(next.body.nextCursor,null);assert.notEqual(next.body.items[0].traderId,page.body.items[0].traderId);});
      r=await get(users[1-(u.ordinal-1)],`/api/traders?${ver}&venueCode=${venue}&limit=1&cursor=${page.body.nextCursor}`);
      check(prefix+'_cursor_reader_isolation',()=>assert.equal(r.status,400));
      r=await get(u,`/api/traders/${venue}/${u.traderId}?${ver}`);check(prefix+'_card',()=>{assert.equal(r.status,200);assert.equal(r.body.trader.traderId,u.traderId);});
      const create={requestSchemaVersion:'v1',clientCommandId:randomUUID(),locale:'ru',step:'configure',entryContext:'catalog',
        venueId:u.venueId,traderId:u.traderId,selectedMode:u.ordinal===1?'fixed':'percent',rawBudget:u.ordinal===1?'200\0':'100',
        rawFixedAmount:'20',rawCopyPercent:u.ordinal===1?'ignored':'3,5',rawMarketLimitPercent:u.ordinal===1?'10':'5',
        rawDailyBuyLimitPercent:u.ordinal===1?'15':'10',proposedTimezone:'UTC'};
      r=await call(u,'POST','/api/demo/drafts',create,{Origin:'https://wrong.invalid'});check(prefix+'_origin_denied',()=>assert.equal(r.status,403));
      r=await call(u,'POST','/api/demo/drafts',{...create,extra:true});check(prefix+'_unknown_field_denied',()=>assert.equal(r.status,400));
      r=await call(u,'POST','/api/demo/drafts',create,{Cookie:''});check(prefix+'_missing_cookie_denied',()=>assert.equal(r.status,401));
      const created=await call(u,'POST','/api/demo/drafts',create);
      check(prefix+'_create',()=>{assert.equal(created.status,201);assert.equal(created.body.receipt.result.changeKind,'created');});
      const draftId=created.body.receipt.result.draftId;
      r=await call(u,'POST','/api/demo/drafts',create);check(prefix+'_exact_create_replay',()=>assert.deepEqual(r.body.receipt,created.body.receipt));
      r=await call(u,'POST','/api/demo/drafts',{...create,rawBudget:'900'});check(prefix+'_key_reuse_denied',()=>{assert.equal(r.status,409);assert.equal(r.body.reasonCode,'KEY_REUSE_CONFLICT');});
      let version='1';
      if(u.ordinal===1){
        r=await get(u,`/api/demo/drafts/${draftId}?${ver}`);check('nul_raw_and_error_provenance',()=>{
          assert.equal(r.body.draft.rawBudget,'200\0');assert.equal(r.body.fieldErrors[0].code,'INVALID_DECIMAL');
          assert.equal(r.body.fieldErrorsSource.receiptId,created.body.receipt.receiptId);
        });
        r=await call(u,'POST','/api/demo/validate',{requestSchemaVersion:'v1',draftId,expectedDraftVersion:'1',proposedTimezone:'UTC'});
        check('invalid_review_persisted',()=>{assert.equal(r.status,200);assert.equal(r.body.review.allowedToStart,false);assert.equal(r.body.review.primaryReasonCode,'NUMERIC_SETTINGS_INVALID');});
        const update={...create,clientCommandId:randomUUID(),expectedDraftVersion:'1',rawBudget:'300'};
        const updated=await call(u,'PATCH',`/api/demo/drafts/${draftId}`,update);version='2';
        check('real_update',()=>{assert.equal(updated.status,200);assert.equal(updated.body.receipt.result.draftVersion,'2');});
        r=await call(u,'PATCH',`/api/demo/drafts/${draftId}`,{...update,clientCommandId:randomUUID(),expectedDraftVersion:'2'});
        check('unchanged_new_key',()=>{assert.equal(r.status,200);assert.equal(r.body.receipt.result.changeKind,'unchanged');});
        r=await get(u,`/api/demo/drafts/${draftId}?${ver}`);check('unchanged_preserves_input_source',()=>assert.equal(r.body.fieldErrorsSource.receiptId,updated.body.receipt.receiptId));
        const stale={...update,clientCommandId:randomUUID()};r=await call(u,'PATCH',`/api/demo/drafts/${draftId}`,stale);const refusal=r;
        check('durable_version_refusal',()=>{assert.equal(r.status,409);assert.equal(r.body.receipt.reasonCode,'VERSION_CONFLICT');});
        r=await q05(u,'C04',stale.clientCommandId);check('q05_rejected_is_200',()=>{assert.equal(r.status,200);assert.deepEqual(r.body.receipt,refusal.body.receipt);});
        r=await call(u,'POST','/api/demo/drafts',create);check('historical_receipt_after_edit',()=>assert.deepEqual(r.body.receipt,created.body.receipt));
      }
      const review=await call(u,'POST','/api/demo/validate',{requestSchemaVersion:'v1',draftId,expectedDraftVersion:version,proposedTimezone:'UTC'});
      check(prefix+'_valid_review',()=>{assert.equal(review.status,200);assert.equal(review.body.review.allowedToStart,true);
        assert.deepEqual(review.body.review.effectiveMarketLimit,{n:u.ordinal===1?'30':'5',d:'1'});});
      const start={requestSchemaVersion:'v1',clientCommandId:randomUUID(),reviewId:review.body.review.reviewId,expectedDraftVersion:version,expectedSlot:review.body.review.expectedSlot};
      const started=await Promise.all([call(u,'POST','/api/sessions',start),call(u,'POST','/api/sessions',start)]);
      check(prefix+'_same_key_concurrent_start',()=>{assert.equal(started[0].status,201);assert.equal(started[1].status,201);assert.deepEqual(started[0].body.receipt,started[1].body.receipt);});
      const receipt=started[0].body.receipt,sessionId=receipt.result.sessionId;
      r=await get(u,`/api/sessions/current?${ver}`);
      check(prefix+'_same_empty_session',()=>{assert.equal(r.status,200);assert.equal(r.body.session.summary.sessionId,sessionId);
        assert.equal(r.body.session.financialSnapshot.contentState,'EMPTY');assert.deepEqual(r.body.session.financialSnapshot.equity,{n:u.ordinal===1?'300':'100',d:'1'});
        assert.equal(r.body.session.financialSnapshot.tradeCount,'0');assert.equal(r.body.session.summary.timezoneDatabaseVersion,config.calendarProfile.tzdb);
        assert.equal(Date.parse(r.body.session.summary.evaluationDeadlineAt)-Date.parse(r.body.session.summary.startedAt),14*86400000);});
      const current=r;r=await get(u,`/api/sessions/${sessionId}?${ver}`);check(prefix+'_read_same_by_id',()=>assert.deepEqual(r.body.session,current.body.session));
      r=await q05(u,'C06',start.clientCommandId);check(prefix+'_q05_start_history',()=>{assert.equal(r.status,200);assert.deepEqual(r.body.receipt,receipt);});
      results.push({u,draftId,sessionId,start});
    }
    const [a,b]=results;
    for(const [label,path]of [['draft',`/api/demo/drafts/${a.draftId}?${ver}`],['session',`/api/sessions/${a.sessionId}?${ver}`]]){
      const r=await get(b.u,path);check('cross_user_'+label+'_hidden',()=>assert.equal(r.status,404));
    }
    let r=await q05(b.u,'C06',a.start.clientCommandId,a.u.userId);check('cross_user_command_hidden',()=>assert.equal(r.status,404));
    r=await call(b.u,'POST','/api/sessions',{...b.start,clientCommandId:randomUUID()});check('used_draft_priority',()=>{assert.equal(r.status,409);assert.equal(r.body.receipt.reasonCode,'DRAFT_USED');});
    const observationLease=await runtime.pool.connect();
    try{
      save('HTTP_COMPLETE',{suite:'polygon-http-db-v1',passed:labels.length});
      const until=Date.now()+60000;
      while(!existsSync(join(dir,'OPERATOR_OBSERVED'))){
        if(Date.now()>=until)throw new Error('Independent SQL observation acknowledgement missing');
        await new Promise(resolve=>setTimeout(resolve,200));
      }
      assert.equal(readFileSync(join(dir,'OPERATOR_OBSERVED'),'utf8').trim(),'pass');
    }finally{observationLease.release();}
    process.stdout.write(JSON.stringify({suite:'polygon-http-db-v1',passed:labels.length,labels,independentObserverAcknowledged:true,scope:'real internal HTTP and PostgreSQL; synthetic Auth fixture; no provider/browser/gateway/unknown-COMMIT proof'})+'\n');
  }finally{await runtime.close();}
}else throw new Error('Expected prepare or run');
