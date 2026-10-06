import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const fixture = JSON.parse(readFileSync(new URL('../design/interactive-fixtures-2026-10-02.json', import.meta.url), 'utf8'));
const collections = ['accounts','sessions','signals','markets','traders','positions','orders','ledger','events','notifications','tickets','messages','faq'];
const sets = Object.fromEntries(collections.map(key => [key, new Map(fixture[key].map(row => [row.id,row]))]));
for (const key of collections) assert.equal(sets[key].size,fixture[key].length,`Duplicate IDs in ${key}`);
const refs = {signalId:'signals',accountId:'accounts',sessionId:'sessions',traderId:'traders',marketId:'markets',positionId:'positions',orderId:'orders',relatedLedgerId:'ledger',relatedOrderId:'orders',relatedPositionId:'positions',eventId:'events',ticketId:'tickets'};
for (const key of collections) for (const row of fixture[key]) {
 for (const [field,target] of Object.entries(refs)) if (row[field] != null) assert.ok(sets[target].has(row[field]),`${row.id}: missing ${field} ${row[field]}`);
 for (const field of ['priceCents','limitPriceCents','markPriceCents']) if (row[field] != null) assert.ok(Number.isInteger(row[field]) && row[field] >= 0 && row[field] <= 100,`${row.id}: bad probability price`);
 for (const [field,value] of Object.entries(row)) if (field.endsWith('Cents') && value != null) assert.ok(Number.isInteger(value),`${row.id}: noninteger ${field}`);
}
assert.equal(fixture.traders.length,24);
assert.equal(new Set(fixture.traders.map(t=>t.address)).size,24);
for(const trader of fixture.traders) {assert.match(trader.address,/^0x[0-9a-f]{40}$/);assert.equal(trader.addressSynthetic,true);}
for (const venue of ['polymarket','limitless']) {
 const traders=fixture.traders.filter(t=>t.venue===venue);assert.equal(traders.length,12);
 const available=traders.filter(t=>t.catalogDataAvailable && t.publicPnlCents!=null);
 assert.ok(available.some(t=>t.publicPnlCents>0),`${venue}: positive example missing`);
 assert.ok(available.some(t=>t.publicPnlCents<0),`${venue}: negative example missing`);
 assert.ok(available.some(t=>t.publicPnlCents===0),`${venue}: zero example missing`);
 assert.ok(traders.some(t=>t.publicPnlCents===null),`${venue}: unavailable example missing`);
}
assert.equal(fixture.traders.filter(t=>t.periods).length,6);
for(const trader of fixture.traders) {
 for(const [period,row] of [[trader.catalogPeriod,trader],...Object.entries(trader.periods??{})]) {
  assert.equal(row.drawdownEvidence.period,period);
  assert.equal(row.drawdownEvidence.status,row.drawdownBasisPoints==null ? 'unavailable' : 'illustrative_unverified');
  assert.equal(row.drawdownEvidence.eligibleForTrustedComparison,false,'Illustrative drawdown cannot drive trusted sorting/filtering/recommendation');
  assert.equal(row.drawdownEvidence.verifiedValueBasisPoints,null,'Illustrative drawdown is not a confirmed numeric value');
 }
}
for (const trader of fixture.traders.filter(t=>t.periods)) {
 assert.deepEqual(Object.keys(trader.periods),['24h','7d','30d','90d']);
 assert.equal(trader.publicPnlCents,trader.periods['30d'].publicPnlCents,'Catalog and profile share 30d result');
 for(const [period,stats] of Object.entries(trader.periods)) { const days={'24h':1,'7d':7,'30d':30,'90d':90}[period];assert.equal(stats.available,trader.historyDays>=days);assert.equal(stats.coverageDays,Math.min(days,trader.historyDays));assert.equal(stats.chartSyntheticIllustration,true);if(!stats.available) {assert.equal(stats.publicPnlCents,null);assert.equal(stats.chartPoints,null);} else {assert.ok(Number.isInteger(stats.closedTrades) && stats.closedTrades>=0);assert.ok(Number.isInteger(stats.winningClosedTrades) && stats.winningClosedTrades>=0 && stats.winningClosedTrades<=stats.closedTrades);assert.equal(stats.successBasisPoints,stats.closedTrades ? Math.round(stats.winningClosedTrades/stats.closedTrades*10000) : null);assert.equal(stats.chartPoints.length,7);assert.equal(stats.chartPoints[0].cumulativePnlCents,0);assert.equal(stats.chartPoints.at(-1).cumulativePnlCents,stats.publicPnlCents);for(const point of stats.chartPoints) assert.ok(Number.isInteger(point.cumulativePnlCents));} }
}
assert.equal(fixture.positions.filter(p=>p.status==='closed').length,14);
assert.equal(fixture.positions.filter(p=>p.status!=='closed').length,5);
assert.equal(fixture.events.length,70);
for(const event of fixture.events) if(event.kind==='skipped') {assert.equal(event.status,'skipped');assert.equal(event.relatedOrderId,null);assert.equal(event.relatedPositionId,null);assert.ok(event.reason);}
assert.ok(fixture.events.some(e=>e.status==='unknown'));
assert.ok(fixture.events.some(e=>e.status==='cancel_pending'));
for(const event of fixture.events) {
 if(['order_status','reconciliation'].includes(event.kind)) assert.equal(event.status,sets.orders.get(event.relatedOrderId).status);
 if(event.kind==='limit_check') assert.equal(event.status,'passed');
 if(event.kind==='execution') assert.equal(event.requiresAttention,false);
 if(event.kind==='market_update') {assert.equal(event.status,'resolved_awaiting_payout');assert.equal(event.relatedPositionId,'position-current-05');assert.equal(event.relatedOrderId,null);}
 if(event.requiresAttention) assert.ok(['unknown','cancel_pending','close_pending','resolved_awaiting_payout'].includes(event.status));
}
assert.equal(fixture.notifications.length,20);
assert.equal(fixture.tickets.length,8);
assert.equal(fixture.messages.length,12);
assert.equal(fixture.faq.length,15);
for(const row of fixture.faq) {assert.ok(row.questionRu && row.answerRu);assert.ok(row.question && row.answer);}
for(const row of fixture.messages) assert.ok(row.textRu && row.text);
assert.ok(fixture.faq.some(row=>row.answerRu.split('\n\n').length>=3));
assert.ok(fixture.messages.some(row=>row.textRu.includes('\n\n')));
assert.ok(new Set(fixture.messages.map(row=>row.text)).size>8);
assert.equal(fixture.sessions.length,1);
const session=fixture.sessions[0],readiness=session.riskReadiness;
assert.equal(session.status,'active','Session lifecycle and risk readiness are separate');
assert.equal(readiness.newBuys,'blocked');
assert.equal(readiness.reason,'unknown_order');
assert.equal(readiness.scope,'illustrative_single_paper_session');
assert.equal(readiness.reconciliationRequired,true);
const readinessOrder=sets.orders.get(readiness.relatedOrderId);
assert.equal(readinessOrder.sessionId,session.id);
assert.equal(readinessOrder.status,'unknown');
assert.equal(readinessOrder.side,'BUY');
assert.equal(readinessOrder.reservedCents,101,'Unknown purchase reserve is retained');
assert.equal(sets.events.get(readiness.relatedEventId).relatedOrderId,readinessOrder.id);
assert.equal(sets.events.get(readiness.relatedEventId).status,'unknown');
assert.equal(new Set(fixture.positions.map(p=>p.traderId)).size,1);
const state = new Map();
let cash=20000, fees=0;
for (const entry of fixture.ledger) {
 assert.ok(entry.orderId,'Every fixture fill must link to an order');
 const order=sets.orders.get(entry.orderId);
 assert.equal(order.marketId,entry.marketId);
 assert.equal(order.side,entry.kind);
 assert.equal(entry.feeCents,fixture.feePolicy.feeCentsPerFill);
 const previous=state.get(entry.positionId) ?? {quantity:0,cost:0,realized:0};
 const gross=entry.quantity*entry.priceCents;
 if (entry.kind==='BUY') {cash-=gross+entry.feeCents;previous.quantity+=entry.quantity;previous.cost+=gross+entry.feeCents;}
 else {
  assert.ok(entry.kind==='SELL' && entry.quantity<=previous.quantity,'Sell cannot exceed held quantity');
  const removedCost=previous.cost*entry.quantity/previous.quantity;
  assert.ok(Number.isInteger(removedCost),'This fixture must allocate exact integer-cent costs');
  cash+=gross-entry.feeCents;previous.quantity-=entry.quantity;previous.cost-=removedCost;previous.realized+=gross-entry.feeCents-removedCost;
 }
 assert.ok(cash>=0,'Fixture cannot spend negative cash');
 fees+=entry.feeCents;state.set(entry.positionId,previous);
}
let cost=0,mark=0,realized=0,unrealized=0;
for (const position of fixture.positions) {
 const computed=state.get(position.id);
 assert.equal(position.quantity,computed.quantity,position.id);
 assert.equal(position.costBasisCents,computed.cost,position.id);
 assert.equal(position.realizedPnlCents,computed.realized,position.id);
 const value=position.quantity*(position.markPriceCents??0);
 assert.equal(position.markValueCents,value,position.id);
 assert.equal(position.unrealizedPnlCents??0,value-computed.cost,position.id);
 assert.ok(position.costBasisCents<=2000,'Position exceeds fixture 10% budget ceiling');
 if(position.status==='awaiting_settlement') assert.equal(sets.markets.get(position.marketId).status,'resolved_awaiting_payout');
 cost+=computed.cost;mark+=value;realized+=computed.realized;unrealized+=value-computed.cost;
}
for(const order of fixture.orders) {
 const fills=fixture.ledger.filter(l=>l.orderId===order.id);
 assert.equal(order.filledQuantity,fills.reduce((sum,l)=>sum+l.quantity,0),order.id);
 assert.equal(order.remainingQuantity,order.quantity-order.filledQuantity,order.id);
 if(['canceled','rejected','error_before_send','filled'].includes(order.status)) assert.equal(order.reservedCents,0,order.id);
 if(order.status==='unknown') assert.ok(order.reservedCents>0,'Unknown buy must retain reserve');
 if(order.side==='BUY' && order.reservedCents>0) assert.equal(order.reservedCents,order.remainingQuantity*order.limitPriceCents+order.estimatedRemainingFeeCents,order.id);
}
const reserved=fixture.orders.reduce((sum,o)=>sum+o.reservedCents,0);
const active=fixture.contexts.active_review;
for(const [key,value] of Object.entries({cashCents:cash,reservedCents:reserved,availableCents:cash-reserved,costBasisCents:cost,markValueCents:mark,equityCents:cash+mark,realizedPnlCents:realized,unrealizedPnlCents:unrealized,totalPnlCents:realized+unrealized,executionExpensesCents:fees})) assert.equal(active[key],value,key);
assert.equal(cash+mark-20000,realized+unrealized,'Equity change equals net result');
assert.ok(cash-reserved>=0);
assert.deepEqual(fixture.contexts.first_launch.positionIds,[]);
assert.deepEqual(fixture.contexts.first_launch.eventIds,[]);
assert.equal(fixture.contexts.first_launch.availableCents,20000);
assert.equal(fixture.contexts.future_accounts.balances,null);
for(const id of fixture.visibleReviewPlan.eventInteractiveIds) assert.ok(sets.events.has(id));
const visibleCounts={catalogRows:'traders',positionRows:'positions',orderRows:'orders',orderSourceCount:'orders',eventRows:'events',ledgerRows:'ledger',notificationRows:'notifications',ticketRows:'tickets',faqRows:'faq',messageRows:'messages'};
for(const [key,collection] of Object.entries(visibleCounts)) assert.equal(fixture.visibleReviewPlan[key],fixture[collection].length,`Visible ${key} matches built collection`);
assert.equal(new Set(fixture.visibleReviewPlan.eventInteractiveIds).size,fixture.events.length);
assert.deepEqual(new Set(fixture.visibleReviewPlan.eventInteractiveIds),new Set(fixture.events.map(event=>event.id)));
// Historical admission cannot be inferred from the current settings snapshot.
const policyEvidence=active.historicalPolicyEvidence;
assert.equal(policyEvidence.status,'unverified');
assert.equal(policyEvidence.sessionTimeZone,null);
assert.equal(policyEvidence.effectiveRuleVersion,null);
assert.equal(policyEvidence.reviewAggregationZone,'Etc/UTC');
const replay=new Map();
for(const entry of fixture.ledger.filter(row=>row.kind==='BUY')) {
 const date=entry.timestamp.slice(0,10);
 const day=replay.get(date)??{date,purchaseCents:0,expenseCents:0};
 day.purchaseCents+=entry.quantity*entry.priceCents;day.expenseCents+=entry.feeCents;replay.set(date,day);
}
assert.deepEqual([...replay.values()],policyEvidence.dailyBuyReplay);
assert.equal(replay.get('2026-10-01').purchaseCents,3390);
assert.equal(fixture.feePolicy.serviceFeeCents,0);
assert.equal(fixture.feePolicy.executionExpenseSource,'synthetic-review-expense-v1; no venue tariff inferred');
const ticket=sets.tickets.get('ticket-01');
const ticketEvent=sets.events.get(ticket.eventId);
assert.equal(ticketEvent.relatedOrderId,'order-closed-04-buy');
assert.equal(sets.orders.get(ticketEvent.relatedOrderId).status,'filled');
assert.equal(sets.orders.get(ticketEvent.relatedOrderId).reservedCents,0);
assert.equal(sets.positions.get(ticketEvent.relatedPositionId).status,'closed');
for(const message of fixture.messages.filter(row=>row.ticketId===ticket.id)) {
 assert.equal(message.relatedOrderId,ticketEvent.relatedOrderId);
 assert.equal(message.relatedPositionId,ticketEvent.relatedPositionId);
 assert.ok(message.timestamp>'2026-09-30T16:00:00Z','Conversation describes the confirmed completed history');
}
assert.match(sets.messages.get('message-02').text,/\$2\.40.*\$0\.01/);
assert.match(sets.messages.get('message-06').text,/−\$0\.22/);
const supportLabels={open:['Sent','Отправлено'],waiting_support:['Waiting for support','Ждём поддержку'],waiting_user:['Waiting for your reply','Ждём вашего ответа'],resolved:['Resolved','Решено']};
for(const row of fixture.tickets) assert.deepEqual([row.statusLabel,row.statusLabelRu],supportLabels[row.status]);
// Acceptance data checks only: no application ledger or execution is introduced.
const financial=JSON.parse(readFileSync(new URL('../design/qa-2026-10-06/audit81-financial-scenarios.json',import.meta.url),'utf8'));
let scenarioCash=financial.startingCashCents,quantityUnits=0,externalFlows=0;
const applied=new Set();
for(const entry of financial.events) {
 if(!applied.has(entry.id)) {
  if(['BUY','REDEEM'].includes(entry.kind)) {
   const gross=entry.quantityUnits*entry.priceCents/financial.shareScale;
   assert.ok(Number.isInteger(gross),'This acceptance case has exact cents; no rounding policy is assumed');
   if(entry.kind==='BUY') {scenarioCash-=gross+entry.feeCents;quantityUnits+=entry.quantityUnits;}
   else {assert.ok(entry.quantityUnits<=quantityUnits);scenarioCash+=gross-entry.feeCents;quantityUnits-=entry.quantityUnits;}
  } else if(entry.kind==='FEE') scenarioCash-=entry.feeCents;
  else if(entry.kind==='DEPOSIT') {scenarioCash+=entry.amountCents;externalFlows+=entry.amountCents;}
  else assert.equal(entry.kind,'RESOLVE'); // Resolution changes valuation, not received cash.
  applied.add(entry.id);
 }
 const value=quantityUnits*entry.markPriceCents/financial.shareScale;
 assert.equal(scenarioCash,entry.expectedCashCents,entry.id);
 assert.equal(quantityUnits,entry.expectedQuantityUnits,entry.id);
 assert.equal(value,entry.expectedMarkCents,entry.id);
 assert.equal(scenarioCash+value,entry.expectedEquityCents,entry.id);
 assert.equal(externalFlows,entry.externalFlowCents,entry.id);
 if(entry.expectedTradingResultCents!=null) assert.equal(scenarioCash+value-financial.startingCashCents-externalFlows,entry.expectedTradingResultCents);
}
const unknown=financial.unknownValuation;
const unknownMark=unknown.markPriceCents==null ? null : unknown.quantityUnits*unknown.markPriceCents/financial.shareScale;
assert.equal(unknownMark,unknown.expectedMarkCents);
assert.equal(unknownMark==null ? null : unknown.cashCents+unknownMark,unknown.expectedEquityCents);
for(const row of financial.reportCounterCases) {
 const observed=new Set(row.observedSignalIds),eligible=new Set(row.eligibleSignalIds),copied=new Set(row.fillSignalIds);
 for(const id of eligible) assert.ok(observed.has(id));
 for(const id of copied) assert.ok(eligible.has(id));
 assert.equal(observed.size,row.expectedObserved);
 assert.equal(eligible.size,row.expectedEligible);
 assert.equal(copied.size,row.expectedCopied);
 assert.equal(row.days>=7 && eligible.size>=10,row.expectedReady);
}
console.log(`Interactive fixtures valid: 24 traders, 19 positions, ${fixture.orders.length} orders, 70 events; available $${(active.availableCents/100).toFixed(2)}, reserve $${(reserved/100).toFixed(2)}, equity $${(active.equityCents/100).toFixed(2)}, net result $${(active.totalPnlCents/100).toFixed(2)}. Synthetic review data only.`);
