# Upstream issue — FILED 2026-09-23 (body preserved for the record)

---

**Title:** qwen36 engine never saves HEAT_FILE under `coli serve` (all platforms; teardown is atexit-only, every stop path is a hard kill)

**Environment:** v1.12.0 (dcd73832f293750086643e1f0ccd2cd6d067259c), Windows 11 26200; Qwen3.6-35B-A3B int4-gs64, CUDA tier (`make qwen36.exe CUDA_DLL=1`), RTX 5070 Laptop 8 GB. Code inspection says POSIX is affected the same way.

**What happens:** the engine's heat save (`qt_shutdown` writing HEAT_FILE, `c/qwen36_tier.c:1142-1150`, banner `[qtier] HEAT_FILE saved`) is registered only via `atexit` (`c/qwen36.c:3478`). No signal handler exists in qwen36 (the `g_shutdown`/`term_sig` machinery is GLM-engine-only, `c/colibri.c:7617-7649`, and POSIX-only), so any hard stop skips the save — and every launcher stop path is a hard stop:

- `Engine.close` (`c/openai_server.py:3373`) uses `terminate()`/`kill()` — the serve path's normal shutdown, also reached from the launcher SIGTERM handler;
- `coli stop` additionally TerminateProcesses the engine pid directly (`c/coli:2248-2264`).

On Windows there is also no way to reach a graceful exit from outside: `os.kill(pid, SIGTERM)` is TerminateProcess (bypasses the SIGTERM handler), and an unhandled CTRL_BREAK/SIGBREAK kills the serve loop before its `finally` can clean up.

Net effect: warm-start persistence (HEAT_FILE) never happens under `coli serve`, on any platform.

**Reproduced on Windows** (from outside the engine): `Popen.terminate()` → no save banner, no heat file. `CTRL_BREAK_EVENT` + `CREATE_NEW_PROCESS_GROUP` → launcher dies without cleanup, engine hard-killed (job object), no save. Logs available.

**Expected:** stopping `coli serve` lets the engine reach its atexit teardown so HEAT_FILE is saved, on all platforms.

**Fix (validation numbers below):** the engine's serve loop reads requests from stdin (`serve_read_req` → `fgets`, `c/qwen36.c:2906`); EOF returns the loop, `main` returns, `atexit` runs, HEAT_FILE is saved. So:

1. `Engine.close`: close the engine's stdin and wait a generous drain window (`COLI_ENGINE_DRAIN_S`, default 30 s — EOF only lands between turns) before the existing terminate/kill ladder;
2. `serve()`: on Windows also handle SIGBREAK — CTRL_BREAK is the one console signal a controller can target at the serve process group, and without a handler it kills the loop before the finally;
3. `Engine.__init__`: spawn the engine in its own process group on Windows so the group-targeted CTRL_BREAK cannot kill it before the drain lands;
4. `coli stop`: stop launchers first and give them the drain window before touching engine pids.

**Validation (Windows, RTX 5070 Laptop, same 5-prompt workload):** before the fix, no heat file after any shutdown; after it — `[qtier] HEAT_FILE saved` on every stop, `[qtier] HEAT_FILE loaded` on restart, and the warm-persisted pass beats the same-process warm pass (decode 10.1-11.0 → 12.1-15.0 tok/s; long-context TTFT 43.9 → 26.6 s). Unit tests for the shutdown handshake included (`c/tests/test_engine_close_drain.py`).

Known remaining gap (out of scope here): `coli stop` from another console still cannot deliver a graceful stop on Windows — os.kill/GenerateConsoleCtrlEvent cannot target an unrelated console; that needs a control channel (HTTP endpoint or file flag).

PR against `dev` follows.
