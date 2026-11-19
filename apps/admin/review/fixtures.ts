export const assignments = {
  ownerA: ['Елена Морозова · STAFF-201 · Владелец A', 'Elena Morozova · STAFF-201 · Owner A'],
  ownerB: ['Максим Орлов · STAFF-202 · Владелец B', 'Maxim Orlov · STAFF-202 · Owner B'],
  lead: ['Олег Смирнов · STAFF-206 · Руководитель операций', 'Oleg Smirnov · STAFF-206 · Operations lead'],
  ops: ['Нора Азиз · STAFF-203 · Операции и поддержка', 'Nora Aziz · STAFF-203 · Operations and support'],
  limited: ['Нора Азиз · STAFF-203 · Назначение DEMO-R1', 'Nora Aziz · STAFF-203 · Assignment DEMO-R1'],
  marketing: ['Ирина Волкова · STAFF-204 · Маркетинг', 'Irina Volkova · STAFF-204 · Marketing'],
  audit: ['Аудитор · STAFF-205 · Просмотр', 'Auditor · STAFF-205 · Read only'],
} as const;

export type Assignment = keyof typeof assignments;
export type Venue = 'Polymarket' | 'Limitless';
export type Issue = 'ok' | 'unknown' | 'partial' | 'stale';

export interface UserFixture {
  id: string;
  name: string;
  date: string;
  session?: {
    id: string;
    venue: Venue;
    issue: Issue;
    budget: number;
    free: number | null;
    reserved: number;
    positions: number;
  };
}

export const users: readonly UserFixture[] = [
  { id: 'U-DEMO-001', name: 'Demo Atlas', date: '2026-10-17', session: { id: 'S-DEMO-001', venue: 'Polymarket', issue: 'ok', budget: 200, free: 160, reserved: 20, positions: 20 } },
  { id: 'U-DEMO-002', name: 'Demo Noor', date: '2026-10-18', session: { id: 'S-DEMO-002', venue: 'Polymarket', issue: 'unknown', budget: 200, free: 160, reserved: 20, positions: 20 } },
  { id: 'U-DEMO-005', name: 'Demo Robin', date: '2026-10-21', session: { id: 'S-DEMO-005', venue: 'Limitless', issue: 'partial', budget: 200, free: 160, reserved: 12, positions: 28 } },
  { id: 'U-DEMO-006', name: 'Demo Cedar', date: '2026-10-22' },
  { id: 'U-DEMO-009', name: 'Demo Orion', date: '2026-10-18', session: { id: 'S-DEMO-009', venue: 'Limitless', issue: 'stale', budget: 200, free: null, reserved: 20, positions: 20 } },
];
