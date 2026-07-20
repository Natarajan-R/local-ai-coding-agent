# The Capability Envelope: What a Local Model + This Harness Can Actually Do

This chapter reports a measured answer to the question every reader will ask:
*how far does a local model actually get, and where is the ceiling — the model,
or my code?* We answer it with numbers, not vibes, and we show the exact
experiment that separates the two.

## The headline numbers

Two benchmarks, run through the full agent (planner → editor, Docker sandbox,
real test execution):

| Benchmark | Model | Score |
|---|---|---|
| HumanEval (164 tasks) | `qwen2.5:7b` + harness | ~86% single run, ~72% mean-of-3 |
| Exercism/aider (34 tasks) | `qwen2.5:7b` | 1 / 34 |
| Exercism/aider (34 tasks) | `qwen2.5-coder:32b` | 12 / 34 |

The 7B is strong on HumanEval (short, self-contained functions) and nearly
helpless on the aider set (multi-file, stateful, exact-output tasks). Moving to
the 32B took the aider score from 1 to 12. The obvious next thought — *rent a
70B and buy more* — is the one this chapter argues you should resist, because we
can measure whether it would help.

## The trap: "the model failed, so it's the model's ceiling"

When the agent fails a task, it is tempting to blame the model. But the agent is
not the model — it wraps the model in a loop that sees test failures and edits
in response. A failure could be the *model* (can't reason to the answer) or the
*harness* (the model could, but the loop lost it). Conflating these wastes money:
you buy a bigger model to fix what was a free code bug.

To separate them we built a **bare-model probe** (`benchmarks/bare_probe.py`):
call the model **directly**, one shot, no agent loop, extract its code, and
score it with the task's real `check()`. It runs in seconds and costs ~1/100th
of a full agent run.

## The mistake, and the control that caught it

The first probe run withheld the test file from the model and reported **0
harness bugs, 22 model-ceiling** across the 22 failing tasks. Clean story —
and wrong.

The control that caught it: run the **same probe on the 12 tasks the agent
PASSES.** If the probe is a valid proxy for agent capability, it should pass
most of them. It passed **1 of 12.** The probe was failing 11 tasks the agent
solves — so "the probe failed it" told us almost nothing.

The reason was a confound: in the real benchmark the agent has the **test file
in its workspace** and iterates against it. The probe had neither the test nor
iteration. It was measuring a strictly harder thing than the agent faces.

## The fix: give the probe what the agent has

We added a `--with-test` mode that shows the model the test file — matching the
agent's information — still one-shot. Now a bare **PASS** means the model *can*
reach the answer when it sees the target, so any agent failure on that task is
in the **iteration loop** (recoverable), not the model. Re-running on the 22:

| Bucket | Count | Tasks |
|---|---|---|
| **RECOVERABLE** (model solves with test; agent fails) | **5** | dot-dsl, go-counting, grep, hangman, tree-building |
| **MODEL CEILING** (fails even one-shot with the test) | 17 | book-store, bottle-song, bowling, connect, food-chain, forth, poker, pov, react, rest-api, scale-generator, sgf-parsing, two-bucket, variable-length-quantity, wordy, zebra-puzzle, zipper |

All 17 ceiling failures were genuine (code ran, tests failed) — zero extraction
artifacts. All 5 recoverable passes ran the real test suite.

## What the map means

Reading the full 34:

- **12 pass today.**
- **5 are recoverable** — free wins living in the iteration harness (the
  context-trimming / traceback-preservation path). Fixing them targets
  ~17/34 with no model change and no spend.
- **17 are model-ceiling** — the 32B cannot produce a passing solution even
  handed the test one-shot. These cluster into genuinely hard categories:
  recursive-descent parsers (`forth`, `sgf-parsing`), constraint solvers
  (`zebra-puzzle`, `two-bucket`, `poker`), and stateful/reactive systems
  (`react`, `zipper`, `pov`, `rest-api`). No harness change recovers these;
  only a stronger model *might*, with no guarantee.

## The money decision

The envelope makes the spend decision concrete:

- The **5 recoverable** cost nothing — they are code, in the loop you already own.
- The **17 ceiling** tasks fail with maximum information (test in hand, one shot).
  A larger model is the only possible lever and an uncertain one; these are hard
  reasoning problems, not formatting slips.

So the high-ROI path is: **fix the iteration harness to bank the 5, re-measure,
and stop.** Renting a bigger model to chase the 17 is real money against an
uncertain, possibly small, gain. The honest ceiling — ~86% HumanEval, and on the
harder aider set a realistic 12→17 of 34 — is a truer and more useful thing to
tell a reader than a score bought with a model they can't run at home.

## A hypothesis we checked and dropped

We noticed the passing-set logs were far larger than the failing-set logs and
wondered if the model simply *writes more* for solvable tasks. Measured directly
(the probe records response chars and code lines per task): recoverable tasks
averaged only slightly more output than ceiling tasks (62 vs 53 code lines), and
the single longest solution of all — `sgf-parsing`, 105 lines — **failed**. The
log-size gap was mostly pytest traceback volume, not model verbosity. Output
length does not predict success. We report it because a benchmark chapter that
only shows the hypotheses that worked is not measuring — it is marketing.

## How to reproduce

```bash
# raw one-shot capability (no test shown):
python benchmarks/bare_probe.py --host <ollama> --model qwen2.5-coder:32b \
    --tasks-file benchmarks/probe_targets.txt

# fair split vs the agent (test shown, matches the agent's workspace):
python benchmarks/bare_probe.py --host <ollama> --model qwen2.5-coder:32b \
    --tasks-file benchmarks/probe_targets.txt --with-test
```

Keep `--num-ctx 16384` (the default): a 32B fits 100% in a 24 GB GPU at 16k and
spills to CPU — several times slower — at 32k. Context size is a speed and cost
lever, not just a capacity one.
