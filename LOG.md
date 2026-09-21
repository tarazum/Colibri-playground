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

## 2026-09-21 (late night) — model verified, GGUF running, CPU build running

- Model download finished (~8 min). Artifact-verified: 22 GB, 46 files,
  `qwen36_meta.json` → `expert_gs = 64`. Final runtime checks (doctor --deep +
  gs=64 banner) deferred until the engine binary exists.
- Per owner queue: Q4_K_M GGUF download started (only Q4_K_M files via
  `--include`).
- CPU `colibri.exe` build started from the pinned source
  (`C:\projects\colibri\build_cpu.bat`: vcvars64 + MSYS2 make).
- Commits `ff99798` (groundwork + Phase 0) and `71095fa` (AGENTS.md +
  FINDINGS.md) pushed to origin/main.
- Build lesson (first CPU build attempt): `make` failed with `gcc: No such
  file or directory` — MSYS2's make lives in `usr\bin` but gcc in
  `mingw64\bin`; BOTH belong on PATH. And the wrapping bash pipeline reported
  success because `tail` was the last command — exit codes of pipes lie the
  same way installer codes do. Fixed in `build_cpu.bat` (`|| exit /b` +
  build log); retry running.

## 2026-09-21 (small hours) — FIRST ENGINE NUMBERS (smoke, not a benchmark)

- Engines built from source: `qwen36.exe` 1.1 MB (CPU) + `colibri.exe` 1.4 MB
  (GLM-5.2 reference); `coli` launcher installed via `pip install -e`.
  FN-003: per-family binaries — windows.md's `colibri.exe` is the GLM-5.2
  engine; plan's build command restored to `make qwen36.exe CUDA_DLL=1`.
- FN-004: engine-by-hand mode = self-test vs ref.json (needs repo-root CWD);
  `coli run` not wired for qwen36 → benchmarks go through `coli serve`
  (OpenAI API), symmetric with llama-server for Phase 11.
- Load path (every run): resident weights 5.4-5.7 s, RSS 9.23 GB after load,
  dense-i8 pass frees 7.2 GB, peak RSS 11.02 GB. Banner
  `[qwen36] group-scaled experts: gs=64` confirmed at runtime — gs64 story
  fully closed (source + metadata + banner + correct output).
- Cold self-test (NOT a benchmark, fixed self-test prompt): TTFT 1.86 s,
  2.63 tok/s decode, expert hit 46.0% cold. Matching tokens 0/12 vs
  full-precision reference — expected for a quantized container, not a defect
  flag; quality screen is Phase 10.
- Doctor (shallow + deep): all green except expected `[warn] accelerator.gpu
  CPU-only engine with GPU present` (CUDA tier is Phase 3). Model = 41
  shards, 23.0 GB. Placement: 30.3 GB RAM budget, 4.9 GB dense, 18.1 GB warm
  experts, **100% projected expert residency** — with 64 GB RAM the whole
  expert set fits in memory; NVMe streaming matters mainly on cold start.
- Serve smoke green: `coli serve` on http://127.0.0.1:8000/v1,
  `/v1/models` → `qwen3.6-colibri`; real chat completion correct and coherent
  (Canberra answer, 37 prompt + 30 completion tokens, finish=stop). Server
  stopped after the test.
- Next-session brief (Phase 2 proper): retarget run_bench.py to the serve
  API, run p1-p5 (1 cold + 3 warm, medians, IDOT_GS=1), record JSONs.
- GGUF downloaded after the model (owner's sequential order): single
  `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf`, 21 GB — Unsloth Dynamic Q4_K_M variant,
  caveat recorded for Phase 11. Disk after everything: 443 GB free.
- Downloads complete: both model artifacts in place; nothing is running in
  the background anymore.

## 2026-09-22 — external review verified (docs/review-2026-09-21.md, commit 1540ae0)

- Owner forwarded an external model's review (5 findings) and asked for a
  careful check; a second independent review by Claude Opus was also
  dispatched. Verification done against the pinned v1.12.0 source:
  - **R-001** (build target `qwen36.exe`, not `colibri.exe`): CONFIRMED —
    same conclusion we reached independently overnight (FN-003); the plan in
    the working tree already carried the fix before the review landed.
  - **R-002** (`IDOT_GS` belongs to `colibri.c`/GLM only): CONFIRMED — our
    earlier "set IDOT_GS=1 for qwen36" advice was WRONG. `qwen36.c` never
    reads it; its knob is `QWEN_EXPERT_KERNEL` (c/qwen36.c:998), fast
    planar-int4 kernel ON by default. Corrected in plan + open_items; root
    cause and lesson recorded as FN-005.
  - **R-003** (persistent `coli serve` + HTTP instead of per-sample CLI):
    CONFIRMED — matches FN-004 from the night run; the reviewer's extra
    argument (a fresh process per sample destroys warm-cache semantics) is
    correct and applies to our current run_bench.py design. Docstring marked
    superseded; the Phase 2 rewrite is queued.
  - **R-004** (determinism + explicit cold/warm-process/warm-persisted
    states): CONFIRMED — `COLI_TEMP` and `HEAT_FILE` verified in source
    (qwen36_tier.c saves/loads the heat table, `[qtier] HEAT_FILE ...`
    banners). Protocol block added to the plan (Phase 2).
  - **R-005** (p3 touching-interval ambiguity): CONFIRMED — explicit
    "touching intervals remain separate" sentence added to p3 (no recorded
    benchmark had used it yet, so an in-place edit was safe).
- The review's next-steps 5-7 (download model, doctor --deep, CPU build)
  were already done overnight — the reviewer only saw the pushed 71095fa.
- Verdict: all five findings valid in direction; none wrong. The one place
  the review was behind reality (build target) was already fixed on our side.
- Claude Opus independent pass (read-only) then sharpened the picture:
  R-001/R-002 CONFIRMED; R-003/R-004 PARTIAL (its `--prompt-file` exists only
  in `coli run`'s deepseek branch and gates only `coli run`; `COLI_TEMP` is
  launcher/server-side with a **0.7 default**, engine CLI loop is
  argmax-deterministic, no clock/PID seed exists); R-005 REFUTED against the
  working tree (we had fixed p3 before the review landed). Opus also found
  errors in the review itself — see review-2026-09-21-response.md.
- Two protocol facts adopted into the plan: benchmark requests MUST set
  `temperature=0` explicitly (server defaults 0.7, `openai_server.py:2746`);
  `warm-persisted`/HEAT_FILE exists only on the CUDA arm (`qwen36_tier.c` is
  CUDA-gated in the Makefile) — CPU phases measure cold vs warm-process only,
  and Phase 5's R4-R5 (heat across restart) moves after the CUDA build.

## 2026-09-22 — Phase 2 CPU baseline (START NOTE)

Plan for this chain: (1) write `tools/bench_serve.py` — persistent
`coli serve` + HTTP client, R-004 protocol (explicit temperature=0, fixed
max_tokens per prompt, state tags cold/warm-process); (2) one cold pass
(fresh server, p1-p5 once) + 3 warm passes on the same server; (3) per-run
JSONs + median summary → `results/cpu/`; (4) grep the server log for expert
hit-rate visibility (open Gate D item). Baseline state: engines built, model
verified, serve smoke green, `origin/main` = `7bf5a11`. Caveat recorded
upfront: OS page cache likely holds much of the 23 GB model (64 GB RAM), so
"cold" means cold *process*, not cold disk — noted in every cold sample.

## 2026-09-22 — Phase 2 CPU baseline: FIRST REAL NUMBERS

Harness `tools/bench_serve.py` (persistent serve + HTTP, R-004 protocol:
temperature=0, fixed max_tokens, state tags). AC power, 38.3 GB RAM free
before run. 20 runs (5 cold + 15 warm), 31 min total, all JSONs +
transcripts in `results/cpu/`.

| prompt | cold tok/s | warm med tok/s | warm TTFT med | wall med | tokens |
|---|---|---|---|---|---|
| p1 short | 3.64 | 4.53 | 6.5 s | 13.6 s | 33 |
| p2 ~400w | 4.19 | 4.53 | 15.3 s | 125.3 s | 500 |
| p3 code | 4.23 | 4.37 | 25.4 s | 102.2 s | 337 |
| p4 ukr | 4.87 | 4.97 | 16.5 s | 106.9 s | 450 |
| p5 long-ctx | 4.18 | 4.25 | 101.6 s | 111.3 s | 43 |

Reading:

- **CPU-only decode ≈ 4.3–5.0 tok/s** — below Gate B's 5 tok/s "usable"
  floor. The CPU arm alone does not justify the stack; Gate C (CUDA tier,
  Phase 3) is now the decisive experiment.
- **Warm-process gains are tiny** (~7%: 4.2 → 4.5) — with 100% RAM
  residency, process warmth adds little; the self-test's 46% cold hit-rate
  story mostly evaporates once everything sits in RAM.
- **Prefill is the CPU killer**: ~5 tok/s prefill too — p5 (535 prompt
  tokens) waits **~101 s for first token even warm**. Long-context work is
  impractical on CPU; this is exactly where the GPU tier must prove itself.
- Quality: p1/p5 answers exactly correct (p5 retrieved both embedded facts);
  generation is deterministic across cold/warm (temperature=0 works).
- FN-006: Ukrainian output carries 10 deterministic U+FFFD chars per ~1370
  (English clean) — tokenizer/streaming artifact, Phase 10 item.
- Open: expert hit rate NOT visible in serve logs (only in the engine
  self-test mode) — Gate D metric still lacks a serve-path source; check
  `coli bench` / PROF=1 before Phase 5.

Verdict recorded for the decision file later: CPU-only = below the useful
band; everything now rides on the CUDA tier.
