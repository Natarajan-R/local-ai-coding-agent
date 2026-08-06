#!/usr/bin/env python3
"""Aggregate signals from the agent's audit trail (logs/audit.jsonl).

Turns the raw per-event JSON-lines audit log into run-level outcomes and
cross-run signals: how runs ended (done / give-up / crash), why they crashed
(rate-limit vs bug), how many retries they burned, which runs thrashed (kept
reflecting with zero passing evaluations), token/time cost, and the most common
reflexion lessons.

Usage:
    python scripts/analyze_audit.py [audit.jsonl] [--grep SUBSTR] [--limit N]

    --grep   only include runs whose task text contains SUBSTR (case-insensitive)
    --limit  how many recent runs to list individually (default 15)
    --lessons how many top reflexion lessons to show (default 10)
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_RATE_LIMIT_RE = re.compile(r"429|too many requests|rate.?limit", re.IGNORECASE)


def _as_bool(v: Any) -> bool:
    """Coerce an audit field that may be a real bool or the string 'True'/'False'."""
    return v is True or (isinstance(v, str) and v.strip().lower() == "true")


@dataclass
class RunSummary:
    """Everything we can reconstruct about a single run from its audit events."""

    run_id: str
    task: str = ""
    model: str = ""
    workspace: str = ""
    final_state: Optional[str] = None
    retries: int = 0
    total_tokens: int = 0
    total_seconds: float = 0.0
    tool_calls: int = 0
    evaluations: int = 0
    evals_passed: int = 0
    reflexions: int = 0
    gave_up: bool = False
    no_progress: bool = False
    max_skipped: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    # One entry per evaluation: (passed, tests_failed-or-None). The failed count is
    # present only once the eval-delta logging change lands; older runs carry None.
    eval_seq: List[tuple] = field(default_factory=list)

    def convergence(self) -> str:
        """A compact per-run convergence trace + verdict from the evaluation sequence."""
        if not self.eval_seq:
            return "(no evaluations)"
        have_nums = any(f is not None for _, f in self.eval_seq)
        if have_nums:
            trace = "→".join("0" if p else (str(f) if f is not None else "?")
                             for p, f in self.eval_seq)
        else:
            trace = "·".join("P" if p else "F" for p, _ in self.eval_seq)
        last_passed = self.eval_seq[-1][0]
        if last_passed:
            verdict = "converged ✓"
        elif have_nums:
            fails = [f for _, f in self.eval_seq if f is not None]
            verdict = "converging" if len(fails) >= 2 and fails[-1] < fails[0] else "STUCK"
        else:
            verdict = "STUCK" if len(self.eval_seq) >= 3 else "failing"
        return f"{trace}   [{verdict}]"

    @property
    def outcome(self) -> str:
        """Classify the run: done / aborted / crash:rate_limit / crash:bug / give_up / running."""
        if self.final_state is None:
            return "running/incomplete"
        if self.final_state == "done":
            return "done"
        if self.final_state == "aborted":
            return "aborted"
        # final_state == "error": distinguish *why*.
        if any(_RATE_LIMIT_RE.search(str(e.get("error", ""))) for e in self.errors):
            return "crash:rate_limit"
        if self.errors:
            etype = self.errors[-1].get("error_type", "Error")
            return f"crash:bug ({etype})"
        if self.gave_up:
            return "give_up:no_progress" if self.no_progress else "give_up"
        return "error:unknown"

    @property
    def thrashed(self) -> bool:
        """Reflected 3+ times without a single passing evaluation — a convergence-failure signal."""
        return self.reflexions >= 3 and self.evals_passed == 0


def load_runs(path: Path) -> Dict[str, RunSummary]:
    """Fold every audit event into per-run summaries keyed by run_id."""
    runs: Dict[str, RunSummary] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = e.get("run_id")
        if not rid:
            continue
        r = runs.get(rid) or RunSummary(run_id=rid)
        runs[rid] = r
        action = e.get("action")
        # Planner/editor mode logs edits as write_file/edit_lines/etc., not tool_call,
        # so count both to get a true "actions taken" figure across both modes.
        if action in ("tool_call", "write_file", "edit_lines", "search_replace", "replace_all"):
            r.tool_calls += 1
        if action == "task_start":
            r.task = (e.get("task") or "").strip()
            r.model = e.get("model", "")
            r.workspace = e.get("workspace", "")
        elif action == "task_end":
            r.final_state = e.get("final_state")
            r.retries = int(e.get("retries") or 0)
            r.total_tokens = int(e.get("total_tokens") or 0)
            r.total_seconds = float(e.get("total_seconds") or 0.0)
        elif action == "evaluation":
            r.evaluations += 1
            passed = _as_bool(e.get("passed"))
            if passed:
                r.evals_passed += 1
            tf = e.get("tests_failed")
            r.eval_seq.append((passed, int(tf) if isinstance(tf, (int, float)) else None))
            sk = e.get("tests_skipped")
            if isinstance(sk, (int, float)):
                r.max_skipped = max(r.max_skipped, int(sk))
        elif action == "reflexion":
            r.reflexions += 1
            if e.get("lesson"):
                r.lessons.append(str(e["lesson"]))
        elif action == "give_up":
            r.gave_up = True
        elif action == "no_progress_stop":
            r.no_progress = True
        elif action == "error":
            r.errors.append(e)
    return runs


def _norm_lesson(text: str) -> str:
    """Collapse a lesson to a comparable, truncated form for frequency counting."""
    return " ".join(text.lower().split())[:120]


def main() -> None:
    """Parse the audit log and print run-level and cross-run signals."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", default="logs/audit.jsonl")
    ap.add_argument("--grep", default=None, help="Only runs whose task contains this substring")
    ap.add_argument("--limit", type=int, default=15, help="Recent runs to list individually")
    ap.add_argument("--lessons", type=int, default=10, help="Top reflexion lessons to show")
    ap.add_argument("--convergence", action="store_true",
                    help="Show the per-run evaluation trace (failing-count deltas / pass-fail sequence)")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"audit log not found: {path}")

    runs = load_runs(path)
    ordered = list(runs.values())  # insertion order ~= chronological (run first seen)
    if args.grep:
        needle = args.grep.lower()
        ordered = [r for r in ordered if needle in r.task.lower()]

    if not ordered:
        raise SystemExit("no runs matched")

    n = len(ordered)
    print(f"\n=== Audit analysis: {path}  ({n} runs"
          + (f", filtered by {args.grep!r}" if args.grep else "") + ") ===\n")

    # 1. Outcome distribution
    outcomes = Counter(r.outcome for r in ordered)
    print("Outcomes:")
    for oc, cnt in outcomes.most_common():
        print(f"  {cnt:5}  {cnt/n:5.0%}  {oc}")

    # 2. Retry behaviour + thrash signal
    retries = [r.retries for r in ordered if r.final_state is not None]
    avg_retry = sum(retries) / len(retries) if retries else 0
    thrashers = [r for r in ordered if r.thrashed]
    print(f"\nRetries: avg {avg_retry:.1f} across completed runs; "
          f"{sum(1 for x in retries if x == 0)} ended at retries=0 (crash-before-retry).")
    print(f"Thrash signal (>=3 reflexions, 0 passing evals): {len(thrashers)} run(s).")

    # 2b. Green-by-skipping: runs that finished `done` yet skipped tests along the way.
    skip_done = [r for r in ordered if r.outcome == "done" and r.max_skipped > 0]
    if skip_done:
        print(f"\n⚠ Done-with-skips ({len(skip_done)} run(s) reached `done` but SKIPPED tests "
              f"— unverified work):")
        for r in skip_done[-args.limit:]:
            print(f"  {r.run_id:8} up to {r.max_skipped} skipped   {' '.join(r.task.split())[:44]}")

    # 3. Failure modes
    etypes = Counter()
    rate_limited = 0
    for r in ordered:
        if r.outcome == "crash:rate_limit":
            rate_limited += 1
        for e in r.errors:
            etypes[e.get("error_type", "Error")] += 1
    if etypes or rate_limited:
        print("\nFailure modes:")
        if rate_limited:
            print(f"  {rate_limited:5}  runs crashed on rate-limit (429)")
        for et, cnt in etypes.most_common(8):
            print(f"  {cnt:5}  error_type={et}")

    # 4. Cost
    tok = sum(r.total_tokens for r in ordered)
    secs = sum(r.total_seconds for r in ordered)
    print(f"\nCost: {tok:,} total tokens · {secs/60:.1f} model-minutes · "
          f"avg {tok//max(n,1):,} tok/run.")

    # 5. Top reflexion lessons
    lesson_counts = Counter()
    for r in ordered:
        for ls in r.lessons:
            lesson_counts[_norm_lesson(ls)] += 1
    if lesson_counts:
        print(f"\nTop reflexion lessons (of {sum(lesson_counts.values())} total):")
        for ls, cnt in lesson_counts.most_common(args.lessons):
            print(f"  {cnt:4}x  {ls}")

    # 5b. Convergence traces (opt-in): shows whether retries reduced failures or thrashed.
    if args.convergence:
        traced = [r for r in ordered if r.eval_seq]
        print(f"\nConvergence traces ({len(traced)} run(s) with evaluations):")
        print("  (numbers = failing test count per evaluation; P/F = pass/fail when counts "
              "predate the eval-delta logging)")
        for r in traced[-args.limit:]:
            print(f"  {r.run_id:8} rfx={r.reflexions:<2} {r.convergence()}")

    # 6. Recent runs table
    print(f"\nMost recent {min(args.limit, n)} run(s):")
    hdr = f"  {'run':8} {'outcome':22} {'rty':>3} {'evl':>3} {'rfx':>3} {'tools':>5} {'tok':>9}  task"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for r in ordered[-args.limit:]:
        task1 = " ".join(r.task.split())[:40]
        print(f"  {r.run_id:8} {r.outcome:22} {r.retries:>3} {r.evaluations:>3} "
              f"{r.reflexions:>3} {r.tool_calls:>5} {r.total_tokens:>9,}  {task1}")
    print()


if __name__ == "__main__":
    main()
