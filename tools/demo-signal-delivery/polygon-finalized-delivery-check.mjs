import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { publishFinalizedPolygonBlock } from './polygon-finalized-delivery.mjs';

const [pglite, capture] = process.argv.slice(2);
assert.ok(pglite && capture, 'Pass a local PGlite package and a normalized Polygon capture');
const { PGlite } = await import(pathToFileURL(resolve(pglite, 'dist/index.js')));
const rows = JSON.parse(await readFile(capture, 'utf8'));
const blocks = Map.groupBy(rows, row => row.header.number);
assert.equal(blocks.size, 2);
assert.ok([...blocks.values()].every(pair => pair.length === 2));
assert.deepEqual([...blocks.values()].map(pair => new Set(pair.map(row => row.log.transactionHash)).size).sort(), [1, 2]);

const path = await mkdtemp(join(tmpdir(), 'polygon-delivery-'));
let db;
try {
  for (const [height, pair] of blocks) {
    const dataDir = join(path, height);
    db = new PGlite({ dataDir });
    for (const sql of ['schema.sql', 'source-checkpoints.sql']) {
      await db.exec(await readFile(new URL(sql, import.meta.url), 'utf8'));
    }
    const wallet = pair[0].log.owner;
    const session = randomUUID();
    const [first, second] = pair.map(row => row.log);
    const header = { ...pair[0].header, timestampSeconds: String(Math.floor(Date.now() / 1000)) };
    // Shift the capture's clock for delivery only. This exercises no quote or financial write.
    await db.query("INSERT INTO demo_delivery.traders VALUES ('polymarket',$1)", [wallet]);
    await db.query("INSERT INTO demo_delivery.source_cursors VALUES ('polymarket',$1,$2,$3)",
      [wallet, Number(height) - 1, header.parentHash]);
    await db.query("INSERT INTO demo_delivery.subscriptions VALUES ($1,'polymarket',$2,to_timestamp($3::bigint - 1))",
      [session, wallet, header.timestampSeconds]);
    const saved = await publishFinalizedPolygonBlock(db, wallet, header, [second, first], new Date());
    assert.equal(saved.enqueued, 2);
    assert.equal(saved.height, Number(height));
    await db.close();
    db = new PGlite({ dataDir });
    const replay = await publishFinalizedPolygonBlock(db, wallet, header, [first, second], new Date());
    assert.equal(replay.replayed, true);
    assert.equal(replay.enqueued, 0);
    const claim = async () => (await db.query("SELECT * FROM demo_delivery.claim(10, interval '10 seconds')")).rows;
    const [head, ...extra] = await claim();
    assert.equal(extra.length, 0);
    assert.deepEqual(head.payload.log, first);
    assert.deepEqual(await claim(), []);
    // A durable nonfinancial outcome and the acknowledgement commit together.
    await db.transaction(async tx => {
      await tx.exec('CREATE TABLE observed_outcomes (id bigint PRIMARY KEY, reason text NOT NULL)');
      await tx.query("INSERT INTO observed_outcomes VALUES ($1,'book_unavailable')", [head.signal_id]);
      const { rows: [ack] } = await tx.query('SELECT demo_delivery.acknowledge($1,$2,$3) AS ok',
        [head.signal_id, session, head.lease_token]);
      assert.equal(ack.ok, true);
    });
    const [next] = await claim();
    assert.deepEqual(next.payload.log, second);
    assert.notEqual(next.execution_key, head.execution_key);
    console.log(JSON.stringify({ block: height, jobs: saved.enqueued, replayJobs: replay.enqueued,
      secondClaimedAfterFirstSkipped: true, blockCommitMs: Math.round(saved.blockCommitMs) }));
    await db.close();
    db = undefined;
  }
} finally {
  await db?.close();
  await rm(path, { recursive: true, force: true });
}
