'use strict';
// Browser-only synthetic recovery. Never accepts real keys, codes, documents or credentials.
let accessRecovery=null;
let recoveryEntryRole='ownerA';
const recoveryUsedCodes=new Set(),recoveryHolds=new Map(),recoveryRequests=new Map();
let recoveryOperationSequence=0;
const recoveryButton=(ru,en,action,primary=false,disabled=false)=>'<button type="button" class="btn'+(primary?' primary':'')+'" data-recovery="'+action+'"'+(disabled?' disabled':'')+'>'+pl(ru,en)+'</button>';
const recoveryStages=[['identity','Проверка личности','Identity'],['keys','Новая защита','New protection'],['result','Проверка результата','Result'],['signin','Новый вход','New sign-in']];
function recoveryLog(ru,en){accessRecovery.events.push({step:accessRecovery.step,text:[ru,en],staff:accessRecovery.staff});}
function recoveryStart(){
 const a=actor(),g=management.assignments[a.id];
 const pending=recoveryRequests.get(a.id);
 if(pending&&!pending.applied){accessRecovery=pending;accessRecovery.step='result';accessRecovery.error=pending.role===state.role?null:['Откройте исходное назначение этого аккаунта.','Open this account’s original assignment.'];account.logged=false;account.recovering=true;state.route='recovery';return;}
 accessRecovery={role:state.role,staff:a.id,owner:a.owner,returnRoute:state.route==='profile'?state.profileReturn:state.route,step:'identity',method:'backup',case:'lost',outcome:'success',identity:false,codeUsed:false,primary:null,backup:null,selectedDevice:'DEMO-KEY-A',operation:null,applied:false,error:null,events:[],revision:g.revision,grantStatus:g.status};
 account.logged=false;account.recovering=true;account.dialog=null;account.error=null;state.route='recovery';
 recoveryLog('Начато восстановление. Рабочий доступ закрыт.','Recovery started. Workspace access closed.');
}
function recoveryError(ru,en){accessRecovery.error=[ru,en];return false;}
function recoveryContextValid(){const x=accessRecovery;return !!x&&state.role===x.role&&actor().id===x.staff;}
function recoveryRevoke(){
 const x=accessRecovery,id=x.staff;
 account.otherSessions=[];account.pendingEnd=null;account.protected=false;
 management.sessions[id]='ended';management.approvals[id]='revoked';finance.proof=null;
 if(finance.own?.floorDraft)finance.own.floorDraft.approvals=finance.own.floorDraft.approvals.filter(a=>a!==id);
 if(typeof technical!=='undefined'){technical.proof=null;technical.review=null;}
 for(const p of [...finance.payouts,...Object.values(finance.policies),...(finance.own?.records||[])]){
  if(['unknown','confirmed','published','cooldown','failed'].includes(p.status))continue;
  p.approvals=(p.approvals||[]).filter(a=>a.id!==id);
  if(p.status==='approved')p.status=p.partner?'prepared':'review';
 }
 emergency.approvals=emergency.approvals.filter(a=>a.id!==id);emergency.proof=null;
 if(emergency.status==='approved')emergency.status='waiting';
 const g=management.assignments[id];g.revision++;x.revision=g.revision;
 recoveryLog('Старые сеансы и неиспользованные подтверждения отозваны.','Old sessions and unused approvals revoked.');
}
function recoveryRightsValid(){const x=accessRecovery,g=management.assignments[x.staff];return g.status==='active'&&g.revision===x.revision&&!management.revoked&&!management.stale&&(!g.expires||g.expires>management.clock)&&x.case==='lost'&&!recoveryHolds.has(x.staff);}
function recoveryAction(action){
 const x=accessRecovery;if(!recoveryContextValid())return false;x.error=null;
 if(action==='identify'&&x.step==='identity'){
  if(x.case==='both'||recoveryHolds.get(x.staff)==='both'||x.method==='external'){if(x.case==='both'){for(const id of ['STAFF-201','STAFF-202'])recoveryHolds.set(id,'both');}if(recoveryHolds.get(x.staff)==='both')x.case='both';x.step='external';recoveryLog('Ожидается независимая защищённая проверка.','Awaiting independent protected verification.');return true;}
  if(x.outcome!=='success')return recoveryError('Проверка не завершена. Доступ не выдан; повторите проверку действующим способом.','Verification did not complete. Access was not granted; retry with a valid method.');
  if(x.method==='code'&&(x.codeUsed||recoveryUsedCodes.has(x.staff)))return recoveryError('Учебный одноразовый код уже использован. Нужна другая проверка.','The synthetic one-time code was used. Another verification is required.');
  if(x.case==='compromised'){recoveryHolds.set(x.staff,'compromised');management.assignments[x.staff].status='blocked';}
  x.codeUsed=x.method==='code';if(x.codeUsed)recoveryUsedCodes.add(x.staff);x.identity=true;x.step='keys';recoveryRevoke();recoveryLog('Личность подтверждена только для замены защиты.','Identity verified for protection replacement only.');return true;
 }
 if(action==='register-primary'&&x.identity&&x.step==='keys'){x.primary={device:x.selectedDevice,verified:false};x.backup=null;return true;}
 if(action==='verify-primary'&&x.step==='keys'&&x.primary){
  if(x.outcome!=='success'||x.selectedDevice!==x.primary.device)return recoveryError('Основной способ не проверен. Повторите проверку.','Primary method was not verified. Retry the check.');
  x.primary.verified=true;recoveryLog('Новый основной способ проверен.','New primary method verified.');return true;
 }
 if(action==='register-backup'&&x.step==='keys'&&x.owner&&x.primary?.verified){
  if(x.selectedDevice===x.primary.device)return recoveryError('Нужен другой физический ключ: основной и запасной не могут быть одним устройством.','Use another physical key: primary and backup must be different devices.');
  x.backup={device:x.selectedDevice,verified:false};return true;
 }
 if(action==='verify-backup'&&x.step==='keys'&&x.backup){
  if(x.outcome!=='success'||x.selectedDevice!==x.backup.device)return recoveryError('Запасной ключ не проверен. Повторите проверку.','Backup key was not verified. Retry the check.');
  x.backup.verified=true;recoveryLog('Другой запасной ключ проверен отдельно.','A different backup key verified separately.');return true;
 }
 if(action==='apply'&&x.step==='keys'&&x.identity&&x.primary?.verified&&(!x.owner||(x.backup?.verified&&x.backup.device!==x.primary.device))){
  if(management.assignments[x.staff].revision!==x.revision)return recoveryError('Данные аккаунта изменились. Нужна новая защищённая проверка.','Account data changed. A fresh protected review is required.');
  x.operation='ACCESS-DEMO-'+(++recoveryOperationSequence)+'-'+x.staff;x.step='result';
  if(x.outcome==='failure'){x.operation=null;x.step='keys';return recoveryError('Замена не началась. Новые способы сохранены для повторной проверки.','Replacement did not start. New methods remain for another check.');}
  if(x.outcome==='unknown'){recoveryRequests.set(x.staff,x);recoveryLog('Результат замены неизвестен. Повтор запрещён.','Replacement outcome unknown. Resubmission blocked.');return true;}
  return recoveryConfirm();
 }
 if(action==='check'&&x.step==='result'&&x.operation&&!x.applied){
  if(x.outcome!=='success')return recoveryError('Нет подтверждения исходной замены. Рабочий доступ остаётся закрытым.','No confirmation of the original replacement. Workspace access stays closed.');
  return recoveryConfirm();
 }
 if(action==='signin'&&x.step==='signin'&&x.applied){
  if(x.outcome!=='success')return recoveryError('Новый вход не подтверждён. Старые сеансы не возвращаются.','New sign-in was not verified. Old sessions are not restored.');
  if(!recoveryRightsValid()){x.step='rights';return true;}
  account.logged=true;account.recovering=false;account.protected=true;account.otherSessions=[];account.notice=['Вход выполнен новой защитой. Старые сеансы и согласия не восстановлены.','Signed in with new protection. Old sessions and approvals were not restored.'];
  x.step='complete';recoveryLog('Новый вход с действующими правами.','New sign-in with current permissions.');navigate(x.returnRoute&& !['entry','logout','recovery'].includes(x.returnRoute)?x.returnRoute:'profile');return true;
 }
 if(action==='retry-identity'&&x.step==='external'&&x.case!=='both'&&recoveryHolds.get(x.staff)!=='both'){x.step='identity';x.method='backup';return true;}
 if(action==='cancel'){account.logged=false;account.recovering=false;account.dialog=null;x.step='cancelled';navigate('logout');return true;}
 return recoveryError('Этот шаг пока недоступен. Выполните предыдущую проверку.','This step is unavailable. Complete the previous check.');
}
function recoveryConfirm(){
 const x=accessRecovery;if(x.applied)return false;x.applied=true;recoveryRequests.delete(x.staff);
 account.otherSessions=[];account.protected=true;
 x.step=recoveryRightsValid()?'signin':'rights';
 recoveryLog('Замена подтверждена. Старые способы отозваны; новый вход проверяется отдельно.','Replacement confirmed. Old methods revoked; new sign-in is separate.');
 return true;
}
function recoverySelect(id,label,values,current){return '<div class="field"><label for="'+id+'">'+label+'</label><select id="'+id+'">'+options(values,current)+'</select></div>';}
function recoveryRender(selector=null){render();if(selector){document.querySelector(selector)?.focus();}else{const main=document.querySelector('#main');main?.setAttribute('tabindex','-1');main?.focus();window.scrollTo(0,0);}}
function recoveryPage(){
 const x=accessRecovery;if(!x)return '';
 const s=x.step;let body='';
 if(s==='identity')body='<h2>'+pl('Чем подтвердить, что это вы?','How can you verify your identity?')+'</h2>'+recoverySelect('recovery-case',pl('Что произошло','What happened'),[['lost',pl('Потерян способ входа','Sign-in method lost')],['compromised',pl('Подозрение на взлом / аккаунт заблокирован','Suspected compromise / account blocked')],...(x.owner?[['both',pl('Доступ потеряли оба владельца','Both owners lost access')]]:[])],x.case)+recoverySelect('recovery-method',pl('Способ проверки','Verification method'),[['backup',pl('Действующий запасной способ','Valid backup method')],['code',pl('Одноразовый код восстановления','One-time recovery code')],['external',pl('Нет доступного способа','No method available')]],x.method)+'<p>'+pl('Код разрешает только заменить защиту. Он не открывает рабочие разделы и денежные действия.','A code only allows replacing protection. It does not open the workspace or money actions.')+'</p>'+recoveryButton('Проверить личность · демо','Verify identity · demo','identify',true);
 if(s==='keys')body='<h2>'+pl('Зарегистрируйте и проверьте новую защиту','Register and verify new protection')+'</h2><p>'+pl(x.owner?'Владельцу нужны два разных физических ключа. Проверка каждого выполняется отдельно.':'Нужен защищённый способ входа по вашему действующему назначению.',x.owner?'An owner needs two different physical keys, verified separately.':'Use a protected sign-in method permitted by your current assignment.')+'</p>'+recoverySelect('recovery-device',pl('Учебное устройство','Synthetic device'),['DEMO-KEY-A','DEMO-KEY-B','DEMO-KEY-C'].map(a=>[a,a]),x.selectedDevice)+'<div class="recovery-method"><h3>'+pl('Основной способ','Primary method')+'</h3><p>'+(x.primary?x.primary.device+' · '+pl(x.primary.verified?'Проверен':'Не проверен',x.primary.verified?'Verified':'Not verified'):pl('Не зарегистрирован','Not registered'))+'</p><div class="actions">'+recoveryButton('Зарегистрировать основной','Register primary','register-primary')+(x.primary?recoveryButton('Проверить основной','Verify primary','verify-primary'): '')+'</div></div>'+(x.owner?'<div class="recovery-method"><h3>'+pl('Запасной физический ключ','Backup physical key')+'</h3><p>'+(x.backup?x.backup.device+' · '+pl(x.backup.verified?'Проверен':'Не проверен',x.backup.verified?'Verified':'Not verified'):pl('Не зарегистрирован','Not registered'))+'</p><div class="actions">'+recoveryButton('Зарегистрировать другой ключ','Register another key','register-backup')+(x.backup?recoveryButton('Проверить запасной','Verify backup','verify-backup'):'')+'</div></div>':'')+'<p>'+pl('После применения старые способы входа будут отозваны. Нужен новый вход; прежние сеансы не возвращаются.','Applying revokes old sign-in methods. A new sign-in is required; previous sessions are not restored.')+'</p>'+recoveryButton('Применить проверенную защиту','Apply verified protection','apply',true,!x.primary?.verified||(x.owner&&!x.backup?.verified));
 if(s==='result')body='<h2>'+pl('Результат замены пока неизвестен','Replacement outcome is unknown')+'</h2><p>'+x.operation+'</p><p>'+pl('Не отправляйте замену повторно. Проверяется исходный запрос; вход пока закрыт.','Do not resubmit replacement. Check the original request; sign-in remains closed.')+'</p>'+recoveryButton('Проверить исходный запрос','Check original request','check',true);
 if(s==='signin')body='<h2>'+pl('Защита восстановлена. Выполните новый вход','Protection restored. Sign in again')+'</h2><p>'+pl('Замена подтверждена. Текущее назначение проверено; новые права не выдавались.','Replacement confirmed. Current assignment checked; no new permissions granted.')+'</p>'+recoveryButton('Войти с новой защитой · демо','Sign in with new protection · demo','signin',true);
 if(s==='rights')body='<h2>'+pl('Защита заменена, рабочий доступ ещё закрыт','Protection replaced; workspace access remains closed')+'</h2><p>'+pl('Блокировка, отзыв, истечение или изменение назначения требуют отдельного решения о доступе. Проверка личности не снимает их автоматически.','Blocked, revoked, expired or changed assignments require a separate access decision. Identity verification does not remove them automatically.')+'</p><p>'+pl('После взлома нужен разбор инцидента. Возврат денежных возможностей проходит отдельное аварийное согласование. Старые сеансы и подтверждения не возвращаются.','After compromise, investigate the incident. Restoring monetary capabilities requires separate emergency approval. Old sessions and approvals are not restored.')+'</p>';
 if(s==='external')body='<h2>'+pl('Нужна независимая защищённая проверка','Independent protected verification required')+'</h2><p>'+pl(x.case==='both'?'Доступ потеряли оба владельца. Денежные действия остаются закрыты. Нет общего ключа или сотрудника, который может обойти проверку.':'Нет действующего способа подтвердить личность. Восстановление ожидает отдельной защищённой процедуры.',x.case==='both'?'Both owners lost access. Money actions remain closed. No master key or employee can bypass verification.':'No valid identity verification method. Recovery awaits a separate protected procedure.')+'</p><p>'+pl('Назначение независимых проверяющих и канал проверки ещё должны быть утверждены перед реализацией. Прототип не принимает документы и секреты.','Independent reviewers and the verification channel must be approved before implementation. The prototype accepts no documents or secrets.')+'</p>'+(x.case!=='both'?recoveryButton('Есть запасной способ','I have a backup method','retry-identity'):'');
 const stage=Math.max(0,recoveryStages.findIndex(z=>z[0]===s));
 return '<main class="recovery-shell" id="main"><header class="recovery-header"><div><h1>'+pl('Восстановление доступа','Account recovery')+'</h1><p>'+escape(pl(actor().nameRu,actor().nameEn))+' · '+x.staff+' · '+accountRole()+'</p></div>'+languageSelect('recovery-language')+'</header><ol class="recovery-steps">'+recoveryStages.map((z,i)=>'<li '+(i===stage?'aria-current="step"':'')+'>'+pl(z[1],z[2])+'</li>').join('')+'</ol><div class="recovery-layout"><section class="panel">'+(x.error?'<p role="alert" class="account-error">'+pl(...x.error)+'</p>':'')+body+'</section><aside class="recovery-context"><h2>'+pl('Доступ сейчас','Access right now')+'</h2><p>'+pl('Только восстановление защиты. Рабочие разделы и денежные действия недоступны.','Protection recovery only. Workspace and money actions are unavailable.')+'</p><h3>'+pl('Что сохраняется','What is preserved')+'</h3><p>'+pl('Сотрудник, назначение и рабочий контекст. Смена языка не сбрасывает шаг. Отправленные переводы продолжают сверку.','Employee, assignment and work context. Language changes preserve this step. Submitted transfers remain under reconciliation.')+'</p>'+recoveryButton('Завершить сеанс восстановления','End recovery session','cancel')+'</aside></div><details class="panel"><summary>'+pl('Журнал восстановления','Recovery history')+' · '+x.events.length+'</summary>'+x.events.map(e=>'<p>'+e.staff+' · '+pl(...e.text)+'</p>').join('')+'</details><details class="account-test"><summary>'+pl('Учебные ответы проверки','Synthetic verification responses')+'</summary>'+recoverySelect('recovery-outcome',pl('Ответ следующей проверки','Next check response'),[['success',pl('Подтверждено','Confirmed')],['failure',pl('Проверка не выполнена','Verification failed')],['unknown',pl('Результат неизвестен','Outcome unknown')]],x.outcome)+'</details><footer>'+pl('Учебный прототип: нет настоящих ключей, кодов, документов или входа в сервис.','Synthetic prototype: no real keys, codes, documents or service authentication.')+'</footer></main>';
}
const recoveryStandaloneBefore=accountStandalone;
accountStandalone=function(){
 if(state.route==='recovery'&&accessRecovery)return recoveryPage();
 const html=recoveryStandaloneBefore();
 if(state.route!=='entry')return html;
 const entry='<section class="panel"><h2>'+pl('Не получается войти?','Cannot sign in?')+'</h2><p>'+pl('Выберите учебный аккаунт. Рабочий вход не выполняется; сначала нужно восстановить защиту.','Choose a synthetic account. This does not sign in; protection must be restored first.')+'</p>'+recoverySelect('recovery-entry-role',pl('Аккаунт для восстановления','Account to recover'),accountFixtures.map(a=>[a.role,pl(a.ru,a.en)]),recoveryEntryRole)+'<button class="btn" data-recovery-entry>'+pl('Начать восстановление','Start recovery')+'</button></section>';
 return html.replace('</main>',entry+'</main>');
};
const recoveryAccountActionBefore=accountAction;
accountAction=function(a,el){
 if(a==='recovery-start'){if(accessRecovery&&!['complete','cancelled'].includes(accessRecovery.step))return;recoveryStart();recoveryRender();return;}
 if(a==='codes-generate'){const already=account.codesCreated;const result=recoveryAccountActionBefore(a,el);if(!already&&account.codesCreated)recoveryUsedCodes.delete(actor().id);return result;}
 if(accessRecovery&&!['complete','cancelled'].includes(accessRecovery.step)&&['enter','entry','recovery-proof','key-next'].includes(a)){recoveryError('Завершите защищённый маршрут восстановления.','Complete the protected recovery flow.');render();return;}
 return recoveryAccountActionBefore(a,el);
};
document.addEventListener('click',e=>{if(e.target.closest('[data-recovery-entry]')&&state.route==='entry'&&accountFixtures.some(a=>a.role===recoveryEntryRole)){state.role=recoveryEntryRole;account=newAccount(state.role);recoveryStart();if(!accessRecovery.operation)accessRecovery.returnRoute='profile';recoveryRender();}});
document.addEventListener('click',e=>{const b=e.target.closest('[data-recovery]');if(b&&!b.disabled){const before=accessRecovery?.step;recoveryAction(b.dataset.recovery);recoveryRender(before===accessRecovery?.step?'[data-recovery="'+b.dataset.recovery+'"]':null);}});
document.addEventListener('change',e=>{if(e.target.id==='recovery-entry-role'){recoveryEntryRole=e.target.value;return;}const x=accessRecovery;if(!x)return;const id=e.target.id;if(id==='recovery-language'){document.querySelector('#recovery-language')?.focus();return;}if(id==='recovery-outcome')x.outcome=e.target.value;else if(id==='recovery-device'&&x.step==='keys')x.selectedDevice=e.target.value;else if(id==='recovery-case'&&x.step==='identity')x.case=e.target.value;else if(id==='recovery-method'&&x.step==='identity')x.method=e.target.value;else return;x.error=null;recoveryRender('#'+id);});
