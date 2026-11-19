import { exactObject, InputError, positiveVersion, uuid, validUnicode } from '../http/input.ts';

export const RAW_FIELDS = ['rawBudget','rawFixedAmount','rawCopyPercent','rawMarketLimitPercent','rawDailyBuyLimitPercent'] as const;
const timezone = (v: unknown): boolean => {
  if (v === null) return true;
  if (typeof v !== 'string' || !/^[A-Za-z][A-Za-z0-9._+\-/]*$/.test(v)) return false;
  try {new Intl.DateTimeFormat('en', {timeZone: v}); return true;} catch {return false;}
};
const invalid = (): never => {throw new InputError();};
export function c04Request(body: unknown, updating: boolean): Record<string, unknown> {
  const v = exactObject(body, ['requestSchemaVersion','clientCommandId','locale','step','entryContext',
    'venueId','traderId','selectedMode',...RAW_FIELDS,'proposedTimezone',...(updating ? ['expectedDraftVersion'] : [])]);
  if (v.requestSchemaVersion !== 'v1' || !uuid(v.clientCommandId) || !['ru','en'].includes(v.locale as string) ||
      !['select_trader','configure','review'].includes(v.step as string) ||
      (v.entryContext !== null && !['catalog','trader_details','session_summary'].includes(v.entryContext as string)) ||
      (v.venueId !== null && !uuid(v.venueId)) || (v.traderId !== null && (!uuid(v.traderId) || v.venueId === null)) ||
      (v.selectedMode !== null && !['fixed','percent'].includes(v.selectedMode as string)) || !timezone(v.proposedTimezone) ||
      (updating && !positiveVersion(v.expectedDraftVersion))) return invalid();
  for (const field of RAW_FIELDS) {
    const raw = v[field];
    if (raw !== null && (typeof raw !== 'string' || !validUnicode(raw) || [...raw].length > 64)) return invalid();
  }
  return v;
}
export function c05Request(body: unknown): Record<string, unknown> {
  const v = exactObject(body, ['requestSchemaVersion','draftId','expectedDraftVersion','proposedTimezone']);
  if (v.requestSchemaVersion !== 'v1' || !uuid(v.draftId) || !positiveVersion(v.expectedDraftVersion) ||
      !timezone(v.proposedTimezone)) return invalid();
  return v;
}
export function c06Request(body: unknown): Record<string, unknown> {
  const v = exactObject(body, ['requestSchemaVersion','clientCommandId','reviewId','expectedDraftVersion','expectedSlot']);
  if (v.requestSchemaVersion !== 'v1' || !uuid(v.clientCommandId) || !uuid(v.reviewId) ||
      !positiveVersion(v.expectedDraftVersion)) return invalid();
  const slot = v.expectedSlot as Record<string, unknown> | null;
  if (slot?.state === 'absent') exactObject(slot, ['state']);
  else if (slot?.state === 'present') {
    exactObject(slot, ['state','generation']); if (!positiveVersion(slot.generation)) return invalid();
  } else return invalid();
  return v;
}
