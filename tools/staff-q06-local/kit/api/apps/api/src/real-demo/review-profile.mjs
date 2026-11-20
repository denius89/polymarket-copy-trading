/** One pinned virtual session plus source observations; execution remains closed. */
export const REVIEW_PROFILE=Object.freeze({
  venueCode:'polymarket',externalTraderId:'0x1111111111111111111111111111111111111111',
  catalogSourceId:'1ae54ea1-7149-48f1-8189-41be4fa064ce',
  traderId:'6e91ae7c-a813-4b98-9bbc-022c0e04c2ff',
  traderRevisionId:'faf7d35a-f4a4-4b8c-a1d4-74ed2bbe1ebd',
  admissionId:'77517c4e-6e3e-4bd3-9007-557f44a1a56d',
  sourceBindingVersion:'1',adapterVersion:'polymarket-empty-session-v1',policyVersion:'real-trader-empty-session-v1',
});
export function isReviewTrader(v) {
  return v!==null&&typeof v==='object'&&
    ['venueCode','externalTraderId','catalogSourceId','traderId','traderRevisionId'].every(k=>v[k]===REVIEW_PROFILE[k])&&
    v.dataOrigin==='public_api'&&((v.startAvailability?.available===true&&v.startAvailability?.capabilityReasonCode===null)||
     (v.startAvailability?.available===false&&['PAPER_START_DISABLED','CATALOG_SOURCE_DISABLED','TRADER_START_DISABLED'].includes(v.startAvailability?.capabilityReasonCode)));
}
export function isReviewCatalogOrigin(v) {
  if(v===null||typeof v!=='object')return false;
  if(v.catalogSourceId===REVIEW_PROFILE.catalogSourceId||v.traderId===REVIEW_PROFILE.traderId||v.traderRevisionId===REVIEW_PROFILE.traderRevisionId)
    return isReviewTrader(v);
  return v.dataOrigin==='synthetic';
}
export function assertReviewRuntimeProfile(config) {
  if(config?.profile!=='polygon-real-trader-empty-session-v1'||config.startEnabled!==true)
    throw Error('Pinned empty-session runtime profile required');
}

/** Origin is a statement about the trader; amounts remain virtual USD. */
export function isSessionOrigin(v) {
  if(v===null||typeof v!=='object')return false;
  const keys=['catalogSourceId','traderId','traderRevisionId'];
  const anyPinned=keys.some(k=>v[k]===REVIEW_PROFILE[k]);
  if(v.dataOrigin==='public_api')return keys.every(k=>v[k]===REVIEW_PROFILE[k]);
  return v.dataOrigin==='synthetic'&&!anyPinned;
}
