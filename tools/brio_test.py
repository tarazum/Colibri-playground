#!/usr/bin/env python3
"""Phase 8 — Brio closed-decision benchmark.

Drives the /v1/brio endpoint (v1.12.0): for each case in
prompts/brio_cases.json, sends {state, question, options} and records the
served probabilities, entropy, answer and latency. 3 repeats per case check
stability (scoring is deterministic at max_tokens=0 — repeats must be
identical). One minimal generation call (max_tokens=1) on the same state
gives the "latency vs normal generation" comparison.

Outputs: results/brio/brio_results.json (raw) + summary.json (per-class
accuracy, probability separation, entropy stats, latency stats).
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODEL = "C:/Models/qwen36_i4_gs64"
OUT_DIR = REPO / "results" / "brio"


def start_server(log_path: Path) -> subprocess.Popen:
    env = {**os.environ, "COLI_PREFIX_LOG": "1"}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8", errors="replace")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    return subprocess.Popen(
        ["coli", "serve", "--auto-tier", "--model", MODEL],
        stdout=log, stderr=subprocess.STDOUT, env=env, creationflags=flags,
    )


def wait_ready(base: str, proc, timeout_s: int = 180) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit(f"[server] died during startup (exit {proc.returncode})")
        try:
            with urllib.request.urlopen(f"{base}/models", timeout=5) as r:
                return json.load(r)["data"][0]["id"]
        except Exception:
            time.sleep(2)
    sys.exit("[server] not ready in time")


def post(base: str, path: str, body: dict) -> tuple[dict, float]:
    req = urllib.request.Request(
        f"{base}{path}", data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.load(r)
    return data, time.perf_counter() - t0


def stop_server(proc) -> None:
    if proc is None:
        return
    if sys.platform == "win32":
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            proc.wait(timeout=30)
        except Exception:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
    else:
        proc.terminate()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    base = "http://127.0.0.1:8000/v1"

    spec = json.loads((REPO / "prompts" / "brio_cases.json").read_text(encoding="utf-8"))
    question, options, cases = spec["question"], spec["options"], spec["cases"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    proc = start_server(OUT_DIR / "logs" / "server.log")
    records = []
    gen_latency = None
    try:
        model_id = wait_ready(base, proc)
        print(f"[server] ready ({model_id})", flush=True)

        # latency reference: minimal normal generation on the same kind of state
        ref = cases[0]
        _, gl = post(base, "/chat/completions", {
            "model": model_id,
            "messages": [{"role": "user",
                          "content": ref["state"] + "\n\n" + question +
                                     "\nAnswer with one word."}],
            "temperature": 0, "max_tokens": 1,
        })
        gen_latency = gl
        print(f"[ref] 1-token generation latency: {gl:.2f}s", flush=True)

        for case in cases:
            reps = []
            for i in range(args.repeats):
                body = {"model": model_id, "state": case["state"],
                        "question": question,
                        "options": options, "normalize": "sum"}
                data, lat = post(base, "/brio", body)
                probs = {c["option"]: c.get("p") for c in data.get("choices", [])}
                reps.append({
                    "answer": data.get("answer"),
                    "entropy": data.get("entropy"),
                    "probs": probs,
                    "latencySeconds": round(lat, 3),
                })
            identical = len({json.dumps({k: r[k] for k in ("answer", "entropy", "probs")},
                                         sort_keys=True) for r in reps}) == 1
            records.append({
                "id": case["id"], "expected": case["expected"],
                "repeats": reps, "stableAcrossRepeats": identical,
            })
            top = reps[0]["probs"].get(reps[0]["answer"])
            ok = reps[0]["answer"] == case["expected"]
            print(f"  [{case['id']}] {case['expected']:6} -> {reps[0]['answer']:6} "
                  f"{'OK ' if ok else 'MISS'} p(top)={top if top is None else round(top,3)} "
                  f"H={reps[0]['entropy'] and round(reps[0]['entropy'],3)} "
                  f"lat={statistics.median(r['latencySeconds'] for r in reps):.2f}s "
                  f"{'stable' if identical else 'UNSTABLE'}", flush=True)
    finally:
        stop_server(proc)

    (OUT_DIR / "brio_results.json").write_text(
        json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "genLatencyRef1Token": round(gen_latency, 3) if gen_latency else None,
                    "repeats": args.repeats, "records": records},
                   indent=2, ensure_ascii=False), encoding="utf-8")

    def cls_stats(cls: str) -> dict:
        rows = [r for r in records if r["expected"] == cls]
        acc = sum(1 for r in rows if r["repeats"][0]["answer"] == cls)
        ents = [r["repeats"][0]["entropy"] for r in rows if r["repeats"][0]["entropy"] is not None]
        tops = [max((p for p in r["repeats"][0]["probs"].values() if p is not None), default=0)
                for r in rows]
        lats = [r["repeats"][0]["latencySeconds"] for r in rows]
        return {"n": len(rows), "correct": acc,
                "accuracy": round(acc / len(rows), 3) if rows else None,
                "entropyMean": round(statistics.mean(ents), 3) if ents else None,
                "entropyMin": round(min(ents), 3) if ents else None,
                "entropyMax": round(max(ents), 3) if ents else None,
                "topProbMean": round(statistics.mean(tops), 3) if tops else None,
                "latencyMedian": round(statistics.median(lats), 3) if lats else None}

    summary = {cls: cls_stats(cls) for cls in ("ALLOW", "REVIEW", "DENY")}
    summary["_overall"] = {
        "accuracy": round(sum(1 for r in records if r["repeats"][0]["answer"] == r["expected"])
                          / len(records), 3),
        "allStableAcrossRepeats": all(r["stableAcrossRepeats"] for r in records),
        "genLatencyRef1Token": round(gen_latency, 3) if gen_latency else None,
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
