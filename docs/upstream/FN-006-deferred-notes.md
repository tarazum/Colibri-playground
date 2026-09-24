# FN-006 — deferred upstream candidate (owner decision 2026-09-25): detailed notes

## Defect (fully characterized)
- Long-form Ukrainian output from the qwen36 int4-gs64 container
  (`Kreuzzelg/qwen36-35b-a3b-colibri-i4-gs64`, ~23 GB, 46 files,
  `qwen36_meta.json: expert_gs=64`) carries exactly **10 U+FFFD replacement
  chars per ~1370 chars** — e.g. «проходи�ть», «математ��у».
- Deterministic: identical count and positions across cold/warm repeats at
  temperature=0 (side-proof that temp=0 gives byte-identical outputs).
- **Not streaming**: reproduces EXACTLY (same 10) in non-streamed mode →
  the corruption is in the tokenizer/detokenizer path, not the SSE layer.
- Scope: long-form Ukrainian prose only. English clean; SHORT Ukrainian
  answers (the whole 6-task quality battery, incl. constrained Ukrainian)
  are clean.
- Impact on benchmarks: none (speed unaffected); quality screen passes
  6/6 — this is a cosmetic-but-real quantization/tokenizer defect.

## Evidence artifacts
- results/cpu/transcripts/p4_*.txt (10 × U+FFFD each, cold+warm)
- results/quality/colibri/p4_nonstream.txt (the non-stream discriminator:
  same 10)
- results/quality/llama/* (same model class via GGUF: zero U+FFFD —
  different tokenizer deployment)

## Blame not yet assigned — the 10-minute discriminator to run BEFORE filing
Round-trip the same p4 text through the container's `tokenizer.json` with
a STANDARD tokenizer library (e.g. Python `tokenizers` offline):
- if encode→decode round-trip is clean there → the container file is fine
  and the defect is in the ENGINE's minimal tokenizer parser
  (`c/qwen36.c` reuses a minimal json.h parser per the source note at
  :67) → file against **JustVugg/colibri**;
- if the round-trip corrupts there too → the container's tokenizer.json
  (or the converter that produced it) is at fault → file against
  **kreuzzelg's container** (HF repo) and/or its converter path.

## Why deferred
Owner's call 2026-09-25: batch-2 upstream effort goes to FN-010 + FN-009
(user-facing correctness); FN-006 stays local until the discriminator is
run and the verdict document is settled. Impact is minor for our verdict
(LAB ONLY recommendation unaffected).

## If filed later
- Title direction: "gs64 container tokenizer corrupts long-form Ukrainian
  (10 × U+FFFD per ~1370 chars, deterministic, non-streaming)"
- Attach: both transcripts, the non-stream discriminator, the
  standard-tokenizer round-trip result.
- Same rule as always: draft → Opus review → owner approval → file.
