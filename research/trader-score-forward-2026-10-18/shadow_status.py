"""Read-only local capture status. Manifest counts are not financial evidence."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent


def inspect(root):
    counts=Counter();statuses=Counter();gaps=[]
    state_path=root/'runner-status.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    locked=False
    if (root/'runner.lock').exists():
        with (root/'runner.lock').open('a') as lock:
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                fcntl.flock(lock,fcntl.LOCK_UN)
            except BlockingIOError:locked=True
    captures=[]
    for directory in sorted(root.glob('capture-*')):
        file=directory/'manifest.json'
        if not file.exists():
            gaps.append({'capture':directory.name,'reason':'manifest_missing'});continue
        manifest=json.loads(file.read_text())
        counts.update(manifest.get('counts',{}));statuses[manifest.get('status','unknown')]+=1
        captures.append(dict(directory=directory.name,status=manifest.get('status'),
                             started_at=manifest.get('startedAt'),ended_at=manifest.get('endedAt'),
                             records=manifest.get('sequence'),events_sha256=manifest.get('eventsSha256')))
    return dict(checked_at=datetime.now(timezone.utc).isoformat(),runner_lock_held=locked,
                runner_reported_state=state,reported_event_counts=dict(counts),
                capture_status_counts=dict(statuses),captures=captures,unfinalized_gaps=gaps,
                local_storage_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
                counts_verified_by_this_status_reader=False,continuous_coverage_proven=False,
                qualified_financial_sessions=0,comparison_executed=False,winner=None,
                next_gate='audit identities, live bindings, coverage and modeled ledger before financial sessions')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=BASE/'observations')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args();report=inspect(args.root)
    content=json.dumps(report,indent=2)+'\n'
    if args.out:args.out.write_text(content)
    print(content)


if __name__=='__main__':main()
