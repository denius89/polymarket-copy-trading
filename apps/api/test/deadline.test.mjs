import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { versions, env } from 'node:process';
import { Temporal } from '@js-temporal/polyfill';
import { calculateEvaluationDeadline, assertCalendarProfile, CalendarUnavailable } from '../src/time/evaluation-deadline.ts';

// Explicit local evidence profile. New runtime requires a reviewed fixture/profile change, not auto-acceptance.
const profile = JSON.parse(readFileSync(env.CCT_CALENDAR_PROFILE_FILE ?? new URL('./calendar-profile.local.json', import.meta.url), 'utf8'));
const vectors = JSON.parse(readFileSync(new URL('./deadline-vectors.json', import.meta.url), 'utf8'));

test('test runtime matches the explicitly pinned calendar profile', () => {
  assert.equal(versions.node, profile.node);
  assert.equal(versions.icu, profile.icu);
  assert.equal(versions.tz, profile.tzdb);
  assertCalendarProfile(profile);
});
for (const vector of vectors) test(`H06 ${vector.id}: ${vector.rule}`, () => {
  const result = calculateEvaluationDeadline(vector.start, vector.zone, profile);
  assert.deepEqual(result, {
    evaluationDeadlineAt: vector.expected,
    deadlineCalculationVersion: 'paper-evaluation-deadline-v1',
    timezoneDatabaseVersion: profile.tzdb,
  });
  assert.deepEqual(calculateEvaluationDeadline(vector.start, vector.zone, profile), result);
});

test('the gap fixture distinguishes the required rule from Temporal compatible', () => {
  const compatible = Temporal.ZonedDateTime.from('2026-03-29T02:30:12.345[Europe/Warsaw]');
  assert.equal(compatible.toInstant().toString({fractionalSecondDigits: 3}), '2026-03-29T01:30:12.345Z');
  assert.notEqual(compatible.toInstant().toString({fractionalSecondDigits: 3}), vectors.find(x => x.id === 'warsaw-gap').expected);
});

test('unknown/mismatched runtime profiles fail closed', () => {
  for (const invalid of [null, {}, {...profile, tzdb: ''}, {...profile, tzdb: `${profile.tzdb}-mismatch`},
    {...profile, node: `${profile.node}-mismatch`}, {...profile, icu: `${profile.icu}-mismatch`}, {...profile, temporalPolyfill: '0.5.0'},
    {...profile, unexpected: true}]) {
    assert.throws(() => calculateEvaluationDeadline(vectors[0].start, 'UTC', invalid), CalendarUnavailable);
  }
});

test('corrupt prepared timestamps and unsupported timezone values never fall back', () => {
  for (const start of [null, '', '2026-02-30T00:00:00.000Z', '2026-01-01T00:00:00Z',
    '2026-01-01T00:00:00.000000Z', '2026-01-01T00:00:00.000+00:00', '2016-12-31T23:59:60.000Z']) {
    assert.throws(() => calculateEvaluationDeadline(start, 'UTC', profile), CalendarUnavailable);
  }
  for (const zone of [null, '', ' Europe/Warsaw', 'Europe/Warsaw ', '+01:00', '-04:00', 'Not/AZone', 'UTC\u0000']) {
    assert.throws(() => calculateEvaluationDeadline(vectors[0].start, zone, profile), CalendarUnavailable);
  }
});

test('out-of-wire-range result is not silently rounded or expanded', () => {
  assert.throws(() => calculateEvaluationDeadline('9999-12-31T00:00:00.000Z', 'UTC', profile), CalendarUnavailable);
});
