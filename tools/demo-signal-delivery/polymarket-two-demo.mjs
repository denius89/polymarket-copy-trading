import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash, randomBytes, randomUUID } from 'node:crypto';
import { appendFile, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import pg from 'pg';
import { publishFinalizedPolygonBlock } from './polygon-finalized-delivery.mjs';

const runFile = promisify(execFile);
const [backend, directory, ...extra] = process.argv.slice(2);
assert.ok(extra.length === 0 && directory && ['--postgres-bin', '--pglite'].includes(backend),
    'Pass --postgres-bin or --pglite followed by its local package directory');
const fixture = new URL('../../local-data/polymarket-active-demo-20261122/isolated-replay/kit/polygon-live-buy-compose-20261113/', import.meta.url);
const { baseline, loadLive, loadSource } = await import(new URL('fixture/baseline.mjs', fixture));
const retained = JSON.parse(await readFile(new URL('./polymarket-taker-replay.json', import.meta.url), 'utf8'));
const freshSource = process.env.CCT_DEMO_FRESH_POLYMARKET_SOURCE;
const freshWallet = process.env.CCT_DEMO_FRESH_POLYMARKET_WALLET;
const retainedState = process.env.CCT_DEMO_PM_STATE_DIRECTORY;
const appStart = process.env.CCT_DEMO_REPLAY_APP_STARTS === '1';
const pairSource = process.env.CCT_DEMO_POLYGON_PAIR;
assert.ok(!pairSource || (!freshSource && !appStart), 'The archived pair uses the isolated replay profile');
const pair = pairSource ? JSON.parse(await readFile(pairSource, 'utf8')).slice(0, 2) : null;
if (pair) {
    assert.equal(pair.length, 2);
    assert.deepEqual(pair[0].header, pair[1].header);
    assert.ok(Number(pair[0].log.logIndex) < Number(pair[1].log.logIndex));
    assert.equal(pair[0].log.owner, pair[1].log.owner);
}
assert.ok(!appStart || backend === '--postgres-bin', 'App starts require native PostgreSQL');
assert.ok((!freshSource && !freshWallet) || (freshSource && freshWallet && backend === '--postgres-bin'),
    'Fresh quotes require a chosen public wallet and isolated native PostgreSQL');
assert.ok(!retainedState || backend === '--postgres-bin', 'Retained demo state requires isolated native PostgreSQL');
let chosen = retained;
const previousWallet = '0x0d6a1ada6d7ff785ab4b7263d9ce8e2baa85aa98';
const wallet = pair?.[0].log.owner ?? freshWallet ?? retained.fixtureWallet;
assert.match(wallet, /^0x[0-9a-f]{40}$/);
let publicTx, logIndex;
const q = n => ({ n: String(n), d: '1' });
const hash = c => '0x' + c.repeat(64);
const evidence = c => c.repeat(64);
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
process.env.USER_KEY = randomBytes(32).toString('hex');
process.env.FIXTURE_TZ = process.versions.tz;
const scratch = await mkdtemp(join(tmpdir(), 'cct-pm-two-'));
let db;
let close;
let stopCluster;
let restartCluster;
let phase = 'isolated database';

async function database() {
    if (backend === '--pglite') {
        const {PGlite} = await import(pathToFileURL(resolve(directory, 'dist/index.js')));
        const {pgcrypto} = await import(pathToFileURL(resolve(directory, 'dist/contrib/pgcrypto.js')));
        const local = new PGlite({database: 'shadow_v00', extensions: {pgcrypto}});
        close = () => local.close();
        return local;
    }
    const state = retainedState ? resolve(retainedState) : scratch;
    if (retainedState) await mkdir(state,{mode:0o700});
    const data = join(state, 'db');
    const command = (name, args) => runFile(resolve(directory, name), args);
    await command('initdb', ['-D', data, '-U', 'postgres', '-A', 'trust', '--locale=C', '--encoding=UTF8']);
    await appendFile(join(data, 'postgresql.conf'), `\nlisten_addresses = ''\nunix_socket_directories = '${scratch}'\nunix_socket_permissions = 0700\n`);
    const startCluster = () => command('pg_ctl', ['start', '-D', data, '-l', join(scratch, 'postgres.log'), '-w']);
    await startCluster();
    stopCluster = () => command('pg_ctl', ['stop', '-D', data, '-m', 'fast', '-w']);
    const admin = new pg.Client({host: scratch, database: 'postgres', user: 'postgres'});
    await admin.connect();
    try { await admin.query('CREATE DATABASE shadow_v00'); } finally { await admin.end(); }
    const connect = async () => {
        const client = new pg.Client({host: scratch, database: 'shadow_v00', user: 'postgres'});
        await client.connect();
        close = () => client.end();
        return {query: (sql, values) => client.query(sql, values), exec: sql => client.query(sql)};
    };
    restartCluster = async () => {
        await close();
        close = undefined;
        const stop = stopCluster;
        await stop();
        stopCluster = undefined;
        await startCluster();
        stopCluster = stop;
        return connect();
    };
    const connection = await connect();
    await connection.exec('CREATE EXTENSION pgcrypto');
    return connection;
}

async function tx(role, action) {
    if (role) assert.match(role, /^polygon_live_writer_[a-f0-9]{32}$/);
    await db.exec('BEGIN ISOLATION LEVEL SERIALIZABLE');
    try {
        if (role) await db.exec('SET LOCAL SESSION AUTHORIZATION ' + role);
        const result = await action();
        await db.exec('COMMIT');
        return result;
    } catch (error) {
        await db.exec('ROLLBACK');
        throw error;
    } finally {
        if (role) await db.exec('SET SESSION AUTHORIZATION postgres');
    }
}

async function rpc(name, packet) {
    const {rows: [{reply}]} = await db.query(`SELECT polygon.${name}($1::jsonb) reply`, [packet]);
    return reply;
}

async function must(name, packet) {
    const reply = await rpc(name, packet);
    assert.equal(reply.http, 200, JSON.stringify(reply));
    return reply;
}

function operation(user, run, fields) {
    return {session_id: user.sid, request: {sessionId: user.sid, operationId: randomUUID(), runId: run,
        evidenceSha256: evidence('f'), ...fields}};
}

async function setupBoth() {
    const users = await baseline(db);
    const exec = db.exec.bind(db);
    const query = db.query.bind(db);
    let resumeSetup = false;
    try {
        db.exec = sql => {
            if (sql.startsWith('CREATE TABLE polygon_live_activity.resume_patch(')) {
                const singleton = 'singleton boolean PRIMARY KEY CHECK(singleton),session_id uuid NOT NULL REFERENCES';
                assert.equal(sql.split(singleton).length, 2);
                sql = sql.replace(singleton, 'singleton boolean NOT NULL CHECK(singleton),session_id uuid PRIMARY KEY REFERENCES');
                resumeSetup = true;
            }
            return exec(sql.replaceAll(previousWallet, wallet));
        };
        db.query = (sql, values) => {
            if (sql.startsWith('SELECT polygon.c04_save(')) values[0].request.rawFixedAmount = 'MjA=';
            if (sql.startsWith('INSERT INTO live_install_input VALUES(')) values[1].displayName = 'Public quote replay';
            return query(sql.replaceAll(previousWallet, wallet), values);
        };
        const {run} = await loadLive(db, users);
        assert.equal(resumeSetup, true);
        return {users, run};
    } finally {
        db.exec = exec;
        db.query = query;
    }
}

async function admit(user, run, kind, request) {
    const id = randomUUID();
    await db.query(`INSERT INTO polygon_buy.admissions VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,
      $10,'local-clock-fixture',$10,$10,clock_timestamp()-interval '1 second',
      COALESCE($11,clock_timestamp()+interval '2 minutes'))`,
      [id,user.sid,run,kind,request,publicTx,logIndex,chosen.token,chosen.condition,
       chosen.timing ? 'fresh-public-quote' : 'public-replay-fixture',chosen.timing?.expiresAt ?? null]);
    return id;
}

async function prepareQueue(users) {
    if (appStart) {
        const {prepareReplayQueue,replayTraderKey} = await import('./replay-queue.mjs');
        for (const user of users) {
            await prepareReplayQueue(db,{venue:'polymarket',sessionId:user.sid,writer:user.writer,appStart});
            assert.equal(await replayTraderKey(db,'polymarket',user.sid,appStart),wallet);
        }
        return;
    }
    await db.exec(await readFile(new URL('./schema.sql', import.meta.url), 'utf8'));
    if (pair) {
        await db.exec(`CREATE TABLE demo_delivery.pilot_marker (kind text PRIMARY KEY);
            INSERT INTO demo_delivery.pilot_marker VALUES ('isolated-public-market-pilot-v1')`);
        await db.exec(await readFile(new URL('./polygon-result-ack.sql', import.meta.url), 'utf8'));
    }
    await db.query('INSERT INTO demo_delivery.traders VALUES ($1,$2)', ['polymarket', wallet]);
    for (const user of users) {
        await db.query('SELECT demo_delivery.subscribe($1,$2,$3)', [user.sid,'polymarket',wallet]);
        await db.query('INSERT INTO demo_delivery.session_writers VALUES ($1,$2::regrole::oid)', [user.sid,user.writer]);
        const ack = pair ? 'acknowledge_polygon_result(bigint,uuid,uuid)' : 'acknowledge_bound(bigint,uuid,uuid,text,text)';
        await db.exec(`GRANT USAGE ON SCHEMA demo_delivery TO ${user.writer};
            GRANT EXECUTE ON FUNCTION demo_delivery.${ack} TO ${user.writer}`);
    }
}

async function publish(users) {
    const {rows: [{now}]} = await db.query('SELECT clock_timestamp()::text now');
    const timing = chosen.timing ?? {occurredAt:now,receivedAt:now,expiresAt:new Date(Date.parse(now)+30_000)};
    const send = () => db.query(`SELECT * FROM demo_delivery.publish('polymarket',$1,$2,$3,$4,$5,$6)`,
      [wallet,chosen.publicExecutionId,timing.occurredAt,timing.receivedAt,timing.expiresAt,
        {marketId: chosen.condition, outcomeId: chosen.token, side: 'BUY'}]);
    const {rows: [initial]} = await send();
    assert.equal(Number(initial.enqueued), 2);
    const {rows: [repeat]} = await send();
    assert.equal(repeat.signal_id, initial.signal_id);
    assert.equal(Number(repeat.enqueued), 0);
    const {rows: jobs} = await db.query("SELECT * FROM demo_delivery.claim(2,interval '25 seconds')");
    assert.equal(jobs.length, 2);
    assert.deepEqual(new Set(jobs.map(job => job.session_id)), new Set(users.map(user => user.sid)));
    assert.ok(jobs.every(job => job.signal_id === initial.signal_id && job.execution_key === chosen.publicExecutionId));
    return jobs;
}

async function acknowledge(job) {
    const keys = [job.signal_id,job.session_id,job.lease_token];
    const {rows: [{accepted}]} = pair
        ? await db.query('SELECT demo_delivery.acknowledge_polygon_result($1,$2,$3) accepted', keys)
        : await db.query('SELECT demo_delivery.acknowledge_bound($1,$2,$3,$4,$5) accepted',
            [...keys,'polymarket',job.execution_key]);
    return accepted;
}

async function applyBuy(user, run, job, header) {
    const {rows: [{settings}]} = await db.query('SELECT current_settings_revision_id settings FROM polygon.paper_sessions WHERE id=$1', [user.sid]);
    const request = {commandId: randomUUID(), intentId: randomUUID(), observationId: randomUUID(),
        expectedVersion: '1', conditionId: chosen.condition, tokenId: chosen.token, sizingRevisionId: settings,
        admissionRevisionId: settings, evidenceRef: (chosen.timing ? 'public-quote:' : 'public-archive:') + chosen.publicExecutionId,
        desiredNotional: q(20), fullQuantity: chosen.quote.quantity, quantityStep: {n:'1',d:'1000000'},
        priceCap: chosen.fixturePriceCap, feeCashBound: chosen.quote.cashFee, delayMs: '0'};
    const admissionId = await admit(user, run, 'reserve', request);
    const binding = {tokenId:chosen.token, conditionId:chosen.condition, outcome:chosen.outcome,
        marketTitle:chosen.market, protocol:'v1', marketSha256:evidence('5')};
    const log = {transactionHash:publicTx, logIndex, blockNumber:header.number, blockHash:header.hash,
        orderHash:hash('d'), owner:wallet, counterparty:'0x'+'e'.repeat(40), side:'BUY', tokenId:chosen.token,
        makerAmountFilledRaw:'10000000', takerAmountFilledRaw:'20000000', feeRaw:'0', builder:hash('0'),
        metadata:hash('0'), rawLogSha256:evidence('1'), receiptSha256:evidence('2')};
    const logs = pair ? pair.map(item => item.log) : [log];
    const evaluations = [{transactionHash:publicTx,logIndex,evidence:{
        schemaVersion:'paper-buy-pending-v1',kind:'candidate',admissionId,binding,evidenceSha256:evidence('8')}}];
    if (pair) {
        const first = logs[0];
        evaluations.unshift({transactionHash:first.transactionHash,logIndex:first.logIndex,evidence:{
            schemaVersion:'paper-buy-evidence-v1',kind:'skip',reason:'book_unavailable',
            evidenceSha256:first.receiptSha256,binding:null}});
    }
    const envelope = {session_id:user.sid, request:{
        ingest:operation(user,run,{previous:user.checkpoint,baselineCanonicalHash:user.checkpoint.hash,
            finalized:header,headers:[header],observedAt:new Date().toISOString(),logs}).request,
        expectedSnapshotVersion:'1', evaluations,
    }};
    let purchaseJob = job;
    if (pair) {
        await tx(user.writer, async () => {
            assert.equal(await acknowledge(job), false, 'The queue cannot acknowledge a missing Activity decision');
            const ingest = await must('live_activity_ingest', envelope);
            assert.equal(ingest.result.accepted, '2');
            assert.equal(await acknowledge(job), true);
        });
        const skipped = await tx(null,() => must('buy_activity_read_v1',
            {auth:user.auth,session_id:user.sid,after_sequence:'0',limit:20}));
        assert.equal(skipped.items.find(item => item.decision.status === 'skipped')?.decision.detailCode, 'book_unavailable');
        const before = await tx(null,() => must('q04_session',{auth:user.auth,session_id:user.sid}));
        assert.deepEqual(before.session.financialSnapshot.free,q(200));
        assert.equal(before.session.financialSnapshot.positionCount,'0');
        const { rows: [claimed] } = await db.query("SELECT * FROM demo_delivery.claim(1,interval '25 seconds')");
        assert.equal(claimed.session_id,user.sid);
        assert.equal(claimed.execution_key,`137:${publicTx}:${logIndex}`);
        assert.equal(await tx(user.writer,() => acknowledge(claimed)),false,
            'A pending admission is not a purchase receipt');
        purchaseJob = claimed;
    }
    const settled = await tx(user.writer, async () => {
        if (!pair) {
            const ingest = await must('live_activity_ingest', envelope);
            assert.equal(ingest.result.accepted, '1');
        }
        await must('live_buy_reserve_v1', {session_id:user.sid,request,admission_id:admissionId});
        // Replay operator supplies the second scoped admission after the reserve's ledger timestamp.
        await db.exec('SET LOCAL SESSION AUTHORIZATION postgres');
        await db.exec('SELECT pg_sleep(0.002)');
        const {rows: [{utc}]} = await db.query('SELECT clock_timestamp()::text utc');
        const settle = {commandId:randomUUID(),intentId:request.intentId,expectedVersion:'2',
            evidenceRef:request.evidenceRef,confirmationId:randomUUID(),
            fills:[{fillId:randomUUID(),price:chosen.quote.price,quantityGross:chosen.quote.quantity,
                quantityFee:q(0),cashFee:chosen.quote.cashFee,executedAt:new Date(utc).toISOString()}]};
        const settleId = await admit(user,run,'settle',settle);
        await db.exec('SET LOCAL SESSION AUTHORIZATION ' + user.writer);
        const payload = {session_id:user.sid,request:settle,admission_id:settleId};
        const receipt = await must('live_buy_settle_v1',payload);
        assert.equal(await acknowledge(purchaseJob), true);
        return {payload, receipt};
    });
    const replay = await tx(user.writer, () => must('live_buy_settle_v1',settled.payload));
    assert.deepEqual(replay,settled.receipt);
    return settled.payload;
}

try {
    db = await database();
    phase = 'two C06 demo sessions';
    const {users,run} = await setupBoth();
    const start = new Date();
    const baselineHeader = {number:pair ? String(Number(pair[0].header.number)-1) : '100',
        hash:pair?.[0].header.parentHash ?? hash('a'),parentHash:hash('9'),
        timestampSeconds:String(Math.floor(start.getTime()/1000)-1)};
    for (const user of users) {
        const arm = await tx(user.writer, () => must('live_activity_arm',
            operation(user,run,{baseline:baselineHeader,baselineReceivedAt:start.toISOString()})));
        user.checkpoint = arm.result.checkpoint;
        user.armedAt = Date.parse(arm.result.armedAt);
        assert.ok(Number.isFinite(user.armedAt));
        const stop = await tx(user.writer, () => must('live_activity_stop',operation(user,run,{status:'stopped'})));
        user.resume = operation(user,run,{expectedLastOperationId:stop.result.operationId,
            expectedCheckpoint:user.checkpoint,expectedHighWatermark:'0'});
    }
    phase = 'verify scoped resume and add the isolated permit';
    assert.equal((await tx(users[1].writer, () => rpc('live_activity_resume',users[1].resume))).http,403);
    const {rows: inserted} = await db.query(`INSERT INTO polygon_live_activity.resume_patch
        SELECT true, a.session_id, a.run_id, a.writer_role, a.writer_oid, $2, 'explicit-clean-stop-resume-v1',
               clock_timestamp(), '{}'::jsonb FROM polygon_live_activity.assignments a
        JOIN polygon_live_activity.stream s USING(session_id)
        WHERE a.session_id=$1 AND s.status='stopped' AND s.high_watermark=0 RETURNING session_id`,
        [users[1].sid,evidence('0')]);
    assert.deepEqual(inserted,[{session_id:users[1].sid}]);
    assert.equal((await tx(users[0].writer, () => rpc('live_activity_resume',users[1].resume))).http,403);

    phase = 'compose the stock write and read SQL';
    await db.exec('BEGIN ISOLATION LEVEL SERIALIZABLE; CREATE SCHEMA live_buy_core AUTHORIZATION polygon_owner; CREATE SCHEMA polygon_buy AUTHORIZATION polygon_owner; SET LOCAL ROLE polygon_owner');
    for (const path of ['core/001-core.sql','core/002-state.sql','core/003-write.sql','core/004-integrity.sql','010-bindings.sql']) {
        const sql = await readFile(new URL(path,fixture),'utf8');
        await db.exec(sql.replace(/^CREATE SCHEMA .*;$/mg,''));
    }
    await db.exec('RESET ROLE');
    await loadSource(db,new URL('009-catalog-operator.sql',fixture));
    await db.exec('SET LOCAL ROLE polygon_owner');
    for (const path of ['011-projection.sql','012-writes-reads.sql','013-activity.sql','014-integrity-reads.sql'])
        await loadSource(db,new URL(path,fixture));
    await db.exec('COMMIT');
    for (const user of users) {
        await tx(null,() => db.query('SELECT polygon_buy.bind_session($1)',[user.sid]));
        await db.exec(`GRANT EXECUTE ON FUNCTION polygon.live_buy_reserve_v1(jsonb),polygon.live_buy_settle_v1(jsonb),
            polygon.live_buy_lookup_v1(jsonb) TO ${user.writer}`);
        await tx(user.writer,() => must('live_activity_resume',user.resume));
    }

    phase = 'publish one public execution';
    await prepareQueue(users);
    const {rows:[{activeFrom}]} = await db.query(
        'SELECT max(active_from)::text "activeFrom" FROM demo_delivery.subscriptions');
    const afterArm = (Math.floor(Math.max(Date.parse(activeFrom), ...users.map(user => user.armedAt)) / 1000) + 1) * 1000;
    await delay(Math.max(0, afterArm - Date.now()) + 5);
    if (freshSource) {
        phase = 'await fresh Polymarket quote';
        const {readFreshPolymarketQuote} = await import('./fresh-polymarket-quote.mjs');
        chosen = await readFreshPolymarketQuote(freshSource,wallet);
    }
    if (pair) {
        const buy = pair[1].log;
        chosen = {...chosen, token:buy.tokenId, sourceExecution:`${buy.transactionHash}:${buy.logIndex}`,
            market:'Archived Tokor execution', outcome:'Fixture outcome',
            publicExecutionId:digest(buy), quoteOrigin:'controlled-quote-for-archived-pair'};
    }
    assert.match(chosen.publicExecutionId, /^[0-9a-f]{64}$/);
    [publicTx,logIndex] = chosen.sourceExecution.split(':');
    assert.match(publicTx, /^0x[0-9a-f]{64}$/);
    assert.match(logIndex, /^(0|[1-9][0-9]*)$/);
    phase = 'publish one public execution';
    const header = {...(pair ? pair[0].header : {number:'101',hash:hash('b'),parentHash:hash('a')}),
        timestampSeconds:String(Math.floor(Date.now()/1000))};
    let jobs;
    if (pair) {
        await db.exec(await readFile(new URL('./source-checkpoints.sql',import.meta.url),'utf8'));
        await db.query("INSERT INTO demo_delivery.source_cursors VALUES ('polymarket',$1,$2,$3)",
            [wallet,baselineHeader.number,baselineHeader.hash]);
        const send = () => publishFinalizedPolygonBlock(db,wallet,header,pair.map(item => item.log),new Date());
        assert.equal((await send()).enqueued,4);
        assert.equal((await send()).enqueued,0);
        ({rows:jobs} = await db.query("SELECT * FROM demo_delivery.claim(2,interval '25 seconds')"));
        assert.equal(jobs.length,2);
        assert.ok(jobs.every(job => job.payload.log.logIndex === pair[0].log.logIndex));
    } else {
        jobs = await publish(users);
    }
    const secondJob = jobs.find(job => job.session_id === users[1].sid);
    assert.equal(await tx(users[0].writer,() => acknowledge(secondJob)),false);
    const reports = [];
    for (const user of users) {
        phase = 'write and reconcile the isolated purchase';
        const settled = await applyBuy(user,run,jobs.find(job => job.session_id === user.sid),header);
        const state = await tx(null,() => must('buy_session_read_v1',{auth:user.auth,session_id:user.sid}));
        const activity = await tx(null,() => must('buy_activity_read_v1',{auth:user.auth,session_id:user.sid,after_sequence:'0',limit:20}));
        const matches = activity.items.filter(item =>
            item.source.transactionHash === publicTx && item.decision.status === 'filled');
        assert.equal(matches.length,1);
        if (pair) assert.equal(activity.items.filter(item => item.decision.status === 'skipped' &&
            item.decision.detailCode === 'book_unavailable').length,1);
        assert.equal(matches[0].decision.status,'filled');
        assert.equal(matches[0].decision.copy.snapshotId,state.snapshotId);
        assert.equal(state.financial.positions.length,1);
        assert.deepEqual(state.financial.freeCash,chosen.afterDebit);
        assert.deepEqual(state.financial.cashExpenses,chosen.quote.cashFee);
        assert.deepEqual(state.financial.positions[0].quantity,chosen.quote.quantity);
        const other = users.find(entry => entry !== user);
        const foreign = await tx(null,() => rpc('buy_activity_read_v1',{auth:other.auth,session_id:user.sid,after_sequence:'0',limit:20}));
        assert.ok([403,404].includes(foreign.http));
        const foreignWrite = await tx(other.writer, () => rpc('live_buy_settle_v1',settled));
        assert.equal(foreignWrite.http,403);
        if (reports.length === 0) {
            const untouched = await tx(null, () => must('q04_session',{auth:other.auth,session_id:other.sid}));
            assert.deepEqual(untouched.session.financialSnapshot.free,q(200));
            assert.equal(untouched.session.financialSnapshot.positionCount,'0');
        }
        reports.push({session:user.sid, command:settled.request.commandId, snapshot:state.snapshotId, cash:state.financial.freeCash,
            sourceToActivityMs:chosen.timing ? Date.now()-chosen.timing.occurredAt.getTime() : undefined,
            shares:state.financial.positions[0].quantity, oneActivity:true, foreignReadDenied:true});
    }
    assert.equal(new Set(reports.map(item => item.command)).size,2);
    assert.equal(new Set(reports.map(item => item.snapshot)).size,2);
    if (restartCluster) {
        phase = 'reopen purchases after an isolated database restart';
        db = await restartCluster();
        for (const [index,user] of users.entries()) {
            const state = await tx(null, () => must('buy_session_read_v1',{auth:user.auth,session_id:user.sid}));
            assert.equal(state.snapshotId,reports[index].snapshot);
            assert.deepEqual(state.financial.freeCash,reports[index].cash);
            assert.deepEqual(state.financial.positions[0].quantity,reports[index].shares);
            const activity = await tx(null, () => must('buy_activity_read_v1',
                {auth:user.auth,session_id:user.sid,after_sequence:'0',limit:20}));
            assert.equal(activity.items.filter(item => item.source.transactionHash===publicTx &&
                item.decision.status==='filled').length,1);
        }
    }
    const {rows: [counts]} = await db.query(`SELECT
        (SELECT count(*)::int FROM demo_delivery.signals) signals,
        (SELECT count(*)::int FROM demo_delivery.jobs WHERE finish_reason='acknowledged') jobs,
        (SELECT count(*)::int FROM live_buy_core.executions) purchases`);
    assert.deepEqual(counts,{signals:pair ? 2 : 1,jobs:pair ? 4 : 2,purchases:2});
    const report = {environment:backend, quoteOrigin:chosen.quoteOrigin ?? 'retained-replay', executionId:chosen.publicExecutionId,
        sourceExecution:chosen.sourceExecution, subscribedFromAppStart:appStart, simulatedRange:true, reopenedAfterDatabaseRestart:!!restartCluster,
        unauthorizedResumeDenied:true,
        foreignAcknowledgementDenied:true, foreignFinancialWriteDenied:true, secondSessionUnchangedAfterFirst:true,
        repeatPurchaseIdempotent:true, skippedThenBought:!!pair, ...counts, sessions:reports};
    if (retainedState) {
        await close();
        close = undefined;
        await stopCluster();
        stopCluster = undefined;
        await writeFile(join(resolve(retainedState),'verified-purchases.json'),JSON.stringify(report,null,2)+'\n',
            {flag:'wx',mode:0o600});
    }
    console.log(JSON.stringify(report,null,2));
} catch(error) {
    console.error(JSON.stringify({phase,error:error.message,code:error.code,detail:error.detail,where:error.where}));
    process.exitCode = 1;
} finally {
    try { await close?.(); } finally {
        await stopCluster?.();
        await rm(scratch,{recursive:true,force:true});
    }
}
