'use strict';
// One in-memory model, two views. This module never calls a product API.
const sharedClientCases={
 'U-DEMO-001':{uid:'U-DEMO-001',sid:'S-DEMO-001',oid:'ORD-001',venue:'Polymarket'},
 'U-DEMO-002':{uid:'U-DEMO-002',sid:'S-DEMO-002',oid:'ORD-002',ticket:'T-101',rec:'REC-101',venue:'Polymarket'},
 'U-DEMO-005':{uid:'U-DEMO-005',sid:'S-DEMO-005',oid:'ORD-005',ticket:'T-102',rec:'REC-103',venue:'Limitless'}
};
const clientRouteKeys=['home','order','funds','terms','positions','traders','activity','support','thread','help','notifications','profile'];
function clientHash(){const match=(window.location?.hash||'').match(/^#client\/(U-DEMO-\d{3})\/([a-z]+)$/);return match&&clientRouteKeys.includes(match[2])?{uid:match[1],route:match[2]}:null;}
function clientURL(){if(window.history?.replaceState)window.history.replaceState(null,'',clientView.active?'#client/'+clientView.uid+'/'+clientView.route:window.location.pathname+window.location.search);}
let clientView={active:false,uid:null,sid:null,route:'home',locale:'ru',returnRoute:'home',admin:null,scroll:0,draft:'',notice:null,selectedMessage:null};
const cl=(ru,en)=>clientView.locale==='ru'?ru:en;
const clientUser=()=>users.find(u=>u.id===clientView.uid);
const clientCanRead=uid=>!!account?.logged&&actor().users&&actor().money&&(!actor().limited||uid==='U-DEMO-002')&&!!users.find(u=>u.id===uid);
function sharedSessionView(u,s){
 if(!s)return null;
 const key=trading.selected[u.id]||tradingSets[u.id]?.[0],c=tradingCases[key];
 if(!c)return {...s,snapshot:'BASE-'+s.id};
 const result={...s,snapshot:s.id+'/'+key,tradeState:key};
 if(['stale','reconnected'].includes(key))return {...result,available:null,reserved:null,positionsCost:null};
 result.reserved=c.reserve;
 if(key==='unknown')return result;
 result.positionsCost=c.position;
 if(['sellPartial','sellUnknown','complete'].includes(key))result.available=null;
 else if(c.fill!==null&&c.reserve!==null)result.available=s.budget-c.reserve-c.position;
 return result;
}
function clientSession(){const u=clientUser();return u?sharedSessionView(u,u.sessions.find(s=>s.id===clientView.sid)):null;}
const clientAmount=v=>v===null||v===undefined?cl('Не подтверждено','Not confirmed'):new Intl.NumberFormat(clientView.locale==='ru'?'ru-RU':'en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(v)+' $';
const clientButton=(ru,en,a,extra='',primary=false)=>'<button type="button" class="btn'+(primary?' primary':'')+'" data-client="'+a+'" '+extra+'>'+cl(ru,en)+'</button>';
function clientOpen(uid){
 if(!clientCanRead(uid))return false;
 const u=users.find(x=>x.id===uid);
 clientView={...clientView,active:true,uid,sid:u.sessions[0]?.id||null,route:'home',returnRoute:'home',locale:state.locale,admin:structuredClone(state),notice:null};
 clientURL();render();window.scrollTo(0,0);return true;
}
function clientReturnAdmin(){
 if(!clientView.active)return false;
 const saved=clientView.admin;clientView.active=false;
 if(saved)Object.assign(state,structuredClone(saved));clientURL();
 render();window.scrollTo(0,saved?.scroll||0);return true;
}
function clientNavigate(route){
 if(!clientView.active||!clientCanRead(clientView.uid))return false;
 if(technicalLocked()&&route!=='status')return false;
 if(['help','profile','notifications','support'].includes(route)&&!['help','profile','notifications','support','thread'].includes(clientView.route)){
  clientView.returnRoute=clientView.route;clientView.scroll=window.scrollY;
 }
 clientView.route=route;clientView.notice=null;clientURL();render();window.scrollTo(0,0);
 document.querySelector('#main h1')?.focus();return true;
}
function clientBack(){
 const route=clientView.returnRoute;clientView.route=route;clientURL();render();window.scrollTo(0,clientView.scroll);return true;
}
function clientTrade(){
 const uid=clientView.uid,key=trading.selected[uid]||tradingSets[uid]?.[0];
 return {key,c:tradingCases[key]};
}
function clientPublicThread(){
 const ticket=support.records.find(x=>x.uid===clientView.uid&&x.sid===clientView.sid);
 if(!ticket)return null;
 return {id:ticket.id,uid:ticket.uid,sid:ticket.sid,status:ticket.status,subject:ticket.subject,body:ticket.body,
  messages:ticket.messages.filter(m=>m.kind==='reply').map(m=>({id:m.id,body:m.body,status:'sent'}))};
}
function clientTerms(){
 const p=financeCurrentPolicy('vip:'+clientView.uid),u=clientUser();
 const expired=p&&p.extra.duration!=='indefinite'&&fnow()>=financeUTC(p.extra.end);
 const vip=p?!expired&&p.extra.intentVIP!=='remove':!!u.vip;
 return {vip,fee:0,version:p?.version||null,start:p?.effective||null,end:p?.extra?.duration==='indefinite'?null:p?.extra?.end||null,futureRate:vip&&p?p.value:null};
}
function clientHeader(title){
 const u=clientUser(),s=clientSession();
 return '<header class="client-header"><strong class="brand">shadow</strong><div class="actions">'+clientButton('Помощь','Help','route','data-route="help"')+clientButton('Уведомления','Notifications','route','data-route="notifications"')+clientButton('Профиль','Profile','route','data-route="profile"')+'</div></header><h1 tabindex="-1">'+escape(title)+'</h1><p class="muted">'+escape(u.name)+' · '+u.id+(s?' · '+s.venue+' · '+s.id:'')+'</p><p class="client-demo-note">'+cl('Демо · без реальных денег · Paper Alpha: комиссия 0%','Demo · no real money · Paper Alpha fee 0%')+'</p>';
}
function clientFunds(){
 const s=clientSession();
 if(!s)return '<section class="panel"><h2>'+cl('Сессия ещё не запущена','No session started yet')+'</h2></section>';
 const blocked=tradingSets[clientView.uid]&&['unknown','stale','reconnected','conflict','sellUnknown'].includes(clientTrade().key);
 return '<section class="panel"><h2>'+cl('Средства демо-сессии','Demo session funds')+'</h2><dl class="client-money">'+
 [[cl('Исходный бюджет','Original budget'),s.budget],[cl('Доступно','Available'),s.available],[cl('В резерве заявок','Reserved for orders'),s.reserved],[cl('Учётная стоимость позиций','Position cost basis'),s.positionsCost]].map(([k,v])=>'<div><dt>'+k+'</dt><dd>'+clientAmount(v)+'</dd></div>').join('')+
 '</dl><p class="muted">'+cl('Учётная стоимость — не текущая рыночная оценка и не прибыль.','Cost basis is neither current market valuation nor profit.')+'</p><small>'+cl('Снимок','Snapshot')+': '+s.snapshot+'</small></section>'+
 (blocked?'<section class="alert"><h2>'+cl('Новые покупки временно недоступны','New buys temporarily unavailable')+'</h2><p>'+cl('Сначала требуется сверка результата. Средства не освобождаются из-за тайм-аута.','The outcome must be reconciled first. A timeout does not release funds.')+'</p>'+clientButton('Посмотреть заявку','View order','route','data-route="order"')+'</section>':'');
}
function clientOrder(){
 const s=clientSession(),{c,key}=clientTrade();if(!s||!c)return '<section class="panel">'+cl('В этом примере нет проблемной заявки.','No problematic order in this example.')+'</section>';
 const title=cl(...c.label);
 return '<section class="alert"><h2>'+title+'</h2><p>'+escape(cl(...c.why))+'</p></section><section class="panel"><h2>'+cl('Что подтверждено','Confirmed evidence')+'</h2><dl class="client-money">'+
 [[cl('Исходная покупка','Original purchase'),20],[cl('Подтверждено по покупке','Confirmed purchase fill'),c.fill],[cl('Может исполниться / резерв','May still fill / reserve'),c.reserve],[cl('Окончательно отменено','Finally cancelled'),c.cancelled]].map(([k,v])=>'<div><dt>'+k+'</dt><dd>'+clientAmount(v)+'</dd></div>').join('')+
 '</dl><p>'+escape(cl(...c.event))+'</p><small>'+s.id+' · '+s.id.replace('S-DEMO-','ORD-')+' · '+key+'</small></section><p class="muted">'+cl('Это просмотр исходной заявки. Повторная отправка не предлагается.','This is the original order view. Resubmission is not offered.')+'</p>';
}
function clientHome(){
 const s=clientSession();return clientFunds()+(s?'<section class="panel"><h2>'+cl('Копирование','Copying')+'</h2><p>'+cl(s.manualPaused?'Пауза пользователя':'Текущее состояние сессии',s.manualPaused?'Paused by user':'Current session state')+'</p><p>'+s.id+' · '+s.venue+'</p>'+
 clientButton('Средства','Funds','route','data-route="funds"')+clientButton('Мои условия','My terms','route','data-route="terms"')+
 clientButton(s.manualPaused?'Возобновить копирование':'Приостановить копирование',s.manualPaused?'Resume copying':'Pause copying','pause','',false)+'</section>':'');
}
function clientTermsPage(){
 const p=clientTerms();return '<section class="panel"><h2>'+cl('Действующая комиссия Shadow','Effective Shadow fee')+'</h2><strong class="client-fee">0%</strong><p>'+cl('Paper Alpha бесплатна. VIP не включает платную версию.','Paper Alpha is free. VIP does not enable the paid version.')+'</p><p>'+cl(p.vip?'VIP назначен':'VIP не назначен',p.vip?'VIP assigned':'VIP not assigned')+'</p>'+
 (p.version?'<p>'+cl('Действующая версия условий','Effective terms version')+' v'+p.version+' · '+escape(p.start)+(p.end?' — '+escape(p.end)+' UTC':' · '+cl('бессрочно','indefinite'))+'</p>':'')+
 (p.futureRate!==null?'<p>'+cl('Будущая индивидуальная ставка','Future individual rate')+': '+escape(p.futureRate)+'%. '+cl('Сейчас не применяется.','Not applied now.')+'</p>':'')+'</section>';
}
function clientThreadPage(){
 const x=clientPublicThread();if(!x)return '<section class="panel">'+cl('Обращений в этом примере нет.','No conversations in this example.')+'</section>';
 return '<section class="panel"><h2>'+x.id+' · '+escape(cl(...x.subject))+'</h2><p>'+cl(...supportStatuses[x.status])+'</p><article class="support-message"><strong>'+escape(clientUser().name)+'</strong><p>'+escape(x.body)+'</p></article>'+
 x.messages.map(m=>'<article class="support-message"><strong>'+cl('Ответ поддержки','Support reply')+'</strong><p>'+escape(m.body)+'</p><small>'+m.id+' · '+cl('Отправлено · доставка и прочтение не подтверждены','Sent · delivery and read status not confirmed')+'</small></article>').join('')+
 (!x.messages.length?'<p class="muted">'+cl('Ответ поддержки пока не получен.','No support reply received yet.')+'</p>':'')+'</section>';
}
function clientBody(){
 const routes={
 home:clientHome,order:clientOrder,funds:clientFunds,terms:clientTermsPage,
 traders:()=>'<section class="panel"><h2>Momentum Fox</h2><p>Polymarket · '+cl('Демо-профиль','Demo profile')+'</p><p>'+cl('У вас уже есть текущая сессия. Выбор нового трейдера доступен после её завершения и сверки.','You already have a current session. A new trader can be selected after completion and reconciliation.')+'</p>'+clientButton('Открыть текущую сессию','Open current session','route','data-route="home"')+'</section>',
 positions:()=>'<section class="panel"><h2>'+cl('Позиции текущей сессии','Current session positions')+'</h2><p>'+cl('Учётная стоимость','Cost basis')+': '+clientAmount(clientSession()?.positionsCost)+'</p><p>'+cl('Количество и рыночная оценка в этом снимке не подтверждены.','Quantity and market valuation are not confirmed in this snapshot.')+'</p></section>',
 activity:()=>clientOrder(),
 support:clientThreadPage,thread:clientThreadPage,
 help:()=>'<section class="panel"><h2>'+cl('Помощь по текущей сессии','Help with this session')+'</h2><details><summary>'+cl('Почему результат заявки неизвестен?','Why is the order outcome unknown?')+'</summary><p>'+cl('Отсутствие ответа не доказывает отказ. Сверяем исходную заявку, сохраняем резерв и не отправляем её повторно.','A missing reply is not evidence of failure. The original order is reconciled, the reserve remains and the order is not resent.')+'</p></details>'+clientButton('Обращение в поддержку','Support conversation','route','data-route="support"')+'</section>',
 notifications:()=>'<section class="panel"><h2>'+cl('По вашей сессии','For your session')+'</h2><p>'+cl('Открывайте исходную заявку или публичную переписку. Просмотр уведомления не меняет результат операции.','Open the original order or public conversation. Viewing a notification does not change the operation outcome.')+'</p>'+clientButton('Проверяемая заявка','Order under review','notification-order')+clientButton('Ответы поддержки','Support replies','route','data-route="support"')+'</section>',
 profile:()=>'<section class="panel"><h2>'+cl('Мой профиль','My profile')+'</h2><p>'+escape(clientUser().name)+' · '+clientView.uid+'</p><div class="field"><label for="client-language">'+cl('Язык интерфейса','Interface language')+'</label><select id="client-language"><option value="ru"'+(clientView.locale==='ru'?' selected':'')+'>Русский · RU</option><option value="en"'+(clientView.locale==='en'?' selected':'')+'>English · EN</option></select></div><p>'+cl('Язык сохраняет текущую сессию, выбранную заявку и паузу. Данные сотрудника не меняются.','Language preserves this session, selected order and pause. Staff identity is unchanged.')+'</p>'+clientButton('Мои условия','My terms','route','data-route="terms"')+'</section>'
 };return (routes[clientView.route]||clientHome)();
}
function clientRender(){
 if(!clientCanRead(clientView.uid)){clientView.active=false;return render();}
 const label=({home:['Главная','Home'],traders:['Трейдеры','Traders'],order:['Заявка','Order'],funds:['Средства','Funds'],terms:['Ваши условия','Your terms'],positions:['Позиции','Positions'],activity:['Активность','Activity'],support:['Поддержка','Support'],thread:['Переписка','Conversation'],help:['Помощь','Help'],notifications:['Уведомления','Notifications'],profile:['Профиль','Profile']})[clientView.route]||['Главная','Home'];
 document.documentElement.lang=clientView.locale;document.title='Shadow · '+cl(...label);
 const toolbar='<aside class="client-review-bar"><span>'+cl('Учебный просмотр клиента','Synthetic client view')+'</span>'+clientButton('Вернуться в админку','Return to admin','return-admin')+'</aside>';
 const status='<main id="main" class="client-workspace"><strong class="brand">shadow</strong><h1 tabindex="-1">'+cl('Сервис временно недоступен','Service temporarily unavailable')+'</h1><section class="alert"><p>'+cl('Приложение закрыто. Новые торговые и денежные действия недоступны.','The app is closed. New trading and money actions are unavailable.')+'</p><p>'+cl('Уже отправленные операции могут завершиться. Возобновление не повторяет старые заявки.','Previously submitted operations may complete. Restoring access does not replay old orders.')+'</p></section>'+clientButton('Обновить статус','Refresh status','refresh')+'</main>';
 const main='<main id="main" class="client-workspace">'+clientHeader(cl(...label))+
 (clientView.notice?'<p class="support-notice" role="status">'+escape(clientView.notice)+'</p>':'')+
 (['help','profile','notifications','support','thread'].includes(clientView.route)?clientButton('Вернуться к сессии','Back to session','back'):'')+
 clientBody()+'<nav class="client-bottom" aria-label="'+cl('Основная навигация','Main navigation')+'">'+[['home','Главная','Home','grid'],['traders','Трейдеры','Traders','users'],['positions','Позиции','Positions','users'],['activity','Активность','Activity','pulse']].map(([key,ru,en,i])=>'<button data-client="route" data-route="'+key+'" '+(clientView.route===key?'aria-current="page"':'')+'>'+icon(i)+cl(ru,en)+'</button>').join('')+'</nav></main>';
 document.querySelector('#announcer').textContent='';
 document.querySelector('#app').innerHTML=toolbar+(technicalLocked()?status:main);
}
function clientAction(a,el){
 if(a==='open')return clientOpen(el.dataset.uid||state.userId);
 if(a==='return-admin')return clientReturnAdmin();
 if(!clientView.active||!clientCanRead(clientView.uid))return false;
 if(a==='refresh'){render();return true;}
 if(technicalLocked())return false;
 if(a==='route')return clientNavigate(el.dataset.route);
 if(a==='back')return clientBack();
 if(a==='notification-order'){clientView.returnRoute='order';return clientNavigate('order');}
 if(a==='pause'){
  const u=clientUser(),s=u.sessions.find(s=>s.id===clientView.sid),{key}=clientTrade();if(!s)return false;
  if(s.manualPaused&&['unknown','stale','reconnected','conflict','sellUnknown'].includes(key)){clientView.notice=cl('Возобновление недоступно до сверки.','Resume is unavailable until reconciliation.');render();return false;}
  s.manualPaused=!s.manualPaused;render();return true;
 }
 return false;
}
const clientBaseRender=render;
render=function(){
 if(clientView.active)return clientRender();
 const direct=clientHash();if(direct&&clientCanRead(direct.uid)){clientOpen(direct.uid);clientView.route=direct.route;clientURL();return clientRender();}
 clientBaseRender();
 if(account?.logged&&actor().users&&['user','session','order','ticket','reconciliationItem','technical','emergency'].includes(state.route)){
  const uid=state.route==='ticket'?supportCurrent()?.uid:state.route==='reconciliationItem'?reconciliationCurrent()?.uid:state.userId;
  const host=document.querySelector('#main .top');if(host&&clientCanRead(uid))host.insertAdjacentHTML('beforeend','<button class="btn client-open" data-client="open" data-uid="'+uid+'">'+pl('Посмотреть как клиент','View as client')+'</button>');
 }
};
document.addEventListener('click',e=>{const el=e.target.closest('[data-client]');if(el&&!el.disabled)clientAction(el.dataset.client,el);});
window.addEventListener?.('hashchange',()=>{const d=clientHash();if(d&&clientCanRead(d.uid)){if(!clientView.active||clientView.uid!==d.uid)clientOpen(d.uid);clientView.route=d.route;clientURL();render();}else if(!d&&clientView.active)clientReturnAdmin();});
document.addEventListener('change',e=>{if(e.target.id==='client-language'&&clientView.active&&['ru','en'].includes(e.target.value)){clientView.locale=e.target.value;render();}});
render();
