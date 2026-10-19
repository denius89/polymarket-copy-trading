"""Bounded recorder safety/lineage checks; no venue credentials or external calls."""
import asyncio
import base64
import gzip
from copy import deepcopy
from http.client import HTTPMessage
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request
from urllib.parse import parse_qs, urlsplit

MODULE = Path(__file__).resolve().parents[1] / "collector.py"
spec = importlib.util.spec_from_file_location("collector", MODULE)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
ADDRESS = "0x" + "a" * 40
ASSET = {"assetId": "123", "conditionId": "0x" + "b" * 64}
CONFIG = {"schemaVersion": "forward-collector-config-v1", "assets": [ASSET],
          "leaders": [{"address": ADDRESS}], "limitless": [], "websocket": False}


class CollectorTests(unittest.TestCase):
    def config(self):
        return c.validate_config(deepcopy(CONFIG))

    def test_config_rejects_secrets_unknown_urls_and_duplicate_scopes(self):
        for key, value in (("apiKey", "secret"), ("baseUrl", "https://example.org")):
            with self.assertRaises(ValueError):
                c.validate_config({**CONFIG, key: value})
        with self.assertRaises(ValueError):
            c.validate_config({**CONFIG, "leaders": [{"address": ADDRESS}, {"address": ADDRESS.upper().replace("0X", "0x")}]})

    def test_config_rejects_nan_bool_and_unbounded_rate(self):
        for value in (float("nan"), float("inf"), True, 0):
            with self.assertRaises(ValueError):
                c.validate_config({**CONFIG, "pollIntervalSeconds": value})
        with self.assertRaises(ValueError):
            c.validate_config({**CONFIG, "activityPages": 1000})

    def test_endpoint_uses_v2_filters_and_opaque_cursor_without_offset(self):
        url = c.endpoint_url("polymarket-activity", {"address": ADDRESS}, start=10, end=20, cursor="abc+/=")
        parsed, query = urlsplit(url), parse_qs(urlsplit(url).query)
        self.assertEqual(parsed.netloc, "data-api.polymarket.com")
        self.assertEqual(parsed.path, "/v2/activity")
        self.assertEqual(query["exclude_deposits_withdrawals"], ["false"])
        self.assertEqual(query["cursor"], ["abc+/="])
        self.assertNotIn("offset", query)

    def test_positions_has_no_dust_floor_or_archived_default(self):
        url = c.endpoint_url("polymarket-positions", {"address": ADDRESS})
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["filter_amount"], ["0"])
        self.assertEqual(query["include_archived"], ["true"])
        self.assertEqual(query["status"], ["OPEN"])

    def test_endpoint_allowlist_rejects_private_arbitrary_and_injection(self):
        for endpoint in ("order", "polymarket-order", "https://example.org"):
            with self.assertRaises(ValueError):
                c.endpoint_url(endpoint)
        for slug in ("../order", "slug?secret=x", "https://example.org"):
            with self.assertRaises(ValueError):
                c.endpoint_url("limitless-book", {"slug": slug})
        with self.assertRaises(ValueError):
            c.endpoint_url("polymarket-book", {"assetId": "123&secret=x"})
        with self.assertRaises(ValueError):
            c.endpoint_url("polymarket-activity", {"address": ADDRESS}, start=1, end=2, offset=0)

    def test_v2_null_is_unavailable_and_short_page_with_cursor_continues(self):
        for document in ({"data": None}, [], {"data": [], "pagination": {"has_more": False}},
                         {"data": [], "pagination": {"has_more": True, "next_cursor": None}}):
            with self.assertRaises(ValueError):
                c.v2_page(document)
        rows, cursor = c.v2_page({"data": [], "pagination": {"has_more": True, "next_cursor": "opaque"}})
        self.assertEqual((rows, cursor), ([], "opaque"))

    def test_no_redirect_to_another_host(self):
        with self.assertRaises(HTTPError):
            c.NoRedirect().redirect_request(Request("https://clob.polymarket.com/book"), None, 302, "found", {}, "https://attacker.invalid/")

    def test_lineage_exact_bytes_chain_and_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            recorder = c.Recorder(path, self.config(), 10000)
            raw = b'{"price":0.12345678901234567890123,"timestamp":"1234"}'
            recorder.append("polymarket", "market_message", ASSET, raw=raw)
            recorder.append("polymarket", "coverage_gap", ASSET, reason="test disconnect")
            recorder.close("completed")
            verified = c.verify_run(path)
            self.assertEqual(verified["verifiedRecords"], 2)
            row = json.loads((path / "events.jsonl").read_text().splitlines()[0])
            self.assertEqual(base64.b64decode(row["rawBase64"]), raw)
            self.assertFalse(row["economicSignalQualified"])
            with (path / "events.jsonl").open("ab") as stream:
                stream.write(b"{}\n")
            with self.assertRaises((ValueError, KeyError)):
                c.verify_run(path)

    def test_existing_run_never_overwritten_and_byte_cap_hard(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            recorder = c.Recorder(path, self.config(), 1000)
            with self.assertRaises(c.ByteLimit):
                recorder.append("polymarket", "market_message", ASSET, raw=b"x" * 1000)
            self.assertEqual(recorder.bytes, 0)
            recorder.close("stopped_byte_limit")
            with self.assertRaises(FileExistsError):
                c.Recorder(path, self.config(), 1000)
            self.assertEqual(c.verify_run(path)["verifiedRecords"], 0)

    def test_lossless_gzip_archive_equivalence_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            recorder = c.Recorder(path, self.config(), 100000)
            recorder.append("polymarket", "market_message", ASSET, raw=b'{"price":"0.5"}')
            recorder.close("completed")
            before = c.verify_run(path)
            raw = (path / "events.jsonl").read_bytes()
            compressed = gzip.compress(raw, mtime=0)
            (path / "events.jsonl.gz").write_bytes(compressed)
            (path / "archive.json").write_text(json.dumps({"schemaVersion": "forward-event-archive-v1",
                "file": "events.jsonl.gz", "compressedSha256": c.sha256(compressed),
                "uncompressedSha256": c.sha256(raw)}))
            (path / "events.jsonl").unlink()
            self.assertEqual(c.verify_run(path), before)
            (path / "events.jsonl.gz").write_bytes(compressed + b"tamper")
            with self.assertRaisesRegex(ValueError, "compressed file hash"):
                c.verify_run(path)

    def test_source_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            recorder = c.Recorder(path, self.config(), 100000)
            recorder.close("completed")
            (path / "collector-source.py.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "frozen source hash"):
                c.verify_run(path)

    def test_http_method_and_sensitive_headers_not_saved(self):
        class Response:
            code = 200
            headers = {"Set-Cookie": "secret", "Authorization": "secret", "Date": "test-date"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return b"{}"
        class Opener:
            def open(self, request, timeout):
                self_test.assertEqual(request.get_method(), "GET")
                self_test.assertFalse(request.has_header("Authorization"))
                return Response()
        self_test = self
        with patch.object(c, "build_opener", return_value=Opener()):
            result = c.fetch_public("polymarket-book", ASSET)
        self.assertEqual(result["headers"], {"date": "test-date"})
        self.assertEqual(result["body"], b"{}")

    def test_failed_http_keeps_unknown_not_empty_page(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder = c.Recorder(Path(temp) / "run", self.config(), 100000)
            collector = c.Collector(self.config(), recorder, 2)
            result = {"endpoint": "polymarket-activity", "url": "https://data-api.polymarket.com/v2/activity",
                      "method": "GET", "startedAt": c.utc_now(), "startedMonotonicNs": 1,
                      "observedAt": c.utc_now(), "observedMonotonicNs": 2, "status": 429,
                      "headers": {"retry-after": "1"}, "error": "HTTP_429", "truncated": False, "body": b'{"error":"rate_limit"}'}
            with patch.object(c, "fetch_public", return_value=result):
                output = asyncio.run(collector.request("polymarket-activity", {"address": ADDRESS}, start=1, end=2))
            self.assertIsNone(output)
            recorder.close("completed")
            events = [json.loads(x) for x in (recorder.directory / "events.jsonl").read_text().splitlines()]
            self.assertEqual([e["kind"] for e in events], ["http_response", "coverage_gap"])
            self.assertEqual(events[0]["request"]["status"], 429)

    def test_long_retry_after_is_respected_without_early_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder = c.Recorder(Path(temp) / "run", self.config(), 100000)
            collector = c.Collector(self.config(), recorder, 2)
            result = {"endpoint": "polymarket-book", "url": "https://clob.polymarket.com/book?token_id=123",
                      "method": "GET", "startedAt": c.utc_now(), "startedMonotonicNs": 1,
                      "observedAt": c.utc_now(), "observedMonotonicNs": 2, "status": 429,
                      "headers": {"retry-after": "3600"}, "error": "HTTP_429", "truncated": False, "body": b"{}"}
            with patch.object(c, "fetch_public", return_value=result) as fetch:
                asyncio.run(collector.request("polymarket-book", ASSET))
                asyncio.run(collector.request("polymarket-book", ASSET))
                self.assertEqual(fetch.call_count, 1)
            self.assertTrue(next(iter(collector.http_backoff.values())) > c.time.monotonic() + 3500)
            recorder.close("completed")

    def test_limitless_events_bounded_public_route(self):
        url = c.endpoint_url("limitless-events", {"slug": "verified-market"})
        self.assertEqual(url, "https://api.limitless.exchange/markets/verified-market/events?page=1&limit=20")
        with self.assertRaises(ValueError):
            c.endpoint_url("limitless-events", {"slug": "verified-market"}, limit=1000)


if __name__ == "__main__":
    unittest.main()
