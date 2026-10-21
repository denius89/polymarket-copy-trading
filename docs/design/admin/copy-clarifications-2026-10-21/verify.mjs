import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const evidence = JSON.parse(fs.readFileSync(path.join(dir, 'evidence.json')));
const rows = new Map(evidence.textReadback.map(row => [row.id, row]));
assert.equal(rows.size, 4);
assert.match(rows.get('I2003:455;1981:9').text, /партнёрский VIP с денежными условиями утверждают два разных владельца/);
assert.match(rows.get('I2003:455;1981:9').text, /VIP пользователя меняет один владелец/);
assert.match(rows.get('I2007:447;1981:9').text, /Two distinct owners approve monetary partner rules and partner VIP with monetary terms/);
assert.match(rows.get('I2007:447;1981:9').text, /One owner changes ordinary pricing and user VIP/);
assert.equal(rows.get('I2187:23326;2081:74').text, 'Решено · пример подтверждения клиента');
assert.equal(rows.get('I2188:87328;2081:74').text, 'Resolved · user-confirmed example');
for (const row of evidence.finalCardMetadata) assert.match(row.content, /height="130"/);
assert.equal(evidence.finalCardMetadata.length, 2);
assert.equal(evidence.docCards.length, 2);
assert.match(evidence.docCards.find(c => c.number === '13.09').paragraphs.join(''), /два разных владельца/);
assert.match(evidence.docCards.find(c => c.number === '09.19').paragraphs.join(''), /не подтверждают торговую или денежную операцию/);
const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json')));
for (const [name, sha] of Object.entries(manifest.sha256)) {
  const bytes = fs.readFileSync(path.join(dir, name));
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), sha, name);
}
for (const name of ['vip-ru.png', 'vip-en.png', 'support-status-ru.png', 'support-status-en.png']) {
  const bytes = fs.readFileSync(path.join(dir, name));
  assert.equal(bytes.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  assert.equal(bytes.readUInt32BE(16), 1440);
}
console.log('Verified VIP RU/EN, ticket status, two 130px cards, guide meanings and four final PNGs. Scoped design check only.');
