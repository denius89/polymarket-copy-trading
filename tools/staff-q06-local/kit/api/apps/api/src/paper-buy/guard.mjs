export class BuyBlocked extends Error {constructor(reason){super(reason);this.reason=reason;}}
export const check=(condition,reason)=>{if(!condition)throw new BuyBlocked(reason);};
export const sha=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
export const integer=v=>Number.isSafeInteger(v);
