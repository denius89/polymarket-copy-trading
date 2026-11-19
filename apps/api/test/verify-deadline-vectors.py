"""Independent check of fixed H06 expected UTC values with Python zoneinfo, not Temporal.

Does not generate or update fixtures. A different tzdb is a bounded cross-check,
not proof that the production runtime has the required timezone data.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, TZPATH


def parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


vectors = json.loads(Path(__file__).with_name("deadline-vectors.json").read_text())
for item in vectors:
    zone = ZoneInfo(item["zone"])
    start = parse(item["start"])
    target = start.astimezone(zone).replace(tzinfo=None) + timedelta(days=14)
    expected = parse(item["expected"])
    valid = []
    for fold in (0, 1):
        candidate = target.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
        if candidate.astimezone(zone).replace(tzinfo=None) == target:
            valid.append(candidate)
    if valid:
        assert expected == min(valid), item["id"]
    else:
        # At the expected boundary, local time crosses the missing target in a single millisecond.
        before = (expected - timedelta(milliseconds=1)).astimezone(zone).replace(tzinfo=None)
        after = expected.astimezone(zone).replace(tzinfo=None)
        assert before < target < after, item["id"]
        assert expected.microsecond == 0, item["id"]
    assert expected > start, item["id"]

version = "not recorded by this zoneinfo installation"
for root in TZPATH:
    for filename in ("tzdata.zi", "+VERSION"):
        path = Path(root) / filename
        if path.is_file():
            version = path.read_text().splitlines()[0]
            break
    if version != "not recorded by this zoneinfo installation":
        break
print(json.dumps({"fixed_vectors": len(vectors), "verdict": "pass", "tzdb_evidence": version}))
