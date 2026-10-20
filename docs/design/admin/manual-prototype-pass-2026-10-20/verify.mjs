import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import zlib from 'node:zlib';

const read = p => fs.readFileSync(new URL(p, import.meta.url));
const json = p => JSON.parse(read(p));
const map = json('../sitemap.json');
const pairs = json('screen-pairs.json');
const coverage = json('coverage.json');
const manifest = json('manifest.json');
const trace = JSON.parse(zlib.gunzipSync(read('manual-trace.json.gz')));
const all = map.sections.flatMap(s => s.screens);
const frameId = t => new URL(t.url).searchParams.get('node-id')?.replace('-', ':');
const rendered = trace.filter(t => t.ax.length > 500 && !t.ax.includes('text Loading'));
const observed = new Set(rendered.map(frameId));
assert.equal(map.revision, '0.27');
assert.equal(all.length, 825);
assert.deepEqual(map.counts, { ru: 830, en: 830 });
assert.equal(pairs.length, 6);
assert.equal(coverage.routes.length, 21);
assert.equal(coverage.fullStateCombinationAcceptance, false);
assert.equal(manifest.fullManualAcceptance, false);
assert.equal(manifest.realOperationsVerified, false);
assert.equal(manifest.visualKitChanged, false);
assert.equal(manifest.uiKitVersion, '0.4.21');
for (const r of coverage.routes) {
  for (const lang of ['ru', 'en']) {
    assert.ok(observed.has(r[lang]), `${r.id} ${lang}: no rendered entry evidence`);
    assert.equal(r[lang + 'Status'], 'reviewed-main-and-selected-risk-branches');
  }
}
for (const p of pairs) {
  assert.ok(all.some(s => s.key === p.key && s.id === p.ru && s.english.id === p.en));
  assert.ok(observed.has(p.ru) && observed.has(p.en), p.key + ': missing browser retest');
}

for (const lang of ['ru', 'en']) {
  const native = json('native-readback-' + lang + '.json');
  assert.equal(native.rootFrames, 830);
  assert.equal(native.roots.length, 6);
  const root = key => native.roots.find(r => r.id === pairs.find(p => p.key === key)[lang]);
  for (const r of native.roots) {
    assert.equal(r.imagePaintCount, 0);
    assert.ok(r.bindings > 0);
    assert.ok(r.fonts.every(f => f.startsWith('Inter / ')));
  }
  const pending = root('ops-partial-recheck');
  const checked = root('ops-partial-rechecked');
  assert.ok(pending.text.some(t => /12\.00/.test(t) && /подтверждение|confirmed/i.test(t)));
  assert.ok(checked.text.some(t => /12\.00/.test(t) && /Частично|Partially/.test(t)));
  assert.ok(checked.text.some(t => t.includes('EVID-DEMO-04')));
  assert.ok(pending.text.some(t => t.includes('$20.00')));
  assert.ok(!pending.links.some(l => /ops-confirmed|ops-mismatch/.test(l.name)));
  assert.ok(pending.links.some(l => l.targets.includes(checked.id)));
  assert.ok(checked.links.some(l => l.targets.includes(pending.id)));
  for (const key of ['support-note-after-reply-draft', 'support-note-after-reply-saved']) {
    assert.ok(root(key).text.some(t => t.includes('MSG-1042-C')));
  }
  const note = root('support-note-after-reply-saved');
  assert.ok(note.text.some(t => t.includes('NOTE-1042-01')));
  assert.ok(note.text.some(t => /Олег Смирнов|Oleg Smirnov/.test(t)));
  assert.ok(note.text.some(t => /Нора Азиз|Nora Aziz/.test(t)));
  const stale = root('health-stale-ll');
  assert.ok(stale.text.some(t => t.includes('CONN-LL-01')));
  assert.ok(stale.links.some(l => l.targets.includes(lang === 'ru' ? '2138:59053' : '2138:69496')));
  const paid = root('payouts-paid-snapshot');
  assert.equal(paid.text.filter(t => t === 'PAY-021 · PART-024').length, 1);
  const nav = json('native-paid-navigation-' + lang + '.json');
  assert.deepEqual(nav.remainingLinksToEarlierSnapshot, []);
  const column = json('native-partner-columns-' + lang + '.json').fields;
  const b = lang === 'ru' ? '2003:355' : '2007:335';
  assert.equal(column.find(f => f.id === b && f.key === 'State#2002:3').value, '$25.00');
  assert.equal(column.find(f => f.id === b && f.key === 'Amount#2002:2').value, lang === 'ru' ? 'Нет данных' : 'Unknown');
  const receipt = rendered.find(t => /RETEST.*acknowledgement retained in list/.test(t.label) && frameId(t) === (lang === 'ru' ? '2954:166821' : '2956:53051'));
  assert.ok(receipt?.ax.includes('READ-DEMO-A'));
  assert.ok(receipt.ax.includes('NOT-DEMO-01B'));
  assert.ok(receipt.ax.includes(lang === 'ru' ? 'прочтение неизвестно' : 'read unknown'));
}

const vars = json('native-notification-state-ru.json').variables;
const en = json('native-notification-state-en.json');
assert.equal(vars.length, 8);
assert.equal(en.helperVariables.length, 8);
assert.ok(en.helperVariables.every(v => v.type === 'STRING' && v.hiddenFromPublishing && v.scopes.join() === 'TEXT_CONTENT'));
assert.deepEqual(en.foundationCollections.filter(c => c.name !== 'Prototype demo state').map(c => c.count), [31, 25, 11, 5]);
for (const locale of ['ru', 'en']) {
  const n = json('native-notification-state-' + locale + '.json');
  assert.equal(n.button.reactions[0].actions.filter(a => a.type === 'SET_VARIABLE').length, 8);
  assert.ok(n.button.reactions[0].actions.every(a => a.type === 'NODE' || vars.some(v => v.id === a.variableId)));
}
const guide = json('guide-sync.json');
assert.equal(guide.screenCards, 825);
assert.equal(guide.uniqueCardNumbers, 825);
assert.equal(guide.newLinks, 12);
assert.equal(guide.allPriorCardNumbersRetained, true);
assert.equal(guide.readbackVerified, true);
assert.equal(guide.notificationClarificationVerified, true);
assert.equal(coverage.temporarySettings.restored, true);
assert.equal(coverage.temporarySettings.viewportReset, true);
for (const shot of manifest.screenshots) {
  const bytes = read(shot.file);
  assert.ok(bytes.subarray(1, 4).toString() === 'PNG' || bytes.subarray(0, 3).equals(Buffer.from([255,216,255])), shot.file);
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), shot.sha256);
}
assert.equal(crypto.createHash('sha256').update(read('manual-trace.json.gz')).digest('hex'), manifest.browserTrace.sha256);
console.log(`Verified 21 scoped RU/EN routes, ${rendered.length} rendered observations, six new pairs, fact continuity, eight prototype strings and guide parity. No full-state or runtime acceptance.`);
