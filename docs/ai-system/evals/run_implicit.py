#!/usr/bin/env python3
"""Evaluate native implicit SKILL.md reads in fresh, read-only Codex CLI sessions.

Use synthetic cases only. CLI authentication and service-state access are inherited;
no credentials are read by this script. This does not test Desktop UI parity.
"""
import argparse
import concurrent.futures
import json
import re
import shlex
import subprocess
import time
from pathlib import Path


def observed_reads(command, output):
    """Conservative evidence for simple native readers; uncertain shapes fail closed."""
    try:
        args = shlex.split(command)
        if args and Path(args[0]).name in {"bash", "sh", "zsh"} and len(args) >= 3 and "c" in args[1]:
            args = shlex.split(args[2])
    except ValueError:
        return set(), True
    if not args:
        return set(), False
    reader = Path(args[0]).name
    candidates = set()
    for arg in args[1:]:
        normalized = str(Path(arg))
        candidates.update(re.findall(r"(?:^|/)(cct-[a-z0-9-]+)/SKILL\.md$", normalized))
    if reader not in {"cat", "sed", "head", "tail", "Get-Content"}:
        possible_read = bool(re.search(r"cct-.*SKILL\.md", command) and re.search(r"open\(|read_text|readFile", command))
        return set(), possible_read
    if any(token in command for token in ("||", "&&", ";", "|", ">", "<", "$(", "`", "\n", "\r")):
        return set(), bool(candidates)
    confirmed = {name for name in candidates if re.search(r"(?m)^name: *" + re.escape(name) + r" *$", output) and "---" in output}
    return confirmed, bool(candidates - confirmed)


def analyze_trace(trace, expected_any, should_activate, returncode=0):
    events = []
    for line in trace.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    loaded, commands, usage, messages = set(), [], [], []
    completed = False
    uncertain_read = False
    for event in events:
        if event.get("type") == "turn.completed":
            completed = True
            usage.append(event.get("usage"))
        item = event.get("item", {})
        if event.get("type") != "item.completed":
            continue
        if item.get("type") == "agent_message":
            messages.append(item.get("text", ""))
        if item.get("type") == "command_execution":
            command = item.get("command", "")
            commands.append({"command": command, "exit_code": item.get("exit_code")})
            if item.get("exit_code") == 0:
                names, uncertain = observed_reads(command, item.get("aggregated_output", ""))
                loaded.update(names)
                uncertain_read |= uncertain
    ok = bool(loaded & set(expected_any)) if should_activate else not loaded
    status = ("pass" if ok else "fail") if returncode == 0 and completed and not uncertain_read else "not_verified"
    return {"status": status, "observed_skill_file_reads": sorted(loaded), "commands": commands,
            "usage": usage, "answer": "\n\n".join(messages), "turn_completed": completed, "uncertain_read": uncertain_read,
            "limits": "Native command trace file-read evidence; not semantic quality, causal benefit, or Desktop parity"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cases", required=True)
    p.add_argument("--oracles", required=True)
    p.add_argument("--cwd", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--workers", type=int, choices=[1, 2], default=2)
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()
    cases = json.loads(Path(args.cases).read_text())["cases"]
    oracles = json.loads(Path(args.oracles).read_text())["oracles"]
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids) or set(ids) != set(oracles):
        p.error("case/oracle IDs must be one-to-one")
    for c in cases:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", c["id"]):
            p.error("unsafe case ID")
        if "cct-" in c["prompt"] or "SKILL.md" in c["prompt"]:
            p.error("implicit prompts must not name the project skill or manifest")
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)

    def run(c):
        folder = out / c["id"]
        folder.mkdir()
        prompt = c["prompt"] + "\nИспользуй только предоставленные факты и применимые локальные инструкции. Без сети, изменений файлов и внешних действий. Ответ до 150 слов."
        (folder / "prompt.txt").write_text(prompt)
        cmd = ["codex", "-a", "never", "exec", "--ephemeral", "--json", "--ignore-user-config",
               "--skip-git-repo-check", "-s", "read-only", "-C", str(Path(args.cwd).resolve()), prompt]
        start = time.monotonic()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
        except subprocess.TimeoutExpired as error:
            for name, data in (("trace.jsonl", error.stdout), ("stderr.log", error.stderr)):
                (folder / name).write_text(data.decode(errors="replace") if isinstance(data, bytes) else data or "")
            record = {"id": c["id"], "status": "not_verified", "reason": "timeout"}
        else:
            (folder / "trace.jsonl").write_text(result.stdout)
            (folder / "stderr.log").write_text(result.stderr)
            key = oracles[c["id"]]
            record = analyze_trace(result.stdout, key["expected_any"], key["should_activate"], result.returncode)
            (folder / "answer.md").write_text(record.pop("answer") + "\n")
            record.update(id=c["id"], returncode=result.returncode, expected_any=key["expected_any"], should_activate=key["should_activate"])
        record["seconds"] = round(time.monotonic() - start, 2)
        (folder / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        return record

    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(run, cases):
            records.append(r)
            print(json.dumps({"id": r["id"], "status": r["status"]}), flush=True)
    (out / "summary.json").write_text(json.dumps({"results": records}, ensure_ascii=False, indent=2) + "\n")
    return 0 if all(r["status"] == "pass" for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
