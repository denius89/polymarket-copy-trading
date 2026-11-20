export interface Rational {n:string;d:string}
export interface CoreState {schemaVersion:'paper-buy-core-state-v1';sessionId:string;version:string;snapshotId:string;cash:Rational;reservedCash:Rational;freeCash:Rational;cashExpenses:Rational;positions:Array<{conditionId:string;tokenId:string;cost:Rational;quantity:Rational;reserved:Rational}>;daily:Array<{day:string;used:Rational;reserved:Rational}>}
export function decodeCoreState(value:unknown,sessionId:string):CoreState;
export function decodeCoreResult(value:unknown,expected:{sessionId:string;commandId:string;kind?:string;intentId?:string}):Record<string,unknown>;
export function validateCoreRequest(kind:'reserve'|'settle',input:unknown):void;
