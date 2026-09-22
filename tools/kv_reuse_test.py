#!/usr/bin/env python3
"""Phase 6 — KV-reuse conversation benchmark (A/B).

Two arms, one script each:
    python tools/kv_reuse_test.py                      # arm A: reuse ON (default)
    python tools/kv_reuse_test.py --no-reuse           # arm B: COLI_KV_PREFIX=0
                                                      # (upstream's own A/B switch,
                                                      #  qwen36.c:1092)

Conversation: long dossier (prompts/kv_doc.txt) + question A, then follow-ups
B and C that resend the FULL history (stateless chat API). The server hashes
the leading messages into a stable cache_slot (openai_server.py:
conversation_cache_slot), and the engine reuses the cached KV prefix for
token-identical prefixes. Arm B disables reuse at the engine level, so the
delta between arms is exactly the value of KV reuse in the same warm process,
same tuned profile, same --auto-tier tier.

Per turn we record client-side TTFT (time to first streamed token), wall time
and generated tokens (temperature=0, max_tokens fixed). Serve logs carry no
per-request TTFT lines (verified), so client-side timing is the honest metric.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "results" / "kv-reuse"
MODEL = "C:/Models/qwen36_i4_gs64"
MAX_TOKENS = 60

QUESTIONS = {
    "A": "Which single configuration change caused the April incident, and what p99 latency did POST /charge reach at its worst?",
    "B": "What did the settlement batch rework break, and how much money was double-credited?",
    "C": "According to the capacity notes, which saturation signal appears FIRST, and what is the headroom target?",
}


def start_server(log_path: Path, no_reuse: bool) -> subprocess.Popen:
    env = {**os.environ, "COLI_PREFIX_LOG": "1"}  # proof line: [PREFIX] reusing N of M
    if no_reuse:
        env["COLI_KV_PREFIX"] = "0"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8", errors="replace")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    proc = subprocess.Popen(
        ["coli", "serve", "--auto-tier", "--model", MODEL],
        stdout=log, stderr=subprocess.STDOUT, env=env, creationflags=flags,
    )
    print(f"[server] pid={proc.pid} no_reuse={no_reuse} log={log_path}", flush=True)
    return proc


def wait_ready(base: str, proc, timeout_s: int = 180) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit(f"[server] died during startup (exit {proc.returncode})")
        try:
            with urllib.request.urlopen(f"{base}/models", timeout=5) as r:
                return json.load(r)["data"][0]["id"]
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            time.sleep(2)
    sys.exit("[server] not ready in time")


def chat(base: str, model_id: str, messages: list[dict]) -> dict:
    body = {
        "model": model_id,
        "messages": messages,
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "stream": True,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    started = time.perf_counter()
    ttft = None
    chunks = 0
    parts: list[str] = []
    with urllib.request.urlopen(req, timeout=900) as resp:
        for raw in resp:
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
                    ttft = time.perf_counter() - started
                chunks += 1
                parts.append(delta["content"])
    wall = time.perf_counter() - started
    return {"text": "".join(parts), "wall": wall, "ttft": ttft, "generated": chunks}


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
    ap.add_argument("--no-reuse", action="store_true",
                    help="arm B: start the server with COLI_KV_PREFIX=0")
    args = ap.parse_args()
    arm = "reuse_off" if args.no_reuse else "reuse_on"

    doc = (REPO / "prompts" / "kv_doc.txt").read_text(encoding="utf-8")
    log_path = OUT_DIR / "logs" / f"server_{arm}.log"
    base = "http://127.0.0.1:8000/v1"

    proc = start_server(log_path, args.no_reuse)
    results = {}
    try:
        model_id = wait_ready(base, proc)
        history: list[dict] = []
        for turn, question in QUESTIONS.items():
            first = (turn == "A")
            content = (doc if first else "") + (
                f"\n\nQuestion {turn}: {question}" if first else question
            )
            history.append({"role": "user", "content": content})
            r = chat(base, model_id, history)
            # Round-trip fix (upstream re-render asymmetry, glm53 #1576 shape):
            # turn N was FED as "<|im_start|>assistant\n<think>\n\n</think>\n\n"
            # + answer, but the server re-renders a resent assistant message
            # WITHOUT the think marker — the prefix would diverge at the first
            # assistant turn and reuse would stay 0 forever. Prepending the
            # marker reconstructs the byte-identical fed prefix.
            # Round-trip fix, layer 2 (divergence-diagnosed 2026-09-23): the
            # model's LAST generated token is a trailing newline (token id 13),
            # which the streamed text drops — the resent prefix then misses
            # exactly the final held token. Append it back.
            history.append({"role": "assistant",
                            "content": "<think>\n\n</think>\n\n" + r["text"] + "\n"})
            rec = {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "arm": arm,
                "turn": turn,
                "historyTokensApprox": sum(len(m["content"]) for m in history) // 4,
                "ttftSeconds": round(r["ttft"], 3) if r["ttft"] is not None else None,
                "wallSeconds": round(r["wall"], 3),
                "generatedTokens": r["generated"],
                "answer": r["text"][:300],
                "serverLog": str(log_path),
            }
            results[turn] = rec
            (OUT_DIR / f"{arm}_turn{turn}.json").write_text(
                json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  turn {turn}: ttft={r['ttft'] and round(r['ttft'],2)}s "
                  f"wall={r['wall']:.1f}s tok={r['generated']}", flush=True)
    finally:
        stop_server(proc)

    (OUT_DIR / f"summary_{arm}.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({t: {"ttft": v["ttftSeconds"], "wall": v["wallSeconds"]}
                      for t, v in results.items()}, indent=1))


if __name__ == "__main__":
    main()
