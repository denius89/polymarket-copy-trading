"""Read-only public API probe; records both successful and failed responses.

No authentication, no trade operations, no access-control circumvention.
Uses a fresh timestamped directory so reruns never overwrite evidence.
"""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

URLS = {
    "feed": "https://api.limitless.exchange/feed/trading?audience=all&limit=30",
    "markets": "https://api.limitless.exchange/markets/active?limit=2",
}


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    folder = Path(__file__).parent / "raw" / now.strftime("%Y%m%dT%H%M%S%fZ")
    folder.mkdir(parents=True)
    records = []
    for name, url in URLS.items():
        observed = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            response = urllib.request.urlopen(url, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        except urllib.error.URLError as error:
            records.append({"url": url, "observed_at": observed,
                            "network_error": str(error), "status": None})
            continue
        with response:
            body = response.read()
            filename = name + ".body"
            (folder / filename).write_bytes(body)
            records.append({"url": url, "observed_at": observed,
                            "status": response.code, "response_headers": dict(response.headers),
                            "body_file": filename, "bytes": len(body),
                            "sha256": hashlib.sha256(body).hexdigest()})
    (folder / "manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps({"folder": str(folder), "statuses": [r["status"] for r in records]}))


if __name__ == "__main__":
    main()
