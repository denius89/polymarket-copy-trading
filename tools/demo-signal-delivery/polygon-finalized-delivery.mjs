import { performance } from 'node:perf_hooks';

const chainId = 137;
const signalLifetimeMs = 30_000;
const hashPattern = /^0x[0-9a-f]{64}$/;
const walletPattern = /^0x[0-9a-f]{40}$/;
const uintPattern = /^(0|[1-9][0-9]{0,14})$/;

// Takes the same normalized, receipt-checked logs as the personal collector.
// The caller verifies Polygon finality and range coverage before publication.
export async function publishFinalizedPolygonBlock(db, wallet, header, logs, receivedAt) {
  if (!walletPattern.test(wallet) || !uintPattern.test(header.number)
      || !uintPattern.test(header.timestampSeconds)
      || !hashPattern.test(header.hash) || !hashPattern.test(header.parentHash)) {
    throw new Error('Invalid finalized Polygon block');
  }
  const height = Number(header.number);
  const occurredAt = new Date(Number(header.timestampSeconds) * 1000);
  if (!Number.isFinite(receivedAt.getTime()) || !Number.isFinite(occurredAt.getTime())
      || occurredAt.getTime() > receivedAt.getTime() + 5000) {
    throw new Error('Polygon source clock skew');
  }
  const expiresAt = new Date(occurredAt.getTime() + signalLifetimeMs);
  const events = [];
  for (const log of logs) {
    if (log.blockNumber !== header.number || log.blockHash !== header.hash
        || log.owner !== wallet || !hashPattern.test(log.transactionHash)
        || !uintPattern.test(log.logIndex) || !['BUY', 'SELL'].includes(log.side)) {
      throw new Error('Polygon execution does not match the finalized block or wallet');
    }
    if (log.side === 'BUY') {
      events.push({
        logIndex: Number(log.logIndex),
        executionKey: `${chainId}:${log.transactionHash}:${log.logIndex}`,
        occurredAt: occurredAt.toISOString(),
        firstReceivedAt: receivedAt.toISOString(),
        expiresAt: expiresAt.toISOString(),
        payload: { kind: 'polygon-finalized-buy', header, log },
      });
    }
  }
  events.sort((one, other) => one.logIndex - other.logIndex);
  const startedAt = performance.now();
  const { rows: [{ saved }] } = await db.query(
    "SELECT demo_delivery.commit_source_block('polymarket',$1,$2,$3,$4,$5) AS saved",
    [wallet, height, header.hash, header.parentHash, JSON.stringify(events)],
  );
  return { ...saved, blockCommitMs: performance.now() - startedAt };
}
