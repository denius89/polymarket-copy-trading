import { readFile, stat } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export function safeRelativePath(value) {
  return typeof value === 'string' && value.length > 0 && !value.startsWith('/') && !value.includes('\\') && !value.split('/').some(part => !part || part === '.' || part === '..') && !/^[a-z][a-z0-9+.-]*:/i.test(value);
}
const hashPattern = /^[a-f0-9]{64}$/;
export function validateDataManifest(manifest, tracked = new Set()) {
  const errors = [];
  if (!Array.isArray(manifest.files) || !manifest.files.length) return ['Data manifest must list source files'];
  const seen = new Set();
  for (const file of manifest.files) {
    if (!safeRelativePath(file.path)) errors.push(`Unsafe source path: ${file.path}`);
    if (seen.has(file.path)) errors.push(`Duplicate source path: ${file.path}`);
    seen.add(file.path);
    if (!Number.isSafeInteger(file.bytes) || file.bytes < 0) errors.push(`Invalid size: ${file.path}`);
    if (!hashPattern.test(file.sha256 ?? '')) errors.push(`Invalid SHA256: ${file.path}`);
    if (file.included_in_git !== false || tracked.has(file.path)) errors.push(`External source included in Git: ${file.path}`);
  }
  return errors;
}
export function validateCatalog(catalog) {
  const errors = [];
  if (catalog.schema_version !== 1) errors.push('Unsupported catalog schema');
  if (catalog.git_file_limit_bytes !== 10 * 1024 * 1024) errors.push('Git file limit must match the documented 10 MiB policy');
  if (!Array.isArray(catalog.entries) || !catalog.entries.length) return [...errors, 'Archive catalog is empty'];
  const ids = new Set();
  for (const entry of catalog.entries) {
    if (!/^[a-z0-9][a-z0-9-]+$/.test(entry.id ?? '') || ids.has(entry.id)) errors.push(`Invalid or duplicate archive ID: ${entry.id}`);
    ids.add(entry.id);
    if (!['research_data', 'private_recovery'].includes(entry.kind)) errors.push(`Unknown archive kind: ${entry.id}`);
    let url;
    try { url = new URL(entry.folder_url); } catch { /* reported below */ }
    if (!url || url.protocol !== 'https:' || url.hostname !== 'drive.google.com' || !/^\/drive\/folders\/[A-Za-z0-9_-]+$/.test(url.pathname) || url.search || url.hash || url.username || url.password) errors.push(`Expected persistent Drive folder URL: ${entry.id}`);
    for (const key of ['manifest_path', 'restore_path']) if (!safeRelativePath(entry[key])) errors.push(`Unsafe ${key}: ${entry.id}`);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(entry.last_verified ?? '') || Number.isNaN(Date.parse(entry.last_verified))) errors.push(`Missing verification date: ${entry.id}`);
    for (const key of ['title', 'access', 'verification']) if (typeof entry[key] !== 'string' || !entry[key].trim()) errors.push(`Missing ${key}: ${entry.id}`);
  }
  return errors;
}
export function trackedFileErrors(path, bytes, limit) {
  const errors = [];
  if (bytes > limit) errors.push(`Tracked file exceeds 10 MiB; preserve on Drive: ${path}`);
  if (/(^|\/)(node_modules|__pycache__)\//.test(path) || /\.py[cod]$/.test(path) || /(^|\/)\.DS_Store$/.test(path)) errors.push(`Generated cache tracked: ${path}`);
  if (/(^|\/)\.env(?:\..+)?$/.test(path) && !path.endsWith('/.env.example') && path !== '.env.example') errors.push(`Environment secrets file tracked: ${path}`);
  if (/\.(pem|key)$/.test(path)) errors.push(`Private-key file tracked: ${path}`);
  return errors;
}

async function main() {
  const root = process.cwd();
  const paths = execFileSync('git', ['ls-files', '-z'], { encoding: 'utf8' }).split('\0').filter(Boolean);
  const tracked = new Set(paths);
  const catalog = JSON.parse(await readFile('docs/storage/catalog.json', 'utf8'));
  const errors = validateCatalog(catalog);
  for (const entry of catalog.entries ?? []) {
    if (!safeRelativePath(entry.manifest_path) || !safeRelativePath(entry.restore_path)) continue;
    for (const path of [entry.manifest_path, entry.restore_path]) {
      try { await stat(resolve(root, path)); } catch { errors.push(`Missing archive documentation: ${path}`); }
      if (!tracked.has(path)) errors.push(`Archive documentation must be tracked: ${path}`);
    }
    try {
      const manifest = JSON.parse(await readFile(entry.manifest_path, 'utf8'));
      if (entry.kind === 'research_data') errors.push(...validateDataManifest(manifest, tracked));
      else {
        if (!Array.isArray(manifest.recovery_archives) || !manifest.recovery_archives.length) errors.push(`Recovery manifest lacks archive hashes: ${entry.id}`);
        for (const archive of manifest.recovery_archives ?? []) if (!hashPattern.test(archive.sha256 ?? '') || !Number.isSafeInteger(archive.bytes) || archive.bytes < 1) errors.push(`Invalid recovery checksum or size: ${entry.id}`);
      }
    } catch (error) { errors.push(`Unreadable archive manifest ${entry.manifest_path}: ${error.message}`); }
  }
  for (const path of paths) {
    try { errors.push(...trackedFileErrors(path, (await stat(path)).size, catalog.git_file_limit_bytes)); }
    catch { errors.push(`Tracked path absent from checkout: ${path}`); }
  }
  if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
  else console.log(`Storage catalog and tracked-file policy valid (${paths.length} tracked paths). Remote availability is checked separately.`);
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) await main();
