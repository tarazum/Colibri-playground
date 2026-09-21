#!/usr/bin/env python3
"""Benchmark runner for the Colibri playground.

Runs a command template against every prompt file N times, saves raw
stdout/stderr per run, and writes one JSON per run into results/<mode>/,
matching the schema in docs/experiment_plan.md section 17.

The metric parser is a STUB: the exact `coli` output format is unknown until
the first real run. Wall time is measured by this script and is trustworthy;
everything parse_output() guesses (tok/s, TTFT, tokens) is a regex guess and
MUST be finished against a real log before results are cited. See
docs/open_items.md.

Usage (once the engine is installed):

    python tools/run_bench.py \
        --mode cpu \
        --repeats 3 \
        --model "C:\\Models\\qwen36_i4_gs64" \
        --cmd "coli.cmd chat --model {model} --prompt-file {prompt_file}"

Placeholders: {prompt_file} (path to the prompt txt) and {model}.
The prompt text itself is always piped on stdin; if the runner reads a file,
use {prompt_file} in the command.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO / "prompts"
RESULTS_DIR = REPO / "results"

# GUESSES ONLY — replace with real patterns after the first `coli` run.
GUESS_PATTERNS = {
    "decodeTokensPerSecond": re.compile(r"([\d.]+)\s*tok/s", re.IGNORECASE),
    "ttftSeconds": re.compile(r"ttft[:\s]+([\d.]+)\s*s?", re.IGNORECASE),
    "generatedTokens": re.compile(r"generated[:\s]+(\d+)\s*tokens?", re.IGNORECASE),
    "expertHitRate": re.compile(r"(?:expert )?hit[ -]?rate[:\s]+([\d.]+)\s*%?", re.IGNORECASE),
}


def parse_output(text: str) -> dict:
    """STUB: extract engine metrics from one run's combined output.

    Returns {} keys with None when nothing matched, so missing metrics are
    visible in the JSON instead of silently absent.
    """
    out = {}
    for key, pat in GUESS_PATTERNS.items():
        m = pat.search(text)
        out[key] = float(m.group(1)) if m else None
    if out.get("expertHitRate") is not None and "%" in text:
        pass  # decide per real format whether the value is 0-1 or 0-100
    return out


def load_prompts() -> list[Path]:
    files = sorted(PROMPTS_DIR.glob("p*.txt"))
    if not files:
        sys.exit(f"no prompt files found in {PROMPTS_DIR}")
    return files


def run_once(cmd_template: str, prompt_file: Path, model: str, timeout_s: int) -> tuple[str, float, int]:
    """Run the command once. Returns (combined_output, wall_seconds, exit_code).

    shell=True on purpose: the template is authored by the local user and may
    contain quoted paths; cmd.exe tokenizes it the way the user typed it.
    The prompt text never enters the command string — it goes via stdin.
    """
    prompt_text = prompt_file.read_text(encoding="utf-8")
    cmd = cmd_template.format(prompt_file=str(prompt_file), model=model)
    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        shell=True,
        input=prompt_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
    )
    wall = time.perf_counter() - start
    return (proc.stdout + "\n--- stderr ---\n" + proc.stderr, wall, proc.returncode)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, help="results subdirectory, e.g. cpu, cuda, warm-cache")
    ap.add_argument("--cmd", required=True, help="command template, see placeholders in the module docstring")
    ap.add_argument("--model", default="", help="model path, substituted as {model}")
    ap.add_argument("--repeats", type=int, default=3, help="repeats per prompt (first may be cold)")
    ap.add_argument("--timeout", type=int, default=1800, help="per-run timeout in seconds")
    ap.add_argument("--colibri-version", default="")
    ap.add_argument("--colibri-commit", default="")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    out_dir = RESULTS_DIR / args.mode
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    prompt_files = load_prompts()
    runs = []
    for pf in prompt_files:
        prompt_id = pf.stem.split("_")[0]  # p1_short_factual.txt -> p1
        for i in range(1, args.repeats + 1):
            print(f"[{prompt_id}] run {i}/{args.repeats} ...", flush=True)
            try:
                output, wall, code = run_once(args.cmd, pf, args.model, args.timeout)
            except subprocess.TimeoutExpired:
                print(f"[{prompt_id}] run {i} TIMEOUT after {args.timeout}s — skipped", flush=True)
                continue
            log_path = log_dir / f"{prompt_id}_r{i}.log"
            log_path.write_text(output, encoding="utf-8")
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "colibriVersion": args.colibri_version or None,
                "colibriCommit": args.colibri_commit or None,
                "model": args.model or None,
                "modelRevision": None,
                "mode": args.mode,
                "promptId": prompt_id,
                "promptTokens": None,
                "generatedTokens": None,
                "ttftSeconds": None,
                "decodeTokensPerSecond": None,
                "wallSeconds": round(wall, 3),
                "ramPeakGb": None,
                "vramPeakGb": None,
                "expertHitRate": None,
                "notes": (f"exit={code}; parser stub — see run_bench.py; " + args.notes).strip("; "),
            }
            record.update(parse_output(output))
            runs.append(record)
            (out_dir / f"{prompt_id}_r{i}.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"    wall={wall:.1f}s exit={code} log={log_path.name}", flush=True)

    # Summary: median per prompt. Report the median, never the best run.
    summary = {}
    for pf in prompt_files:
        prompt_id = pf.stem.split("_")[0]
        walls = [r["wallSeconds"] for r in runs if r["promptId"] == prompt_id]
        toks = [r["decodeTokensPerSecond"] for r in runs if r["promptId"] == prompt_id and r["decodeTokensPerSecond"]]
        summary[prompt_id] = {
            "samples": len(walls),
            "wallSecondsMedian": round(statistics.median(walls), 3) if walls else None,
            "decodeTokensPerSecondMedian": round(statistics.median(toks), 3) if toks else None,
        }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
