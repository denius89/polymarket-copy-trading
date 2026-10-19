#!/usr/bin/env python3
"""Bounded public observation recorder. No accounts, orders, fills or scoring.

Python 3.11+; websockets 15.x is optional (required only for market WebSocket).
Raw observations deliberately remain unqualified for economic replay.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import gzip
import importlib.metadata
import json
import math
from pathlib import Path
import re
import signal
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler
import uuid

SCHEMA = "forward-observation-v1"
WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
MAX_BODY_BYTES = 4 * 1024 * 1024
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}\Z")
CONDITION = re.compile(r"0x[0-9a-fA-F]{64}\Z")
ASSET = re.compile(r"[0-9]{1,100}\Z")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,250}\Z")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def finite_number(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: finite number required")
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{name}: required range {lower}..{upper}")
    return value


def validate_config(raw):
    allowed = {"schemaVersion", "assets", "leaders", "limitless", "pollIntervalSeconds",
               "activityOverlapSeconds", "activityPages", "websocket", "metadataIntervalSeconds"}
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise ValueError("unknown config fields; secrets/endpoints are never accepted")
    if raw.get("schemaVersion") != "forward-collector-config-v1":
        raise ValueError("unsupported config schema")
    result = dict(raw)
    for key in ("assets", "leaders", "limitless"):
        result.setdefault(key, [])
        if not isinstance(result[key], list) or len(result[key]) > 8:
            raise ValueError(f"{key}: at most 8 explicit scopes")
    for item in result["assets"]:
        if not isinstance(item, dict) or set(item) != {"assetId", "conditionId"}:
            raise ValueError("asset scope needs only assetId and conditionId")
        if not ASSET.fullmatch(str(item["assetId"])) or not isinstance(item["assetId"], str):
            raise ValueError("assetId must be a decimal string")
        if not CONDITION.fullmatch(str(item["conditionId"])):
            raise ValueError("invalid conditionId")
    for item in result["leaders"]:
        if not isinstance(item, dict) or set(item) != {"address"} or not ADDRESS.fullmatch(str(item["address"])):
            raise ValueError("leader scope requires a public EVM address")
    for item in result["limitless"]:
        if not isinstance(item, dict) or set(item) != {"slug"} or not SLUG.fullmatch(str(item["slug"])):
            raise ValueError("Limitless scope requires only a safe slug")
    for key, field in (("assets", "assetId"), ("leaders", "address"), ("limitless", "slug")):
        identities = [item[field].lower() for item in result[key]]
        if len(set(identities)) != len(identities):
            raise ValueError(f"duplicate {key} scope")
    result.setdefault("pollIntervalSeconds", 15)
    result.setdefault("metadataIntervalSeconds", 60)
    result.setdefault("activityOverlapSeconds", 60)
    result.setdefault("activityPages", 2)
    result.setdefault("websocket", True)
    finite_number(result["pollIntervalSeconds"], "pollIntervalSeconds", 2, 3600)
    finite_number(result["metadataIntervalSeconds"], "metadataIntervalSeconds", 30, 86400)
    finite_number(result["activityOverlapSeconds"], "activityOverlapSeconds", 1, 3600)
    if type(result["activityPages"]) is not int or not 1 <= result["activityPages"] <= 5:
        raise ValueError("activityPages needs integer 1..5")
    if type(result["websocket"]) is not bool:
        raise ValueError("websocket must be boolean")
    if not any(result[key] for key in ("assets", "leaders", "limitless")):
        raise ValueError("collection requires at least one explicit scope")
    return result


def endpoint_url(endpoint, scope=None, **query):
    """Construct GET-only URLs from hard-coded public hosts/routes, never user URLs."""
    scope = scope or {}
    if endpoint == "polymarket-discovery":
        if query:
            raise ValueError("discovery has fixed bounded query")
        return "https://gamma-api.polymarket.com/markets?closed=false&active=true&limit=5"
    if endpoint == "limitless-discovery":
        if query:
            raise ValueError("discovery has fixed bounded query")
        return "https://api.limitless.exchange/markets/active?limit=5&page=1"
    if endpoint in ("polymarket-book", "polymarket-fee-rate", "polymarket-tick-size"):
        asset = scope.get("assetId", "")
        if not isinstance(asset, str) or not ASSET.fullmatch(asset) or query:
            raise ValueError("invalid asset request")
        route = {"polymarket-book": "book", "polymarket-fee-rate": "fee-rate",
                 "polymarket-tick-size": "tick-size"}[endpoint]
        return f"https://clob.polymarket.com/{route}?" + urlencode({"token_id": asset})
    if endpoint == "polymarket-market":
        condition = scope.get("conditionId", "")
        if not isinstance(condition, str) or not CONDITION.fullmatch(condition) or query:
            raise ValueError("invalid condition request")
        return f"https://clob.polymarket.com/markets/{condition}"
    if endpoint in ("polymarket-activity", "polymarket-positions"):
        address = scope.get("address", "")
        if not isinstance(address, str) or not ADDRESS.fullmatch(address):
            raise ValueError("invalid public address")
        if endpoint == "polymarket-positions":
            if set(query) - {"cursor"}:
                raise ValueError("positions only accepts cursor paging")
            params = {"user": address, "limit": 500, "status": "OPEN", "filter_type": "TOKENS",
                      "filter_amount": 0, "include_archived": "true", **query}
            return "https://data-api.polymarket.com/v2/positions?" + urlencode(params)
        if set(query) - {"start", "end", "cursor"} or not {"start", "end"} <= set(query):
            raise ValueError("activity needs explicit fixed window")
        if any(type(query[k]) is not int or query[k] < 0 for k in ("start", "end")):
            raise ValueError("invalid activity window")
        if query["start"] > query["end"]:
            raise ValueError("invalid activity window")
        cursor = query.get("cursor")
        if cursor is not None and (not isinstance(cursor, str) or not 1 <= len(cursor) <= 8192):
            raise ValueError("invalid cursor")
        params = {"user": address, "limit": 500, "sort_by": "TIMESTAMP", "sort_direction": "ASC",
                  "exclude_deposits_withdrawals": "false", **query}
        return "https://data-api.polymarket.com/v2/activity?" + urlencode(params)
    if endpoint in ("limitless-market", "limitless-book", "limitless-events"):
        slug = scope.get("slug", "")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or query:
            raise ValueError("invalid market slug")
        suffix = {"limitless-book": "/orderbook", "limitless-events": "/events?page=1&limit=20"}.get(endpoint, "")
        return f"https://api.limitless.exchange/markets/{slug}{suffix}"
    raise ValueError("endpoint outside public GET allowlist")


def v2_page(document):
    if not isinstance(document, dict) or not isinstance(document.get("data"), list):
        raise ValueError("v2 data must be array (null means unavailable, not empty ledger)")
    paging = document.get("pagination")
    if not isinstance(paging, dict) or type(paging.get("has_more")) is not bool or "next_cursor" not in paging:
        raise ValueError("v2 pagination evidence missing")
    cursor = paging["next_cursor"]
    if cursor is not None and (not isinstance(cursor, str) or not 1 <= len(cursor) <= 8192):
        raise ValueError("v2 cursor malformed")
    if paging["has_more"] != (cursor is not None):
        raise ValueError("v2 has_more/next_cursor conflict")
    return document["data"], cursor


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "redirect refused", headers, fp)


def fetch_public(endpoint, scope=None, *, timeout=8, **query):
    """Bounded transport; redirects, credentials, methods and cookie storage unavailable."""
    url = endpoint_url(endpoint, scope, **query)
    started_at, started_ns = utc_now(), time.monotonic_ns()
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "CCT-Forward-ReadOnly/1.0"}, method="GET")
    opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    status, headers, body, error = None, {}, b"", None
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
        error = f"HTTP_{exc.code}"
    except (URLError, OSError, TimeoutError) as exc:
        response = None
        error = type(exc).__name__
    truncated = False
    if response is not None:
        try:
            with response:
                status = response.code
                # An allowlist excludes Set-Cookie/auth headers from evidence.
                headers = {k.lower(): v for k, v in response.headers.items()
                           if k.lower() in {"date", "content-type", "retry-after", "etag", "last-modified", "cache-control", "age"}}
                body = response.read(MAX_BODY_BYTES + 1)
                if len(body) > MAX_BODY_BYTES:
                    body, truncated, error = body[:MAX_BODY_BYTES], True, "body_limit"
        except (OSError, TimeoutError) as exc:
            error = type(exc).__name__
    received_at, received_ns = utc_now(), time.monotonic_ns()
    return {"endpoint": endpoint, "url": url, "method": "GET", "startedAt": started_at,
            "startedMonotonicNs": started_ns, "observedAt": received_at,
            "observedMonotonicNs": received_ns, "status": status, "headers": headers,
            "error": error, "truncated": truncated, "body": body}


class ByteLimit(Exception):
    pass


class Recorder:
    def __init__(self, directory, config, max_bytes):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.run_id = str(uuid.uuid4())
        self.config = config
        self.max_bytes = max_bytes
        self.sequence, self.bytes = 0, 0
        self.chain = None
        self.counts = Counter()
        self.status = "running"
        self.source_bytes = Path(__file__).read_bytes()
        self.source_sha256 = sha256(self.source_bytes)
        self.started_at = utc_now()
        self.started_ns = time.monotonic_ns()
        self.stream = (self.directory / "events.jsonl").open("xb", buffering=0)
        (self.directory / "config.json").write_bytes(canonical(config) + b"\n")
        (self.directory / "collector-source.py.txt").write_bytes(self.source_bytes)
        self.checkpoint()

    def append(self, venue, kind, scope, *, raw=None, observed_at=None, observed_ns=None, **details):
        record = {"schemaVersion": SCHEMA, "runId": self.run_id, "sequence": self.sequence + 1,
                  "observedAt": observed_at or utc_now(), "observedMonotonicNs": observed_ns or time.monotonic_ns(),
                  "venue": venue, "kind": kind, "scope": scope, "prevRecordSha256": self.chain,
                  "economicSignalQualified": False, **details}
        if raw is not None:
            record["rawBase64"] = base64.b64encode(raw).decode()
            record["rawBytes"] = len(raw)
            record["bodySha256"] = sha256(raw)
        digest = sha256(canonical(record))
        record["recordSha256"] = digest
        line = canonical(record) + b"\n"
        if self.bytes + len(line) > self.max_bytes:
            raise ByteLimit("event bytes cap reached")
        self.stream.write(line)
        self.sequence += 1
        self.bytes += len(line)
        self.chain = digest
        self.counts[f"{venue}:{kind}"] += 1
        return record

    def checkpoint(self, **extra):
        manifest = {"schemaVersion": "forward-capture-manifest-v1", "runId": self.run_id,
                    "status": self.status, "startedAt": self.started_at, "updatedAt": utc_now(),
                    "startedMonotonicNs": self.started_ns, "sequence": self.sequence,
                    "eventBytes": self.bytes, "eventByteLimit": self.max_bytes,
                    "lastRecordSha256": self.chain, "counts": dict(self.counts),
                    "collectorSha256": self.source_sha256,
                    "configSha256": sha256((self.directory / "config.json").read_bytes()),
                    "economicSignalsQualified": 0, "actualOrdersSent": 0,
                    "actualFillsObserved": 0, "historicalReplayPnl": None,
                    "continuityGuaranteed": False, "completeLeaderLedger": False,
                    "pythonVersion": sys.version, **extra}
        path = self.directory / "manifest.json"
        temp = self.directory / "manifest.tmp"
        temp.write_bytes(canonical(manifest) + b"\n")
        temp.replace(path)

    def close(self, status, **extra):
        self.status = status
        self.stream.close()
        digest = hashlib.sha256()
        with (self.directory / "events.jsonl").open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        self.checkpoint(endedAt=utc_now(), eventsSha256=digest.hexdigest(), **extra)


class Collector:
    def __init__(self, config, recorder, duration):
        self.config, self.recorder = config, recorder
        self.deadline = time.monotonic() + duration
        self.stop = asyncio.Event()
        self.start_epoch = int(time.time())
        self.http_backoff = {}

    def remaining(self):
        return max(0, self.deadline - time.monotonic())

    def record(self, *args, **kwargs):
        try:
            return self.recorder.append(*args, **kwargs)
        except ByteLimit:
            self.stop.set()
            raise

    async def request(self, endpoint, scope=None, **query):
        if not self.remaining() or self.stop.is_set():
            return None
        identity = (endpoint, json.dumps(scope or {}, sort_keys=True))
        if self.http_backoff.get(identity, 0) > time.monotonic():
            return None
        result = await asyncio.to_thread(fetch_public, endpoint, scope,
                                         timeout=max(.1, min(8, self.remaining())), **query)
        venue = endpoint.split("-", 1)[0]
        raw = result.pop("body")
        self.record(venue, "http_response", scope or {}, raw=raw, transport="https", request=result,
                    observed_at=result["observedAt"], observed_ns=result["observedMonotonicNs"])
        if result["error"] or result["status"] != 200:
            retry = result["headers"].get("retry-after", "15")
            try:
                seconds = float(retry)
                retry = max(2, seconds) if math.isfinite(seconds) and seconds >= 0 else 15
            except (ValueError, TypeError):
                try:
                    date = parsedate_to_datetime(retry)
                    if date.tzinfo is None:
                        raise ValueError("Retry-After date has no timezone")
                    retry = max(2, date.timestamp() - time.time())
                except (ValueError, TypeError, OverflowError):
                    retry = 15
            self.http_backoff[identity] = time.monotonic() + retry
            self.record(venue, "coverage_gap", scope or {}, transport="https",
                        reason=result["error"] or f"HTTP_{result['status']}", endpoint=endpoint,
                        recovery="later GET observation does not repair missing interval")
            return None
        if result["truncated"]:
            return None
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            self.record(venue, "invalid_payload", scope or {}, endpoint=endpoint,
                        reason="HTTP200 body is not valid JSON")
            return None

    async def poll(self):
        last_metadata = float("-inf")
        last_activity_end = self.start_epoch
        while self.remaining() and not self.stop.is_set():
            cycle_start = time.monotonic()
            metadata = cycle_start - last_metadata >= self.config["metadataIntervalSeconds"]
            if metadata:
                last_metadata = cycle_start
            for asset in self.config["assets"]:
                await self.request("polymarket-book", asset)
                if metadata:
                    for endpoint in ("polymarket-fee-rate", "polymarket-tick-size", "polymarket-market"):
                        await self.request(endpoint, asset)
            end = int(time.time())
            start = max(0, last_activity_end - int(self.config["activityOverlapSeconds"]))
            for leader in self.config["leaders"]:
                if metadata:
                    positions = await self.request("polymarket-positions", leader)
                    try:
                        position_rows, position_cursor = v2_page(positions)
                        if position_cursor:
                            self.record("polymarket", "positions_baseline_incomplete", leader,
                                        reason="bounded OPEN positions page has next_cursor")
                        if any(not isinstance(row, dict) or str(row.get("proxy_wallet", "")).lower() != leader["address"].lower()
                               for row in position_rows):
                            self.record("polymarket", "positions_baseline_incomplete", leader,
                                        reason="position row identity mismatch")
                    except ValueError as exc:
                        self.record("polymarket", "positions_baseline_incomplete", leader, reason=str(exc))
                cursor, seen_cursors = None, set()
                for page in range(self.config["activityPages"]):
                    query = {"start": start, "end": end}
                    if cursor is not None:
                        query["cursor"] = cursor
                    response = await self.request("polymarket-activity", leader, **query)
                    if response is None:
                        break
                    try:
                        rows, cursor = v2_page(response)
                    except ValueError as exc:
                        self.record("polymarket", "invalid_payload", leader,
                                    reason=str(exc), endpoint="polymarket-activity")
                        break
                    mismatch = any(not isinstance(row, dict) or str(row.get("proxy_wallet", "")).lower() != leader["address"].lower()
                                   for row in rows)
                    self.record("polymarket", "activity_window_quality", leader, start=start, end=end,
                                page=page, rowCount=len(rows), identityValid=not mismatch,
                                economicIdentity="unqualified API rows, transactionHash not guaranteed unique event ID",
                                paginationReachedEnd=cursor is None,
                                completeWindow=False, activityScope="v2 default types; TIP opt-in not included")
                    if cursor is None:
                        break
                    if cursor in seen_cursors:
                        self.record("polymarket", "coverage_gap", leader,
                                    reason="repeated v2 cursor", start=start, end=end)
                        break
                    seen_cursors.add(cursor)
                    if page == self.config["activityPages"] - 1:
                        self.record("polymarket", "coverage_gap", leader,
                                    reason="activity fixed-window page budget exhausted", start=start, end=end)
            last_activity_end = end
            for market in self.config["limitless"]:
                if metadata:
                    await self.request("limitless-market", market)
                await self.request("limitless-book", market)
                events = await self.request("limitless-events", market)
                self.record("limitless", "market_events_quality", market,
                            page=1, pageBudget=1, rowLimit=20,
                            responseAvailable=isinstance(events, dict) and isinstance(events.get("events"), list),
                            completeWindow=False,
                            identity="public profile not guaranteed wallet; taker-only aggregate MINED rows unqualified",
                            caching="documented response cache may delay source visibility")
            self.recorder.checkpoint()
            delay = min(self.remaining(), max(0, self.config["pollIntervalSeconds"] - (time.monotonic() - cycle_start)))
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=delay)
            except TimeoutError:
                pass

    async def websocket(self):
        if not self.config["assets"] or not self.config["websocket"]:
            return
        try:
            import websockets
        except ImportError:
            self.record("polymarket", "coverage_gap", {}, transport="wss", reason="websockets dependency unavailable")
            return
        attempt = 0
        while self.remaining() and not self.stop.is_set():
            attempt += 1
            connection_id = f"{self.recorder.run_id}:{attempt}"
            scope = {"connectionId": connection_id, "assetIds": [a["assetId"] for a in self.config["assets"]]}
            self.record("polymarket", "connection_start", scope, transport="wss", url=WS_URL,
                        sequenceContinuity="not_proven", reconnect=attempt > 1)
            try:
                async with websockets.connect(WS_URL, open_timeout=min(8, self.remaining()),
                                              ping_interval=None, close_timeout=1,
                                              max_size=MAX_BODY_BYTES, max_queue=16) as ws:
                    subscription = {"assets_ids": scope["assetIds"], "type": "market", "custom_feature_enabled": True}
                    await ws.send(json.dumps(subscription))
                    self.record("polymarket", "subscription_sent", scope, transport="wss", subscription=subscription,
                                economicSignalQualified=False)
                    next_ping = time.monotonic() + 10
                    last_pong = time.monotonic()
                    while self.remaining() and not self.stop.is_set():
                        if time.monotonic() >= next_ping:
                            await ws.send("PING")
                            next_ping = time.monotonic() + 10
                            self.record("polymarket", "heartbeat_sent", scope, transport="wss")
                        if time.monotonic() - last_pong > 30:
                            raise TimeoutError("application heartbeat PONG timeout")
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=min(1, self.remaining()))
                        except TimeoutError:
                            continue
                        received_at, received_ns = utc_now(), time.monotonic_ns()
                        if isinstance(raw, str):
                            raw = raw.encode()
                        kind = "heartbeat_received" if raw == b"PONG" else "market_message"
                        if kind == "heartbeat_received":
                            last_pong = time.monotonic()
                        self.record("polymarket", kind, scope, raw=raw, transport="wss",
                                    observed_at=received_at, observed_ns=received_ns,
                                    streamSequenceGuaranteed=False)
            except ByteLimit:
                raise
            except Exception as exc:
                self.record("polymarket", "coverage_gap", scope, transport="wss",
                            reason=type(exc).__name__, error=str(exc)[:300],
                            recovery="invalidate local book; wait for fresh full snapshot; missing interval remains")
            finally:
                self.record("polymarket", "connection_end", scope, transport="wss")
            if self.remaining() and not self.stop.is_set():
                try:
                    await asyncio.wait_for(self.stop.wait(), timeout=min(2, self.remaining()))
                except TimeoutError:
                    pass

    async def run(self):
        self.record("system", "capture_start", {}, transport="local",
                    interpretation="public observations only; no authoritative economic signals or fills",
                    clockSync="not_externally_verified", deadlineMonotonic=self.deadline)
        tasks = [asyncio.create_task(self.poll()), asyncio.create_task(self.websocket())]
        try:
            await asyncio.gather(*tasks)
        finally:
            self.stop.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


def verify_run(directory):
    """Verify byte-level lineage; deliberately does not certify market completeness."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    config_raw = (directory / "config.json").read_bytes()
    if sha256(config_raw) != manifest["configSha256"]:
        raise ValueError("config hash mismatch")
    source = directory / "collector-source.py.txt"
    if not source.is_file() or sha256(source.read_bytes()) != manifest["collectorSha256"]:
        raise ValueError("frozen source hash mismatch")
    validate_config(json.loads(config_raw))
    prior, sequence, size, digest = None, 0, 0, hashlib.sha256()
    event_path = directory / "events.jsonl"
    archived = not event_path.is_file()
    if archived:
        event_path = directory / "events.jsonl.gz"
        archive = json.loads((directory / "archive.json").read_text())
        if archive.get("schemaVersion") != "forward-event-archive-v1" or archive.get("file") != "events.jsonl.gz":
            raise ValueError("invalid event archive contract")
        compressed_digest = hashlib.sha256()
        with event_path.open("rb") as compressed:
            for chunk in iter(lambda: compressed.read(1024 * 1024), b""):
                compressed_digest.update(chunk)
        if compressed_digest.hexdigest() != archive.get("compressedSha256"):
            raise ValueError("compressed file hash mismatch")
        if archive.get("uncompressedSha256") != manifest.get("eventsSha256"):
            raise ValueError("archive origin hash mismatch")
    opener = gzip.open if archived else open
    with opener(event_path, "rb") as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            row = json.loads(line)
            sequence += 1
            claimed = row.pop("recordSha256")
            if row["sequence"] != sequence or row["prevRecordSha256"] != prior:
                raise ValueError("event chain continuity mismatch")
            if row["runId"] != manifest["runId"] or row["schemaVersion"] != SCHEMA:
                raise ValueError("event scope mismatch")
            if sha256(canonical(row)) != claimed:
                raise ValueError("record hash mismatch")
            if "rawBase64" in row:
                body = base64.b64decode(row["rawBase64"], validate=True)
                if sha256(body) != row["bodySha256"] or len(body) != row["rawBytes"]:
                    raise ValueError("raw body hash mismatch")
            if row["economicSignalQualified"] is not False:
                raise ValueError("collector cannot qualify an economic signal")
            prior = claimed
    if (sequence, size, prior) != (manifest["sequence"], manifest["eventBytes"], manifest["lastRecordSha256"]):
        raise ValueError("manifest terminal state mismatch")
    if manifest.get("eventsSha256") != digest.hexdigest():
        raise ValueError("events file hash missing or mismatched; run incomplete")
    return {"verifiedRecords": sequence, "verifiedBytes": size, "captureStatus": manifest["status"],
            "marketContinuityVerified": False, "economicSignalsQualified": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    discover = commands.add_parser("discover")
    discover.add_argument("--venue", choices=("polymarket", "limitless"), required=True)
    discover.add_argument("--output", required=True, help="new directory for bounded raw GET evidence")
    capture = commands.add_parser("capture")
    capture.add_argument("--config", required=True)
    capture.add_argument("--output", required=True, help="new directory, never overwrite a run")
    capture.add_argument("--duration-seconds", type=float, required=True)
    capture.add_argument("--max-bytes", type=int, default=100_000_000)
    verify = commands.add_parser("verify")
    verify.add_argument("directory")
    args = parser.parse_args(argv)
    if args.command == "verify":
        print(json.dumps(verify_run(args.directory), indent=2))
        return 0
    if args.command == "discover":
        result = fetch_public(f"{args.venue}-discovery")
        body = result.pop("body")
        directory = Path(args.output)
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "response.bin").write_bytes(body)
        result.update(bodySha256=sha256(body), bodyBytes=len(body), capability="public_discovery_only",
                      collectorSha256=sha256(Path(__file__).read_bytes()))
        (directory / "evidence.json").write_bytes(canonical(result) + b"\n")
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == 200 and not result["error"] else 2
    finite_number(args.duration_seconds, "duration-seconds", 1, 86400)
    finite_number(args.max_bytes, "max-bytes", 1000, 1_000_000_000)
    config = validate_config(json.loads(Path(args.config).read_text()))
    recorder = Recorder(args.output, config, args.max_bytes)
    status, error = "completed", None
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    def stop_on_sigterm(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, stop_on_sigterm)
    try:
        asyncio.run(Collector(config, recorder, args.duration_seconds).run())
    except ByteLimit:
        status = "stopped_byte_limit"
    except KeyboardInterrupt:
        status = "stopped_operator"
    except Exception as exc:
        status, error = "failed", f"{type(exc).__name__}: {str(exc)[:300]}"
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        try:
            ws_version = importlib.metadata.version("websockets")
        except importlib.metadata.PackageNotFoundError:
            ws_version = None
        recorder.close(status, error=error, durationLimitSeconds=args.duration_seconds,
                       websocketsVersion=ws_version)
    print(json.dumps(verify_run(args.output), indent=2))
    return 2 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
