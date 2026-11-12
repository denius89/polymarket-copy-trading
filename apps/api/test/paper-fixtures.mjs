import { encodeRaw, RAW_ENCODING } from '../src/paper/raw-codec.ts';
export const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
export const at='2026-11-04T10:00:00.000Z';
export const M=n=>({n:String(n),d:'1'});
export const form=()=>({locale:'ru',step:'configure',entryContext:'catalog',venueId:id(10),traderId:id(11),selectedMode:'fixed',
  rawBudget:'100',rawFixedAmount:'5',rawCopyPercent:'2,5',rawMarketLimitPercent:'10',rawDailyBuyLimitPercent:'20',proposedTimezone:'Europe/Warsaw'});
export const request=()=>({requestSchemaVersion:'v1',clientCommandId:id(70),...form()});
export const identity=()=>({http:200,user_id:id(1),read_context_id:id(1),scope_id:id(2),scope_revision:`q02-read-scope-v1:${id(2)}:1`});
export const ref=(type='C04')=>({actorRealm:'user',actorId:id(1),commandType:type,clientCommandId:id(type==='C04'?70:71)});
export const receipt=(type='C04')=>({receiptId:id(type==='C04'?80:81),recordSchemaVersion:'v1',commandType:type,outcome:'succeeded',createdAt:at,reasonCode:null,reasonDetails:[],
  result:type==='C04'?{draftId:id(20),ownershipId:id(21),draftVersion:'1',changeKind:'created',lastSavedAt:at,expiresAt:'2026-11-11T10:00:00.000Z'}:
    {sessionId:id(30),settingsRevisionId:id(31),snapshotVersion:'1',sessionVersion:'1'},...(type==='C04'?{fieldErrors:[]}:{})});
export const draft=()=>({http:200,raw_encoding:RAW_ENCODING,draft:encodeRaw({...form(),draftId:id(20),currentOwnershipId:id(21),draftVersion:'1',ownerKind:'user',state:'editable',
  lastSavedAt:at,expiresAt:'2026-11-11T10:00:00.000Z',createdAt:at,updatedAt:at,usedAt:null,usedBySessionId:null}),field_errors:[],field_errors_source:{receiptId:id(80),draftVersion:'1'}});
const numbers=()=>({budget:M(100),fixedAmount:M(5),copyPercent:null,marketLimitPercent:'10.00',dailyBuyLimitPercent:'20.00',effectiveMarketLimit:M(10),effectiveDailyBuyLimit:M(20)});
export const review=()=>({http:200,raw_encoding:RAW_ENCODING,review:encodeRaw({reviewId:id(22),draftId:id(20),ownershipId:id(21),recordSchemaVersion:'v1',draftVersion:'1',
  ownerKind:'user',ownerUserId:id(1),venueId:id(10),catalogSourceId:id(12),traderId:id(11),traderRevisionId:id(13),catalogVersion:'1',traderControlVersion:'1',
  policyVersionId:id(14),paperControlId:id(15),paperControlVersion:'1',selectedMode:'fixed',rawBudget:'100',rawFixedAmount:'5',rawCopyPercent:'2,5',
  rawMarketLimitPercent:'10',rawDailyBuyLimitPercent:'20',proposedTimezone:'Europe/Warsaw',normalizationValid:true,...numbers(),expectedSlot:{state:'absent'},
  allowedToStart:true,requiresAuthentication:false,primaryReasonCode:null,reasonDetails:[],fieldErrors:[],warnings:[{code:'SYNTHETIC_DATA',params:{}},{code:'COPYING_NOT_CONNECTED',params:{}}],
  checkedAt:at,expiresAt:'2026-11-04T10:10:00.000Z',createdAt:at})});
export const session=()=>({http:200,session:{
  summary:{sessionId:id(30),mode:'paper',venueId:id(10),catalogSourceId:id(12),traderId:id(11),traderRevisionId:id(13),traderDisplayName:'Synthetic',
    dataOrigin:'synthetic',lifecycle:'active',controlState:'copying_not_connected',contentState:'EMPTY',coverageState:'no_trade_data',sessionVersion:'1',snapshotVersion:'1',
    settingsRevisionId:id(31),asOf:at,startedAt:at,evaluationDeadlineAt:'2026-11-18T10:00:00.000Z',ianaTimezone:'Europe/Warsaw',
    deadlineCalculationVersion:'paper-evaluation-deadline-v1',timezoneDatabaseVersion:'2025a',createdAt:at,updatedAt:at},
  settings:{settingsRevisionId:id(31),sessionId:id(30),recordSchemaVersion:'v1',sequence:'1',previousRevisionId:null,...numbers(),sizingMode:'fixed',policyVersionId:id(14),
    calculationVersion:'paper-settings-calculation-v1',signalMaxAgeSeconds:30,commandReceiptId:id(81),createdAt:at},
  financialSnapshot:{snapshotId:id(32),sessionId:id(30),settingsRevisionId:id(31),recordSchemaVersion:'v1',snapshotVersion:'1',sessionVersion:'1',ledgerSequence:'1',
    projectionCalculationVersion:'paper-empty-snapshot-v1',lifecycle:'active',controlState:'copying_not_connected',contentState:'EMPTY',dataOrigin:'synthetic',coverageState:'no_trade_data',unit:'virtual_USD',
    initialFunding:M(100),free:M(100),equity:M(100),reserved:M(0),positionCost:M(0),positionValue:M(0),tradingResult:M(0),tradeCount:'0',positionCount:'0',orderCount:'0',asOf:at,createdAt:at},
}});
