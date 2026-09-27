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

## 2026-09-22 — Phase 3 CUDA tier (START NOTE)

Plan: (1) back up the CPU engine binary as `qwen36_cpu.exe` for Gate C A/B;
(2) build `make cuda-dll CUDA_ARCH=sm_120` then `make qwen36.exe CUDA_DLL=1
ARCH=native` via the .bat pattern (vcvars64 + mingw64\bin + usr\bin + CUDA
bin); (3) verify `[CUDA] device 0:` + nonzero resident set in the serve log
(the Makefile's `.build-config` stamp guards against a fake-CUDA "up to
date" binary); (4) extend bench_serve.py with a warm-persisted pass
(HEAT_FILE save on clean stop → restart → rerun, CUDA arm only); (5) full
benchmark → `results/cuda/` + nvidia-smi logger during the run. Known risks:
driver 592.82 reports CUDA 13.1 vs toolkit 13.4 (minor-version compat should
hold; if the GPU run fails on driver version → update driver or pin toolkit
13.1); Smart App Control already proven non-blocking (CPU binaries ran).
Baseline: Phase 2 CPU medians 4.3-5.0 tok/s warm, prefill ~5 tok/s.

## 2026-09-22 — Phase 3 CUDA tier: RESULTS

Build: clean, artifact-verified (`coli_cuda.dll` 950 KB nvcc + `qwen36.exe`
linking qwen36_tier.c with -DCOLI_CUDA; `.build-config` = CUDA_DLL=1|native).
CPU binary backed up as `qwen36_cpu.exe`. Activation flag discovered: the
server silently runs the CPU path WITHOUT `--auto-tier`; with it the full
proof chain prints (`[CUDA] device 0: RTX 5070, 8.5 GB, sm_120` →
`[qtier] CUDA VRAM expert tier active` → 2413/10240 experts in VRAM 4.25 GB,
lm_head int8 + 30 DeltaNet projections on GPU). Driver 13.1 vs toolkit 13.4:
no runtime errors — minor-version compatibility held.

CPU (warm med) vs CUDA (warm med), temperature=0, same prompts:

| prompt | CPU tok/s | CUDA tok/s | speedup | CPU TTFT | CUDA TTFT | wall: CPU→CUDA |
|---|---|---|---|---|---|---|
| p1 short | 4.53 | 5.62 | 1.24× | 6.5 s | 5.2 s | 13.6→10.9 s |
| p2 500 tok | 4.53 | 9.73 | 2.15× | 15.3 s | 7.3 s | 125→58 s |
| p3 code | 4.37 | 8.25 | 1.89× | 25.4 s | 11.0 s | 102→51 s |
| p4 ukr | 4.97 | 9.29 | 1.87× | 16.5 s | 9.1 s | 107→57 s |
| p5 long-ctx | 4.25 | 5.06 | 1.19× | 101.6 s | 59.0 s | 111→67 s |

Reading:

- **Gate C passes meaningfully**: long generations ~1.9-2.15× faster
  end-to-end, TTFT 1.7-2.3× faster. CUDA warm already beats CPU warm on
  every prompt; CUDA *cold* mostly beats CPU *warm* too.
- Decode lands in the 8-10 tok/s band on real workloads (best sample 11.7).
  Gate B's "clearly useful ≥10" is borderline-touchable; "usable 5-10" solid.
- **Thermals are a non-issue**: 44-54 °C, peak 44 W of 95 W, VRAM ≤6.25 GB.
- **Variance warning**: warm pass 2 dipped to 4.6-6.9 tok/s across all
  prompts (pass 1: 8-10, pass 3: 5.6-11.7) — medians reported; source of
  the dip unknown (tier reshuffle? background interference?) — flagging as
  a watch item, not a conclusion.
- p5 prefill variance is high (TTFT 32-64 s warm); long-context TTFT is the
  weakest remaining number (~1 min median).
- **FN-007**: warm-persisted (HEAT_FILE) is dead through `coli serve` on
  Windows — the launcher hard-kills the engine child (TerminateProcess), so
  the engine's save-teardown never runs; verified with two shutdown paths in
  results/cuda-heat-validation. Persisted samples recorded but marked
  INVALID in summary.json. Workaround candidates: direct engine run, or an
  upstream fix.
- Hit rate still not exposed in serve logs (Gate D metric gap remains).

Verdict direction: with CUDA the stack crosses into "usable"; the remaining
Phase 5+ questions are KV-reuse, placement/tune, and the llama.cpp
comparison.

## 2026-09-22 — lessons system adopted (project journal + playbook + memory)

- Owner asked whether we keep a learned-lessons journal: we did not (lessons
  were scattered across LOG.md entries). Created `LESSONS_LEARNED.md` and
  backfilled 11 lessons (LL-001…LL-011) from the whole session.
- Discovered the cross-project playbook (`C:\projects\playbook`, 43 lessons
  from AliasRelay/IDENN/OrderBookPredictor) with a promotion contract in its
  README. Promoted 7 of our universal lessons: PB-067 (exit codes lie →
  artifact proof), PB-068 (Git Bash → temp .bat), PB-069 (silent mode
  fallback → assert the banner), PB-070 (warm-state benchmarks need a
  persistent process), PB-071 (explicit sampling params in every benchmark
  request), PB-072 (Windows graceful shutdown proven per process-tree
  level), PB-073 (external AI reviews verified three ways). INDEX.md and
  README.md updated (50 lessons, 4 projects).
- AGENTS.md "Уроки" section now routes lessons (project journal / playbook /
  Mnemosyne-global) and requires re-reading the journal + playbook INDEX
  before each brief.
- Mnemosyne global memory stored (id f8f142036b0e1ab6): the lessons
  discipline applies to ALL projects on this machine.
- Both repos left uncommitted pending owner's word (between phases).

## 2026-09-22 — Phase 4 automatic placement (START NOTE)

Committed the lessons milestone (playbook f0ad3b1 local — no remote;
playground 3d93ce0 pushed; push rule widened to phases OR milestones).
Plan for Phase 4: (1) `coli plan` output → results/placement/ (what lands
in VRAM, how much stays free); (2) `coli tune` (measures and saves the
machine profile) → results/placement/, background, artifact-verified;
(3) compare against the observed Phase 3 auto-tier placement (2413/10240
experts in VRAM, 4.25 GB budget); (4) no hand-tuning before the automatic
baseline is measured. KNOWN LIMIT: FN-007 — learned-heat influence on
placement cannot be tested through coli serve on Windows; record what tune
says about its own profile persistence.

## 2026-09-22 — Phase 4 placement/tune: RESULTS

- `coli plan` (auto-tier and plain): identical projection — VRAM hot tier
  5.4 GB / ~3068 experts, limit "CPU expert tail and GPU compute". NOTE:
  plan promises the tier even without --auto-tier, while serve silently
  skips it without the flag (reinforces PB-069 banner assertion).
- `coli tune --auto-tier` (artifact-verified, TUNE_EXIT=0): auto-placement
  puts the TRUNK first — 1207 MB (lm_head int8 + 30 DeltaNet projections)
  — then 4.25 GB for ~2412 experts. Winner: **OMP_NUM_THREADS=4 at
  9.23 tok/s vs 8.71 at the default 8 threads (+6.0%)** — consistent with
  the hybrid Zen5/Zen5c layout (4 fast cores beat 8 heterogeneous ones).
  Profile saved to AppData and copied to `results/placement/tune_profile.json`.
- Validation warm pass with the tuned profile (server banner:
  `[TUNE] applied measured profile · +6.0%`): p1 9.7, p2 11.1, p3 11.1,
  p4 11.3, p5 6.7 tok/s (single pass, no median — variance watch applies).
  First touch of Gate B's "clearly useful ≥10" band on real workloads.
  p5 TTFT still 48 s — long-context prefill remains the open lever
  (Phase 6 KV-reuse).
- Bonus: the tune profile JSON carries per-sample `hit_pct`/`ttft`/`tok_s`
  — the first machine-readable source of the Gate D hit-rate metric
  (serve logs still do not expose it).
- Phase 4 conclusion: auto-placement + one tune run moved CUDA decode
  from 8.3-9.7 (Phase 3 medians) to ~11 tok/s measured; no hand-tuning
  was needed or performed.

## 2026-09-22 — Phase 6 KV-reuse (START NOTE)

Owner gave the go. Plan: (1) find the KV-reuse mechanism in the v1.12.0
source (how activated, what proof line it logs — PB-069 discipline);
(2) write tools/kv_reuse_test.py: one warm server (auto-tier, tuned
profile), conversation = long doc (~1-1.5k tokens) + question A + follow-up
B + follow-up C, measuring per-turn TTFT/wall/tok-s with temperature=0 and
fixed caps; control = same turns with a mutated prefix (prefix match
impossible → full re-prefill) in the SAME process, plus optionally a
no-reuse flag if the source exposes one; (3) results → results/kv-reuse/.
Expected: turn-1 pays the full prefill; turns 2-3 with reuse should drop
TTFT sharply (the p5 TTFT ~48 s warm is the pain this phase measures).
Baseline: p5 warm TTFT 48-102 s (CUDA tuned/untuned).

## 2026-09-22 — Phase 6 KV-reuse: RESULTS (negative, well-evidenced)

Setup: `tools/kv_reuse_test.py`, conversation = ~890-token dossier
(prompts/kv_doc.txt) + 3 turns, temperature=0, max_tokens=60, auto-tier +
tuned profile. Plus an engine-level diagnostic with raw /v1/completions and
byte-identical prefixes. All artifacts in `results/kv-reuse/`.

- Arm A (reuse on, CUDA active per banner): turn TTFTs 61.4 / 72.4 / 66.2 s
  — proportional to full history size (890/969/1024 tok at ~14.5 tok/s) →
  every turn re-prefilled everything.
- Arm B (COLI_KV_PREFIX=0): INVALID as a control — the env var halves the
  cache (16→8/layer), tripping the tier gate
  (`cap=8 != n_experts=256 -> tier disabled`) → the arm silently ran CPU
  (FN-008). TTFTs 195-225 s are CPU numbers, not reuse-off CUDA numbers.
- Engine-level probe (byte-identical prefix, raw completions): REQ2 (same
  prefix + tail) TTFT 100.5 s vs REQ1 full prefill 101.7 s vs mutated
  control 96.9 s — no collapse. KV-reuse does not engage at all (FN-009).
- Consequence for the verdict: multi-turn long-context work pays a FULL
  re-prefill per follow-up (~1-1.5 min per turn at CUDA prefill rates);
  the headline v1.12.0 feature that would fix this is not observable in
  the serve path on this machine. Strong candidate for an upstream issue
  with our artifacts attached.
- Minor observations logged: completions-mode server starts with
  cache=256/layer vs chat-mode 16/layer; completions SSE streams `text`,
  not `delta.content` (harness note).

## 2026-09-22 — Phase 6 addendum: independent Opus review FLIPPED the diagnosis

Owner asked to run the Phase 6 conclusions past Claude Opus as an
independent reviewer (same three-way discipline as the R-00x review).
Verdicts: claim "reuse never engages" = PARTIAL (observation right,
attribution wrong); confound = PARTIAL (real, but not caused by the env
var); "every follow-up pays full re-prefill" = CONFIRMED for the current
client+template combination. What the review found that we missed:

1. `COLI_PREFIX_LOG=1` (qwen36.c:3117, documented in docs/ENVIRONMENT.md)
   — the proof line that distinguishes "not faster" from "not wired up".
   Should have been step one of the phase.
2. The engine record arithmetic is PERFECT: held=944 = 902 prompt + 42
   generated; held=908 = 869 + 39. The KV machinery works.
3. The divergence is client-side text round-trip: chat re-render drops the
   `<think>\n\n</think>\n\n` marker the turn was fed with (glm53 #1576
   class, openai_server.py:1256-1258); our think-marker prefix fix got
   further but still diverges (answer re-tokenization); the completions
   probe diverges on BPE boundary + stripped stop tokens. A conforming
   OpenAI client cannot reconstruct a token-exact prefix.
4. FN-008 corrected: arm B's cache=8/layer came from launch-time VRAM
   re-measurement (arm A's VRAM not yet freed), not from COLI_KV_PREFIX.
5. Our first engine probe was methodologically invalid (compared the whole
   record incl. generation; we appended our own answer text instead of the
   model's). Corrected probe (engine_diagnostic2): still "(diverged)".

Refined verdict recorded: KV-reuse = working engine machinery, unreachable
through the public API in v1.12.0; every follow-up pays a full re-prefill;
the fix belongs upstream (server-side session continuation or a token-exact
echo). Opus review raw output preserved in the session log; artifacts in
results/kv-reuse/logs/.

## 2026-09-23 — KV-reuse SOLVED through the public API (client-side)

Chain: owner's idea → Opus consultation → 3-line diagnostic patch → a
one-character fix.

1. Opus consultation (raw output in the session log): A (pure API escape
   like /score pin) is dead — every path is token-prefix-gated; recommended
   "Step 0": instrument the engine to print the FIRST divergence index,
   because "every later decision hangs on that number".
2. Local diagnostic patch (kept in the clone, diff exported to
   docs/patches/qwen36_prefix_divergence_diag.patch): prints first
   diverging position + both token ids in the no-reuse branch.
3. Result: divergence at 943 of 944 (turn C: 1040 of 1041) — the LAST
   held token only. held_id=13 = the trailing NEWLINE the model generated;
   the streamed text the client echoes back drops it.
4. Final client-side round-trip fix (tools/kv_reuse_test.py): assistant
   turn resent as `"<think>\n\n</think>\n\n" + text + "\n"`.

Measured with the fix (arm A, CUDA, tuned profile):

| turn | TTFT before fix | TTFT after | PREFIX line |
|---|---|---|---|
| A (full prefill) | ~65-68 s | 68.0 s | held=0 (fresh, expected) |
| B | 68.5 s | **2.75 s** | reusing 944 of 981 (96%) |
| C | 73.3 s | **3.04 s** | reusing 1040 of 1080 (96%) |

Follow-up TTFT: ~68 s → ~3 s (**~22×**). The Phase 6 verdict flips from
"unreachable" to: **KV-reuse works end-to-end through the public chat API
once the client reconstructs the fed token stream exactly** (think marker +
trailing newline). The upstream defects are now precisely characterized:
(a) chat re-render drops the fed think marker; (b) the streamed text drops
the final generated newline token, so a conforming client cannot echo a
token-exact prefix. Both are tiny, well-evidenced issue candidates — with
the one-line server-side marker fix and/or streaming the trailing token,
any standard client would work without our workaround.

Practical meaning for the verdict: multi-turn long-context IS usable today
on this stack (with our documented client contract), at ~3 s follow-up TTFT.

## 2026-09-23 — Phase 8 Brio (START NOTE)

Plan: (1) discover the Brio API surface in the v1.12.0 source (the /score
endpoint per the earlier Opus consultation: raw strings prefix /
prefix+" "+option, max_tokens=0, logprob rows; find exact path, request
fields, whether the server computes probabilities/entropy or we do);
(2) dataset: 30 cases — 10 obvious ALLOW, 10 obvious DENY, 10 ambiguous
REVIEW (synthetic code-review / CI / security verdict texts);
(3) tools/brio_test.py: run all cases x 3 repeats (stability), record
probabilities, entropy (ours if not served), latency per call;
(4) compare latency vs a minimal generation call; (5) analysis: probability
separation per class, entropy on obvious vs ambiguous, cross-repeat
stability. Outputs → results/brio/. Baseline expectations: obvious cases →
low entropy + high top probability; ambiguous → high entropy; deterministic
scoring (temperature n/a at max_tokens=0) → identical repeats.

## 2026-09-23 — Phase 8 Brio: RESULTS

API: POST /v1/brio {model, state, question, options, normalize} → answer,
entropy, choices[{option, p, tokens}]. Dataset: prompts/brio_cases.json
(30 cases: 10 ALLOW / 10 DENY / 10 REVIEW, synthetic code-review/CI/security
texts). Harness: tools/brio_test.py (3 repeats + 1-token generation latency
ref). Gotcha found on the way: the request MUST carry `model` (else
check_model 404s with a confusing "model `None` does not exist").

Run 1, normalize=mean (DEFAULT): catastrophic — ALL 30 cases answered DENY
(README typo fix → p(DENY)=0.73), p(REVIEW)≈0.004. Vocabulary probes
isolated the cause: DENY=2 tokens vs ALLOW=1 — mean-logprob-per-token
systematically favors multi-token options (DISCUSS=3 and MAYBE=2 also won
their probes). With normalize=sum the same trivial case: ALLOW 0.974.
→ FN-010 (upstream-issue candidate: dangerous default).

Run 2, normalize=sum (results/brio/*_sum.json):
- ALLOW 10/10, p(top) mean 0.961, entropy mean 0.168
- DENY 9/10 (D07 "CI red" text → ALLOW), entropy mean 0.357
- REVIEW 0/10 as a CHOICE (the model never picks the middle option), but
  entropy mean 0.642 — the HIGHEST class: entropy correctly flags the
  ambiguous middle even when the forced answer is wrong
- answer stability 30/30 across repeats (probs wobble slightly — parallel
  fp noise; the answer never flips)
- latency: median 6.0 s per case (pin + 3 options) vs 10.0 s for a
  1-token generation on the same state — cheaper than generating a single
  token, let alone an answer
- overall forced-answer accuracy 19/30 = 63%; with entropy as the
confidence gate (e.g. route H>0.5 to a human), the obvious classes are
clean.

## 2026-09-23 — Phase 9 thermal marathon (START NOTE)

Plan: one CONTINUOUS generation session, 16 minutes (p2-style requests,
500-token caps, back-to-back, temperature=0, tuned profile + auto-tier) via
tools/thermal_test.py; nvidia-smi logger (-l 5) in parallel →
results/thermal/logs/. Analysis: tok/s bucketed by minute (first 3 min vs
last 3 min), GPU temp/power/clock curves, throttle detection (SM clock
drops under sustained load), VRAM stability. Known limitation: CPU/fan
telemetry not readily scriptable on this Windows box — GPU-side metrics are
the reliable ones (Phase 3 watch: peaks were 54 °C / 44 W with pauses;
this run has none).

## 2026-09-23 — Phase 9 thermal: RESULTS

16 minutes of continuous generation (24 requests, 500-token caps, p2
prompt, tuned profile + auto-tier). Artifacts: results/thermal/.

- **No thermal throttling**: GPU temp 43 → 57 °C max (median 55), power
  median 39 W / max 55 W of the 95 W cap, SM clock still spikes to 2647
  MHz at peak temperature; util median 23% (the GPU is not even the
  saturated side — consistent with the "CPU expert tail" limiter).
- **Sustained speed IMPROVED over the run**: median decode by minute
  climbed monotonically 9.6 → 15.5 tok/s (+61% from first to last minute).
  With temperature flat, this is not thermals — it is the learned
  hot-expert VRAM tier filling under sustained same-domain load: the
  first DIRECT evidence of the learned-placement value (Gate D signal,
  process-level, non-persistent).
- Reading for the verdict: measured Phase 3/4 numbers (8-11 tok/s) are
  conservative floors for sustained interactive sessions on one topic;
  the stack does not decay under load — it warms UP. Laptop stays cool
  and quiet-class power (≤55 W).
- Harness bug found and fixed: elapsedMin mixed time.time() with
  perf_counter (negative-minute bucket keys); bucket values and ordering
  were valid, timestamps were not; fixed for future runs.

## 2026-09-23 — FN-007 SOLVED end-to-end and reported upstream (issue #1733, PR #1734)

Owner's plan: consult Opus first, then file the issue AND write the patch
so our own test passes, offering the patch upstream. Executed in full:

1. Opus sanity check: **NO-GO as drafted** — my draft wrongly framed the
   bug as Windows-only (qwen36 has no signal handlers at all: POSIX is
   broken the same way; only atexit exists) and my CTRL_BREAK fix could
   not work (no receiver). Correct trigger found by the review: close the
   engine's stdin (serve loop fgets EOF → main returns → atexit → save).
2. Patch (4 hunks, all in the Python layer, zero C changes):
   Engine.close stdin-drain (COLI_ENGINE_DRAIN_S=30), serve() SIGBREAK
   handler on Windows, engine spawned in its own process group, coli stop
   launcher-first. Plus c/tests/test_engine_close_drain.py (2 unit tests,
   pass in 0.6 s). First validation attempt failed → revealed the second
   half of the bug (launcher had no graceful Windows stop either) → hunks
   3-4 → second validation green.
3. Validation (results/cuda-heat-validation-fixed2/): `[qtier] HEAT_FILE
   saved` on every stop, `[qtier] HEAT_FILE loaded` on restart;
   **warm-persisted BEATS warm-process**: decode 10.1-11.0 → 12.1-15.0
   tok/s, p5 TTFT 43.9 → 26.6 s. Learned heat survives restarts and pays
   from the first token — the strongest Gate D evidence of the project.
4. Upstream: issue https://github.com/JustVugg/colibri/issues/1733
   (corrected body, cross-platform framing), PR against dev
   https://github.com/JustVugg/colibri/pull/1734 (clean branch from
   v1.12.0, only the fix + test; the local diagnostic qwen36.c patch
   stays out). Lab clone now runs the fix branch.
5. LL-013 recorded: fix-via-signal requires the receiver to handle it —
   read the receiver's handler table before proposing the mechanism.

## 2026-09-23 — Phase 11 llama.cpp comparison (START NOTE)

Plan: (1) fetch the latest prebuilt CUDA Windows build of llama.cpp
(ggml-org releases: llama-b*-bin-win-cuda-x64.zip + cudart zip →
C:\Tools\llamacpp; no build step — that itself is comparison data);
(2) start llama-server on the pinned GGUF
(C:\Models\qwen36_Q4_K_M\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf, 21 GB,
UD-Q4_K_M — quant-scheme caveat recorded) with a placement that mirrors
the comparison's question: GPU trunk + CPU experts (--cpu-moe style if
the build supports it, else partial -ngl), ctx 8192, threads 4 (mirrors
our omp-4 finding), port 8010; (3) reuse tools/bench_serve.py against
--base-url (its OpenAI-compatible API) — same p1-p5, temperature=0, fixed
caps, cold + 3 warm passes → results/comparison/llamacpp/; (4) nvidia-smi
logger + RAM working set; (5) compare vs colibri tuned numbers
(Phase 4: 9.7-11.3 tok/s warm, TTFT 3-48 s; persisted-heat 12.1-15.0).
Fairness caveats: quant differs (int4-gs64 vs UD-Q4_K_M); placement
strategies differ by design — the comparison is stacks, not kernels.

## 2026-09-24 — Phase 11 llama.cpp comparison: RESULTS

Setup: prebuilt b11160 CUDA-13.4 Windows build (download + unzip, no
compile; 144 MB bin + 404 MB cudart), llama-server with the pinned GGUF
(UD-Q4_K_M, 21 GB), `-c 8192 -t 4 -ngl 99 --cpu-moe` (GPU trunk + CPU
experts — mirrors colibri's placement), model load 7.7 s, ~3.8 GB VRAM.
Same harness (bench_serve via --base-url), same p1-p5, temperature=0.
Harness notes: llama streams reasoning models as `reasoning_content` —
fixed by `chat_template_kwargs:{enable_thinking:false}` + parser
fallback (parity with colibri's thinking-off path). First (parser-broken)
run's walls already matched; the fixed run (results/comparison/
llamacpp-fixed/) is authoritative.

Warm medians (3 passes, variance ~1%):

| prompt | llama tok/s | llama TTFT | colibri best tok/s | colibri best TTFT |
|---|---|---|---|---|
| p1 | 32.6 | 0.16 s | 11.2 (tuned) | 2.4 s |
| p2 | 33.1 | 1.1 s | 14.4 (persisted) | 4.4 s |
| p3 | 33.2 | 0.12 s | 12.1 (persisted) | 7.5 s |
| p4 | 33.0 | 1.07 s | 15.0 (persisted) | 4.9 s |
| p5 | 32.9 | 0.14 s | 13.4 (persisted) | 26.6 s |

Colibri "best" = tuned profile or persisted-heat runs — its strongest
numbers of the project; llama still wins decode ~2.2-2.7x and long-context
TTFT by ~200x (0.14 s vs 26.6 s — llama's prefix cache keeps the 535-token
prompt across requests; colibri's KV-reuse (fixed by us) reaches 2.75 s).
GPU during llama run: 44-53 °C, ≤49 W, 3.8 GB VRAM, util med 40% — cooler
AND lighter than colibri's tier. Quality: transcripts correct (p1/p5
facts exact; p3 follows the touching-interval rule). Stability: 32.9-33.2
tok/s across all warm passes.

Caveats recorded: quant differs (UD-Q4_K_M vs int4-gs64); placement
strategies differ by design; llama's cold pass benefited from a warm page
cache and server slots pre-seeded by the earlier run (its warm numbers are
the fair comparison point).

Gate E reading: on THIS machine, for THIS model class, the simpler stack
is decisively faster end-to-end, lighter on VRAM, zero-build, and its
multi-turn caching works out of the box. Colibri's remaining differentiators
are Brio-style closed decisions, engine flexibility, and the
very-large-model streaming story (not tested here).

## 2026-09-24 — Phase 10 quality screen: RESULTS

Battery: prompts/quality_battery.json (C# reasoning, SQL, Python debug,
Ukrainian constrained, English constrained, structured JSON), temperature=0,
tools/quality_screen.py, both engines (results/quality/{colibri,llama}/).

- Automated checks: 6/6 PASS on BOTH engines (Ukrainian bullet/constraint
  shape, exact 2-sentence + required/forbidden words + trailing digit,
  valid JSON with all fields). Zero U+FFFD in battery outputs on both.
- Semantic review: the one visible difference is q1 (LINQ deferred
  execution): llama answers cleanly ("20,40,60" with a tight explanation);
  colibri first says "20,40", then self-corrects mid-answer and leaks
  meta-chatter ("Wait, the prompt asks for at most four sentences, let me
  re-evaluate"). Single sample — anecdote, not a verdict — but noted as a
quant-degradation signal for the decision file. q3 (tricky dedup bug)
gets comparable hedged answers from both; q4/q5/q6 equivalent.
- FN-006 RESOLVED diagnostically: p4 rerun NON-STREAMED reproduces exactly
  10 U+FFFD → the corruption is in the CONTAINER'S TOKENIZER path, not
  streaming; deterministic; long-form Ukrainian only (battery q4 clean).
  Upstream-issue candidate #4, blame narrowed.

## 2026-09-24 — PR #1734 CI round 1: one failure, diagnosed and fixed

First CI run on the PR: all engine/CUDA/cluster jobs green; Python tests
failed on `DispatcherTest.test_close_wakes_pending_generation_and_is_idempotent`
(the Linux/macOS check jobs failed on the same suite). Root cause: our
drain ladder only called terminate() on TimeoutExpired — but the suite's
FakeProcess.wait() RETURNS None instead of raising, so terminate() was
skipped entirely and the dispatcher stayed alive. Fix: decide the ladder
by `poll()` after the drain wait (correct for real engines AND test
doubles). Locally: our 2 drain tests + the full upstream
test_openai_server module (176 tests) green. Pushed f5497c8; the CI
matrix restarted and may wait for maintainer approval to run (fork PR).
Hourly background watch scheduled (PR #1734 + issue #1733, reports only
on movement); the owner will also ping manually when a run appears.

## 2026-09-24 — PR #1734 MERGED upstream; issue #1733 closed by our fix

The hourly watch fired with the news: the maintainer merged #1734 into
`dev` (merge commit 50c9e1608, 2026-09-24T19:54Z) and closed #1733 with a
comment confirming our mechanism ("stopping coli serve closes the engine's
stdin and waits for it to exit on its own, so its atexit teardown
(HEAT_FILE) runs; SIGBREAK is handled on Windows..."). The merged code
carries our implementation verbatim (_ENGINE_DRAIN_S / COLI_ENGINE_DRAIN_S,
stdin drain, SIGBREAK handler, engine process-group isolation) and our
unit test now lives in their suite. The CI rerun after our poll()-ladder
fix went green (implicit in the merge).

Actions taken: lab clone resynced to origin/dev (now running the merged
fix natively; only our local qwen36.c divergence-diag patch and build
bats remain uncommitted there); FN-007 updated to merged; the hourly
upstream watch is obsolete — owner to disable it in the Automations page
(the agent has no delete-automation tool).

Milestone: this playground leaves a merged upstream contribution —
warm-start persistence (HEAT_FILE) now works in Colibrì for every user,
with the fix designed, validated, and defended end-to-end here.

## 2026-09-25 — upstream batch 2 (START NOTE): FN-010 + FN-009 fixes; FN-006 deferred

Owner's orders: implement FN-010 (normalize default → sum + warning) and
FN-009 (think-marker re-render + trailing-token stream fix, per the qwen38
pattern); each draft goes through an Opus review BEFORE filing; FN-006 is
shelved with detailed notes (owner decision).

## 2026-09-25 — upstream batch 2 PREPARED (not filed; awaiting owner approval)

FN-010 (brio normalize): branch fix/brio-normalize-default (8298d71) —
default sum in both forms, stderr warning on unequal token counts under
mean, docs/brio.md updated, 11/11 tests green. Draft v2 (Opus GO):
volunteers REVIEW 0/10 under sum, 63% overall, repeat instability, and
the overwritten-artifacts caveat (mean-run numbers survive in LOG).

FN-009 (kv round-trip): the investigation went three layers deep —
(1) raw-frame probe: engine streams faithfully; (2) the true mechanism
found: token id 13 is '.', and the tokenizer merged '.<' (15294) across
'<|im_end|>' — a pretokenizer symbol-run swallowing added tokens; we
built and validated that engine fix (97% reuse) — then discovered
upstream had ALREADY landed the equivalent (`next_special` in
encode_text, #1653); (3) the remaining renderer gap: our Fix A (9 lines,
now with a doubled-header guard, branch fix/qwen36-kv-roundtrip 6a33d8c)
validated on current dev with a STANDARD client: reusing 940/972 (97%),
follow-up TTFT 96 s → 3.7 s; quality battery 6/6 after the change.
Opus review: NO-GO as v1 framing — the conformance test
(test_qwen36_chat_template.py, byte-equality vs chat_template.jinja;
skipped locally without the template) would fail, and first-hand
jinja2 rendering of the PINNED template confirms it renders history
turns bare on both branches: token-exact round-trip is impossible BY
DESIGN under the official template. Draft v2 reframed as an explicit
trade-off proposal (template literalism vs KV reuse; carve-out needed;
alternative server-side splice offered; thinking-on limitation stated).

Lab clone: branch `lab` = origin/dev + both fixes (7e2384e, 1f462f8);
qwen36.exe rebuilt from dev C code; stash with obsolete mixes dropped.
Nothing published anywhere — issues/PRs await the owner's approval,
per standing order.

## 2026-09-25 — PROJECT VERDICT: LAB ONLY (Owner's decision)

Owner chose В-1 (agent recommendation) — recorded in docs/final_results.md
as the DECISION. The experiment is complete: 11 phases measured, verdict
grounded in numbers, one upstream merge already landed (#1734), FN-010
filed and in CI (#1752/#1753), FN-009/FN-006 shelved with ready drafts/
notes. The daily-driver path on this machine is llama.cpp (tools and
models in place); Colibrì stays a documented lab capability with review
triggers (new releases with out-of-the-box KV reuse / heat / TTFT, or a
hardware change). Standing watch: automation-1dabca01 until #1753
reaches a terminal state.

## 2026-09-25 — FN-010 MERGED: second upstream contribution landed

The watch fired with the news: PR #1753 merged into dev at 21:20 UTC
(merge commit 4e28e39); issue #1752 auto-closed ("Fixed by #1753... the
default is now sum. It ships with the next release"). The maintainer
independently verified our token-count analysis on their tokenizer
(ALLOW/REVIEW=1, DENY=2, MAYBE=2, DISCUSS=3 — "exactly as you reported")
and noted the mean-per-token rationale nuance in his comment.

Actions: lab branch resynced — dev now carries the brio fix natively;
only the FN-009 renderer cherry-pick remains on top (bf5fc89); FN-010
marked closed-merged in FINDINGS. Project scoreboard: 2 upstream merges
(#1734 heat-save, #1753 brio-sum), 1 shelved ready draft (FN-009),
1 deferred with notes (FN-006). VERDICT stands: LAB ONLY.

## 2026-09-26 — FN-009 filed issue-first (#1759, no PR); Phase 12 brief drafted

Owner approved posting the shelved FN-009 as ISSUE + branch (my
recommendation over an immediate PR: the fix deliberately diverges from
chat_template.jinja, so a PR would land with a knowingly-red conformance
test before the maintainer even agrees the trade is his to make; the
branch compare-link gives him the full diff, and the PR is one command
away on his word). Issue: JustVugg/colibri#1759 — evidence, option (b)
implementation (guarded, 97% reuse / 3.7 s measured), alternatives
(status quo / server-side splice), scope notes. Branch pushed:
tarazum:fix/qwen36-kv-roundtrip.

Also drafted: docs/phase12-glm53-flash-brief.md (backlog; owner will
say when). Key feasibility fact verified in upstream docs: the glm53
conversion is ONE-PASS shard-at-a-time (download+convert together,
--min-free-gb 30), so peak disk ≈ 195 GB container + one shard — fits
today's ~443 GB free without any hardware purchase.

## 2026-09-26 — Phase 12 START (glm53-flash feasibility; owner gave the go)

Start note per AGENTS. State: 378 GB free (verified by owner); brief at
docs/phase12-glm53-flash-brief.md (peak ~235 GB, guard 30 GB, S7 cleanup
after numbers). Plan: S1 build glm53 engine (CPU smoke, then CUDA DLL) →
S2 background one-pass conversion to C:\Models\glm53_flash_i4
(artifact-verified: dir growth + converter log + --min-free-gb 30) →
S3 doctor + one short generation (minute-scale TTFT is EXPECTED) with
telemetry → S4 Brio verdict (5-10 cases, sum default) → S5 heat semantics
of glm53 + does our stdin-drain fix save anything → S6 numbers to
results/phase12/ + hardware-notes extrapolation replacement → S7 delete
the container. No other large downloads until S7. Next command after
this note: converter recon, then `build_cpu.bat glm53.exe`.

## 2026-09-27 — Phase 12 COMPLETE (all slices, artifact-verified)

Numbers (full JSON: results/phase12/phase12_results.json):

- Conversion: 62 shards, 194.7 GB, 212 min unauthenticated.
- Storage probe: O_DIRECT 4.54 GB/s / buffered 6.44 GB/s on 14 MB
  blocks — the DRAM-less OS-shared KIOXIA vastly above fear.
- Doctor: 39.7 GB RAM budget, 29.1 GB warm experts, 17% projected
  residency, NO VRAM tier for glm53 (CPU path by design).
- Generation (short prompt, temperature=0): COLD TTFT 43.3 s, decode
  0.46 tok/s, answer correct; warm repeats TTFT ~35 s, decode 0.61
  tok/s (+30%). Footprint: 34.5 GB RSS, system responsive at 2 GB free.
- **Brio verdicts from the 321B brain (sum default = our #1753): 5/6
  correct; short states 65-87 s with p(top) up to 0.998; the ~600-word
  dossier verdict in 12 min (correct, H=0.65 honest uncertainty).**
- Heat: glm53 has NO learned-heat mechanism (no counter in source;
  expert LRU process-local) — warm-up is per-process only; our
  stdin-drain fix applies but there is nothing to save.
- S7 cleanup: container deleted, disk back to 378 GB free, engine
  exited cleanly.

Reading for the verdict's LAB-ONLY niche: "ask the giant occasionally"
is REAL on this laptop — a minute per short verdict, ~12 min per
document verdict. The visible limiter at these speeds is CPU expert
compute, not disk (18 MB/s effective vs 4.5 GB/s available) — so on a
gaming PC, MORE RAM (hit rate) buys more than more disk.
hardware-notes §5 updated (extrapolations replaced by measurements). Plan: (1) FN-006 deferred
notes → docs/upstream/; (2) FN-010: find the normalize defaults in
openai_server.py, flip to sum, add a bias warning when mean is requested
with unequal option token counts, extend their test_brio_api.py, validate
with our brio_test.py (default no-normalize request must report sum);
(3) FN-009: Fix A render_chat_qwen think-marker (copy render_chat_qwen38
pattern), Fix B — locate where the final generated '\n' (token id 13) is
dropped from the stream (python detok/StopFilter vs engine emit path),
fix it, and validate with a STANDARD client echo (no marker, no trailing
newline added) expecting [PREFIX] reusing 96%; (4) one Opus review with
separate GO/NO-GO per draft; (5) file issue+PR per accepted draft (dev
branch, per CONTRIBUTING); (6) update FINDINGS/open_items/memory, push.

Phase verdict: int4-gs64 quality is adequate for practical use (structure,
instructions, JSON, Ukrainian all pass); one reasoning-sloppiness signal
vs the GGUF sibling; tokenizer corruption on long-form Ukrainian remains
the sharpest quality defect.

Phase verdict: Brio mechanics work, fast and deterministic; entropy is the
honest confidence signal; the default normalization is broken (FN-010 —
use sum); the middle option needs prompt/option engineering to ever win;
with an entropy threshold this is a usable classifier for obvious cases.

## 2026-09-27 — Public-readiness audit + README rewrite (repo went public)

Trigger: MIT + public visibility (907545c) while README still described the
project in future tense from 2026-09-21. Owner asked for a fresh-eyes pass.

Audit (subagent sweep, 299 tracked files) — verdict per category:

- Secrets/tokens: CLEAN (0 findings; only benign test-data mentions).
- Results hygiene: no tracked file > 1 MB; logs are deliberate evidence
  (gitignore whitelist). One username path in
  results/placement/tune_autotier.txt:117 — left as-is (raw artifact).
- Stale framing: README (future tense, no verdict) — FIXED below;
  open_items.md line 162 "no benchmark data exists" etc. — covered by a
  status banner (historical log, boxes untouched on purpose).
- Unresolvable private references (Owner decision, NOT changed):
  AGENTS.md:3,60 (IDENN, playbook), LESSONS_LEARNED.md:5-7 (PB-NNN
  back-links), LOG.md:288, final_results.md:70-71 (LACA + dead link to
  model_and_process_recommendations_sep2026.md). Recommendation: one-line
  "(private)" markers instead of removal — these are working docs.

Changes:

- README.md: full rewrite — verdict LAB ONLY up front, key-numbers table
  (Colibrì vs llama.cpp), upstream scoreboard (#1734, #1753 merged;
  #1759 -> maintainer PR #1767 with our Co-authored-by; FN-006 deferred),
  Phase 12 numbers (321B on the laptop), updated repo layout (final_results
  as entry point), methodology, MIT.
- docs/open_items.md: status banner only.
