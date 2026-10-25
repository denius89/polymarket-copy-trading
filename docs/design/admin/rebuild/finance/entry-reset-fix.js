
const slots=['tariff','protection','source','partner/P-DEMO-01','partner/P-DEMO-02','address/P-DEMO-01','address/P-DEMO-02',...MODEL.cases.map(c=>'vip/'+c.uid)];
const reset=[FS('incidentAvailable',false),FS('failure',false),FS('sendWasReady',false),FS('fundWasReady',false),FS('proofContext','')];
for(const k of ['incidentAck','incidentClosed'])if(vars[F(k)])reset.push(FS(k,false));
for(const slot of slots){reset.push(...setPair(F('slot/'+slot+'/policyValue'),'Значение не указано','Value not entered'),...setPair(F('slot/'+slot+'/policyStatus'),'Черновик: заполните учебный пример','Draft: fill the synthetic example'));}
const entry=await figma.getNodeByIdAsync('3990:108');
for(const b of entry.children.filter(n=>'reactions'in n&&n.reactions.length&&n.name.includes('STAFF-'))){const rx=JSON.parse(JSON.stringify(b.reactions));for(const q of rx){delete q.action;q.actions=[when(FQ('handoff',false),reset),...q.actions];}await b.setReactionsAsync(rx);mutated.push(b.id);}
const setting=await figma.getNodeByIdAsync(FROOTS.financeSettings),source=await figma.getNodeByIdAsync(FROOTS.financeSource);
const src=setting.findOne(n=>n.name==='Собственный источник'),target=source.findOne(n=>n.name==='Изменение или активация: два владельца');
if(src&&target){await target.setReactionsAsync(JSON.parse(JSON.stringify(src.reactions)));mutated.push(target.id);}
return{createdNodeIds:created,mutatedNodeIds:mutated};
