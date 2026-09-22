# Open Items

What the 2026-09-21 review could not close in-session, and how to close each item.

License note: everything this project needs is free — Colibrì (Apache-2.0),
model containers (Apache-2.0), CUDA Toolkit, VS 2022 Build Tools, MSYS2,
llama.cpp/Ollama, unsloth GGUF. No paid licenses required. Owner pre-approved
installs on 2026-09-21 subject to that.

## Install checklist (all free) — DONE 2026-09-21

- [x] CUDA Toolkit — installed: **13.4.1**, nvcc V13.4.59, compiles `sm_120`
- [x] VS 2022 Build Tools + C++ workload — turned out to be **already installed**
      (17.14.37502.11) with MSVC 14.44.35207 and Windows SDK 10.0.26100.0 —
      exactly the versions upstream validated. The winget failure (VS_EXIT=6)
      was its bootstrap *upgrade* step, cosmetic; the toolchain itself is intact
- [x] MSYS2 20260611 + `pacman`: make 4.4.1, mingw-w64 gcc 16.1.0
- [x] huggingface_hub CLI (pip)
- [ ] llama.cpp build or Ollama — decide at Phase 11; the GGUF repo is already pinned

End-to-end proof: `tools/toolchain_smoke.bat` (vcvars64 → cl compiles+runs →
nvcc compiles sm_120) — **NVCC_SMOKE_OK, 2026-09-21**. Re-run it after any
toolchain change.

## Blocked on a real engine run

- [x] gs64 vs v1.12.0 — FULLY CLOSED 2026-09-21 (runtime): banner
      `[qwen36] group-scaled experts: gs=64` printed on every load; doctor
      green (41 shards, 23.0 GB, RAM plan viable); real generation via the
      API returns correct coherent answers
- [x] CPU engine built: `qwen36.exe` (plus `colibri.exe` GLM-5.2 engine) and
      the `coli` launcher installed (`pip install -e C:\projects\colibri`).
      Build recipe: `C:\projects\colibri\build_cpu.bat [target]` (vcvars64 +
      mingw64\bin + usr\bin both on PATH)
- [x] OpenAI API smoke green: `coli serve` on :8000/v1, `/v1/models` →
      `qwen3.6-colibri`, chat completion correct (37+30 tokens, finish=stop)
- [ ] `tools/run_bench.py`: retarget from CLI-wrapper to the serve API
      (FN-004: `coli run` not wired for qwen36; API path is symmetric with
      llama-server for Phase 11). Parse TTFT/tok-s from serve logs or stream
      timings; wall time already trustworthy
- [x] expert hit rate in serve logs: self-test mode prints it (46.0% cold);
      the serve path does NOT log it (verified in the Phase 2 server log) —
      Gate D still lacks a serve-path metric source. Next: check `coli
      bench`, `PROF=1` or dashboard output before Phase 5
- [x] Phase 2 CPU baseline DONE (results/cpu/): warm decode 4.3-5.0 tok/s
      (below the 5 tok/s floor), prefill ~5 tok/s (p5 TTFT ~101 s warm),
      warm-process delta only ~7%. Decision weight moved to the CUDA tier
- [x] Phase 3 CUDA tier DONE (results/cuda/): build clean, `[CUDA] device 0`
      proof chain confirmed (needs `--auto-tier`, without it the server
      silently runs CPU!). Warm medians: decode 8.3-9.7 tok/s on long
      generations (1.9-2.15× over CPU), TTFT 1.7-2.3× faster, p5 wall 111→67 s.
      Thermals 44-54 °C / ≤44 W / ≤6.25 GB VRAM. Driver-13.1-vs-toolkit-13.4
      risk did not materialize. CPU binary kept as `qwen36_cpu.exe` for A/B.
- [x] Phase 4 placement/tune DONE (results/placement/): auto-placement =
  trunk-first (1207 MB lm_head+dnproj on GPU) + 4.25 GB / 2412 experts;
  tune winner OMP_NUM_THREADS=4 (+6%); tuned warm pass p2-p4 ≈ 11.1-11.3
  tok/s (Gate B "clearly useful" band, single-pass caveat); profile in
  AppData + repo copy; [TUNE] banner confirms pickup
- [x] Phase 6 KV-reuse SOLVED (2026-09-23): works through the public API
      with a client-side round-trip contract — assistant turn resent as
      `<think>\n\n</think>\n\n` + text + trailing `\n` (the streamed text
      drops the final newline token; the chat re-render drops the think
      marker). Follow-up TTFT 68 s → 2.75-3.04 s, `[PREFIX] reusing 96%`.
      Divergence-index diagnostic patch kept in the lab clone and exported
      to docs/patches/. Upstream issue candidates narrowed to two tiny,
      precisely evidenced defects (think-marker re-render; trailing token
      not streamed)
- [ ] FN-007: warm-persisted (HEAT_FILE) blocked upstream — launcher
      hard-kills the engine child on Windows; pick a workaround (direct
      engine run with SNAP+HEAT_FILE, or upstream patch CTRL_BREAK to child)
      before Phase 5
- [x] Gate D metric source found: tune profile JSON carries hit_pct per
      sample (results/placement/tune_profile.json) — use tune-mode samples
      for hit-rate evidence until serve exposes it
- [ ] warm-pass variance watch: CUDA warm pass 2 dipped to 4.6-6.9 tok/s
      (passes 1/3 were 5.6-11.7) — if it repeats in later phases, capture
      per-request GPU/CPU util and tier state to explain it
- [ ] p5 long-context TTFT remains ~1 min median on CUDA (high variance
      32-64 s) — the KV-reuse phase (Phase 6) is the lever that matters
- [ ] FN-006: 10 deterministic U+FFFD chars per ~1370 chars of Ukrainian
      output (English clean) — reproduce in non-stream mode to split
      tokenizer vs streaming blame; Phase 10 screen item
- [x] expert-kernel env for qwen36 — CORRECTED (R-002, source-verified):
      `IDOT_GS` is GLM-engine-only (`c/colibri.c:1101`); `qwen36.c` reads
      `QWEN_EXPERT_KERNEL` (`c/qwen36.c:998`) and its fast planar-int4 kernel
      is ON by default. Nothing to set for benchmarks; `=0` is the A/B knob
- [x] engine binary name — resolved (with a twist, FN-003): per-family engine
      binaries; ours is **`qwen36.exe`** (`colibri.exe` = the GLM-5.2 engine
      that windows.md describes). Plan Phase 3 build command stands as
      `make qwen36.exe CUDA_DLL=1 ARCH=native`; Windows CUDA only via
      `CUDA_DLL=1`

## Phase 3 build watch-items (from upstream docs/windows.md, 2026-09-21)

- [ ] CUDA runtime pairing: toolkit 13.4.1 vs driver 592.82 (reports CUDA
      13.1). Compilation for sm_120 is verified (NVCC_SMOKE_OK); minor-version
      compatibility should cover runtime, but if the first GPU run fails with
      a driver-version error → update the GPU driver or pin the toolkit to
      13.1/12.8 and rebuild
- [ ] Smart App Control can block self-compiled binaries — check it is off
      (needs reboot to change)
- [ ] build must run where `cl.exe` resolves to the x64 MSVC compiler
      (vcvars64 / x64 Native Tools Prompt); the 32-bit prompt fails nvcc
- [x] build from a git clone, not the release zip — cloned to
      `C:\projects\colibri`, `v1.12.0` pinned, SHA
      `dcd73832f293750086643e1f0ccd2cd6d067259c`
- [x] engine binary name: unified `colibri.exe` in v1.12.0 (plan updated)
- [ ] first GPU run must print `[CUDA] device 0:` + a resident set with
      nonzero tensor count — that is the proof CUDA is active
- [ ] shells started before the CUDA install do not see nvcc on PATH — build
      in a fresh shell (the smoke script sets the path explicitly as a fallback)

## Blocked on downloads (Phase 1)

- [x] colibri v1.12.0 clone + commit SHA recorded — `C:\projects\colibri`,
      `dcd73832f293750086643e1f0ccd2cd6d067259c`
- [x] 22 GB gs64 container → `C:\Models\qwen36_i4_gs64` — DONE 2026-09-21,
      artifact-verified: 22 GB, 46 files, `qwen36_meta.json` reports
      `expert_gs = 64`. Remaining runtime checks after the engine is built:
      `doctor --deep` + the `[qwen36] group-scaled experts: gs=64` banner
- [x] ~20 GB comparison GGUF — DONE 2026-09-21: single file
      `C:\Models\qwen36_Q4_K_M\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf`, 21 GB.
      NOTE: it is Unsloth's **UD**-Q4_K_M (dynamic quant), not vanilla Q4_K_M —
      record in Phase 11 comparisons. Runner of choice: llama.cpp prebuilt
      CUDA binaries (metrics map cleanly: prompt-eval → TTFT, eval-rate →
      tok/s; same OpenAI-API harness as coli serve)
- [x] CPU build of `colibri.exe` — DONE (plus `qwen36.exe` and the `coli`
      launcher; see the engine-run section above)

## Deliberately not done

- CI, issue templates, dashboards, containers, any heavier process — add
  when a repeated pain shows up, not before (reasoning in LOG.md, 2026-09-21)
- G: drive (4 GB free) ignored — too small to matter
- No benchmark data exists yet: all gates A-E are open
