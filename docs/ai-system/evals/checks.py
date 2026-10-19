#!/usr/bin/env python3
"""Offline evidence checks. Does not run agents, APIs, or grade semantics."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[1]
CATALOG_PATH = BASE / "catalog.json"
SKILLS = ({r["id"]: r["name"] for r in json.loads(CATALOG_PATH.read_text())["skills"]}
          if CATALOG_PATH.exists() else {"S01": "cct-project-context", "S21": "cct-knowledge-curation", "S10": "cct-ai-quality"})


def read_json(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_check(query=None):
    cards = read_json(BASE / "knowledge/sources.json")["sources"]
    problems, seen = [], set()
    required = {"id", "title", "publisher", "locator", "section", "access", "observed_at", "currency", "version", "sha256", "supports", "limits", "tags", "used_by", "refresh_when", "usage"}
    for c in cards:
        if required - c.keys():
            problems.append(f"{c.get('id')}: missing fields {sorted(required - c.keys())}")
            continue
        if c["id"] in seen:
            problems.append(f"duplicate source {c['id']}")
        seen.add(c["id"])
        if c["access"] not in {"read", "partial", "index_only", "unavailable", "candidate"}:
            problems.append(f"{c['id']}: invalid access")
        if c["currency"] not in {"current_at_observation", "needs_recheck", "superseded", "conflict", "unknown"}:
            problems.append(f"{c['id']}: invalid currency")
        try:
            if datetime.fromisoformat(c["observed_at"]).tzinfo is None:
                raise ValueError("timezone missing")
        except ValueError:
            problems.append(f"{c['id']}: invalid observation time")
        if c["access"] in {"read", "partial"} and not c["supports"]:
            problems.append(f"{c['id']}: observed source without scoped claims")
        if not c["limits"] or not c["refresh_when"]:
            problems.append(f"{c['id']}: limits or refresh condition missing")
        if not c["locator"].startswith("https://"):
            path = REPO / c["locator"]
            if not path.is_file():
                problems.append(f"{c['id']}: file missing")
            elif digest(path) != c["sha256"]:
                problems.append(f"{c['id']}: changed since reading; recheck affected knowledge")
    if query:
        hits = [c for c in cards if query.casefold() in json.dumps(c, ensure_ascii=False).casefold()]
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    return problems


def validate():
    problems = source_check()
    if CATALOG_PATH.exists():
        rows = read_json(CATALOG_PATH)["skills"]
        ids = [r["id"] for r in rows]
        if len(ids) != len(set(ids)) or set(ids) != {f"S{i:02d}" for i in range(1, 24)}:
            problems.append("catalog must contain 23 distinct S01–S23 entries")
        if len({r["name"] for r in rows}) != len(rows):
            problems.append("duplicate catalog skill name")
        source_ids = {c["id"] for c in read_json(BASE / "knowledge/sources.json")["sources"]}
        graph = {r["id"]: r["depends_on"] for r in rows}
        for r in rows:
            if any(dep not in graph for dep in r["depends_on"]):
                problems.append(f"{r['id']}: unknown dependency")
            if any(sid not in source_ids for sid in r["source_ids"]):
                problems.append(f"{r['id']}: unknown source")
            if not (REPO / r["learning_path"]).is_file():
                problems.append(f"{r['id']}: missing learning pack")
        def visit(node, trail):
            if node in trail:
                raise ValueError("catalog dependency cycle: " + " -> ".join(trail + [node]))
            for dep in graph.get(node, []):
                visit(dep, trail + [node])
        try:
            for node in graph:
                visit(node, [])
        except ValueError as e:
            problems.append(str(e))
    for sid, name in SKILLS.items():
        folder = REPO / ".agents/skills" / name
        path = folder / "SKILL.md"
        text = path.read_text()
        # The bundled skill-creator validator additionally checks YAML semantics.
        if not text.startswith("---\n") or f"name: {name}\n" not in text:
            problems.append(f"{sid}: missing or mismatched manifest")
        if not (folder / "agents/openai.yaml").is_file():
            problems.append(f"{sid}: UI metadata missing")
    # Frozen fixtures/snapshots preserve their original unresolved references.
    # They are evidence, not installed documentation; lint only maintained links.
    archive_roots = [p.parent / name for p in BASE.glob("evals/independent-*/archive-map.json") for name in ("round1", "round2")]
    for path in list(BASE.rglob("*.md")) + [REPO / ".agents/skills" / n / "SKILL.md" for n in SKILLS.values()]:
        if any(folder in path.parents for folder in archive_roots):
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" not in target and not target.startswith("#"):
                if not (path.parent / target.split("#")[0]).exists():
                    problems.append(f"{path.name}: broken local reference {target}")
    cases = read_json(BASE / "evals/cases.json")["cases"]
    oracles = read_json(BASE / "evals/oracles.json")["oracles"]
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids) or set(ids) != set(oracles):
        problems.append("case/oracle IDs not one-to-one")
    for c in cases:
        for loc in c.get("artifacts", {}):
            p = Path(loc)
            if p.is_absolute() or ".." in p.parts:
                problems.append(f"{c['id']}: unsafe fixture path")
        if not oracles[c["id"]]["checks"]:
            problems.append(f"{c['id']}: no acceptance criteria")
    return problems


def prepare(case_id, output):
    """Export only prompt, minimal raw fixtures and requested skill, never oracle."""
    cases = read_json(BASE / "evals/cases.json")["cases"]
    case = next(c for c in cases if c["id"] == case_id)
    for loc in case.get("artifacts", {}):
        if Path(loc).is_absolute() or ".." in Path(loc).parts:
            raise ValueError("Unsafe fixture path")
        if Path(loc).parts[0] in {"task.md", "SKILL.md", "metadata.json", "results"}:
            raise ValueError("Fixture collides with evaluator control or result path")
    out = Path(output).resolve()
    # Exports cannot overwrite source material or an existing evaluator workspace.
    if out == REPO or REPO in out.parents or out == BASE:
        raise ValueError("Use a fresh temporary directory outside the repository")
    out.mkdir(parents=True, exist_ok=False)
    out.joinpath("results").mkdir()
    out.joinpath("task.md").write_text(case["prompt"] + "\n\nUse only these synthetic fixtures for case facts. No external actions. Write outputs only under results/; all supplied artifacts, including answer.md if present, are read-only.\n")
    for loc, content in case.get("artifacts", {}).items():
        p = out / loc
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    if case["mode"] == "task":
        name = SKILLS[case["skill"]]
        out.joinpath("SKILL.md").write_text((REPO / ".agents/skills" / name / "SKILL.md").read_text())
        out.joinpath("task.md").write_text(out.joinpath("task.md").read_text() + "\nRead SKILL.md explicitly. Project fact references in that skill are replaced by supplied fixtures for this exercise. Do not read the real project, learning examples, cases.json or oracles.json.\n")
    else:
        metadata = {}
        for sid, name in SKILLS.items():
            metadata[sid] = (REPO / ".agents/skills" / name / "SKILL.md").read_text().split("---", 2)[1].strip()
        out.joinpath("metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    return str(out)


def grade(record, case_id, oracles):
    """Validate reviewer adjudication; meaningful judgments remain reviewer work."""
    checks = oracles[case_id]["checks"]
    if record.get("case_id") != case_id:
        raise ValueError("case ID mismatch")
    if record.get("evaluation_kind") not in {"self_pilot", "independent_explicit", "metadata_review", "runtime_discovery"}:
        raise ValueError("evaluation kind missing")
    if record["evaluation_kind"] == "independent_explicit" and (record.get("oracle_visible") is not False or record.get("same_author") is not False):
        raise ValueError("independent result must have evaluator separation and no visible oracle")
    if record.get("evaluation_kind") == "runtime_discovery" and not record.get("discovery_evidence"):
        raise ValueError("runtime discovery requires runtime evidence")
    if set(record.get("checks", {})) != {c["id"] for c in checks}:
        raise ValueError("missing or extra checks")
    states = []
    for c in checks:
        value = record["checks"][c["id"]]
        if value.get("status") not in {"pass", "fail", "not_verified"} or not value.get("evidence", "").strip():
            raise ValueError("every verdict needs a valid status and concrete reviewer evidence")
        states.append(value["status"])
    # No numerical average can conceal failure, including any critical failure.
    return "fail" if "fail" in states else "not_verified" if "not_verified" in states else "pass"


def grade_file(record_path):
    path = Path(record_path).resolve()
    record = read_json(path)
    response = (path.parent / record["response_file"]).resolve()
    if path.parent not in response.parents or not response.is_file():
        raise ValueError("response must exist beside or below the record")
    if digest(response) != record.get("response_sha256"):
        raise ValueError("response changed since adjudication")
    if not record.get("trace") or not record.get("observed_at"):
        raise ValueError("trace and observation time required")
    for metric in ("tokens", "cost_usd", "latency_seconds"):
        value = record.get(metric)
        if value is not None and (not isinstance(value, (float, int)) or isinstance(value, bool) or value < 0):
            raise ValueError(f"invalid {metric}")
    return grade(record, record["case_id"], read_json(BASE / "evals/oracles.json")["oracles"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sources = sub.add_parser("sources")
    sources.add_argument("--query")
    export = sub.add_parser("prepare")
    export.add_argument("case_id")
    export.add_argument("output")
    scoring = sub.add_parser("grade")
    scoring.add_argument("record")
    args = parser.parse_args()
    try:
        if args.command in {"validate", "sources"}:
            problems = validate() if args.command == "validate" else source_check(args.query)
            print(json.dumps({"check": args.command, "status": "fail" if problems else "pass", "problems": problems}, ensure_ascii=False, indent=2))
            return bool(problems)
        if args.command == "prepare":
            print(prepare(args.case_id, args.output))
            return 0
        result = grade_file(args.record)
        print(json.dumps({"status": result, "meaning": "reviewer judgments validated; semantic quality not automatically proven"}))
        return 0 if result == "pass" else 1
    except (ValueError, KeyError, StopIteration, OSError) as e:
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
