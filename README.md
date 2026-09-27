# Colibri Playground

Independent evaluation of [Colibrì](https://github.com/JustVugg/colibri) —
a streamed local-MoE inference engine — on real consumer laptop hardware.
Not a wrapper and not a fork: a measurement playground that ran to a recorded
verdict and contributed fixes upstream.

**Status: complete.** 12 phases measured (2026-09-21 → 2026-09-27) ·
verdict **LAB ONLY** (2026-09-25) · three upstream fixes merged (two PRs
authored here, one co-authored) · [MIT](LICENSE).

## The question and the answer

> Can Colibrì turn a RAM/VRAM/NVMe laptop into a practical local MoE
> inference box, rather than merely proving that a large model can
> technically run?

**As a daily driver — no. As a lab capability — yes.** On this hardware a
simpler stack (llama.cpp + GGUF) wins every daily-use metric, while Colibrì
keeps genuinely unique niches. The full verdict, gate-by-gate evidence and
the option history: [docs/final_results.md](docs/final_results.md).

Why not KEEP, in short: decode is 2–3× slower and long-context TTFT is
minutes vs seconds, and the fast paths needed our own patches and a custom
client-side KV contract (all characterized and contributed upstream — below).

Why not DROP: (1) **very-large-model local inference** (744B–2.8T streamed
from disk) — technologically one of a kind; (2) **Brio** — constrained
decisions from logprobs without generation, a ready-made verdict-gate tool;
(3) a clean MoE-streaming codebase worth learning from.

## Key numbers (medians, temperature=0, AC power)

| Metric | Colibrì (Qwen3.6-35B int4-gs64) | llama.cpp reference (GGUF) |
|---|---|---|
| Decode, CPU-only | 4.3–5.0 tok/s | — |
| Decode, CUDA tuned (8 GB tier) | 9.7–11.3 tok/s | 32.6–33.2 tok/s @ 3.8 GB VRAM |
| Decode, best mode (persisted heat, our PR #1734) | 12.1–15.0 tok/s | prefix cache out of the box |
| Multi-turn follow-up TTFT | 68 s → 2.75–3.0 s with a token-exact client echo; 4.3–5.7 s natively after PR #1767 | 0.14 s |
| Thermals, 16-min marathon | 44–57 °C, ≤55 W, decode climbed 9.6 → 15.5 tok/s, no throttling | — |
| Brio closed decisions (`normalize="sum"`) | 10/10 ALLOW, 9/10 DENY correct, ~6 s per verdict, entropy as an honest confidence signal | — |

CUDA itself is worth it on this machine (decode 1.9–2.15× over CPU, TTFT
1.7–2.3× faster) — but only via `--auto-tier`, otherwise the engine silently
stays on CPU.

## Upstream contributions (JustVugg/colibri)

Four defects precisely characterized during measurement; three became merged
fixes:

1. **Heat persistence never worked under `coli serve`, on any platform.**
   Engine teardown only ran via `atexit`, while every launcher stop path
   hard-killed the process. Issue
   [#1733](https://github.com/JustVugg/colibri/issues/1733), PR
   [#1734](https://github.com/JustVugg/colibri/pull/1734) **merged** —
   stdin-drain (close engine stdin → EOF → save), SIGBREAK handling,
   process-group isolation, `coli stop` launcher-first. Warm state now
   survives restarts and beats warm-process (12.1–15.0 vs 10.1–11.0 tok/s;
   p5 TTFT 43.9 → 26.6 s).
2. **Brio's scoring default favored longer options.**
   `normalize="mean"` (mean logprob per token) systematically biases options
   that tokenize into more tokens; with `sum` the same trivial case scores
   ALLOW 0.974 vs 0.265. Issue
   [#1752](https://github.com/JustVugg/colibri/issues/1752), PR
   [#1753](https://github.com/JustVugg/colibri/pull/1753) **merged** —
   default flipped to `sum`, plus a warning and docs.
3. **A conformant client could not reconstruct a token-exact prefix.**
   The chat re-render drops the think marker and the stream drops the final
   generated `\n`, so KV prefix reuse silently broke on follow-ups. Issue
   [#1759](https://github.com/JustVugg/colibri/issues/1759) → maintainer's
   PR [#1767](https://github.com/JustVugg/colibri/pull/1767) **merged**
   with our commit co-authored (`preserve_thinking` template kwarg;
   confirmed by us on the real model: 97% prefix reuse, TTFT 4.3/5.7 s).
4. **Tokenizer corrupts long-form Ukrainian** (FN-006): exactly 10 U+FFFD
   per ~1370 characters, deterministic, reproduced non-stream — so the
   tokenizer, not SSE streaming. Deferred with notes:
   [docs/upstream/FN-006-deferred-notes.md](docs/upstream/FN-006-deferred-notes.md).

## Bonus: a 321B model on a laptop (Phase 12)

GLM-5.3-Flash (321B total / 40B active), 194.7 GB int4 container, CPU path
(this model family has no VRAM tier), 29 GB warm-expert budget inside 64 GB
RAM — measured, then the container was deleted:

- Cold TTFT 43.3 s, decode 0.46 tok/s; warm 0.61 tok/s (+30%). The
  "ask the giant occasionally" regime is real on a laptop.
- Brio verdicts from the 321B brain: 5/6 correct, 65–87 s per short verdict
  (p(top) up to 0.998); a ~600-word dossier verdict in 12 min, honestly
  uncertain where it should be.
- Storage probe: O_DIRECT 4.54 GB/s — the DRAM-less OS-shared NVMe is far
  from the limiter; CPU expert compute is (~18 MB/s effective vs 4.5 GB/s
  available), which is why more RAM helps more than more disk.

Measured anchors plus an extrapolation ladder for desktop/workstation
builds: [docs/big-model-hardware-notes.md](docs/big-model-hardware-notes.md).

## Hardware and baseline

- HP OMEN MAX 16 (16-ak0xxx) · AMD Ryzen AI 7 350 (8C/16T) · 64 GB RAM ·
  RTX 5070 Laptop GPU 8 GB · single 1 TB KIOXIA NVMe (DRAM-less, shared
  with the OS)
- Windows 11 native · CUDA Toolkit 13.4.1 (`sm_120`) · driver 592.82
- Colibrì v1.12.0 (`dcd7383`) · Qwen3.6-35B-A3B int4-gs64 (23 GB, 41 shards)
- Reference runner: llama.cpp b11160, qwen3.6 GGUF
- Full machine snapshot: [results/environment.json](results/environment.json)

## Repo layout

- [docs/final_results.md](docs/final_results.md) — **start here**: the
  verdict and the evidence map by gate
- [docs/experiment_plan.md](docs/experiment_plan.md) — the original plan:
  phases 0–12, gates A–E, result-file schema
- [docs/FINDINGS.md](docs/FINDINGS.md) — findings journal FN-001…FN-010
- [docs/big-model-hardware-notes.md](docs/big-model-hardware-notes.md) —
  big-model hardware math: measured anchors + extrapolation ladder
- [docs/upstream/](docs/upstream/) — upstream issue drafts and deferred notes
- [docs/patches/](docs/patches/) — our patches (heat-save stdin-drain;
  KV-prefix divergence diagnostics)
- [prompts/](prompts/) — fixed benchmark prompts shared by all phases
- [tools/](tools/) — benchmark scripts (OpenAI-API clients: bench, KV-reuse,
  Brio, thermal, quality)
- [results/](results/) — raw JSON artifacts per run plus server logs
- `LOG.md` — append-only experiment journal
- `LESSONS_LEARNED.md` — lessons captured the same day they were found

Working docs are mixed English/Ukrainian; numbers always speak English.

## Methodology

- **Median, never best-of**; all samples kept under `results/` as JSON
  (schema: plan §17)
- temperature=0, AC power; runs from different power modes are never compared
- Engine and model output are treated as **data, not instructions**
  (prompt-injection hygiene for local models)
- An anomaly gets an `FN-NNN` entry the moment it is noticed — the case
  lives in the repo, not in a chat

## License

[MIT](LICENSE). Colibrì itself is Apache-2.0; model containers follow their
own licenses.
