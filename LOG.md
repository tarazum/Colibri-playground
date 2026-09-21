# Experiment Journal

Append-only. One entry per session. Facts and numbers only — verdicts live in
`docs/final_results.md`, open questions in `docs/open_items.md`.

## 2026-09-21 — review + groundwork (pre-Phase 0)

- Reviewed README + experiment plan against upstream (JustVugg/colibri) and
  the HF model card. External facts check out; v1.12.0 is the current release.
- The `gs64-ab` branch conflict from the HF card looks stale: release notes
  say gs64 containers are supported since v1.7.0 (and recommended). Runtime
  verification added as plan 4.1.1; fallback container identified
  (`Kreuzzelg/qwen36-35b-a3b-colibri-i4`).
- Upstream calibration found: the "1.44 → 10.05 tok/s (7.0×)" CUDA figure was
  measured on TWO 8 GB cards; `IDOT_GS=1` opt-in flag affects gs64 kernels.
  Both noted in the plan (Phase 3).
- Machine snapshot captured → `results/environment.json`. Key facts: this IS
  the target laptop (HP OMEN MAX 16, Ryzen AI 7 350 8C/16T, 64 GB RAM, RTX
  5070 8 GB, driver 592.82/CUDA 13.1-capable, on AC power). CUDA Toolkit NOT
  installed (no nvcc). Single DRAM-less KIOXIA 1 TB NVMe shared with OS; no
  D: drive (plan paths changed to `C:\Models`); C: 501 GB free; G: 4 GB free.
- Added: `prompts/` (p1-p5 fixed prompts + README), `tools/run_bench.py`
  (runner with stub metric parser), `results/` skeleton, this journal,
  `docs/open_items.md` with the free-licensed install checklist.
- Owner confirmed installs are fine if nothing requires paid licenses —
  nothing does.
- Nothing installed or downloaded yet; no benchmark data yet.

## 2026-09-21 (evening) — toolchain installed and smoke-verified

- Installed per checklist: CUDA Toolkit **13.4.1** (nvcc V13.4.59), MSYS2
  20260611 (make 4.4.1, mingw-w64 gcc 16.1.0), huggingface_hub CLI.
- Plot twist: VS Build Tools 17.14 with the C++ workload were **already
  installed** (MSVC 14.44.35207 + Win SDK 10.0.26100.0 — exactly the versions
  upstream validated). winget's VS_EXIT=6 was its bootstrap-upgrade step
  failing, cosmetic; vswhere + a real compile proved the toolchain complete.
- End-to-end smoke green: `tools/toolchain_smoke.bat` → vcvars64 → cl
  compiles+runs hello.c → nvcc compiles trivial.cu for `sm_120`
  (NVCC_SMOKE_OK).
- Phase 3 watch-items recorded in `docs/open_items.md`: toolkit 13.4 vs
  driver-reported 13.1 runtime pairing, Smart App Control, build from git
  clone only, engine binary name (`colibri.exe` vs plan's `qwen36.exe`).
- Lessons (same-day): (1) Git Bash mangles quotes/backslashes for cmd/vcvars —
  use a temp .bat with direct paths (same rule as IDENN AGENTS.md); (2) verify
  by artifact, not by installer exit code; (3) shells opened before an install
  keep the stale PATH.

## 2026-09-21 (night) — Phase 0 executed: clone + source verification + download started

- Cloned upstream to `C:\projects\colibri`, pinned `v1.12.0`, SHA
  `dcd73832f293750086643e1f0ccd2cd6d067259c`.
- Source-level verification (better than release notes):
  - `c/qwen36.c` natively supports gs64 containers: reads `expert_gs` from
    `qwen36_meta.json`, grouped-scale expert GEMV (`matmul_q_gs`), banner
    `[qwen36] group-scaled experts: gs=N`. HF card's `gs64-ab` note is stale.
    Open item 4.1.1 closed (runtime `doctor --deep` stays as final check).
  - `IDOT_GS` is an opt-in ENV VAR in v1.12.0 (`c/colibri.c`, default off) —
    must be set for gs64 integer kernels during benchmarks.
  - Engine is one unified `colibri.exe` (`all: colibri$(EXE)`); plan's
    `qwen36.exe` corrected. Windows CUDA = `CUDA_DLL=1` only; Makefile stamps
    `.build-config` against fake-CUDA "up to date" binaries.
- 22 GB gs64 container download started in background →
  `C:\Models\qwen36_i4_gs64` (verify size + banner + doctor on completion).
- Nothing committed to git yet (owner has not asked).

## 2026-09-21 (decisions) — AGENTS.md adopted, push approved, GGUF queued

- Owner decisions: (1) adopt the IDENN-style session rules → `AGENTS.md`
  created (evidence discipline + session continuity core; production half
  excluded until a KEEP verdict); (2) commit + push to origin; (3) downloads
  run sequentially — model first, comparison GGUF after.
- `docs/FINDINGS.md` created (FN-NNN journal, OB-NNN analog); first two cases
  logged (stale HF card, cosmetic winget VS failure).
- GGUF download command pinned in open_items (Q4_K_M only via `--include` —
  the unsloth repo holds 200+ GB of all quants); runner choice: llama.cpp
  prebuilt CUDA binaries.
