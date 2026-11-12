import { versions } from 'node:process';
import { Temporal } from '@js-temporal/polyfill';

export const DEADLINE_ALGORITHM = 'paper-evaluation-deadline-v1' as const;
export const TEMPORAL_POLYFILL_VERSION = '0.5.1' as const;

/** Operator-approved profile, never inferred from a browser or accepted by echoing runtime values. */
export interface CalendarProfile {
  node: string;
  icu: string;
  tzdb: string;
  temporalPolyfill: typeof TEMPORAL_POLYFILL_VERSION;
}
export interface EvaluationDeadline {
  evaluationDeadlineAt: string;
  deadlineCalculationVersion: typeof DEADLINE_ALGORITHM;
  timezoneDatabaseVersion: string;
}

/** Internal failure: adapter returns technical unavailability and rolls back C06. */
export class CalendarUnavailable extends Error {
  constructor() { super('Calendar calculation unavailable'); this.name = 'CalendarUnavailable'; }
}

export function assertCalendarProfile(profile: CalendarProfile): void {
  if (!profile || typeof profile !== 'object' ||
      Object.keys(profile).sort().join(',') !== 'icu,node,temporalPolyfill,tzdb' ||
      !profile.node || !profile.icu || !profile.tzdb ||
      profile.node !== versions.node || profile.icu !== versions.icu || profile.tzdb !== versions.tz ||
      profile.temporalPolyfill !== TEMPORAL_POLYFILL_VERSION) throw new CalendarUnavailable();
}

/** Pure CPU calculation between c06_prepare and c06_finish on the same DB transaction. */
export function calculateEvaluationDeadline(
  startedAt: string, ianaTimezone: string, profile: CalendarProfile,
): EvaluationDeadline {
  assertCalendarProfile(profile);
  try {
    // DB prepared values must remain canonical. Temporal's permissive parsing is not a wire validator.
    if (typeof startedAt !== 'string' ||
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(startedAt) ||
        typeof ianaTimezone !== 'string' || !/^[A-Za-z][A-Za-z0-9._+\-/]*$/.test(ianaTimezone)) {
      throw new CalendarUnavailable();
    }
    const start = Temporal.Instant.from(startedAt);
    if (start.toString({ fractionalSecondDigits: 3 }) !== startedAt) throw new CalendarUnavailable();
    const target = start.toZonedDateTimeISO(ianaTimezone).toPlainDateTime().add({ days: 14 });
    const earlier = target.toZonedDateTime(ianaTimezone, { disambiguation: 'earlier' });
    let deadline = earlier;
    if (!earlier.toPlainDateTime().equals(target)) {
      // Gap: shifting by the offset difference would preserve minutes incorrectly.
      // The first instant after the discontinuity is the accepted boundary, even for a skipped date.
      const later = target.toZonedDateTime(ianaTimezone, { disambiguation: 'later' });
      const transition = earlier.getTimeZoneTransition('next');
      if (!transition || Temporal.ZonedDateTime.compare(transition, later) > 0 ||
          Temporal.PlainDateTime.compare(transition.toPlainDateTime(), target) <= 0 ||
          Temporal.PlainDateTime.compare(transition.subtract({ nanoseconds: 1 }).toPlainDateTime(), target) >= 0) {
        throw new CalendarUnavailable();
      }
      deadline = transition;
    }
    const instant = deadline.toInstant();
    if (Temporal.Instant.compare(instant, start) <= 0 || instant.epochNanoseconds % 1_000_000n !== 0n) {
      throw new CalendarUnavailable();
    }
    const evaluationDeadlineAt = instant.toString({ fractionalSecondDigits: 3 });
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(evaluationDeadlineAt)) {
      throw new CalendarUnavailable();
    }
    return {
      evaluationDeadlineAt,
      deadlineCalculationVersion: DEADLINE_ALGORITHM,
      timezoneDatabaseVersion: profile.tzdb,
    };
  } catch {
    // Do not expose timezone/provider/library messages or manufacture a UTC fallback.
    throw new CalendarUnavailable();
  }
}
