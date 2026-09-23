import { access } from "node:fs/promises";

const requiredPaths = [
  "docs/PROJECT_STATE.md",
  "docs/01_product_and_economics.md",
  "docs/02_technical_concept.md",
  "docs/03_execution_plan.md",
  "docs/04_project_outlook.md",
  "docs/05_vibecoding_operating_plan.md",
  "docs/06_ux_audit_and_user_flow.md",
  "references/Polymarket_Project_Dialogue_Handoff.md",
  ".env.example",
];

const missing = [];

for (const path of requiredPaths) {
  try {
    await access(path);
  } catch {
    missing.push(path);
  }
}

if (missing.length > 0) {
  console.error(`Missing required project files:\n${missing.join("\n")}`);
  process.exitCode = 1;
} else {
  console.log("Project structure is valid.");
}
