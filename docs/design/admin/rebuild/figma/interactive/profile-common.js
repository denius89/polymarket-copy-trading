// Append after common.js; inject PROFILE model. Native Figma scenarios, not authentication.
const A=k=>'account/'+k;
const aset=(k,v)=>set(A(k),v), aref=k=>ref(A(k)), aeq=(k,v)=>eq(A(k),v);
const apair=(k,ru,en)=>setPair(A(k),ru,en);
const avis=(n,k)=>visible(n,A(k));
const showTab=key=>PROFILE.views.flatMap(k=>[aset('view/'+k,k===key),aset('notView/'+k,k!==key)]);
const keyStages=['registerPrimary','testPrimary','registerBackup','testBackup','review'];
const keyStage=key=>keyStages.map(k=>aset('key/'+k,k===key));
const close=[{type:'CLOSE'}];
const overlay=key=>({type:'NODE',destinationId:PROFILE.roots[key],navigation:'OVERLAY',transition:null,resetScrollPosition:true});
const swap=key=>({...overlay(key),navigation:'SWAP'});
const go=key=>({...overlay(key),navigation:'NAVIGATE'});
const fromAccount=fn=>when(aeq('role',PROFILE.accounts[0].role),fn(PROFILE.accounts[0]),PROFILE.accounts.slice(1).reduceRight((no,a)=>[when(aeq('role',a.role),fn(a),no)],[]));
const alertText=(ru,en)=>[...apair('noticeText',ru,en),aset('notice',true)];
const endOthers=[aset('laptopActive',false),aset('mobileActive',false),aset('otherActive',false)];
const authStart=purpose=>[aset('purpose',purpose),aset('operationError',false),aset('operationUnknown',false),overlay('auth')];
const primary=await figma.getNodeByIdAsync('2077:22085'),quiet=await figma.getNodeByIdAsync('2077:22089');
for(const c of [primary,quiet])for(const t of c.findAllWithCriteria({types:['TEXT']}))for(const s of t.getStyledTextSegments(['fontName']))await figma.loadFontAsync(s.fontName);
const styles={12:'S:ee20f524fc83319e69313e18e042cc03682c1c5c,',14:'S:bc557184905d0960b434ff365a67efddde9a111f,',16:'S:0a02e61675da333e7ed3238e6e740aeaf8696f82,',18:'S:2c86601aac2434a091c61c39df224fe7070c0a86,',20:'S:c6ec4d5df1d0aeedae1b91e8b3ef26f57d48dba6,',24:'S:b405e33d1cb9a52dcc1fcd0aa7688dea6eb2dd89,'};const styleJobs=[];
function tx(parent,ru,en,w=0,size=14,weight='Regular',color='text'){const n=text(parent,ru,en,w,size,weight,color);styleJobs.push({n,style:weight==='Medium'&&size===14?'S:98976c4e05f7a72e968a80dd149b28b68b1cafaa,':styles[size]||styles[14]});return n;}
function btn(parent,ru,en,actions,w=160,tone='secondary'){const master=tone==='primary'?primary:tone==='quiet'?quiet:comp;const n=master.createInstance();parent.appendChild(n);n.resize(w,44);n.name=ru;created.push(n.id,...n.findAll(()=>true).map(x=>x.id));const t=n.findAllWithCriteria({types:['TEXT']})[0];t.setBoundVariable('characters',ru.startsWith('$')?vars[ru.slice(1)]:tr(ru,en));if(actions)click(n,actions);return n;}
function row(parent,name,w,gap=12){return box(parent,name,w,'HORIZONTAL',gap);}
function section(parent,name,w=832){const n=panel(parent,name,w);n.itemSpacing=20;n.cornerRadius=12;return n;}
function subhead(parent,ru,en,helpRu,helpEn,w=784){tx(parent,ru,en,w,20,'Semi Bold');if(helpRu)tx(parent,helpRu,helpEn,w,14,'Regular','muted');}
function divider(parent,w){const n=figma.createRectangle();parent.appendChild(n);n.resize(w,1);n.fills=[paint('border')];created.push(n.id);return n;}
function field(parent,labelRu,labelEn,key,w=600,actions=null){const f=box(parent,labelEn,w,'VERTICAL',8);tx(f,labelRu,labelEn,w,12,'Regular','muted');const b=box(f,'Field / '+labelEn,w,'HORIZONTAL',12,'canvas');b.paddingLeft=b.paddingRight=16;b.paddingTop=b.paddingBottom=12;b.cornerRadius=9;b.strokes=[paint('border')];tx(b,'$account/'+key,'',w-32,14);if(actions)click(b,actions);return f;}
const paths={user:'<circle cx="12" cy="8" r="3"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>',shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',sessions:'<rect x="3" y="3" width="18" height="13" rx="2"/><path d="M8 21h8m-4-5v5"/>',language:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z"/>',rights:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6m-6 4h6m-6 4h4"/>'};
function icon(parent,key){const n=figma.createNodeFromSvg('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a3adc2" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+paths[key]+'</svg>');parent.appendChild(n);created.push(n.id,...n.findAll(()=>true).map(x=>x.id));return n;}
function notice(parent,w){const n=box(parent,'Result notice',w,'VERTICAL',8,'selected');n.paddingTop=n.paddingBottom=14;n.paddingLeft=n.paddingRight=16;n.cornerRadius=10;tx(n,'$account/noticeText','',w-32);avis(n,'notice');return n;}
function error(parent,flag,ru,en,w){const n=tx(parent,ru,en,w,14);n.fills=[{type:'SOLID',color:{r:1,g:.65,b:.65}}];avis(n,flag);return n;}
// Figma permits conditions only at the top action level. Expand nested branches into
// disjoint predicates; predicates refer to unchanged branch inputs within each click.
function flatten(actions){
 function expand(list){let paths=[{condition:literal(true),actions:[]}];for(const a of list){if(a.type!=='CONDITIONAL'){for(const p of paths)p.actions.push(a);continue;}const branches=[];let unmatched=literal(true);for(const b of a.conditionalBlocks){const c=b.condition?expr('AND',unmatched,b.condition):unmatched;for(const sub of expand(b.actions))branches.push({condition:expr('AND',c,sub.condition),actions:sub.actions});if(b.condition)unmatched=expr('AND',unmatched,expr('NOT',b.condition));}paths=paths.flatMap(p=>branches.map(b=>({condition:expr('AND',p.condition,b.condition),actions:[...p.actions,...b.actions]})));}return paths;}
 if(!actions.some(a=>a.type==='CONDITIONAL'))return actions;
 // Native playback treated a second conditioned block as fallback. Use independent
 // two-arm conditions with explicit empty fallback, never a multi-branch chain.
 return expand(actions).map(p=>({type:'CONDITIONAL',conditionalBlocks:[{condition:p.condition,actions:p.actions},{actions:[]}]}));
}
async function finish(){for(const {n,style}of styleJobs)await n.setTextStyleIdAsync(style);for(const {id,actions}of reactions)await(await figma.getNodeByIdAsync(id)).setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:flatten(actions)}]);return {createdNodeIds:created,mutatedNodeIds:mutated,reactions:reactions.length};}
function localeButtons(parent,w=120){for(const [label,id]of [['RU',MODEL.ru],['EN',MODEL.en]])btn(parent,label,label,[{type:'SET_VARIABLE_MODE',variableCollectionId:MODEL.localeCollection,variableModeId:id}],w,'quiet');}
const logoutActions=[aset('logged',false),set('canUsers',false),set('canMoney',false),set('noUsers',true),...MODEL.cases.map(c=>set('show/'+c.key,false)),go('logout')];
const nameSave=[when(aeq('draftEmpty',true),[aset('nameError',true)],[aset('nameError',false),aset('nameMode',aref('draftMode')),aset('savedAvatarAlt',aref('avatarAlt')),fromAccount(a=>[when(aeq('draftMode',1),[...apair('name',a.shortRu,a.shortEn),...setPair('staff',a.shortRu+' · '+a.id+' · '+MODEL.roles.find(r=>r.key===a.role).ru.split(' · ').pop(),a.shortEn+' · '+a.id+' · '+MODEL.roles.find(r=>r.key===a.role).en.split(' · ').pop())],[...apair('name',a.nameRu,a.nameEn),...setPair('staff',MODEL.roles.find(r=>r.key===a.role).ru,MODEL.roles.find(r=>r.key===a.role).en)])]),...alertText('Личные данные сохранены. Права не изменились.','Personal details saved. Permissions are unchanged.')])];
const cancelName=[aset('nameError',false),aset('draftEmpty',false),aset('avatarAlt',aref('savedAvatarAlt')),aset('draftMode',aref('nameMode')),fromAccount(a=>[when(aeq('nameMode',1),apair('draftName',a.shortRu,a.shortEn),apair('draftName',a.nameRu,a.nameEn))])];
function languageLink(parent){btn(parent,'$ui/currentLanguage','',[nav('language',true)],220);}
function initAccount(a){return [...Object.entries(defaults).filter(([k])=>!['response','emailExpiryFixture'].includes(k)).map(([k,v])=>aset(k,k==='role'?a.role:k==='owner'?a.owner:k==='notOwner'?!a.owner:v)),...apair('laptopState','Активен','Active'),...apair('mobileState','Активен','Active'),...apair('confirmClose','Отменить','Cancel'),...showTab('details'),...keyStage('registerPrimary'),...apair('name',a.nameRu,a.nameEn),...apair('draftName',a.nameRu,a.nameEn),...apair('email',a.email,a.email),...apair('draftEmail',a.email.replace('@','+work@'),a.email.replace('@','+work@')),...apair('initials',a.initials,a.initials),...apair('staffId',a.id,a.id),...apair('method',a.owner?'Два физических ключа · проверены':'Ключ доступа на устройстве · проверен',a.owner?'Two physical keys · verified':'Device-bound passkey · verified')];}

function openTermination(target,ru,en){return [when(aeq('terminationPending',true),[aset('operationUnknown',true),aset('terminationReady',false),overlay('confirm')],[aset('terminationReady',true),...apair('confirmClose','Отменить','Cancel'),aset('target',target),...apair('sessionTarget',ru,en),aset('operationError',false),aset('operationUnknown',false),overlay('confirm')])];}
