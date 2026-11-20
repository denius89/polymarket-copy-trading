export interface RealTraderRequest {venueCode:'polymarket'|'limitless';externalTraderId:string}
export class BoundaryError extends Error {status:number;reasonCode:string;reasonParams:Readonly<Record<string,string>>;constructor(status:number,reasonCode:string,reasonParams?:Record<string,string>)}
export function parseResolveRequest(rawQuery:string,bodyBytes?:number):RealTraderRequest;
export function resolveAuthorizedSnapshot(request:RealTraderRequest,value:unknown,readScope:unknown):Record<string,unknown>;
