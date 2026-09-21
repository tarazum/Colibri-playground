# Colibrì Experiment Plan

## 1. Goal

Evaluate whether Colibrì is practically useful on the target Windows gaming laptop, not merely whether it can launch a large model.

The first experiment deliberately starts with **Qwen3.6-35B-A3B** instead of a 700B+ model. The goal is to establish a useful baseline on a model that fits the intended hardware profile and has an upstream-tested CUDA tier for 8 GB GPUs.

Primary questions:

1. Can the model run reliably on Windows native?
2. How much does the RTX 5070 / 8 GB CUDA tier improve real decode speed?
3. Does Colibrì's learned expert placement materially improve warm runs?
4. Are first-token latency and multi-turn latency acceptable?
5. Is Brio useful for constrained verdict/classification workloads?
6. Is the complexity justified compared with a simpler local runner?

---

## 2. Baseline

Initial upstream baseline:

- Colibrì release: **v1.12.0**
- baseline date: **2026-09-21**
- OS: Windows native
- GPU: NVIDIA RTX 5070 Laptop (Blackwell), 8 GB VRAM — ≈7.4 GB usable under WDDM with the display attached
- CUDA architecture: `sm_120`
- storage: single KIOXIA KBG60ZNV1T02 1 TB NVMe, shared with the OS (no second disk)
- first model: **Qwen3.6-35B-A3B**
- container: **int4-gs64**
- model repo: `Kreuzzelg/qwen36-35b-a3b-colibri-i4-gs64`
- expected model size: roughly 20-22 GB

Before the first benchmark, capture the actual machine state instead of relying on remembered specs.

A first snapshot was captured on 2026-09-21 in `results/environment.json` (HP OMEN MAX 16, Ryzen AI 7 350, 64 GB RAM, RTX 5070 8 GB, on AC power). Re-capture free RAM/VRAM and power state before each benchmark phase — free space and driver state drift.

Record:

```powershell
nvidia-smi
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,Size
python --version
nvcc --version
```

Also record:

- exact Colibrì commit SHA
- NVIDIA driver version
- CUDA Toolkit version
- free RAM before launch
- free disk space
- laptop power mode
- whether the laptop is on AC power

Do not compare runs made under different power modes as if they were equivalent.

---

## 3. Success Criteria

This playground is an experiment, so we need gates.

### Gate A: functional

Pass if all are true:

- Qwen3.6 loads without model corruption/errors
- chat completes a normal multi-turn exchange
- OpenAI-compatible API works
- repeated runs produce stable behavior
- CUDA path is actually active when requested

### Gate B: useful performance

Target, not a hard upstream promise:

- warm decode around **10 tok/s or better** is clearly useful
- **5-10 tok/s** is usable but requires judging latency and thermals
- below **5 tok/s** needs a strong reason to keep the stack

We should report the measured number, not force the result into these bands.

### Gate C: CUDA value

CUDA must produce a meaningful end-to-end improvement over CPU-only on the same prompt and model.

Record:

```text
CPU tok/s
CUDA tok/s
speedup = CUDA / CPU
```

A GPU path that changes impressive-looking internal metrics but barely moves end-to-end generation is not a win.

### Gate D: warm-cache value

Repeat the same workload after Colibrì has learned expert heat.

Record:

- cold tok/s
- warm tok/s
- expert hit rate
- model RSS
- VRAM use
- time to first token

The learned hierarchy is one of Colibrì's main ideas, so it must earn measurable value.

### Gate E: operational value

Keep Colibrì only if the total experience is acceptable:

- setup complexity
- startup time
- model disk footprint
- noise/heat/power on the laptop
- stability
- API integration friction
- performance versus a simpler runner

---

## 4. Phase 0 - Safe Environment Check

Do this before downloading experimental giant models.

### 4.1 Clone upstream

```powershell
git clone https://github.com/JustVugg/colibri.git
cd colibri
git checkout v1.12.0
git rev-parse HEAD
```

Save the SHA in the results.

### 4.1.1 gs64 container check — RESOLVED at source level (2026-09-21)

The HF model card claimed the gs64 container needs the `gs64-ab` branch.
Checked directly in the cloned v1.12.0 source: `c/qwen36.c` natively reads
`expert_gs` from `qwen36_meta.json`, has the grouped-scale expert GEMV path
(`matmul_q_gs`) and prints `[qwen36] group-scaled experts: gs=N` at load. The
card note is stale. Keep the runtime confirmation as a cheap final check after
download (expect that banner line, plus a clean `doctor --deep`).

### 4.2 Verify Python

The Windows launcher uses Python even though the inference engines themselves are C.

```powershell
python --version
```

### 4.3 Inspect GPU

```powershell
nvidia-smi
```

Expected target:

- NVIDIA GPU visible
- 8 GB VRAM
- current driver loaded

Observed 2026-09-21: RTX 5070 Laptop, driver 592.82 (CUDA 13.1 capable),
~0.7 GB VRAM already used by the OS under WDDM — plan placement for ~7.4 GB,
not the full 8 GB.

The CUDA Toolkit is **not installed** yet (no `nvcc` on PATH). `sm_120`
requires CUDA Toolkit 12.8 or newer; an older NVCC fails the Phase 3 build.
Toolkit, VS 2022 Build Tools and MSYS2 are all free — see the install
checklist in `docs/open_items.md`.

### 4.4 Disk check

The Qwen3.6 test needs about 22 GB for the model. Keep ~60 GB free on C: for:

- model files (~22 GB)
- CUDA Toolkit + VS Build Tools (~10-15 GB)
- comparison GGUF for Phase 11 (~20 GB)
- logs and checkpoints

Observed 2026-09-21: C: has ~501 GB free; there is no D: drive, so model
paths are `C:\Models\...`. The single NVMe is a DRAM-less OEM drive shared
with the OS: close background I/O during benchmarks, and expect disk
bandwidth — not CPU — to be the main CPU-mode bottleneck.

Do **not** start with GLM-5.x; its model footprint is roughly 370+ GB and would mix the engine evaluation with a huge storage experiment.

### 4.5 Early hit-rate smoke check

Gate D depends on the expert hit rate being observable. During the first CPU
chat run, confirm the engine logs the hit rate (or exposes it via `plan` or
the dashboard). If it does not, find the supported way to read it before
investing in later phases — otherwise Gate D loses its main metric.

---

## 5. Phase 1 - Get Qwen3.6

Install the Hugging Face CLI if needed:

```powershell
python -m pip install -U "huggingface_hub[cli]"
```

Download the recommended Colibrì container:

```powershell
hf download Kreuzzelg/qwen36-35b-a3b-colibri-i4-gs64 --local-dir C:\Models\qwen36_i4_gs64
```

There is only one NVMe on this machine, so `C:\Models` is the path. If a second, faster disk is added later, move the model there and re-baseline.

Record:

- total model size
- download source
- model revision (the commit hash `hf download` reports; pin with `--revision` if it matters)

---

## 6. Phase 2 - CPU Baseline

The first successful run should be deliberately boring.

Goal:

> prove the model/container/runtime path works before adding CUDA complexity.

Use the upstream Windows launcher/build path appropriate to the checked-out release.

Run the readiness checks first:

```powershell
coli.cmd doctor --model C:\Models\qwen36_i4_gs64
coli.cmd doctor --deep --model C:\Models\qwen36_i4_gs64
```

Then chat:

```powershell
coli.cmd chat --model C:\Models\qwen36_i4_gs64
```

If running from a source checkout rather than a release archive, use the source launcher form documented by upstream.

### CPU benchmark prompts

Use the fixed prompts committed under `prompts/` (see `prompts/README.md`):

1. `p1_short_factual.txt` — short factual answer
2. `p2_explanation.txt` — ~400 word structured explanation
3. `p3_code.txt` — code-generation task with checkable output
4. `p4_ukrainian.txt` — Ukrainian-language task
5. `p5_long_prompt_short_answer.txt` — long prompt, short answer

`tools/run_bench.py` wraps the runs and writes per-run JSON into `results/cpu/`.
Its metric parser is a stub until the first real `coli` output is captured —
finish it against real logs before trusting any parsed number.

For each run capture:

- prompt tokens
- generated tokens
- TTFT
- decode tok/s
- total wall time
- peak RAM
- CPU utilization
- CPU temperature if available

Run at least:

- 1 cold run
- 3 warm repeats

Do not quote the fastest run as the result. Keep all samples and report the median.

---

## 7. Phase 3 - CUDA on 8 GB VRAM

This is the main hardware experiment.

Upstream supports a Qwen3.6 CUDA VRAM tier and has published 8 GB GPU measurements. On Windows, the CUDA-enabled Qwen3.6 engine uses the DLL-loader build path.

Expected source-build outline for the v1.12.0 baseline:

```text
make cuda-dll CUDA_ARCH=sm_120
make colibri.exe CUDA_DLL=1 ARCH=native
```

Verified against the actual v1.12.0 Makefile (2026-09-21): the engine is one
unified `colibri.exe` (older docs' per-model binaries are gone), on Windows the
CUDA path must be `CUDA_DLL=1` (runtime DLL, never `CUDA=1`), and the Makefile
stamps `.build-config` so a CPU-only binary can't masquerade as CUDA-enabled.

Run the build from the Windows toolchain environment required by upstream:

- MSYS2 / GNU make (`pacman -S --needed mingw-w64-x86_64-gcc make`, and put `C:\msys64\usr\bin` on PATH in the build shell so make's POSIX recipes find `sh.exe`)
- Visual Studio 2022 C++ build tools (x64 — via vcvars64 or the x64 Native Tools Prompt; the 32-bit prompt fails nvcc)
- CUDA Toolkit
- build from a git clone, not the release zip (the zip lacks the Makefile and backend_cuda.cu)
- Smart App Control must be off, or it blocks self-compiled binaries

Before executing this phase, verify the exact current upstream Windows instructions because build details can change quickly.

Two calibrations from upstream release history:

- gs64 containers need the opt-in `IDOT_GS=1` **environment variable** for the
  grouped planar IDOT integer kernels — confirmed in v1.12.0 source
  (`c/colibri.c`: default off, env-enabled). Set it for benchmark runs; build
  both ways only if it changes numbers.
- the upstream "1.44 → 10.05 tok/s (7.0×)" figure was measured on **two**
  8 GB cards. Calibrate single-card expectations noticeably lower — 10 tok/s
  is not a single-card promise.

### CUDA checks

We need proof that CUDA is active, not merely that a CUDA-capable binary exists.

Capture:

- startup banner
- detected device count
- VRAM allocation
- expert residency
- placement decisions
- `nvidia-smi` while generating

### Test matrix

Run the same prompts as the CPU baseline.

Compare:

| Test | CPU cold | CPU warm | CUDA cold | CUDA warm |
|---|---:|---:|---:|---:|
| Short answer | | | | |
| Long explanation | | | | |
| Code | | | | |
| Ukrainian | | | | |
| Long prompt / short answer | | | | |

Metrics:

- TTFT
- tok/s
- wall time
- RAM
- VRAM
- expert hit rate

---

## 8. Phase 4 - Automatic Placement

Colibrì can place routed experts and dense components across CPU/GPU memory.

We want to compare:

1. automatic placement
2. expert-only / reduced placement where supported
3. any profile selected by `coli tune`

Run:

```powershell
coli.cmd plan --model C:\Models\qwen36_i4_gs64
coli.cmd tune --model C:\Models\qwen36_i4_gs64
```

If the source launcher syntax differs, use the equivalent upstream command.

Save the output.

Questions:

- what did Colibrì place in VRAM?
- how much VRAM remained free?
- did auto placement beat the simpler policy?
- did the result change after expert heat was learned?

No hand-tuning until the automatic baseline is measured.

---

## 9. Phase 5 - Cold vs Warm Learning

The learned hot-expert cache is a core Colibrì claim.

Use one repeatable workload:

- same system prompt
- same domain
- several related requests
- restart and rerun

Suggested domains:

- C# code review
- SQL analysis
- Ukrainian text analysis

Run sequence:

```text
R1 cold
R2 same workload
R3 same workload
R4 restart process
R5 same workload using persisted heat/history
```

Record for every run:

- tok/s
- TTFT
- expert hit rate
- RAM
- VRAM
- disk reads
- total wall time

We specifically want to see whether the engine gets faster in a way that survives a restart.

---

## 10. Phase 6 - KV Reuse and Multi-turn Chat

v1.12.0 includes previous-turn KV reuse for Qwen3.6.

Test a realistic conversation:

1. give a 1-3k token document/code sample
2. ask question A
3. ask follow-up B
4. ask follow-up C that depends on the same context

Control run: repeat the same conversation with a fresh context per turn (or
KV reuse disabled, if upstream exposes a flag). The delta between the two
runs isolates KV-reuse value from other warm effects.

Compare:

- first-turn prefill
- second-turn latency
- third-turn latency
- generated tok/s

The interesting number is not only decode speed. For local coding/analysis work, avoiding repeated long prefill may matter more.

---

## 11. Phase 7 - OpenAI-Compatible API

Start the local server:

```powershell
coli.cmd serve --model C:\Models\qwen36_i4_gs64
```

Verify:

- server startup
- models endpoint if exposed
- chat completion
- streaming
- multi-turn conversation
- error behavior
- clean shutdown

Then test it from a tiny client rather than only the bundled UI.

This is the integration gate for later experiments with local tools.

---

## 12. Phase 8 - Brio

Brio is one of the most interesting Colibrì-specific tests.

Instead of generating free text, give the model a closed decision set and inspect probability plus entropy.

First test:

```text
ALLOW | REVIEW | DENY
```

Candidate inputs:

- code review summary
- CI/policy evidence
- security rule evaluation
- synthetic Causal Core-style verdict cases

Questions to measure:

- latency versus normal generation
- probability separation
- entropy on obvious cases
- entropy on intentionally ambiguous cases
- stability across repeat runs

### Minimum Brio dataset

Create at least:

- 10 obvious ALLOW cases
- 10 obvious DENY cases
- 10 ambiguous REVIEW cases

Do not judge Brio from three cherry-picked examples.

The output should be stored as structured JSON for later analysis.

---

## 13. Phase 9 - Thermal / Laptop Reality Check

A gaming laptop benchmark that lasts 20 seconds can lie.

Run one sustained generation session for at least 15 minutes.

Record every few minutes:

- tok/s
- GPU temperature
- GPU clock
- GPU power
- CPU temperature
- CPU clock
- fan behavior if observable

Useful command:

```powershell
nvidia-smi --query-gpu=timestamp,temperature.gpu,power.draw,clocks.sm,memory.used,utilization.gpu --format=csv -l 5
```

Check for:

- thermal throttling
- speed decay
- unstable CUDA behavior
- excessive noise/power for the achieved throughput

A fast first minute followed by throttling is not the same result as sustained performance.

---

## 14. Phase 10 - Quality Sanity Check

Performance is useless if the chosen quantization materially damages output.

Use a small fixed prompt set:

- C# reasoning
- SQL
- Python
- Ukrainian
- instruction following
- structured JSON

Check:

- obvious regressions
- loops/repetition
- broken structured output
- language degradation
- refusal/instruction-following anomalies

This is not meant to replace a full academic benchmark. It is a practical regression screen.

---

## 15. Phase 11 - Compare With a Simpler Runner

Colibrì must justify its complexity.

Comparison stack, pinned 2026-09-21:

- runner: llama.cpp (Ollama is acceptable if its Qwen3.6 support is more convenient — pick one and stay with it)
- model: `unsloth/Qwen3.6-35B-A3B-GGUF`, Q4_K_M quant (`ggml-org/Qwen3.6-35B-A3B-GGUF` is the official mirror if unsloth's layout misbehaves)

Download the comparison GGUF together with Phase 1 so this phase cannot be silently skipped at the end.

Compare:

- setup time
- disk use
- RAM
- VRAM
- TTFT
- tok/s
- API usability
- stability
- multi-turn behavior

Exact numerical equality is not required if the quantization/container differs, but the comparison must note that limitation.

The key question:

> Does Colibrì's memory hierarchy give us something materially useful on this machine that a simpler stack does not?

---

## 16. Phase 12 - Optional Large-model Experiment

Only after Qwen3.6 is understood.

Candidate: GLM-5.x through Colibrì.

Reason to try:

- validate the headline claim that very large MoE models can run on consumer hardware

Reasons not to start there:

- roughly 370+ GB model footprint
- heavy NVMe traffic
- decode can become disk-bound
- likely far slower than Qwen3.6 on a laptop

Success criterion for this phase is different:

> technical feasibility and architectural learning, not daily usability.

Do not spend hundreds of GB on this phase unless the Qwen3.6 results make the engine itself interesting enough.

---

## 17. Result Files

Keep raw results.

Suggested structure:

```text
results/
  environment.json
  cpu/
  cuda/
  placement/
  warm-cache/
  kv-reuse/
  brio/
  thermal/
  comparison/
```

Every benchmark result should contain:

```json
{
  "timestamp": "",
  "colibriVersion": "",
  "colibriCommit": "",
  "model": "",
  "modelRevision": "",
  "mode": "",
  "promptId": "",
  "promptTokens": 0,
  "generatedTokens": 0,
  "ttftSeconds": 0,
  "decodeTokensPerSecond": 0,
  "wallSeconds": 0,
  "ramPeakGb": 0,
  "vramPeakGb": 0,
  "expertHitRate": null,
  "notes": ""
}
```

Raw logs are more valuable than a hand-written "felt fast" note.

---

## 18. Final Decision

At the end, write `docs/final_results.md`.

Required conclusion:

### KEEP

Use when Colibrì offers practical value on this laptop:

- good sustained performance
- meaningful CUDA/warm-cache wins
- acceptable operational complexity
- useful API/Brio functionality

### LAB ONLY

Use when the architecture is genuinely interesting but:

- setup is too complex
- performance is marginal
- heat/power is poor
- simpler runners are more practical

### DROP

Use when:

- speed is poor
- GPU tier adds little
- reliability is weak
- complexity is not justified

No "promising" conclusion without numbers.

---

## 19. First Execution Order

The first pass should stay small:

1. capture machine specs
2. clone/pin Colibrì v1.12.0
3. download Qwen3.6 int4-gs64
4. run doctor/deep doctor
5. CPU baseline
6. build/enable CUDA tier
7. CUDA baseline
8. cold/warm comparison
9. `plan` and `tune`
10. KV reuse
11. Brio
12. 15-minute thermal run
13. compare with simpler runner
14. decide whether a giant-model experiment is worth the disk space

That sequence gives useful answers early and avoids spending 370+ GB merely to discover that the engine is not a good fit for the laptop.
