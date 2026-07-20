#!/usr/bin/env python3
"""Benchmark the REAL aider CLI on our own benchmark tasks, same local model.

A fair head-to-head vs our agent: aider gets the same stub + test in a fresh
workspace, iterates with --auto-test (its TDD loop, mirroring our agent), and is
scored with the task's own check(). Talks to local ollama via OLLAMA_API_BASE.

Run with the venv python that HAS pytest (so check() and the test-cmd resolve):
    ~/book04/ai-coding-agent/.venv/bin/python benchmarks/aider_tool_bench.py \
        --prefix HumanEval --limit 5
    ... --prefix HumanEval                 # all 164
    ... --tasks HumanEval_0,HumanEval_2    # specific
    ... --one-shot                         # no test iteration (canonical HumanEval)

Writes a JSON + a table. aider must be on PATH (or at ~/.local/bin/aider).
"""
from __future__ import annotations
import argparse, glob, importlib.util, json, os, resource, shutil, signal, subprocess, sys, tempfile
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent / "tasks"
VENV_PY = sys.executable                      # has pytest; used for check() + test-cmd
VENV_BIN = str(Path(VENV_PY).parent)
AIDER = next((p for p in (os.path.expanduser("~/.local/bin/aider"), "aider")
              if os.path.exists(p) or p == "aider"), "aider")

# aider is NOT sandboxed: it edits the host filesystem and runs --test-cmd as a
# plain host process. A model-written infinite loop or runaway allocation will
# happily eat all RAM and freeze the desktop (this machine has no swap). These
# caps are the seatbelt our own agent gets for free from its Docker sandbox.
MEM_LIMIT = 8 * 1024 ** 3   # address space per process, inherited by every child
CPU_LIMIT = 120             # CPU-seconds — kills spin loops that fit in RAM
TEST_TIMEOUT = 60           # wall-clock cap on a single pytest invocation


def _limits():
    """Run in the child before exec; rlimits are inherited by every descendant."""
    resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT, MEM_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT, CPU_LIMIT))


def _kill_tree(proc):
    """Kill the whole process group — subprocess timeouts orphan grandchildren."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        proc.kill()


def _load(name: str):
    tid = name if name.endswith("") and (TASKS_DIR / f"{name}.py").exists() else name
    spec = importlib.util.spec_from_file_location(tid, TASKS_DIR / f"{tid}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return tid, m


def _stub(files): return next(k for k in files if not (k.startswith("test_") or k.endswith("_test.py")))
def _test(files): return next((k for k in files if k.startswith("test_") or k.endswith("_test.py")), None)


def run_one(name, model, host, timeout, one_shot, num_ctx):
    tid, m = _load(name)
    ws = Path(tempfile.mkdtemp())
    for fn, content in m.FILES.items():
        (ws / fn).write_text(content, encoding="utf-8")
    stub, test = _stub(m.FILES), _test(m.FILES)

    # aider defaults ollama to a 2k context and SILENTLY truncates past it, which
    # would hand our agent (16k) an unfair win. Pin the same window for both.
    settings = ws / ".aider.model.settings.yml"
    settings.write_text(
        f"- name: ollama_chat/{model}\n  extra_params:\n    num_ctx: {num_ctx}\n",
        encoding="utf-8")

    env = os.environ.copy()
    env["OLLAMA_API_BASE"] = host
    env["OLLAMA_CONTEXT_LENGTH"] = str(num_ctx)   # belt-and-braces: server-side default
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + VENV_BIN + ":" + env.get("PATH", "")
    cmd = [AIDER, "--model", f"ollama_chat/{model}", "--no-git", "--yes-always",
           "--no-auto-commits", "--no-stream", "--no-pretty", "--map-tokens", "0",
           "--model-settings-file", str(settings)]
    if not one_shot and test:
        # iterate like our agent: run the visible test, feed failures back.
        # `timeout` caps a single run so a generated infinite loop can't hang aider.
        cmd += ["--auto-test", "--test-cmd",
                f"timeout -k 5 {TEST_TIMEOUT} {VENV_PY} -m pytest -q -x {test}"]
    cmd += ["--message",
            f"Implement the function(s) in {stub} to satisfy the docstring and pass the tests. "
            f"Edit only {stub}; do not modify the test.", stub]

    result = {"task": tid, "ok": False, "error": "", "num_ctx": num_ctx}
    proc, out, err = None, "", ""
    try:
        # start_new_session: own process group, so _kill_tree reaches grandchildren
        proc = subprocess.Popen(cmd, cwd=ws, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                start_new_session=True, preexec_fn=_limits)
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        result["error"] = "timeout"
        _kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except Exception:
            pass
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:120]
        if proc:
            _kill_tree(proc)
    # Keep evidence: aider's own warnings (context truncation, API errors) used to
    # be captured into pipes and discarded, which hid a 2k-context handicap.
    blob = (out or "") + (err or "")
    result["warnings"] = sorted({ln.strip() for ln in blob.splitlines()
                                 if any(k in ln.lower() for k in
                                        ("warning", "context window", "exceed", "error"))})[:8]
    result["output_tail"] = blob[-1500:]
    # score with the task's own check() — venv-with-pytest first on PATH
    os.environ["PATH"] = VENV_BIN + ":" + os.environ.get("PATH", "")
    try:
        result["ok"] = bool(m.check(ws))
    except Exception as exc:
        result["error"] = (result["error"] + f" check:{type(exc).__name__}").strip()
    shutil.rmtree(ws, ignore_errors=True)   # don't accumulate 34 temp workspaces
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="HumanEval", help="task prefix to run (HumanEval / Exercism)")
    ap.add_argument("--tasks", default="", help="comma-separated task names (overrides --prefix)")
    ap.add_argument("--tasks-file", default="")
    ap.add_argument("--limit", type=int, default=0, help="first N tasks only (0 = all)")
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--ollama-host", default="http://localhost:11434")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--num-ctx", type=int, default=16384,
                    help="context window; MUST match our agent's for a fair comparison")
    ap.add_argument("--one-shot", action="store_true", help="no test iteration (canonical HumanEval)")
    ap.add_argument("--out", default="aider_tool_results.json")
    args = ap.parse_args()

    if args.tasks_file:
        names = [l.strip() for l in Path(args.tasks_file).read_text().splitlines() if l.strip()]
    elif args.tasks:
        names = [t.strip() for t in args.tasks.split(",") if t.strip()]
    else:
        names = sorted((Path(p).stem for p in glob.glob(str(TASKS_DIR / f"{args.prefix}_*.py"))),
                       key=lambda s: (len(s), s))
    if args.limit:
        names = names[:args.limit]

    mode = "one-shot" if args.one_shot else "iterative (--auto-test)"
    print(f"aider {args.model} via {args.ollama_host} — {len(names)} task(s), {mode}, "
          f"num_ctx={args.num_ctx}\n")
    print(f"{'TASK':22} RESULT")
    print("-" * 40)
    results, npass = [], 0
    for n in names:
        r = run_one(n, args.model, args.ollama_host, args.timeout, args.one_shot, args.num_ctx)
        results.append(r)
        npass += r["ok"]
        tag = "PASS" if r["ok"] else ("fail" + (f" [{r['error']}]" if r["error"] else ""))
        print(f"  {r['task']:20} {tag}")

    print("\n" + "=" * 40)
    print(f"aider ({args.model}): {npass}/{len(names)} passed")
    Path(args.out).write_text(json.dumps(results, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
