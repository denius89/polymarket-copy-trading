"""Read the JSON messages of one Polymarket buy service from standard input."""

from collections import Counter, defaultdict
import argparse
import json
from math import ceil
import re
import sys


def milliseconds(value):
    return value if type(value) is int and 0 <= value <= 3_600_000 else None


def add_sample(samples, label, end, start=0):
    if end is not None and start is not None and end >= start:
        samples[label].append(end - start)


def read_events(lines):
    stages = defaultdict(lambda: defaultdict(list))
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        signal = str(event.get('signalId', ''))
        stage = event.get('stage')
        if not signal.isascii() or not 1 <= len(signal) <= 19 or not signal.isdigit():
            continue
        if isinstance(stage, str) and stage.startswith('polygon-'):
            stages[int(signal)][stage].append(event)
    return stages


def summarize(signals, observations):
    samples = defaultdict(list)
    skips = Counter()
    stage_counts = Counter()
    for signal_id, signal in signals.items():
        stage_counts.update(signal.keys())
        resolved = signal.get('polygon-direct-signal', [{}])[0]
        visibility = signal.get('polygon-queue-signal-visible', [{}])[0]
        inserted = milliseconds(visibility.get('insertionAgeMs', resolved.get('publishedMs')))
        visible = milliseconds(visibility.get('signalAgeMs', resolved.get('firstSeenMs')))
        add_sample(samples, 'sourceToInsertion', inserted)
        add_sample(samples, 'sourceToVisible', visible)
        add_sample(samples, 'insertionToVisible', visible, inserted)
        add_sample(samples, 'visibleToPrepared', milliseconds(resolved.get('verifiedMs')))
        observation = observations.get(signal_id, {})
        add_sample(samples, 'visibleToObservation', milliseconds(observation.get('observationAgeMs')), visible)

        # This event is emitted *after* the history check in the checked quote route.
        # Only claimMs measures the lease call, including its transaction exit.
        claim = signal.get('polygon-queue-quote-claim', [{}])[-1]
        add_sample(samples, 'claimCall', milliseconds(claim.get('claimMs')))
        history = signal.get('polygon-quote-history-checked', [{}])[-1]
        history_ms = milliseconds(history.get('historyMs'))
        history_end = milliseconds(history.get('signalAgeMs'))
        add_sample(samples, 'historyCheck', history_ms)
        add_sample(samples, 'sourceToHistoryEnd', history_end)

        # Keep before/after differences within the same successful attempt.
        committed = signal.get('polygon-queue-purchase-committed', [])
        if len(committed) == 1:
            purchase = committed[0]
            book = milliseconds(purchase.get('sourceToBookMs'))
            issue = milliseconds(purchase.get('sourceToIssueMs'))
            finish = milliseconds(purchase.get('sourceToCommitMs'))
            add_sample(samples, 'recordedSourceToBook', book)
            add_sample(samples, 'recordedSourceToIssue', issue)
            add_sample(samples, 'recordedSourceToCommit', finish)
            add_sample(samples, 'recordedBookToCommit', finish, book)
            add_sample(samples, 'recordedIssueCall', milliseconds(purchase.get('issueMs')))
            add_sample(samples, 'recordedWriteCommit', milliseconds(purchase.get('writeCommitMs')))

        refused = signal.get('polygon-direct-skip', [])
        if refused and not committed:
            reason = refused[-1].get('reason')
            if isinstance(reason, str) and re.fullmatch(r'[A-Za-z0-9_]{1,64}', reason):
                skips[reason] += 1
            add_sample(samples, 'refusedSourceToSkip', milliseconds(refused[-1].get('ageMs')))

    expired = [row for row in observations.values() if row['outcome'] == 'signal_expired']
    return {
        'distinctSignalsWithLogs': len(signals),
        'distinctSignalsByStage': dict(stage_counts),
        'lastSkipWithoutRecordedPurchase': dict(skips),
        'expiredJobs': {
            'total': len(expired),
            'observationAfterDeadline': sum(row['observationAfterDeadline'] is True for row in expired),
            'priorJobUnfinishedAtDeadline': sum(row['priorJobUnfinishedAtDeadline'] is True for row in expired),
            'observationBeforeDeadlineWithPriorJob': sum(
                row['observationAfterDeadline'] is False and row['priorJobUnfinishedAtDeadline'] is True
                for row in expired
            ),
            'observationMissing': sum(row['observationAgeMs'] is None for row in expired),
        } if observations else None,
        'milliseconds': {
            key: {'samples': len(values), 'p95': sorted(values)[ceil(len(values) * 0.95) - 1]}
            for key, values in samples.items()
        },
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations', help='JSON lines from polygon-observation-timings.sql')
    args = parser.parse_args()
    observations = {}
    if args.observations:
        with open(args.observations, encoding='utf-8') as rows:
            observations = {row['signalId']: row for row in map(json.loads, rows)}
    print(json.dumps(summarize(read_events(sys.stdin), observations), sort_keys=True))
