# Big-model Colibrì: hardware notes (laptop disk upgrade vs gaming PC / RAID)

Date: 2026-09-26 · Context: verdict LAB ONLY recorded; this is the
"Phase 12 (optional large-model experiment)" feasibility thinking.
Provenance: numbers marked [measured] come from this playground's runs
(Qwen3.6-35B int4-gs64, RTX 5070 Laptop 8 GB, 64 GB RAM, single DRAM-less
KIOXIA 1 TB NVMe shared with the OS); numbers marked [upstream] come from
JustVugg/colibri docs/README; everything else is extrapolation — honest
engineering guesses, to be replaced by Phase 12 measurements.

## 1. What the engine needs (bottleneck math)

Streamed MoE decode ≈ how fast routed-expert weights arrive, minus cache:

- GLM-5.2/5.3 (744B): ~14.2 MB per expert, ~8 active experts/token
  [upstream, source comment] → **~114 MB read per generated token** at
  zero cache hit; dense parts stay resident in RAM.
- The lever chain, in order of strength:
  1. **RAM** — hot-expert cache + learned heat (persistence fixed by our
     merged PR #1734). Hit rate directly subtracts from disk traffic;
     sustained same-domain work warms up dramatically [measured: our
     thermal marathon climbed 9.6→15.5 tok/s on the 35B as the tier
     filled].
  2. **Independent NVMe devices** — the engine has native dual-SSD
     striping [upstream]; independent queues beat one shared disk.
  3. **VRAM tier** — trunk + hottest experts; multi-GPU supported
     [upstream: 2× 8 GB → 10 tok/s on qwen36].
  4. CPU cores/IPC for the expert matmuls that do arrive.
- Streaming efficiency is far below sequential-paper numbers (high-QD
  ~14 MB reads, O_DIRECT, cold misses at every layer). Calibration point
  [measured]: our laptop cold decode 3.6–4.2 tok/s on the 35B ≈ 1.8 MB
  ×10 experts ≈ ~70–80 MB/s effective — a few % of the disk's paper
  bandwidth, with the OS sharing the drive.

## 2. Laptop + big disk (the original question)

- **Slots**: OMEN MAX 16 spec sheets reference a SINGLE M.2 (Gen4 or
  Gen5 by SKU, up to 4 TB) [hp.com]; for our exact 16-ak0xxx verify in
  the Maintenance & Service Guide. Plan = REPLACE 1 TB with 2–4 TB, not
  add a second.
- What fits: GLM-5.3-Flash 321B (~195 GB) fits even TODAY (~443 GB free
  [measured]); GLM-5.2/5.3 744B (~372–419 GB) fits on a 2 TB drive;
  Kimi K3 (~1.6 TB) fits a 2 TB drive alone.
- Expected speeds: Flash 321B — well under 1 tok/s cold, better with
  warm heat (our 64 GB RAM is the strong card); 744B — [upstream
  datapoints on weaker boxes: 0.05–0.1 tok/s; our RAM + working heat
  persistence improves, but not to interactive]. Long-prompt TTFT:
  minutes.
- Verdict for the laptop: **"ask the giant once" regime** — Brio
  verdicts / one-shot plans. Not chat. Phase 12's plan criterion
  ("technical feasibility and learning, not daily usability") matches.

## 3. Gaming PC (the new question) — can it be made fast?

Yes, materially faster — and the biggest lever is NOT RAID:

- **RAM first**: a desktop with 128–192 GB DDR5 holds a third-to-half
  of the 744B hot set (or ALL of Flash 321B's experts after learning).
  Sustained same-domain decode multiplies with hit rate; this is the
  single strongest upgrade.
- **Disks second — engine striping beats RAID**: the access pattern is
  high-queue-depth ~14 MB reads. The engine's own dual-SSD striping
  [upstream] across two INDEPENDENT NVMe drives (two controllers, two
  queues) is the documented and usually better path; classic RAID0
  bundles them behind one abstraction with less gain than expected,
  and parity RAID buys nothing for read-mostly model storage. If RAID
  anyway: plain RAID0 across 2–4 Gen4/Gen5 drives WITH DRAM buffers,
  and no RAID card in the middle (CPU/software only).
- **GPU third**: 16–24 GB card (or a used 24 GB) as the CUDA tier for
  trunk + hottest experts; multi-GPU is supported.
- **Realistic ladder** (2× 2–4 TB Gen4/5 + 128–192 GB RAM + 24 GB GPU,
  extrapolated): Flash 321B ≈ 1–3 tok/s sustained same-domain, TTFT tens
  of seconds; 744B ≈ 0.2–0.5 tok/s cold→better warm — still "ask
  occasionally". **Full residency of 744B needs ~400 GB RAM —
  workstation class (Xeon-W/Threadripper), a different budget league.**
- **The further step**: Colibrì has local cluster mode across machines
  (Segment/Edge ABI) [upstream] — two networked boxes can pool disks
  and RAM before anyone buys a 400 GB workstation.
- **Cost-effectiveness caveat** [measured, Phase 11]: for DAILY work, a
  24 GB GPU PC running a 70B-class GGUF fully in VRAM (llama.cpp,
  5–15+ tok/s) beats streaming-744B on every speed metric. The
  big-model path buys MODEL CLASS (a brain no consumer GPU can hold),
  not tokens-per-hryvnia. Both can coexist on the same box.

## 4. If we ever run Phase 12

1. Start WITHOUT new hardware: Flash 321B fits today's free space
   (~195 GB of ~443 GB) — measure cold/warm/Brio on the laptop, build
   the extrapolation baseline.
2. Only then decide the disk: 2–4 TB single-slot replacement (laptop)
   or the gaming-PC route (RAM → disks → GPU, in that order).
3. Success criterion per plan §16: feasibility + learning, not daily
   usability.

## Sources

- HP OMEN MAX 16 storage specs & SSD upgrade guide — hp.com
- Upstream model sizes/tiers/striping/cluster — JustVugg/colibri README,
  docs/, and source comments (v1.12.0 dcd7383 / dev)
- All [measured] figures — this repo, results/ (Phases 2–11)
