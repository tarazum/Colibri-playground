# Upstream issue draft — FN-007 (not yet filed)

Repo: JustVugg/colibri · target: GitHub Issue (bug template) · prepared 2026-09-23

---

**Title:** Windows: `coli serve` never saves HEAT_FILE — the launcher
hard-kills the engine child on shutdown

**Environment:** v1.12.0 (commit dcd73832f293750086643e1f0ccd2cd6d067259c),
Windows 11 26200, Qwen3.6-35B-A3B int4-gs64 container, CUDA tier
(qwen36.exe CUDA_DLL=1), RTX 5070 Laptop.

**What happens:** the engine's heat-save teardown never runs when the
server is stopped through `coli serve`, so `HEAT_FILE` (warm-start
persistence, `qwen36_tier.c` save path around lines 1142-1150, banner
`[qtier] HEAT_FILE saved`) is never written. The feature is effectively
dead on Windows.

**Why:** the engine child is stopped via terminate()/`os.kill(pid,
SIGTERM)` — on Windows both are TerminateProcess (the code's own comment
at `c/coli` line ~2263 notes this: "os.kill(SIGTERM) is TerminateProcess
on Windows anyway"). The C engine has no chance to run its teardown.
`env_for_engine` correctly passes HEAT_FILE through (`os.environ.copy()`),
so the environment variable reaches the engine — only the shutdown signal
does not.

**Reproduced twice, from outside the engine:**
1. `Popen.terminate()` on `coli serve` → no `[qtier] HEAT_FILE saved`, no
   heat file on disk.
2. `CTRL_BREAK_EVENT` with `CREATE_NEW_PROCESS_GROUP` → the Python
   launcher shuts down gracefully, the engine child is still killed hard;
   no save banner, no file.

Logs available on request (serve logs with `[qtier] dev 0: budget...`,
`[qtier] CUDA VRAM expert tier active`, clean shutdown, no save).

**Expected:** stopping `coli serve` on Windows lets the engine child run
its teardown so HEAT_FILE is saved (and `[qtier] HEAT_FILE saved` appears
in the log), matching the POSIX behavior.

**Suggested fix direction:** on Windows, before terminate(), signal the
ENGINE child directly with `CTRL_BREAK_EVENT` (spawned with
`CREATE_NEW_PROCESS_GROUP`), wait briefly for the save banner/log, then
fall back to the current hard kill.

---

Sibling candidates from the same evaluation, filed separately if welcome:
- brio `normalize="mean"` default is token-count biased (multi-token
  options systematically win; all 30 of our test cases answered DENY under
  mean, correct under sum)
- KV prefix reuse cannot round-trip through the public API (chat re-render
  drops the fed `<think>` marker; the streamed text drops the final
  generated newline token)
