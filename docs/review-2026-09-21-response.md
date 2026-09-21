# Response to review-2026-09-21 (R-001 … R-005)

Date: 2026-09-22
Verification: three-way — the original review (written against pushed
`71095fa`), our own source-level check against pinned v1.12.0, and an
independent read-only review by Claude Opus (`--model opus`, evidence quoted
with file:line; its claims were spot-checked by us in the source before
recording them here).

Context the review did not have: at the time it landed, the working tree
already contained uncommitted overnight work (engine built, gs64 banner
confirmed at runtime, serve smoke green, FN-003/FN-004 recorded).

## Verdicts

| Finding | Review claim | Our check | Independent (Opus) | Action taken |
|---|---|---|---|---|
| R-001 | build target is `qwen36.exe`, not `colibri.exe` | confirmed — we found the same overnight (FN-003); fix was already in the tree | **CONFIRMED** + registry evidence (`family_registry.py` `engine_artifact="qwen36"`); adds: `qwen36_tier.c` links only under CUDA flags | already fixed in plan; kept |
| R-002 | `IDOT_GS=1` advice wrong for qwen36 | confirmed — `qwen36.c` never reads it; knob is `QWEN_EXPERT_KERNEL` (default ON) | **CONFIRMED** + names a second knob `IDOT` (`qwen36.c:837`, opt-in int8 dot) the review missed | fixed in plan + open_items; root cause → FN-005 |
| R-003 | runner must go through persistent `coli serve` | confirmed — matches FN-004; per-sample process spawning destroys warm semantics | **PARTIAL** — `--prompt-file` exists only inside `coli run`'s deepseek-v4 branch; `has_cli_adapter=False` gates only `coli run`, chat remains a supported qwen36 path | `run_bench.py` docstring marked superseded; Phase 2 rewrite = serve + HTTP |
| R-004 | `COLI_TEMP=0`, seed claims, cold/warm-process/warm-persisted states | HEAT_FILE confirmed in `qwen36_tier.c` | **PARTIAL** — `COLI_TEMP` is launcher/server-side (`openai_server.py:2746`, default **0.7**), not engine-side; the bare engine loop is argmax-deterministic; no clock/PID seeding exists in `qwen36.c`; and **warm-persisted is CUDA-arm-only** (Makefile gate: `qwen36_tier.c` requires CUDA/CUDA_DLL=1) | protocol added to the plan: explicit `temperature=0` per request, state tags, CPU-arm caveat (no persisted heat on CPU) |
| R-005 | p3 touching-interval ambiguity | valid against `ff99798` | **REFUTED as of the working tree** — the clarifying sentence was added before the review landed; Status "Open" is stale | fixed in place (safe: no recorded benchmark had used p3) |

## Errors found in the review itself

1. Line 21 says "four items should be corrected" — five findings follow.
2. R-004's premise "unset seed = clock/PID based randomness" is not true for
   qwen36: no `srand`/clock seeding exists in `qwen36.c`; sampling
   non-determinism enters only through serve requests with temp > 0. This is
   the same engine-confusion class the review (rightly) flags in our docs.
3. R-004 defines `warm-persisted` without noting it cannot exist on the CPU
   arm — material for our Phase 5 planning (heat persistence moves to the
   CUDA phases).
4. R-003 implies adapter routing blocks the chat path; the flag only gates
   `coli run`.
5. R-002's correction removes the wrong knob but names no correct one; the
   actual qwen36 knobs are `QWEN_EXPERT_KERNEL` (`=0` → legacy int8 unpack)
   and `IDOT` (opt-in int8 dot).

## Net assessment

The review was worth running: it caught one genuine error of ours (R-002 —
recorded as FN-005 with the root cause), independently confirmed two things
we had already found overnight (R-001, R-003), and its two PARTIALs still
pointed in the right direction. The owner's caution was also justified: two
of its five findings contain factual errors of its own, found only because a
second independent model cross-checked the same source. Three-way
verification is now part of the process for external reviews.
