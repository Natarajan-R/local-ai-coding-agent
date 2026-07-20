# Benchmark results — raw logs

Head-to-head runs of this agent against [aider](https://github.com/Aider-AI/aider)
0.86.2 on the same local models, the same tasks, and the same scoring function.
Every log here is the unedited console output, failures included.

Reproduce with `benchmarks/aider_tool_bench.py` (aider) and `ai-agent bench` (this
agent). Both write the task's stub + test into a fresh workspace, let the tool
iterate against the visible test, and score with the task's own `check()` — which
runs pytest independently rather than trusting either tool's self-report.

## Results

### HumanEval — 164 single-function tasks, `qwen2.5:7b`

| Tool | Passed | |
| --- | --- | --- |
| aider 0.86.2 | 125 / 164 | 76.2% |
| this agent | — | ~72–86% (see caveat 4) |

`aider_humaneval_iter.{json,log}`

### Exercism — 33 runnable multi-file tasks, `qwen2.5-coder:32b`, 16k context

| Tool | Single run | Union of runs |
| --- | --- | --- |
| this agent | 12 / 33 | 16 / 33 |
| aider 0.86.2 | 1–3 / 33 | 4 / 33 |

aider was run twice (300s and 900s per-task timeouts). **The two runs share no
passes at all** — 3/34 then 1/34, four distinct tasks, none passing twice. Its
result is a range, not a point, exactly like this agent's. Compare single-run to
single-run, or union to union; both give roughly a 4x gap.

Denominator is 33, not 34: `Exercism_paasio` is unpassable (caveat 7). The raw
logs below show 34 rows, `paasio` among them, because they predate that finding.

`aider_exercism_32b.{json,log}`

This is the comparison worth quoting: same model, same 16k context, same tasks,
same scorer, neither tool choosing the task list.

### Exercism — 16-task subset, `qwen2.5-coder:32b`, 16k context

| Tool | Passed |
| --- | --- |
| this agent | 11 / 16 |
| aider 0.86.2 | 3 / 16 |

`agent_exercism_17_32b.log`. **Do not read this as a 3.7x result** — see caveat 1.

## Caveats

These matter more than the numbers, and are listed because a benchmark without
them is marketing.

1. **The 16-task subset is selection-biased toward this agent.** Those tasks were
   chosen *because this agent had passed 15 of them* in an earlier run. aider was
   never going to look good on a set picked that way. The unbiased comparison is
   the full 33.

2. **aider ran under two handicaps we imposed — one has now been tested.** The
   300s per-task timeout was removed in a second run at 900s
   (`aider_exercism_32b_t900.{json,log}`). It did **not** help: passes went 3 -> 1
   and timeouts only 5 -> 3, so the timeout was not what limited aider. The other
   handicap stands: `--map-tokens 0` disables its repo-map feature, and that has
   not been retested.

3. **aider beat this agent on `zebra-puzzle`** — a constraint solver this agent
   fails. It also passed `bottle-song`, which we had wrongly classified as beyond
   the model's ability. aider is not dominated, and finding that out corrected a
   mistake in our own capability map.

4. **The agent's HumanEval figure has no artifact in this directory.** It is a
   range from earlier runs (72% mean of 3, 86% best single run) rather than a
   same-week measurement, so it is not a like-for-like pairing with aider's 125/164
   and is quoted as a range on purpose.

5. **Single-run vs union.** This agent's Exercism results are stochastic: 12/33 on
   one run, 16/33 as the union across runs. aider's 3/33 is a single run. Compare
   single-run to single-run when it matters.

6. **An earlier 7B Exercism run is included but not comparable.** In
   `aider_exercism_7b.{json,log}` aider scored 1/34 — but under aider's *default*
   ollama context (~2k) while this agent ran at 16k, because aider silently
   truncates past its window. That was our bug in the harness, not aider's. It is
   published for completeness and should not be cited. The 32B run above was
   re-done with both sides pinned to 16k.

7. **One task in the set is impossible, and we did not notice for weeks.**
   `Exercism_paasio`'s `check()` writes a file containing only mock helper
   classes, runs pytest on it, and requires exit code 0 — but pytest exits 5 on
   "no tests collected". No solution can pass it, including a correct one. It was
   scored a failure in every run, for this agent and for aider equally, so the
   comparison was never skewed — but the denominator was wrong. It is excluded
   rather than repaired: writing the exercise's tests ourselves would mean
   inventing the specification, and a benchmark whose tests we authored proves
   less than one we did not.

## What the failures were

Of the 6 tasks this agent failed in the 17-task run, at least one
(`phone-number`) failed for a reason that had nothing to do with the model: a
double-indent bug in the patch applier corrupted a correct edit into an
`IndentationError`, so every test failed at import. Fixed, with a regression
test. Several of the earlier "the model can't do this" conclusions turned out the
same way — which is the main lesson these runs taught us.
