# Colibri Playground

Research playground for evaluating [Colibrì](https://github.com/JustVugg/colibri) on consumer laptop hardware.

The first target is **Qwen3.6-35B-A3B** with the recommended **int4-gs64** container, running on a Windows laptop with an **RTX 5070-class Blackwell GPU / 8 GB VRAM** and local NVMe storage.

## Core Question

> Can Colibrì turn a RAM/VRAM/NVMe laptop into a practical local MoE inference box, rather than merely proving that a large model can technically run?

We care about practical use, not just successful startup.

## What We Will Measure

- CPU-only baseline
- CUDA acceleration on 8 GB VRAM
- cold vs warm decode
- expert-cache learning between runs
- automatic placement and tuning
- prompt prefill and follow-up latency
- KV reuse on multi-turn conversations
- sustained thermals on a laptop
- OpenAI-compatible API usability
- Brio constrained decisions
- comparison with a simpler local runner where possible

## First Model

**Qwen3.6-35B-A3B**

Recommended Colibrì container:

`Kreuzzelg/qwen36-35b-a3b-colibri-i4-gs64`

Why first:

- ~35B total / ~3B active parameters
- ~20-22 GB model container
- specifically supported by Colibrì
- documented CUDA VRAM tier
- real upstream measurements exist on 8 GB GPUs
- much more useful for a laptop evaluation than starting with a ~370 GB GLM-5.x experiment

Large-model experiments such as GLM-5.x are explicitly **Phase 2**, not the starting point.

## Experiment Plan

See [docs/experiment_plan.md](docs/experiment_plan.md).

## Upstream Baseline

Initial baseline:

- Colibrì: **v1.12.0**
- baseline date: **2026-09-21**
- OS path: Windows native first
- primary GPU path: CUDA
- primary model: Qwen3.6-35B-A3B int4-gs64

We should record the exact upstream commit for every benchmark run.

## Decision

At the end, classify the result as one of:

- **KEEP** — useful enough for regular local work or integration experiments
- **LAB ONLY** — technically interesting, but not worth using as a normal local inference path
- **DROP** — complexity/performance tradeoff is not competitive on this machine

The decision must be based on measured results, not on architecture appeal.
