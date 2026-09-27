# Reply draft for #1759 (NOT posted; awaiting owner approval)

Re-ran the 3-turn dossier on `acf7044` (PR #1767), real model
(Qwen3.6-35B-A3B int4-gs64, 23 GB), RTX 5070 Laptop 8 GB, CUDA tier,
temperature=0, plain standard-client echo (no `preserve_thinking` in the
request, no client-side workarounds):

```
[PREFIX] reusing 940 of  972 prompt tokens (97%)
[PREFIX] reusing 1024 of 1058 prompt tokens (97%)
```

Turn-2/3 TTFT: 4.3 s / 5.7 s (the same conversation re-prefilled every
turn at ~96-100 s before). Turn-1 cold TTFT was 157 s in this run — the
page cache was still cold after an unrelated 195 GB experiment; not part
of what's under test, noted for honesty.

Nice find on `preserve_thinking` — we had rendered the template only
with its defaults, so the kwarg never showed itself; the model card
naming KV utilization makes this the template's own answer rather than
a carve-out. Our exploratory branch (tarazum:fix/qwen36-kv-roundtrip)
is superseded by this; feel free to drop it from consideration — #1767
is the better implementation (conformance in both modes, plus the two
cases the old default got wrong).

Confirmation: real-model numbers above; your tiny fixture + these
lines cover the matrix.
