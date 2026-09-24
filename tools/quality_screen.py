#!/usr/bin/env python3
"""Phase 10 — quality sanity screen for the chosen quantization.

Runs a fixed 6-task battery (C# reasoning, SQL, Python debugging,
Ukrainian instruction-following, constrained English, structured JSON)
against a server, temperature=0, saves transcripts, applies the automatic
checks it can (JSON validity, constraint compliance) and leaves semantic
review to the operator. For the colibri engine it also reruns p4
non-streamed to split FN-006 (U+FFFD) between tokenizer and streaming.

Engines:
  python tools/quality_screen.py --engine colibri
  python tools/quality_screen.py --engine llama
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_ROOT = REPO / "results" / "quality"
GGUF = "C:/Models/qwen36_Q4_K_M/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
LLAMA = "C:/Tools/llamacpp/bin/llama-server.exe"
COLI_MODEL = "C:/Models/qwen36_i4_gs64"


def start(engine: str, log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8", errors="replace")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    if engine == "colibri":
        cmd = ["coli", "serve", "--auto-tier", "--model", COLI_MODEL]
    else:
        cmd = [LLAMA, "-m", GGUF, "--host", "127.0.0.1", "--port", "8010",
               "-c", "8192", "-t", "4", "-ngl", "99", "--cpu-moe"]
    return subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=flags)


def wait_ready(base: str, proc) -> str:
    deadline = time.time() + 240
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit(f"[server] died during startup (exit {proc.returncode})")
        try:
            with urllib.request.urlopen(f"{base}/models", timeout=5) as r:
                return json.load(r)["data"][0]["id"]
        except Exception:
            time.sleep(2)
    sys.exit("[server] not ready in time")


def stop(proc):
    if proc is None:
        return
    if sys.platform == "win32":
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            proc.wait(timeout=40)
        except Exception:
            proc.terminate()
    else:
        proc.terminate()


def chat(base, model_id, prompt, max_tokens, stream=True):
    body = {"model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": max_tokens, "stream": stream,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"{base}/chat/completions",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    parts: list[str] = []
    with urllib.request.urlopen(req, timeout=900) as r:
        if not stream:
            data = json.load(r)
            return data["choices"][0]["message"].get("content") or ""
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
            piece = delta.get("content") or delta.get("reasoning_content")
            if piece:
                parts.append(piece)
    return "".join(parts)


def auto_check(task: dict, text: str) -> list[str]:
    issues = []
    tid = task["id"]
    if tid == "q4":
        lines = [l for l in text.strip().splitlines() if l.strip()]
        if not (2 <= len(lines) <= 4) or sum(1 for l in lines if l.strip().startswith(("-", "*", "•"))) < 3:
            issues.append(f"bullet-list shape: {len(lines)} lines")
        for w in ("функці", "програм"):
            if w in text.lower():
                issues.append(f"forbidden word: {w}")
    if tid == "q5":
        sents = [s for s in text.replace("7", "").split(".") if s.strip()]
        if len(sents) != 2:
            issues.append(f"sentence count {len(sents)} != 2")
        if "index" not in text.lower():
            issues.append("missing 'index'")
        if "table" in text.lower():
            issues.append("forbidden 'table'")
        if not text.rstrip().endswith("7"):
            issues.append("does not end with 7")
    if tid == "q6":
        try:
            obj = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
            for f in ("engine", "supports_cuda", "max_context", "alternatives"):
                if f not in obj:
                    issues.append(f"json missing field {f}")
        except ValueError:
            issues.append("output is not valid JSON")
    return issues


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=("colibri", "llama"), required=True)
    args = ap.parse_args()
    out_dir = OUT_ROOT / args.engine
    out_dir.mkdir(parents=True, exist_ok=True)
    base = ("http://127.0.0.1:8000/v1" if args.engine == "colibri"
            else "http://127.0.0.1:8010/v1")

    battery = json.loads((REPO / "prompts" / "quality_battery.json")
                         .read_text(encoding="utf-8"))["tasks"]
    proc = start(args.engine, out_dir / "logs" / "server.log")
    results = []
    try:
        model_id = wait_ready(base, proc)
        print(f"[server] ready ({args.engine})", flush=True)
        for task in battery:
            text = chat(base, model_id, task["prompt"], task["max_tokens"])
            (out_dir / f"{task['id']}.txt").write_text(text, encoding="utf-8")
            issues = auto_check(task, text)
            results.append({"id": task["id"], "kind": task["kind"],
                            "autoIssues": issues, "chars": len(text),
                            "ufffd": text.count("\ufffd")})
            print(f"  [{task['id']}] {task['kind']}: {len(text)} chars, "
                  f"U+FFFD={text.count(chr(0xFFFD))}, auto-issues={issues}",
                  flush=True)
        if args.engine == "colibri":
            p4 = (REPO / "prompts" / "p4_ukrainian.txt").read_text(encoding="utf-8")
            nonstream = chat(base, model_id, p4, 450, stream=False)
            (out_dir / "p4_nonstream.txt").write_text(nonstream, encoding="utf-8")
            n = nonstream.count("\ufffd")
            print(f"  [FN-006] p4 NON-STREAM: U+FFFD count = {n}", flush=True)
            results.append({"id": "fn006-nonstream", "ufffd": n})
    finally:
        stop(proc)

    (out_dir / "screen_results.json").write_text(
        json.dumps({"engine": args.engine,
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
