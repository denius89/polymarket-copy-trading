import { access, readdir, readFile, stat } from "node:fs/promises";
import { dirname, extname, join, normalize, resolve, sep } from "node:path";
import { relativeLinkTargets } from "./markdown-links.mjs";

const root = process.cwd();

const requiredPaths = [
  "README.md",
  "README.en.md",
  "docs/REPOSITORY_GUIDE.md",
  "docs/storage/catalog.json",
  "CONTRIBUTING.md",
  "SECURITY.md",
  "AGENTS.md",
  "docs/README.md",
  "docs/ROADMAP.md",
  "docs/PROJECT_STATE.md",
  "docs/01_product_and_economics.md",
  "docs/02_technical_concept.md",
  "docs/03_execution_plan.md",
  "docs/20_limitless_partner_integration.md",
  "docs/21_polymarket_access_and_spike_plan.md",
  "docs/22_limitless_access_and_spike_plan.md",
  "docs/23_dual_venue_adapter_contract.md",
  "docs/24_parallel_workstreams.md",
  "docs/29_bilingual_product_language.md",
  "docs/30_binance_copy_trading_ui_benchmark.md",
  "docs/31_project_readiness_audit.md",
  "docs/decisions/README.md",
  "docs/decisions/0007_limitless_first_integration.md",
  "docs/decisions/0008_dual_venue_product_scope.md",
  "docs/decisions/0009_novice_first_direct_mvp.md",
  "artifacts/README.md",
  ".github/workflows/repository-check.yml",
  "references/README.md",
  ".env.example",
];

const ignoredDirectories = new Set([".git", "node_modules", ".next", "dist", "build", "coverage"]);

// Frozen evaluation workspaces retain their original links and temporary paths.
// Check the reports above them and the active skills/docs, not these replicas.
const archivedEvaluationRoots = new Set([
  "docs/ai-system/evals/independent-2026-10-17/round1",
  "docs/ai-system/evals/independent-2026-10-17/round2",
  "docs/ai-system/evals/independent-catalog-2026-10-17/round1",
  "docs/ai-system/evals/independent-deep-2026-10-17/round1",
  "docs/ai-system/evals/independent-deep-2026-10-17/round2",
]);

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function collectMarkdown(directory, result = []) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory() && archivedEvaluationRoots.has(path.slice(root.length + 1).split(sep).join("/"))) continue;
    if (entry.isDirectory()) await collectMarkdown(path, result);
    else if (entry.isFile() && extname(entry.name) === ".md") result.push(path);
  }
  return result;
}


const errors = [];

for (const path of requiredPaths) {
  if (!(await exists(join(root, path)))) errors.push(`Missing required path: ${path}`);
}

for (const markdownPath of await collectMarkdown(root)) {
  const markdown = await readFile(markdownPath, "utf8");
  for (const target of relativeLinkTargets(markdown)) {
    const destination = normalize(resolve(dirname(markdownPath), target));
    if (destination !== root && !destination.startsWith(`${root}${sep}`)) {
      errors.push(`Link escapes repository: ${markdownPath.slice(root.length + 1)} -> ${target}`);
      continue;
    }
    try {
      await stat(destination);
    } catch {
      errors.push(`Broken relative link: ${markdownPath.slice(root.length + 1)} -> ${target}`);
    }
  }
}

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`Project structure and Markdown links are valid (${requiredPaths.length} required paths).`);
}
