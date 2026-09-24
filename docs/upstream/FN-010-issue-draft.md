# Upstream draft 1 v2 — FN-010 (NOT filed; Opus-reviewed GO; awaiting owner approval)

Changes from v1 per the independent review: docs/brio.md updated in the PR
(default + example), and the draft now volunteers the full benchmark
picture (REVIEW 0/10 under sum, 63% overall, repeat instability) instead
of stopping at the headline. Known caveat: the mean-run artifacts were
overwritten by the sum rerun; the all-DENY numbers survive in our
experiment LOG (linked) and are reproducible in one pass with
`normalize: "mean"`.

---

**Title:** brio: `normalize="mean"` default silently favors multi-token
options — DENY answered all 30 benchmark cases

**Environment:** current dev, qwen36 int4-gs64, Windows / CUDA tier.

**What happens:** mean-logprob-per-token compares averages across options
of different token lengths; on any menu mixing token counts — which
closed-decision menus almost always do — multi-token options get a
systematic advantage.

Measured (30-case code-review benchmark, options ALLOW/REVIEW/DENY):

- default `mean`: **DENY on all 30**, incl. a one-word README typo fix
  (p=0.73); p(REVIEW)≈0.004. Cause: DENY=2 tokens vs ALLOW=1; vocabulary
  probes confirm the class (DISCUSS=3, MAYBE=2 won theirs).
- explicit `sum`: ALLOW 10/10 (p 0.96), DENY 9/10 — but REVIEW remains
  0/10 as a forced choice (its class carries the highest entropy, 0.64 vs
  0.17/0.36 — the honest confidence signal); overall forced-answer
  accuracy 19/30 = 63%. Per-choice probabilities wobble slightly across
  repeats (parallel fp noise); the chosen answer never flipped in 90
  scored calls.

**Fix (PR attached):** default `sum` in both request forms; `mean` stays
available for equal-token menus and now warns on stderr (naming counts)
when token counts differ; `docs/brio.md` updated (default + example);
tests: pinned default updated, two new tests (default is sum; warning on
unequal counts, quiet on equal). Minor known behavior: the schema form
warns once per field.

We are happy to re-run and attach the mean-arm artifacts if useful.
