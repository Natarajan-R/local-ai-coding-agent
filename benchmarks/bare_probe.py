#!/usr/bin/env python3
"""Bare-model probe — split HARNESS-loss from MODEL-ceiling on failing tasks.

Runs the MODEL DIRECTLY (one chat call, no agent loop, no tools) on each task,
extracts the code, and scores it with the task's own check(). Interpretation:

  bare model PASS  -> the model CAN solve it; the AGENT is losing it -> HARNESS BUG (fixable)
  bare model FAIL  -> the model genuinely can't -> MODEL CEILING (not a harness issue)

This is ~100x cheaper than a full agent run (one call/task, seconds) and gives a
clean split that a bigger-model full-run does NOT. Same technique that turned the
HumanEval failures into a fix-list.

Usage:
    python bare_probe.py --host http://localhost:11434 --model qwen2.5-coder:32b
    python bare_probe.py --host <32b-url> --model qwen2.5-coder:32b --tasks book-store,wordy
    python bare_probe.py ... --tasks-file /tmp/probe_targets.txt      # one name per line

Reads nothing but the task files; writes a JSON + a table to stdout. No agent, no
workspace mutation of the repo (uses temp dirs).
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent / "tasks"
VENV_BIN = str(Path(sys.executable).parent)  # so check()'s `python -m pytest` finds pytest


def _load(name: str):
    tid = name if name.startswith("Exercism_") else f"Exercism_{name}"
    spec = importlib.util.spec_from_file_location(tid, TASKS_DIR / f"{tid}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return tid, m


def _stub_name(files: dict) -> str:
    return next(k for k in files
               if not (k.startswith("test_") or k.endswith("_test.py")))


def _test_name(files: dict) -> str | None:
    return next((k for k in files
                 if k.startswith("test_") or k.endswith("_test.py")), None)


def _call_model(host: str, model: str, prompt: str, timeout: int, num_ctx: int) -> str:
    # num_ctx matters for SPEED and COST, not just capacity: a 32B at 16k fits
    # 100% in GPU VRAM; at 32k it spills to CPU (~17% CPU / 83% GPU on a 24GB card),
    # and the CPU-resident layers slow the whole generation several-fold. Keep it
    # at 16k so the model stays GPU-resident. 16k is ample for one-shot solutions.
    body = json.dumps({
        "model": model, "stream": False,
        "options": {"temperature": 0.1, "num_ctx": num_ctx},
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(f"{host.rstrip('/')}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["message"]["content"]


def _extract_code(text: str, stub: str) -> str:
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    code = (m.group(1) if m else text).strip()
    if "def " not in code and "class " not in code:   # model returned only a body
        code = stub + "\n" + code
    return code


def probe_one(name: str, host: str, model: str, timeout: int, num_ctx: int,
              with_test: bool = False) -> dict:
    tid, m = _load(name)
    stub_name = _stub_name(m.FILES)
    stub = m.FILES[stub_name]
    prompt = (
        m.TASK
        + f"\n\nThe file `{stub_name}` currently contains only this stub:\n"
        + f"```python\n{stub}\n```\n"
    )
    # --with-test matches what the AGENT sees: the exercism test file lives in the
    # agent's workspace, so a fair one-shot comparison must show the model the same
    # expected inputs/outputs. Withholding it (the default) measures raw one-shot
    # capability; including it isolates whether the failure is model-reasoning or
    # the agent's iteration loop.
    test_name = _test_name(m.FILES)
    if with_test and test_name:
        prompt += (
            f"\nYour solution must pass this test suite (`{test_name}`), which is run "
            f"UNCHANGED — implement to satisfy it, do not modify it:\n"
            f"```python\n{m.FILES[test_name]}\n```\n"
        )
    prompt += (
        "Implement it fully. Return ONLY the COMPLETE file (all imports + full "
        "working code) in a single ```python code block."
    )
    result = {"task": tid, "ok": False, "error": "", "raw_len": 0, "code_lines": 0}
    try:
        raw = _call_model(host, model, prompt, timeout, num_ctx)
        code = _extract_code(raw, stub)
        result["raw_len"] = len(raw)            # chars the model actually emitted
        result["code_lines"] = code.count("\n") + 1  # lines of extracted solution
        ws = Path(tempfile.mkdtemp())
        (ws / stub_name).write_text(code, encoding="utf-8")
        os.environ["PATH"] = VENV_BIN + ":" + os.environ.get("PATH", "")
        result["ok"] = bool(m.check(ws))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:120]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--model", default="qwen2.5-coder:32b")
    ap.add_argument("--tasks", default="", help="comma-separated task names")
    ap.add_argument("--tasks-file", default="", help="file with one task name per line")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--num-ctx", type=int, default=16384,
                    help="context size; 16384 keeps a 32B 100%% on GPU (fast). 32k spills to CPU.")
    ap.add_argument("--with-test", action="store_true",
                    help="show the model the test file too (matches what the AGENT sees); "
                         "a PASS here means the failure is RECOVERABLE (iteration/harness), not model-ceiling")
    ap.add_argument("--out", default="bare_probe_results.json")
    args = ap.parse_args()

    if args.tasks_file:
        names = [l.strip() for l in Path(args.tasks_file).read_text().splitlines() if l.strip()]
    elif args.tasks:
        names = [t.strip() for t in args.tasks.split(",") if t.strip()]
    else:
        print("Give --tasks or --tasks-file", file=sys.stderr); sys.exit(2)

    mode = "WITH the test file (fair vs agent)" if args.with_test else "one-shot, no test"
    # PASS means different things by mode: without the test a solve implies the agent
    # is losing a task the model can already do; with the test a solve implies the
    # model can reach the answer when it sees the target, so the agent's failure is
    # in the iteration loop (recoverable), not the model.
    pass_interp = ("RECOVERABLE (model solves WITH test → agent iteration should too)"
                   if args.with_test else "HARNESS BUG (agent loses a solvable task)")
    fail_interp = ("MODEL CEILING (fails even WITH the test in view)"
                   if args.with_test else "MODEL CEILING")
    print(f"Probing {len(names)} task(s) with bare {args.model} at {args.host} [{mode}]\n")
    print(f"{'TASK':30} {'BARE':6} {'raw':>6} {'ln':>4}  INTERPRETATION")
    print("-" * 78)
    results = []
    harness, ceiling = [], []
    for n in names:
        r = probe_one(n, args.host, args.model, args.timeout, args.num_ctx, args.with_test)
        results.append(r)
        if r["ok"]:
            verdict, interp = "PASS", pass_interp
            harness.append(r["task"])
        else:
            verdict, interp = "fail", (fail_interp + (f" [{r['error']}]" if r["error"] else ""))
            ceiling.append(r["task"])
        print(f"  {r['task']:28} {verdict:6} {r['raw_len']:>6} {r['code_lines']:>4}  {interp}")

    label = "RECOVERABLE (fix the harness)" if args.with_test else "HARNESS BUGS (fix these)"
    print("\n" + "=" * 78)
    print(f"{label} — bare model solves, agent fails: {len(harness)}")
    for t in harness:
        print(f"    {t}")
    print(f"MODEL CEILING — bare model also fails: {len(ceiling)}")
    if results:
        avg_raw = sum(r["raw_len"] for r in results) / len(results)
        avg_ln = sum(r["code_lines"] for r in results) / len(results)
        print(f"model output: avg {avg_raw:.0f} chars / {avg_ln:.0f} code lines per task")
    Path(args.out).write_text(json.dumps(results, indent=2))
    print(f"\nWrote {args.out}")
    print("NOTE: bare-model PASS is a lower bound (crude single-shot extraction). "
          "A PASS is real (check() runs the true test); some 'fails' may be "
          "extraction artifacts, so the harness-bug count can only go UP.")


if __name__ == "__main__":
    main()
