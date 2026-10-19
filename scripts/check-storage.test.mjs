import test from 'node:test';
import assert from 'node:assert/strict';
import { safeRelativePath, validateCatalog, validateDataManifest, trackedFileErrors } from './check-storage.mjs';
const source = { path: 'research/run/input.parquet', bytes: 0, sha256: 'a'.repeat(64), included_in_git: false };
const catalog = () => ({ schema_version: 1, git_file_limit_bytes: 10485760, entries: [{ id: 'saved-data', kind: 'research_data', title: 'Inputs', access: 'private', verification: 'Size verified, remote hashes unknown', last_verified: '2026-10-19', folder_url: 'https://drive.google.com/drive/folders/abc_123', manifest_path: 'research/manifest.json', restore_path: 'research/README.md' }] });
test('external data manifest remains valid in a clone without source bytes', () => assert.deepEqual(validateDataManifest({ files: [source] }), []));
test('raw input accidentally added to Git is rejected even if manifest says external', () => assert.match(validateDataManifest({ files: [source] }, new Set([source.path])).join(), /included in Git/));
test('source ambiguity and bad hashes/sizes cannot pass', () => {
  const errors = validateDataManifest({ files: [source, { ...source, bytes: -1, sha256: 'unknown' }] }).join();
  for (const reason of ['Duplicate', 'Invalid size', 'Invalid SHA256']) assert.ok(errors.includes(reason));
});
test('manifests cannot escape the repository through paths or URI forms', () => {
  for (const path of ['../outside', '/private/x', 'https://host/x', 'C:\\x', 'a/../b', 'a//b']) assert.equal(safeRelativePath(path), false, path);
  assert.match(validateDataManifest({ files: [{ ...source, path: '../outside' }] }).join(), /Unsafe/);
});
test('catalog requires permanent folder locators instead of signed downloads', () => {
  assert.deepEqual(validateCatalog(catalog()), []);
  for (const url of ['https://example.com/file?token=x', 'https://drive.google.com/drive/folders/abc?token=x', 'https://user:secret@drive.google.com/drive/folders/abc']) {
    const data = catalog(); data.entries[0].folder_url = url; assert.match(validateCatalog(data).join(), /persistent/);
  }
});
test('duplicate catalog IDs and missing recovery instructions fail', () => {
  const data = catalog(); data.entries.push({ ...data.entries[0], restore_path: '../x' });
  assert.match(validateCatalog(data).join(), /duplicate/); assert.match(validateCatalog(data).join(), /Unsafe restore/);
});
test('limit boundary keeps small evidence while routing larger files to Drive', () => {
  assert.deepEqual(trackedFileErrors('research/results.csv', 10485760, 10485760), []);
  assert.match(trackedFileErrors('research/results.csv', 10485761, 10485760).join(), /exceeds/);
});
test('cache and secret filenames fail while the public env example passes', () => {
  for (const path of ['x/__pycache__/a.pyc', 'node_modules/x.js', '.env', 'apps/web/.env.production', 'signer.key']) assert.ok(trackedFileErrors(path, 1, 10485760).length, path);
  assert.deepEqual(trackedFileErrors('.env.example', 1, 10485760), []);
});

// README HTML should be checked without treating vendor documentation examples as live assets.
import { relativeLinkTargets } from './markdown-links.mjs';
test('actual Markdown and HTML artwork links are checked', () => {
  assert.deepEqual(relativeLinkTargets('![cover](cover.svg) <img src="screen.png"> <a href="guide.md#start">Read</a>'), ['cover.svg', 'screen.png', 'guide.md']);
});
test('fenced examples, longer closing fences and inline examples are not live links', () => {
  const text = ['~~~html', '<img src="example.jpg">', '~~~~', '`<a href="example.md">`', '[Read](real.md)'].join('\n');
  assert.deepEqual(relativeLinkTargets(text), ['real.md']);
});
