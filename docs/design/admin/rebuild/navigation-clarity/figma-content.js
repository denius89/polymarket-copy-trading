await figma.setCurrentPageAsync(await figma.getNodeByIdAsync('1981:29'));
figma.skipInvisibleInstanceChildren=false;
await Promise.all(['Regular','Medium','Semi Bold','Bold'].map(style=>figma.loadFontAsync({family:'Inter',style})));
const created=[],mutated=[];const col=await figma.variables.getVariableCollectionByIdAsync('VariableCollectionId:3986:28');
async function update(id,ru,en){const v=await figma.variables.getVariableByIdAsync(id);v.setValueForMode('3986:1',ru);v.setValueForMode('3986:2',en);mutated.push(v.id);return v;}
function makeVar(name,ru,en){const v=figma.variables.createVariable('navigation/clarity/'+name,col,'STRING');v.scopes=['TEXT_CONTENT'];v.setValueForMode('3986:1',ru);v.setValueForMode('3986:2',en);created.push(v.id);return v;}
const unified=await figma.variables.getVariableByIdAsync('VariableID:4361:2292');
await update('VariableID:4143:434','Восстановление ограничения','Restore restricted access');
await update('VariableID:4143:436','Это процедура снятия выбранного запрета, а не отдельный режим отключения. Другие ограничения сохраняются; сделки и переводы не запускаются.','This removes one selected restriction; it is not another shutdown mode. Other restrictions remain; trades and transfers do not restart.');
await update('VariableID:4101:411','Проверьте, совпадают ли записи Shadow с подтверждёнными данными площадки или сети.','Check whether Shadow records match confirmed venue or network evidence.');
await update('VariableID:4305:2337','Технический режим полностью закрывает пользовательскую часть. Восстановление снимает выбранный запрет после проверки и двух подтверждений.','Technical mode fully closes the user service. Recovery lifts a selected restriction after checks and two approvals.');
const help=makeVar('reconciliation-explanation','Например, заявка отправлена, но ответ потерялся. Проверяем исходную операцию, чтобы не отправить её повторно. Сверка ничего не отправляет и не исправляет баланс. Нет подтверждения — результат неизвестен; расхождение требует разбора. Здесь три торговых снимка; выплаты и пополнения сверяются в своих карточках.','For example, an order was sent but its response was lost. Check the original operation to avoid resending it. Reconciliation sends nothing and does not edit balances. Missing evidence means an unknown outcome; differences need investigation. These are three trading snapshots; payouts and funding are checked in their own details.');
const why=makeVar('reconciliation-why','Зачем нужна сверка','Why reconcile?');
const recoveryIntro=makeVar('recovery-intro','Для полного отключения используйте его процедуру выключения. Здесь можно продолжить запрос или открыть учебный пример другого ограничения, например подключения Limitless. Снятие запрета не отправляет сделки и выплаты.','For full shutdown, use its turn-off procedure. Here you can continue a request or open a synthetic example of another restriction, such as a Limitless connection. Removing a restriction does not send trades or payouts.');
const recoveryTitle=makeVar('recovery-title','Восстановление выбранного ограничения','Recover a selected restriction');
const recoveryLink=makeVar('recovery-link','Открыть запрос восстановления','Open recovery request');
const fullTitle=makeVar('shutdown-title','Полное отключение сервиса','Full service shutdown');
function text(parent,variable,name,size=14){const n=figma.createText();n.fontName={family:'Inter',style:size===16?'Semi Bold':'Regular'};n.fontSize=size;n.lineHeight={unit:'PIXELS',value:size===16?24:21};n.characters=name;n.setBoundVariable('characters',variable);n.fills=[{type:'SOLID',color:{r:0.91,g:0.93,b:0.97}}];parent.appendChild(n);n.textAutoResize='HEIGHT';n.resize(parent.width-parent.paddingLeft-parent.paddingRight,30);n.layoutSizingHorizontal='FILL';created.push(n.id);return n;}
function panel(parent,name,index){const n=figma.createAutoLayout('VERTICAL',{name,itemSpacing:12,paddingLeft:20,paddingRight:20,paddingTop:20,paddingBottom:20,cornerRadius:12,fills:[{type:'SOLID',color:{r:0.078,g:0.094,b:0.14}}]});parent.insertChild(index,n);n.resize(parent.width-parent.paddingLeft-parent.paddingRight,150);n.layoutSizingHorizontal='FILL';n.primaryAxisSizingMode='AUTO';created.push(n.id);return n;}
const source=await figma.getNodeByIdAsync('4143:585');
for(const id of ['4304:2295','4311:2321']){
 const root=await figma.getNodeByIdAsync(id),main=root.children.find(n=>n.name==='Main content');
 const title=main.children.find(n=>n.type==='TEXT'&&n.name==='Технический режим');if(title){title.setBoundVariable('characters',unified);title.textAutoResize='HEIGHT';mutated.push(title.id);}
 const status=main.children.find(n=>n.name==='Mode status and next action');if(status&&!status.children.some(n=>n.name==='Full shutdown title')){const tx=text(status,fullTitle,'Full shutdown title',16);status.insertChild(0,tx);}
 if(!main.children.some(n=>n.name==='Restriction recovery explanation')){const before=main.children.findIndex(n=>n.name==='Technical columns');const p=panel(main,'Restriction recovery explanation',before<0?main.children.length-1:before);text(p,recoveryTitle,'Recovery title',16);text(p,recoveryIntro,'Recovery explanation');const b=source.clone();p.appendChild(b);created.push(b.id,...b.query('*').map(n=>n.id));b.name='Open recovery request';b.resize(Math.min(360,p.width-40),52);for(const tx of b.query('TEXT')){tx.setBoundVariable('characters',recoveryLink);tx.textAutoResize='HEIGHT';tx.resize(b.width-32,tx.height);}await b.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:id==='4311:2321'?'4161:65427':'4143:371',navigation:'NAVIGATE',transition:null,resetScrollPosition:true}]}]);}
 root.resize(root.width,Math.max(root.height,main.y+main.height+40));mutated.push(root.id,main.id);
}
for(const id of ['4100:294','4161:64832','4100:295','4161:64952']){
 const root=await figma.getNodeByIdAsync(id),main=root.children.find(n=>n.name==='Main content');const permitted=main.children.find(n=>n.name==='Reconciliation permitted content')||main;
 if(!permitted.children.some(n=>n.name==='Reconciliation explanation')){const p=panel(permitted,'Reconciliation explanation',Math.min(3,permitted.children.length));text(p,why,'Why reconcile',16);text(p,help,'Reconciliation explanation text');}
 root.resize(root.width,Math.max(root.height,main.y+main.height+40));mutated.push(root.id,main.id);
}
const permission=await figma.variables.getVariableByIdAsync('VariableID:4143:375');
const roots=figma.currentPage.children.filter(n=>n.type==='FRAME'&&/^(READY|MOBILE) \/ /.test(n.name));
for(const root of roots){const side=root.children.find(n=>['Persistent navigation','Mobile menu content'].includes(n.name));const target=side?.children.find(n=>n.name==='Ограничения и восстановление');if(target){target.setBoundVariable('visible',permission);mutated.push(target.id);}
 const main=root.children.find(n=>n.name==='Main content');if(!main)continue;const tabs=main.children.find(n=>n.name==='Finance navigation');const group=side?.children.find(n=>n.name==='Finance navigation group');const reco=group?.children.find(n=>n.name==='Сверка операций');
 if(tabs&&reco&&!tabs.children.some(n=>n.name==='Сверка операций')){const b=reco.clone();tabs.appendChild(b);b.resize(180,52);for(const tx of b.query('TEXT')){tx.textAutoResize='HEIGHT';tx.resize(148,tx.height);}created.push(b.id,...b.query('*').map(n=>n.id));tabs.layoutWrap='WRAP';mutated.push(tabs.id);}
}
return {createdNodeIds:created,mutatedNodeIds:[...new Set(mutated)],rootCount:roots.length};
