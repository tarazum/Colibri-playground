#!/usr/bin/env python3
"""Phase 9 — thermal marathon: sustained generation for N minutes.

Sends back-to-back chat completions (p2 prompt, 500-token cap,
temperature=0) for the whole duration against one persistent server
(auto-tier, tuned profile), recording per-request decode rate and timing.
Paired with an external `nvidia-smi -l 5` CSV logger (results/thermal/logs/)
this shows whether measured speed is stable or a first-minutes burst.

Usage: python tools/thermal_test.py --minutes 16
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODEL = "C:/Models/qwen36_i4_gs64"
OUT_DIR = REPO / "results" / "thermal"
PROMPT = (REPO / "prompts" / "p2_explanation.txt").read_text(encoding="utf-8")
MAX_TOKENS = 500


def start_server(log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8", errors="replace")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    return subprocess.Popen(
        ["coli", "serve", "--auto-tier", "--model", MODEL],
        stdout=log, stderr=subprocess.STDOUT, creationflags=flags,
    )


def wait_ready(base: str, proc) -> str:
    deadline = time.time() + 180
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit(f"[server] died during startup (exit {proc.returncode})")
        try:
            with urllib.request.urlopen(f"{base}/models", timeout=5) as r:
                return json.load(r)["data"][0]["id"]
        except Exception:
            time.sleep(2)
    sys.exit("[server] not ready in time")


def one_request(base: str, model_id: str) -> dict:
    body = {"model": model_id,
            "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0, "max_tokens": MAX_TOKENS, "stream": True}
    req = urllib.request.Request(f"{base}/chat/completions",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    t0 = time.perf_counter()
    ttft = None
    chunks = 0
    with urllib.request.urlopen(req, timeout=900) as r:
        for raw in r:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except ValueError:
                continue
            delta = (obj.get("choices") or [{}])[0].get("delta", {})
            if delta.get("content"):
                if ttft is None:
                    ttft = time.perf_counter() - t0
                chunks += 1
    wall = time.perf_counter() - t0
    decode = (chunks - 1) / (wall - ttft) if ttft and chunks > 1 else None
    return {"wall": wall, "ttft": ttft, "generated": chunks, "decode": decode}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=16)
    args = ap.parse_args()
    base = "http://127.0.0.1:8000/v1"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    proc = start_server(OUT_DIR / "logs" / "server.log")
    records = []
    t_start = None
    try:
        model_id = wait_ready(base, proc)
        print(f"[server] ready ({model_id}); sustained load for {args.minutes} min",
              flush=True)
        t_start = time.time()
        t0_pc = time.perf_counter()
        deadline = t0_pc + args.minutes * 60
        n = 0
        while time.perf_counter() < deadline:
            r = one_request(base, model_id)
            n += 1
            rec = {"request": n,
                   "elapsedMin": round((time.perf_counter() - t0_pc) / 60, 2),
                   **{k: (round(v, 3) if isinstance(v, float) else v)
                      for k, v in r.items()}}
            records.append(rec)
            print(f"  #{n:3} t={rec['elapsedMin']:5.1f}m tok={r['generated']} "
                  f"tok/s={r['decode'] and round(r['decode'], 2)} wall={r['wall']:.0f}s",
                  flush=True)
    finally:
        import signal
        if sys.platform == "win32":
            try:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
                proc.wait(timeout=30)
            except Exception:
                proc.terminate()
        else:
            proc.terminate()

    out = {
        "startedUtc": datetime.fromtimestamp(
            t_start, tz=timezone.utc).isoformat(timespec="seconds") if t_start else None,
        "minutes": args.minutes,
        "requests": records,
    }
    (OUT_DIR / "thermal_results.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    # minute-bucketed decode rates: burst vs sustained
    buckets: dict[int, list[float]] = {}
    for r in records:
        if r["decode"]:
            buckets.setdefault(int(r["elapsedMin"]), []).append(r["decode"])
    summary = {str(m): round(statistics.mean(v), 2) for m, v in sorted(buckets.items())}
    (OUT_DIR / "summary_by_minute.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
