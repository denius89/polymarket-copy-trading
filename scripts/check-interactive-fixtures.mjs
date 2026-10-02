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
console.log(`Interactive fixtures valid: 24 traders, 19 positions, ${fixture.orders.length} orders, 70 events; available $${(active.availableCents/100).toFixed(2)}, reserve $${(reserved/100).toFixed(2)}, equity $${(active.equityCents/100).toFixed(2)}, net result $${(active.totalPnlCents/100).toFixed(2)}. Synthetic review data only.`);
