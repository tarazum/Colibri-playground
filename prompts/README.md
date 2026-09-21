# Fixed Benchmark Prompts

Shared by every phase (CPU/CUDA, cold/warm, comparison). Referenced by
`promptId` in results JSON.

| id | file | purpose | expected output |
|---|---|---|---|
| p1 | `p1_short_factual.txt` | minimal prefill, decode-dominated | 1-2 sentences |
| p2 | `p2_explanation.txt` | mid-length structured generation | ~400 words |
| p3 | `p3_code.txt` | code correctness, structured output | function + 5 tests |
| p4 | `p4_ukrainian.txt` | Ukrainian quality and fluency | ~300 words |
| p5 | `p5_long_prompt_short_answer.txt` | prefill-dominated, retrieval from context | 1-2 sentences |

Rules:

- files are plain prompt text — pipe them straight into the runner
- **never** edit a file after the first benchmark that used it; add a
  `*_v2.txt` instead and record which version each result used
- p3 correctness can be verified mechanically by running the generated tests
- p5's answer is checkable against facts in the report (pool 20 → 64;
  worst p99 = 840 ms)
