# Forward observation recorder · 18 October 2026

`collector.py` is a bounded, public **observation** recorder for the forward shadow experiment. It has no account connection, signing code, order endpoint, execution adapter or score publisher. The recorder does not create fills or a monetary path from a public book.

## What is collected

| Layer | Capture | Interpretation |
| --- | --- | --- |
| Polymarket market feed | Raw public market WebSocket messages, subscription, application PING/PONG, connection boundaries and failures | Arrival evidence at this recorder; public trades do not identify a selected leader by themselves. No exchange sequence guarantee. |
| Polymarket books | GET `/book?token_id=…` | Independent snapshot at completion of that HTTP response. It does not replace missing WebSocket intervals or prove our execution. |
| Polymarket economics | GET `/fee-rate`, `/tick-size`, `/markets/{conditionId}` | Raw current responses, including errors. A returned base rate alone is not a proven all-in copier fee bound. |
| Selected Polymarket wallets | GET `/v2/positions`, GET `/v2/activity`, consistent window and cursor filters | Public observations, not a reconstructed complete wallet ledger or automatically qualified economic signals. |
| Limitless selected markets | GET `/markets/{slug}`, `/markets/{slug}/orderbook`, `/markets/{slug}/events?page=1&limit=20` | Market-only instrumentation with a bounded finalized-trade page. This version does not collect its public wallet history or WebSocket feed. |

Discovery is a separate bounded GET with a saved response, not an automatic cohort selection or evidence of representative coverage. Polymarket and Limitless discovery have separate status: an earlier 403 is not assumed to persist. Root bootstrap and live run evidence establish what actually worked for this run.

The first configuration is a **limited-asset instrumentation pilot**, not the full copier panel. Assets are explicitly enrolled before capture, maximum eight per venue; a selected leader can trade other assets. Such activity is retained but missing books for those assets cannot be manufactured afterwards. No dynamic enrollment, market rotation or retrospective fill is implied.

## Public API contract checked today

The current [Polymarket migration guide](https://docs.polymarket.com/migrate/data-api-v1-to-v2) says new readers should use v2 and announces retirement of v1 on 24 October 2026. The collector therefore uses the [v2 response/cursor contract](https://docs.polymarket.com/api-reference/data-api/overview), snake-case rows, and stable filters across a fixed-window cursor walk. It never applies v1 offset arithmetic to v2.

For [wallet activity](https://docs.polymarket.com/api-reference/feeds/list-account-activity), `exclude_deposits_withdrawals=false` is explicit. No activity type filter is supplied: the documented default set excludes opt-in `TIP`, so that layer remains incomplete for money reconciliation. The recorder does not silently treat absent transfer types as zero. Every page retains its actual body; pagination reaching its end means only that this API walk ended, not that the account ledger is complete. Page budget exhaustion, repeated cursors, unavailable data and malformed envelopes are recorded as gaps/invalid evidence. Short or empty pages with `next_cursor` continue.

For [positions](https://docs.polymarket.com/api-reference/wallet/list-positions-for-a-user-or-market), the baseline requests `status=OPEN`, `filter_type=TOKENS`, `filter_amount=0`, `include_archived=true`. It is one bounded page; a next cursor marks it incomplete. OPEN includes still-held resolved positions, while inactive markets can still be excluded by the venue. The request is not a statement of opening cash or all custody balances. A position snapshot followed by activity cannot automatically establish inventory immediately before a leader's sale.

The public [raw market WebSocket contract](https://docs.polymarket.com/market-data/realtime-data) specifies the asset subscription and application heartbeat. [Official legacy CLOB endpoint constants](https://github.com/Polymarket/py-clob-client/blob/main/py_clob_client/endpoints.py) support the public REST paths used here; their actual availability and returned schema are recorded per run. The contemporary [book reference](https://docs.polymarket.com/api-reference/market-data/get-order-book) is an additional contract locator. For Limitless, [GET orderbook documentation](https://docs.limitless.exchange/api-reference/trading/orderbook) supplies the selected-market path. Documentation is separated from observed availability in the saved responses.

Limitless [market events](https://docs.limitless.exchange/api-reference/trading/market-events) are documented as finalized CLOB trades ordered newest first, with taker-side aggregates and optional public profile attribution. The recorder fetches only page 1, limit 20. Cached responses and more than 20 new trades between polls can leave holes; neither an empty page nor a username establishes complete wallet inventory. Cache headers are retained. No profile-to-wallet association, maker activity, economic deduplication or precise event identity is guessed from these rows.

## Configuration and bounded use

Python 3.11+, with `websockets` 15.x for the public stream. Without that dependency the recorder saves an explicit WebSocket gap and continues REST; it does not claim stream coverage. No automatic package installation occurs. Discovery/REST/verification use Python's standard library.

```json
{
  "schemaVersion": "forward-collector-config-v1",
  "assets": [{"assetId": "123", "conditionId": "0x0000000000000000000000000000000000000000000000000000000000000000"}],
  "leaders": [{"address": "0x0000000000000000000000000000000000000000"}],
  "limitless": [{"slug": "replace-with-a-verified-live-market-slug"}],
  "pollIntervalSeconds": 15,
  "metadataIntervalSeconds": 60,
  "activityOverlapSeconds": 60,
  "activityPages": 2,
  "websocket": true
}
```

This schema example is not a valid research cohort. Use root's saved, verified live bootstrap configuration. Maximum eight assets, eight leaders and eight Limitless slugs; poll interval at least two seconds; activity page budget one to five. Unknown config fields, including URLs, secrets or signing options, are rejected.

From this package directory:

```sh
python3 collector.py discover --venue polymarket --output runs/discovery-unique
python3 collector.py capture --config pilot-config.json --output runs/capture-unique --duration-seconds 60 --max-bytes 10000000
python3 collector.py verify runs/capture-unique
python3 -m unittest discover -s tests -p 'test_collector.py' -v
```

Each output directory must be new. A capture requires an explicit duration, between one second and one day, plus a hard event-file byte cap (maximum one billion bytes). Total directory size also includes the small configuration, frozen source and manifest. The experiment supervisor supplies its overall deadline, aggregate disk budget and stop mechanism separately; this CLI is not an installed service or future scheduling promise. It sends no account traffic. Ctrl-C or SIGTERM closes the capture with `stopped_operator`; SIGKILL, machine sleep/power loss or disk failure may leave an incomplete run. Missing terminal hashes must fail verification rather than be silently relabeled completed. A blocking HTTP operation can take up to its remaining bounded timeout to finish during stop.

GET requests are built only from fixed public hosts and paths. Redirects are refused; the code cannot accept an arbitrary URL, change HTTP method or send authentication headers. Cookie/auth response headers are not retained. A valid positive `Retry-After` is honored even when it exceeds the capture window; there is no shorter client ceiling that causes an early retry. Invalid headers use a bounded fallback delay. A later response never erases the earlier gap.

## Evidence and timing

`events.jsonl` preserves raw bytes as base64 without float conversion, plus their SHA-256. Each envelope has the run ID, local record sequence, UTC `observedAt`, local monotonic nanoseconds, transport, venue and **requested** scope. Raw venue payload identity still has to be verified by downstream qualification; requested asset IDs do not certify a returned book's identity. HTTP response clocks represent completion of body receipt; request-start clocks and status remain in `request`. WebSocket clocks are taken immediately after the receive operation completes. Source timestamps stay in raw bytes. Neither source time nor block time replaces receipt time.

The sequence orders local persistence. It is not an exchange sequence, a leader's economic event sequence or a deduplication ID. Scheduling can persist a completed HTTP response after an intervening WebSocket observation; use the recorded receive clocks rather than inferring chronology from line order alone. Clock synchronization is explicitly `not_externally_verified`; monotonic clocks are meaningful within this process, not across different machines or reboots.

`prevRecordSha256` and `recordSha256` form an append-only content chain. `manifest.json` records status, config hash, the **initial frozen collector source** hash, terminal event-file hash, counts and byte limits. `collector-source.py.txt` preserves those exact source bytes even if the working copy is edited later. Initial/running manifests do not contain a terminal event-file hash. `verify` checks configuration, source, raw bodies, record chain, run scope and final counts/hash; it explicitly does not certify financial data quality or market continuity.

Capture reconnection/failure markers invalidate any downstream local reconstructed book. A new snapshot can begin a new eligibility interval; it cannot repair the missing interval. Quiet-market heartbeat success also cannot prove that no market messages were dropped. This recorder keeps raw deltas rather than inventing an authoritative rebuilt book. Normal completion describes the bounded recorder, not all endpoints succeeding.

After capture closes, the supervisor may losslessly gzip `events.jsonl` to save disk space. Original manifest and record hashes remain hashes of the uncompressed bytes. The verifier accepts `events.jsonl.gz` when the raw file is absent, requires `archive.json` with `schemaVersion=forward-event-archive-v1`, fixed `file=events.jsonl.gz`, `compressedSha256` and `uncompressedSha256`, and checks both the compressed container and original byte stream. This conversion neither repairs an incomplete run nor changes its status. The capture writer itself remains append-only and does not compress a file that is still being written.

All records have `economicSignalQualified=false`, manifests have zero qualified economic signals, zero actual orders/fills and `historicalReplayPnl=null`. These are instrumentation facts, not a synthetic zero-return observation. The independent qualification and comparison protocol must decide if a separate conditional ledger is usable. No virtual wealth, fee schedule, scalar score or H30 outcome is produced here.
