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

- [x] gs64 vs v1.12.0 — RESOLVED at source level 2026-09-21: `c/qwen36.c` in
      the cloned v1.12.0 natively supports `expert_gs` containers (banner
      `[qwen36] group-scaled experts: gs=N` at load). The HF card's
      `gs64-ab` note is stale. Runtime `doctor --deep` after download stays as
      a cheap final confirmation; fallback container unchanged
      (`Kreuzzelg/qwen36-35b-a3b-colibri-i4`)
- [ ] `tools/run_bench.py` `parse_output()`: regexes are guesses; finish them
      against a real `coli` log before citing any parsed number (wall time is
      measured by the script itself and is trustworthy now)
- [ ] expert hit rate: confirm where the engine logs/exposes it (plan 4.5);
      Gate D depends on it
- [x] `IDOT_GS` in v1.12.0 — confirmed OPT-IN via environment variable
      (`c/colibri.c`: default off, `IDOT_GS=1` enables grouped planar IDOT for
      gs64 tensors). Set it for benchmark runs
- [x] engine binary name — resolved: unified `colibri.exe` in v1.12.0
      (`all: colibri$(EXE)`; plan updated). Windows CUDA path must use
      `CUDA_DLL=1`, never `CUDA=1`

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
- [ ] 22 GB gs64 container to `C:\Models\qwen36_i4_gs64` — download RUNNING
      since 2026-09-21 (background); verify size + `doctor --deep` + the
      `[qwen36] group-scaled experts: gs=64` banner when it finishes
- [ ] ~20 GB comparison GGUF (`unsloth/Qwen3.6-35B-A3B-GGUF`, Q4_K_M only) —
      QUEUED after the model finishes (owner decision 2026-09-21: sequential
      downloads). Download ONLY the Q4_K_M file(s): the repo holds all quants,
      200+ GB total — use `hf download unsloth/Qwen3.6-35B-A3B-GGUF
      --include "*Q4_K_M*" --local-dir C:/Models/qwen36_Q4_K_M`. Runner of
      choice: llama.cpp prebuilt CUDA binaries (metrics map cleanly:
      prompt-eval → TTFT, eval-rate → tok/s)

## Deliberately not done

- CI, issue templates, dashboards, containers, any heavier process — add
  when a repeated pain shows up, not before (reasoning in LOG.md, 2026-09-21)
- G: drive (4 GB free) ignored — too small to matter
- No benchmark data exists yet: all gates A-E are open
