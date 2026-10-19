// Run through use_figma with one CONFIG literal per Final page.
// Prototype state is illustrative. This does not implement authentication/storage.
const c = CONFIG;
const p = await figma.getNodeByIdAsync(c.page);
await figma.setCurrentPageAsync(p);
c.resume=p.children.find(n=>n.name==='ADR-0048 · '+c.key+' · existing session')?.id;
if(!c.resume)throw new Error('Continuation frame must exist before route patch');
const ids = [...new Set([c.setup,c.percentSetup,c.review,c.percentReview,c.email,c.confirm,
  c.welcome,c.before,c.catalog,c.resume,c.launch,c.landing,...c.errors].filter(Boolean))];
const loaded = await Promise.all(ids.map(id=>figma.getNodeByIdAsync(id)));
const frames = new Map(loaded.filter(Boolean).map(n=>[n.id,n]));
const visible=(n,root)=>{while(n&&n!==root){if(n.visible===false)return false;n=n.parent;}return true;};
if(!c.mobile){
  const confirm=frames.get(c.confirm),welcome=frames.get(c.welcome);
  c.verify=confirm.findAll(n=>'reactions' in n&&visible(n,confirm)&&n.name==='Button/Send secure link')[0]?.id;
  c.mainPrimary=welcome.findAllWithCriteria({types:['INSTANCE']}).find(n=>visible(n,welcome)&&n.componentProperties.Style?.value==='Primary')?.id;
  c.mainActions=[c.mainPrimary];
  if(!c.verify||!c.mainPrimary)throw new Error('Desktop email/main controls not found');
}
async function loadText(t){await Promise.all(t.getStyledTextSegments(['fontName']).map(s=>figma.loadFontAsync(s.fontName)));}
const mutatedNodeIds=[];
const before=[];
const nav=id=>({type:'NODE',destinationId:id,navigation:'NAVIGATE',transition:null,resetScrollPosition:true});
const set=(id,value)=>({type:'SET_VARIABLE',variableId:id,variableValue:{type:typeof value==='boolean'?'BOOLEAN':'STRING',resolvedType:typeof value==='boolean'?'BOOLEAN':'STRING',value}});
const eq=(id,value)=>({type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'EQUALS',expressionArguments:[{type:'VARIABLE_ALIAS',resolvedType:typeof value==='boolean'?'BOOLEAN':'STRING',value:{type:'VARIABLE_ALIAS',id}},{type:typeof value==='boolean'?'BOOLEAN':'STRING',resolvedType:typeof value==='boolean'?'BOOLEAN':'STRING',value}]}});
const branch=(id,value,actions)=>({condition:eq(id,value),actions});
const cond=blocks=>({type:'CONDITIONAL',conditionalBlocks:blocks});
const say=c.ru?{
  active:'Сессия уже активна. Новая не запущена; черновик настройки сохранён.',
  paused:'Сессия на паузе. Вход её не возобновляет; черновик настройки сохранён.',
  blocked:'Остались позиции или незавершённая сверка. Новая сессия недоступна; черновик сохранён.',
  completed:'Сессия завершена; открытых позиций и незавершённой сверки нет. Можно выбрать трейдера для новой проверки.'
}:{
  active:'A session is already active. No new session was started; your settings draft is kept.',
  paused:'Your session is paused. Signing in does not resume it; your settings draft is kept.',
  blocked:'Positions or reconciliation are still open. A new session is unavailable; your draft is kept.',
  completed:'Your session is complete, with no open positions or reconciliation. You can choose a trader for a new check.'
};
const resumeActions=state=>[set(c.v.ResumeBody,say[state]),set(c.v.ResumeCta,state==='completed'?(c.ru?'Выбрать трейдера':'Choose a trader'):(c.ru?'Открыть текущую сессию':'Open current session')),set(c.stage,state==='paused'?'paused':state==='completed'?'completed':'active'),nav(c.resume)];
const priorities=()=>[
  branch(c.v.AccountState,'empty',[set(c.stage,'empty'),nav(c.empty)]),
  ...['active','paused','blocked','completed'].map(s=>branch(c.v.AccountState,s,resumeActions(s)))
];
const draftBranches=()=>[
  branch(c.v.DraftMode,'percent',[nav(c.percentReview)]),
  branch(c.v.DraftMode,'fixed',[nav(c.review)]),
  {actions:[set(c.stage,'before'),nav(c.catalog)]}
];
async function reactions(id,actions){
  const n=await figma.getNodeByIdAsync(id);
  if(!n||!('setReactionsAsync' in n))throw new Error('Missing action '+id);
  before.push({id,actions:n.reactions});
  // The bridge only preserves two blocks in one CONDITIONAL. Compile ordered
  // decisions to binary guarded conditions; exactly one branch may navigate.
  const compiled=[];
  for(const a of actions){
    if(a.type!=='CONDITIONAL'||a.conditionalBlocks.length<=2){compiled.push(a);continue;}
    compiled.push(set(c.v.RouteChosen,false));
    for(const b of a.conditionalBlocks){
      const free=eq(c.v.RouteChosen,false);
      const condition=b.condition?{type:'EXPRESSION',resolvedType:'BOOLEAN',value:{expressionFunction:'AND',expressionArguments:[free,b.condition]}}:free;
      compiled.push(cond([{condition,actions:[set(c.v.RouteChosen,true),...b.actions]},{actions:[]}]));
    }
  }
  await n.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:compiled}]);
  mutatedNodeIds.push(id);
}
function primary(f){
  const a=f.children.filter(n=>n.type==='INSTANCE'&&visible(n,f)&&/Action/.test(n.name));
  const b=a.find(n=>Object.values(n.componentProperties).some(v=>v.type==='VARIANT'&&v.value==='Primary'));
  if(!b)throw new Error('Missing primary action '+f.id);
  return b;
}
async function label(n,text){
  const texts=n.type==='TEXT'?[n]:n.findAllWithCriteria({types:['TEXT']}).filter(t=>visible(t,n));
  await Promise.all(texts.map(loadText));
  if(n.type==='INSTANCE'){
    const key=Object.keys(n.componentProperties).find(k=>n.componentProperties[k].type==='TEXT'&&/Label/i.test(k));
    if(key){n.setProperties({[key]:text});mutatedNodeIds.push(n.id);return;}
  }
  const t=n.type==='TEXT'?n:n.findAllWithCriteria({types:['TEXT']}).find(t=>visible(t,n));
  if(t){t.characters=text;mutatedNodeIds.push(t.id);}
}
const roles={};
for(const mode of ['fixed','percent']){
  const setup=frames.get(mode==='fixed'?c.setup:c.percentSetup);
  const review=frames.get(mode==='fixed'?c.review:c.percentReview);
  const toReview=mode==='fixed'?c.review:c.percentReview;
  const toSetup=mode==='fixed'?c.setup:c.percentSetup;
  const setupButton=primary(setup),startButton=primary(review);
  roles[mode+'Setup']=setupButton.id;roles[mode+'Start']=startButton.id;
  await reactions(setupButton.id,[set(c.draft,true),set(c.v.DraftMode,mode),nav(toReview)]);
  await label(setupButton,c.ru?'Проверить настройки':'Review settings');
  const start=[
    branch(c.v.AccountState,'empty',[nav(c.empty)]),
    ...['active','paused','blocked'].map(s=>branch(c.v.AccountState,s,resumeActions(s))),
    branch(c.auth,true,[set(c.draft,false),set(c.v.DraftMode,'none'),set(c.v.AccountState,'empty'),set(c.stage,'empty'),nav(c.launch)]),
    {actions:[set(c.draft,true),set(c.v.DraftMode,mode),set(c.v.Origin,mode),nav(c.email)]}
  ];
  await reactions(startButton.id,[cond(start)]);
  await label(startButton,c.ru?'Запустить демо':'Start demo');
  const edit=review.findAll(n=>'reactions' in n&&visible(n,review)&&/Изменить настройки|Change settings/.test(n.name));
  for(const n of edit){await reactions(n.id,[set(c.v.DraftMode,mode),nav(toSetup)]);roles[mode+'Edit']=n.id;}
}
roles.confirm=c.verify;
await reactions(c.verify,[set(c.auth,true),cond([...priorities(),...draftBranches()])]);
const back=cond([
  branch(c.v.Origin,'percent',[nav(c.percentReview)]),
  branch(c.v.Origin,'fixed',[nav(c.review)]),
  {actions:[nav(c.landing||c.welcome)]}
]);
await reactions(c.emailBack,[back]);
await reactions(c.confirmBack,[nav(c.email)]);
await label(await figma.getNodeByIdAsync(c.emailBack),c.ru?'Назад':'Back');
await label(await figma.getNodeByIdAsync(c.confirmBack),c.ru?'Изменить email':'Change email');
// Main entry retains an existing draft; guest browsing does not authenticate.
const newStage=cond([branch(c.v.AccountState,'new',[set(c.stage,'before')]),{actions:[]}]);
for(const id of c.mainActions)await reactions(id,[set(c.v.Origin,'main'),newStage,nav(c.email)]);
if(c.mainPrimary)await label(await figma.getNodeByIdAsync(c.mainPrimary),c.ru?'Начать':'Get started');
if(c.guestAction){await reactions(c.guestAction,[newStage,nav(c.catalog)]);await label(await figma.getNodeByIdAsync(c.guestAction),c.ru?'Трейдеры':'Browse traders');}
const resumeButtons=frames.get(c.resume).findAllWithCriteria({types:['INSTANCE']}).filter(n=>visible(n,frames.get(c.resume)));
c.resumePrimary=resumeButtons.find(n=>n.componentProperties.Style?.value==='Primary')?.id;
c.resumeSecondary=resumeButtons.find(n=>n.componentProperties.Style?.value==='Secondary')?.id;
if(!c.resumePrimary||!c.resumeSecondary)throw new Error('Continuation actions are missing');
roles.resumePrimary=c.resumePrimary;roles.resumeSecondary=c.resumeSecondary;
await reactions(c.resumePrimary,[cond([
  branch(c.v.AccountState,'completed',[set(c.v.AccountState,'new'),set(c.stage,'before'),nav(c.catalog)]),
  branch(c.v.AccountState,'paused',[nav(c.paused)]),
  branch(c.v.AccountState,'empty',[nav(c.empty)]),
  {actions:[nav(c.active)]}
])]);
await reactions(c.resumeSecondary,[nav(c.catalog)]);
// Anonymous entry navigation must not open the prepared active example as history.
for(const f of frames.values())for(const n of f.findAll(n=>'reactions' in n&&visible(n,f)&&/^(Nav\/home|Nav · home|Home)$/.test(n.name)))
  await reactions(n.id,[cond([...priorities(),{actions:[nav(c.before)]}])]);
// Remove profile-return promises from error text; errors never clear entry context.
for(const f of [frames.get(c.email),frames.get(c.confirm),...c.errors.map(id=>frames.get(id))])for(const t of f.findAllWithCriteria({types:['TEXT']})){
  if(!visible(t,f))continue;
  if(/После (проверки|подтверждения).*профиль|After verification, your profile will open/.test(t.characters)){
    await loadText(t);
    t.characters=c.ru?'После проверки вернёмся к вашему действию. Черновик сохранён.':'After verification, return to your task. Your draft is kept.';mutatedNodeIds.push(t.id);
  }
  if(/ШАГ 3 ИЗ 3|STEP 3 OF 3/.test(t.characters)&&(f.id===c.email||f.id===c.confirm)){t.visible=false;mutatedNodeIds.push(t.id);}
}
// Desktop verification uses the existing input as an email code field.
if(!c.mobile){
  const f=frames.get(c.confirm);
  for(const t of f.findAllWithCriteria({types:['TEXT']})){
    if(!visible(t,f))continue;
    if(/^(Электронная почта|Email|you@example.com|Подтвердите email|Verify your email)$/.test(t.characters))await loadText(t);
    if(/^(Электронная почта|Email)$/.test(t.characters)){t.characters=c.ru?'Код из письма':'Code';mutatedNodeIds.push(t.id);}
    else if(t.characters==='you@example.com'){t.characters='123 456';mutatedNodeIds.push(t.id);}
    else if(/^(Подтвердите email|Verify your email)$/.test(t.characters)){t.characters=c.ru?'Введите код из письма':'Enter the email code';mutatedNodeIds.push(t.id);}
  }
  await label(await figma.getNodeByIdAsync(c.verify),c.ru?'Проверить и продолжить':'Verify and continue');
}
// The EN mobile disclosure already exists as a hidden layer; restore it in both modes.
const disclosures=[];
if(c.key==='me')for(const id of ['2502:20038','3087:3480']){
  const t=await figma.getNodeByIdAsync(id);
  if(t?.type!=='TEXT')throw new Error('Missing existing disclosure text '+id);
  for(const s of t.getStyledTextSegments(['fontName']))await figma.loadFontAsync(s.fontName);
  t.characters='New signals only. Existing orders and positions stay unchanged.';
  t.visible=true;t.textAutoResize='HEIGHT';
  mutatedNodeIds.push(t.id);disclosures.push({id:t.id,width:t.width,height:t.height,parent:t.parent.id});
}
if(c.key==='me')for(const id of ['2502:20018','3087:3460']){
  const table=await figma.getNodeByIdAsync(id);
  for(const row of table.children.filter(n=>n.type==='FRAME'&&n.visible)){
    row.resize(row.width,36);row.counterAxisSizingMode='FIXED';mutatedNodeIds.push(row.id);
  }
  table.primaryAxisSizingMode='AUTO';mutatedNodeIds.push(table.id);
}
return {key:c.key,roles,resume:c.resume,mutatedNodeIds:[...new Set(mutatedNodeIds)],disclosures,beforeCount:before.length};
