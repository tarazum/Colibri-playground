#!/usr/bin/env python3
"""Benchmark harness v2: persistent `coli serve` + OpenAI-compatible HTTP.

Supersedes tools/run_bench.py (per-sample CLI spawning destroyed warm-cache
semantics; coli chat has no --prompt-file — see docs/review-2026-09-21.md
R-003 and docs/FINDINGS.md FN-004).

Protocol (docs/experiment_plan.md, "Benchmark protocol R-004"):
- one COLD pass in a fresh server process (p1-p5 once each)
- N WARM passes on the same running server (default 3)
- every request: explicit temperature=0, fixed max_tokens per prompt
- every result JSON carries an explicit state tag

Timing is client-side and honest about method:
- wallSeconds        — full request time (always trustworthy)
- ttftSeconds        — time to first streamed content chunk (None if the
                      server forced a non-streaming fallback)
- decodeTokensPerSecond — (generatedTokens-1)/(wall-ttft); generatedTokens
                      comes from usage.completion_tokens when the server
                      reports it, else chunk count (each SSE delta ~= 1 token)
- note "cold" means cold PROCESS: the OS page cache may already hold the
  model files, which is recorded but not controlled

Usage:
    python tools/bench_serve.py                       # manages its own server
    python tools/bench_serve.py --base-url http://127.0.0.1:8000/v1
                                                       # reuse a running server
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
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO / "prompts"

# prompt id -> (filename, max_tokens) — fixed caps keep runs comparable
PROMPT_SPECS = [
    ("p1", "p1_short_factual.txt", 60),
    ("p2", "p2_explanation.txt", 500),
    ("p3", "p3_code.txt", 700),
    ("p4", "p4_ukrainian.txt", 450),
    ("p5", "p5_long_prompt_short_answer.txt", 80),
]

COLIBRI_VERSION = "v1.12.0"
COLIBRI_COMMIT = "dcd73832f293750086643e1f0ccd2cd6d067259c"


def load_prompts() -> list[dict]:
    out = []
    for pid, fname, max_tokens in PROMPT_SPECS:
        text = (PROMPTS_DIR / fname).read_text(encoding="utf-8")
        out.append({"id": pid, "file": fname, "text": text, "max_tokens": max_tokens})
    return out


class Server:
    """Owns the coli serve subprocess (or reuses an existing one)."""

    def __init__(self, model: str, base_url: str | None, log_path: Path,
                 heat_file: str | None = None, auto_tier: bool = False):
        self.model = model
        self.external = base_url is not None
        self.base = (base_url or "http://127.0.0.1:8000/v1").rstrip("/")
        self.proc: subprocess.Popen | None = None
        self.log_path = log_path
        self.heat_file = heat_file
        self.auto_tier = auto_tier
        self.starts = 0
        self.saved_heat = None  # None = not attempted/unknown

    def start(self) -> None:
        if self.external:
            print(f"[server] reusing {self.base}", flush=True)
            return
        self.starts += 1
        log_path = self.log_path if self.starts == 1 else \
            self.log_path.with_name(f"{self.log_path.stem}_{self.starts}.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = open(log_path, "a", encoding="utf-8", errors="replace")
        env = None
        if self.heat_file:
            env = {**__import__("os").environ, "HEAT_FILE": self.heat_file}
            print(f"[server] HEAT_FILE={self.heat_file}", flush=True)
        cmd = ["coli", "serve", "--model", self.model]
        if self.auto_tier:
            cmd.append("--auto-tier")
        # own process group so CTRL_BREAK reaches the launcher (and its engine
        # child) for a graceful shutdown — the only path that saves HEAT_FILE;
        # Popen.terminate() on Windows is TerminateProcess (hard kill, no save)
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        self.proc = subprocess.Popen(
            cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
            creationflags=flags,
        )
        print(f"[server] started pid={self.proc.pid}, log={log_path}", flush=True)

    def wait_ready(self, timeout_s: int = 180) -> str:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                sys.exit(f"[server] died during startup (exit {self.proc.returncode}); see {self.log_path}")
            try:
                with urllib.request.urlopen(f"{self.base}/models", timeout=5) as r:
                    models = json.load(r)
                mid = models["data"][0]["id"]
                print(f"[server] ready, model id = {mid}", flush=True)
                return mid
            except (urllib.error.URLError, OSError, ValueError, KeyError):
                time.sleep(2)
        sys.exit("[server] not ready within timeout")

    def stop(self) -> None:
        if self.proc is None:
            return
        # graceful first: CTRL_BREAK -> launcher shuts down -> engine teardown
        # saves HEAT_FILE; only then hard-kill as a fallback
        if sys.platform == "win32":
            try:
                self.proc.send_signal(signal.CTRL_BREAK_EVENT)
                self.proc.wait(timeout=30)
                print("[server] stopped via CTRL_BREAK", flush=True)
            except (subprocess.TimeoutExpired, OSError):
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=20)
                    print("[server] stopped via terminate fallback", flush=True)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    print("[server] killed", flush=True)
        else:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
                print("[server] stopped cleanly", flush=True)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                print("[server] killed", flush=True)
        self.proc = None
        if self.heat_file:
            name = self.log_path.name if self.starts == 1 else \
                f"{self.log_path.stem}_{self.starts}.log"
            try:
                text = (self.log_path.parent / name).read_text(
                    encoding="utf-8", errors="replace")
                self.saved_heat = "HEAT_FILE saved" in text[-8000:]
            except OSError:
                self.saved_heat = False
            print(f"[server] heat saved: {self.saved_heat}", flush=True)


def one_request(base: str, model_id: str, prompt: dict, timeout_s: int) -> dict:
    """One streaming chat completion; returns measured metrics + raw text."""
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt["text"]}],
        "temperature": 0,
        "max_tokens": prompt["max_tokens"],
        "stream": True,
        "stream_options": {"include_usage": True},
        # Qwen3.6 is a hybrid reasoner: llama.cpp streams its output as
        # reasoning_content unless thinking is disabled in the template.
        # colibri runs its own thinking-off path server-side and ignores
        # this kwarg; the parser also falls back to reasoning_content.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    url = f"{base}/chat/completions"
    started = time.perf_counter()
    ttft = None
    chunks = 0
    usage = None
    parts: list[str] = []
    fallback = False

    def send(payload: dict):
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        return urllib.request.urlopen(req, timeout=timeout_s)

    try:
        resp = send(body)
    except urllib.error.HTTPError as e:
        # server may reject stream_options — retry without it, then unstreamed
        if e.code == 400:
            body.pop("stream_options")
            try:
                resp = send(body)
            except urllib.error.HTTPError:
                body["stream"] = False
                resp = send(body)
                fallback = True
        else:
            raise

    if fallback:
        data = json.load(resp)
        wall = time.perf_counter() - started
        usage = data.get("usage")
        parts.append(data["choices"][0]["message"].get("content") or "")
    else:
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
            if obj.get("usage"):
                usage = obj["usage"]
            delta = (obj.get("choices") or [{}])[0].get("delta", {})
            content = delta.get("content") or delta.get("reasoning_content")
            if content:
                if ttft is None:
                    ttft = time.perf_counter() - started
                chunks += 1
                parts.append(content)
        wall = time.perf_counter() - started

    generated = None
    if usage and isinstance(usage.get("completion_tokens"), int):
        generated = usage["completion_tokens"]
    elif fallback:
        generated = None
    else:
        generated = chunks
    decode = None
    if ttft is not None and generated and generated > 1 and wall > ttft:
        decode = (generated - 1) / (wall - ttft)

    notes = []
    if fallback:
        notes.append("non-stream fallback: no client-side TTFT")
    if usage is None:
        notes.append("no usage frame: generated=chunk count (approx)")
    return {
        "text": "".join(parts),
        "wall": wall, "ttft": ttft, "generated": generated,
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
        "decode": decode, "notes": notes,
    }


def record(out_dir: Path, state: str, prompt: dict, r: dict, mode: str, model: str) -> dict:
    rec = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "colibriVersion": COLIBRI_VERSION,
        "colibriCommit": COLIBRI_COMMIT,
        "model": model,
        "modelRevision": None,
        "mode": mode,
        "state": state,
        "promptId": prompt["id"],
        "promptTokens": r["prompt_tokens"],
        "generatedTokens": r["generated"],
        "ttftSeconds": round(r["ttft"], 3) if r["ttft"] is not None else None,
        "decodeTokensPerSecond": round(r["decode"], 3) if r["decode"] is not None else None,
        "wallSeconds": round(r["wall"], 3),
        "ramPeakGb": None,
        "vramPeakGb": None,
        "expertHitRate": None,
        "notes": ("; ".join(r["notes"]) + ("" if state != "cold" else
                   "; cold = cold PROCESS, OS page cache may be warm")).strip("; "),
    }
    path = out_dir / f"{prompt['id']}_{state}_{datetime.now().strftime('%H%M%S')}.json"
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "transcripts").mkdir(exist_ok=True)
    (out_dir / "transcripts" / f"{prompt['id']}_{state}.txt").write_text(
        r["text"], encoding="utf-8")
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="C:/Models/qwen36_i4_gs64")
    ap.add_argument("--base-url", default=None, help="reuse a running server instead of managing one")
    ap.add_argument("--mode", default="cpu")
    ap.add_argument("--warm-passes", type=int, default=3)
    ap.add_argument("--heat-file", default=None,
                    help="enable the warm-persisted pass: server runs with "
                         "HEAT_FILE=<path>, clean stop saves heat, restart "
                         "reloads it (CUDA arm only)")
    ap.add_argument("--auto-tier", action="store_true",
                    help="pass --auto-tier to coli serve (engages the CUDA "
                         "VRAM expert tier; without it the server silently "
                         "runs the CPU path)")
    ap.add_argument("--states", default="cold,warm,persisted",
                    help="comma subset of cold,warm,persisted "
                         "(persisted requires --heat-file)")
    ap.add_argument("--prompts", default=None,
                    help="comma list of prompt ids to run, e.g. p1,p5")
    ap.add_argument("--out", default=None, help="output dir (default results/<mode>)")
    ap.add_argument("--request-timeout", type=int, default=900)
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else REPO / "results" / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts = load_prompts()

    server = Server(args.model, args.base_url, out_dir / "logs" / "server.log",
                    heat_file=args.heat_file, auto_tier=args.auto_tier)
    t0 = time.time()
    server.start()
    model_id = server.wait_ready()

    states = {s.strip().lower() for s in args.states.split(",") if s.strip()}
    if "persisted" in states and not args.heat_file:
        sys.exit("--states persisted requires --heat-file")
    if args.prompts:
        keep = {s.strip().lower() for s in args.prompts.split(",")}
        prompts = [p for p in prompts if p["id"] in keep]
    warm_count = args.warm_passes if "warm" in states else \
        (1 if "persisted" in states else 0)

    def show(pid: str, r: dict) -> None:
        print(f"  [{pid}] wall={r['wall']:.1f}s ttft="
              f"{r['ttft'] if r['ttft'] is None else round(r['ttft'],2)}s "
              f"tok={r['generated']} tok/s={r['decode'] and round(r['decode'],2)}",
              flush=True)

    runs: list[dict] = []
    try:
        if "cold" in states:
            print(f"=== COLD pass (fresh process, {len(prompts)} prompts) ===",
                  flush=True)
            for p in prompts:
                r = one_request(server.base, model_id, p, args.request_timeout)
                runs.append(record(out_dir, "cold", p, r, args.mode, args.model))
                show(p["id"], r)
        for i in range(1, warm_count + 1):
            recording = "warm" in states
            label = f"WARM pass {i}/{warm_count}" + \
                ("" if recording else " (unrecorded warmup for persisted)")
            print(f"=== {label} ===", flush=True)
            for p in prompts:
                r = one_request(server.base, model_id, p, args.request_timeout)
                if recording:
                    runs.append(record(out_dir, "warm-process", p, r, args.mode, args.model))
                show(p["id"], r)
        if "persisted" in states:
            print("=== WARM-PERSISTED: clean stop (HEAT_FILE save), restart, rerun ===",
                  flush=True)
            server.stop()
            if not server.saved_heat:
                print("[warn] HEAT_FILE save not confirmed in log; "
                      "persisted samples may be meaningless", flush=True)
            server.start()
            model_id = server.wait_ready()
            for p in prompts:
                r = one_request(server.base, model_id, p, args.request_timeout)
                rec = record(out_dir, "warm-persisted", p, r, args.mode, args.model)
                if server.saved_heat is False:
                    rec["notes"] = (rec["notes"] + "; HEAT_FILE save NOT confirmed").strip("; ")
                runs.append(rec)
                show(p["id"], r)
    finally:
        server.stop()

    summary = {}
    for p in prompts:
        cold = [x for x in runs if x["promptId"] == p["id"] and x["state"] == "cold"]
        warm = [x for x in runs if x["promptId"] == p["id"] and x["state"] == "warm-process"]
        pers = [x for x in runs if x["promptId"] == p["id"] and x["state"] == "warm-persisted"]
        walls = [x["wallSeconds"] for x in warm]
        decs = [x["decodeTokensPerSecond"] for x in warm if x["decodeTokensPerSecond"]]
        ttfts = [x["ttftSeconds"] for x in warm if x["ttftSeconds"] is not None]
        summary[p["id"]] = {
            "cold": cold[0] if cold else None,
            "warmSamples": len(warm),
            "wallSecondsMedian": round(statistics.median(walls), 3) if walls else None,
            "decodeTokensPerSecondMedian": round(statistics.median(decs), 3) if decs else None,
            "ttftSecondsMedian": round(statistics.median(ttfts), 3) if ttfts else None,
            "warmPersisted": pers[0] if pers else None,
        }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"total {time.time()-t0:.0f}s; results in {out_dir}", flush=True)


if __name__ == "__main__":
    main()
