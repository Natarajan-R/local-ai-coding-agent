"""Prompt templates for the agent's planning and execution phases."""
from __future__ import annotations

from pathlib import Path

ALL_TOOL_DESCRIPTIONS = {
    "read_file": "read_file(path, start_line?, end_line?): Read a file, or a 1-indexed line range.",
    "write_file": "write_file(path, content): Create or overwrite a file.",
    "edit_lines": "edit_lines(path, start_line, end_line, search, replace): Replace line range start_line to end_line (inclusive) matching search with replace. Fast & drift-safe.",
    "search_replace": "search_replace(path, search, replace): Replace ONE exact text block in a file.",
    "replace_all": "replace_all(path, old, new): Replace EVERY occurrence of a string in ONE file.",
    "rename_symbol": "rename_symbol(old, new): Rename an identifier across the WHOLE repository, every file, in one call. The right tool for any rename spanning more than one file.",
    "read_symbol": "read_symbol(symbol, path?): Show the exact source of one function/method/class. Use Class.method for a method. The right way to look at code you intend to edit.",
    "add_docstring": "add_docstring(path, symbol, docstring): Add/replace the docstring of ONE function, method or class. Pass the text only — no quotes. Use Class.method for methods.",
    "add_parameter": "add_parameter(path, symbol, name, value, default?): Add a parameter to a function/method signature and automatically update all call sites across the whole repository.",
    "list_files": "list_files(directory?): List files, optionally scoped to a subdirectory.",
    "search_text": "search_text(query): Grep file contents to locate code in a large repo.",
    "outline": "outline(path): Show a file's class/function signatures (no bodies).",
    "find_symbol": "find_symbol(name): Find where a class/function is defined (path:line).",
    "find_importers": "find_importers(name): Find which files import a module/symbol (impact analysis).",
    "remember": "remember(text, kind): Save a durable fact for FUTURE runs (a project convention, a lesson learned, or a preference). Use sparingly, only for facts that will help next time.",
    "run_command": "run_command(command): Run a shell command in the sandbox.",
    "solve_constraints": "solve_constraints(variables, constraints, all_different?, minimize?, maximize?): Solve scheduling/allocation/version-choice exactly via a solver. Variables: {name, type: int|real|bool, min?, max?, domain?}; constraints like 'b >= a + 3'.",
    "find_definition": "find_definition(path, line, character): Find definition of a symbol (0-indexed line and character).",
    "find_references": "find_references(path, line, character): Find references to a symbol (0-indexed line and character).",
    "get_diagnostics": "get_diagnostics(): Get current compiler/linting diagnostics in the workspace.",
    "finish": "finish(summary): Signal task completion."
}


def get_tool_format(exclude_names: set[str] | None = None) -> str:
    """Render the bullet-list of available tools, omitting any in ``exclude_names``."""
    exclude = exclude_names or set()
    tools_list = []
    for name, desc in ALL_TOOL_DESCRIPTIONS.items():
        if name not in exclude:
            tools_list.append(f"- {desc}")
    
    tools_str = "\n".join(tools_list)
    return f"""Tool call format: respond with EXACTLY ONE tool call and nothing else.
If native tool calling is unavailable, emit a single fenced block:
```json
{{"name": "read_file", "arguments": {{"path": "example.py"}}}}
```
Available tools:
{tools_str}"""


FEWSHOT_EXAMPLES = """Here are two examples of correct tool-call sequences.

Example A - create a new file:
Task: Create greet.py with a function hello() that returns "hi".
  assistant: {"name": "write_file", "arguments": {"path": "greet.py", "content": "def hello():\\n    return \\"hi\\"\\n"}}
  tool: Wrote 27 bytes to greet.py
  assistant: {"name": "finish", "arguments": {"summary": "Created greet.py with hello()."}}

Example B - fix a bug and verify:
Task: divide(a, b) in calc.py crashes when b is 0; return None instead.
  assistant: {"name": "read_file", "arguments": {"path": "calc.py"}}
  tool: def divide(a, b):\\n    return a / b\\n
  assistant: {"name": "search_replace", "arguments": {"path": "calc.py", "search": "    return a / b", "replace": "    if b == 0:\\n        return None\\n    return a / b"}}
  tool: Applied edit to calc.py
  assistant: {"name": "run_command", "arguments": {"command": "python -m pytest -q"}}
  tool: [ok] 1 passed
  assistant: {"name": "finish", "arguments": {"summary": "divide() returns None when b == 0; tests pass."}}

Note: While these examples show basic edits, always check the Available Tools list first 
to use semantic refactoring tools (like `rename_symbol` or `add_parameter`) for structural changes.

Notice: each action happens once, and `finish` is called immediately after the
change is made and verified once."""


def system_prompt(exclude_names: set[str] | None = None) -> str:
    """Build the main agent system prompt, embedding the available-tools list."""
    tool_format = get_tool_format(exclude_names)
    prompt = """You are an autonomous AI coding agent working inside a sandboxed workspace.
You solve software tasks by reading files, editing them, and running commands via tools.

Rules:
- Work only within the provided workspace.
- If the repository context is a large-repo overview (not a full skeleton), first
  locate the relevant files with `search_text` / `list_files`, and understand them
  with `outline` / `read_file`, before editing.
- Make the smallest change that correctly solves the task — but "smallest" means no
  gratuitous edits, NOT "stop after one file". If the task spans several files, all of
  them are part of the smallest correct change.
- Change only what the task asks you to change; preserve existing behaviour everywhere else.
  If a test you wrote fails, your test is wrong until you have evidence otherwise — fix the
  test, not the code it tests. Rewriting the code under test so your own test passes makes
  the suite green and the contract broken, and nothing will tell the user.
- Prefer `edit_lines` or `search_replace` for edits to existing files and `write_file` for new files. For small changes in large files, always prefer `edit_lines`.
- About to change a specific function, method or class? Call `read_symbol` on it FIRST
  and copy the text you get back into your `edit_lines` or `search_replace`. Never grep for `def
  __init__` — every class has one, and you will edit the wrong class's constructor."""

    exclude = exclude_names or set()
    if "add_docstring" not in exclude:
        prompt += """\n- Writing docstrings? Use `add_docstring`, once per function, method and class —
  never `search_replace` or `write_file`. It places the text at the right indentation
  itself, so it cannot break the file. `outline` lists every symbol you need to cover;
  a class docstring does NOT document its methods — `__init__` and the rest each need
  their own call."""
        
    if "rename_symbol" not in exclude or "replace_all" not in exclude:
        prompt += "\n- Renaming something? Pick the tool that matches the SCOPE of the rename:"
        if "rename_symbol" not in exclude:
            prompt += """\n  * It appears in MORE THAN ONE FILE (a class, a function, anything imported
    elsewhere) → `rename_symbol` ONCE. Not once per file — once, total. It does
    the whole repository in a single call."""
        if "replace_all" not in exclude:
            prompt += """\n  * It appears many times in ONE file only (a local variable, a parameter) →
    `replace_all` on that file."""
        prompt += """\n  Do NOT issue a series of `search_replace` calls for a rename: each edit changes
  the file, so your later search blocks will no longer match and the edits will fail.
  Do NOT call `replace_all` file by file for a repository-wide rename — you will
  miss files, and every file you miss is a broken import."""

    if "add_parameter" not in exclude:
        prompt += """\n- Adding a parameter to a function or method? Use `add_parameter` ONCE. This tool automatically updates the signature AND all call sites across the codebase. When the task asks for a "sensible" parameter value, a single uniform placeholder value (like '"USD"' or '1') passed to `add_parameter` is completely correct and sufficient. Do NOT try to manually edit the call sites using `search_replace` or `replace_all` afterward to make them different per call site — doing so is redundant, error-prone, and will introduce bugs. Accept the uniform value and call `finish`."""

    prompt += """\n- If the task requires changes in MULTIPLE files, edit EVERY target file FIRST, and only
  then run the tests. Renaming something in file A breaks file B until B is updated too —
  testing after A alone will fail and tell you nothing.
- Verify once, after all the edits are in place, then stop.
- If an edit fails with "search block not found", the file has changed since you read it.
  Re-read it with `read_file` before trying again — do not retry the same block.
- Do not call the `finish` tool if there are active compiler, syntax, or import errors in 
  the workspace. Ensure all modified files compile cleanly first.
- Verify that your written Python code has clean, standard syntax. Do not write duplicate 
  async keywords (e.g. 'async async def') or double-defined decorators.
- Before writing ANY test file, you MUST first `read_file` the implementation files your
  tests will import. Your tests MUST match the actual method signatures, return types,
  and constructor parameters of the implementation exactly. The #1 cause of test failures
  is writing tests from memory that don't match the code you actually wrote. Read first,
  then write tests that match the real API.
- IMPORT PATH RULE: NEVER use the workspace directory name in import paths. The workspace
  directory (e.g. "task_queue_ws_08", "web_scraper_ws3") is NOT a Python package. Use
  "from src.xxx import Yyy" — not "from task_queue_ws_08.xxx import Yyy". The code lives
  under src/, not under the workspace directory name.
- COMPLEX STRINGS: If the file content contains f-strings, triple-quoted strings, or
  nested quotes that might break JSON parsing, use `run_command` with a heredoc instead
  of `write_file`. Example:
  run_command(command='''cat > path/to/file.py << 'PYEOF'\n<file content here>\nPYEOF''')
  `run_command` does NOT count against the mutation budget.
- Call exactly one tool per step. Respond ONLY with a tool call, no prose.

Critical loop-avoidance rules:
- NEVER repeat a tool call you have already made. Each `write_file` succeeds the
  first time; do not write the same file again.
- Once EVERY required change is made and verified once, your VERY NEXT action MUST be the
  `finish` tool. Do not re-verify repeatedly.
- Verify at most ONCE. Do not read a file you just wrote, and do not run the same
  command twice. One successful check is enough -- then call `finish`.
- NEVER call `finish` for work you have not actually done. `finish` reports completed
  work; it is not a way out of uncertainty. If you are unsure what to do next, inspect
  (`read_file`, `outline`, `search_text`) or make the edit — do not declare success.

Python correctness rules:
- Rule 9 — ASYNC/AWAIT: When writing async functions (async def), NEVER use
  time.sleep(). Always use `await asyncio.sleep()`. time.sleep() BLOCKS the
  event loop and will hang all concurrent tasks.
- Rule 10 — PYTHON vs JAVASCRIPT: Use True, False, None (capitalized). NOT
  true, false, null (lowercase). Use isinstance() for type checking.
- Rule 11 — IMPORT BEFORE USE: Before using any class or function, make sure it
  is imported at the top of the file. Check the file's imports section. If a name
  is used but not imported, add the import.
- Rule 12 — NO DUPLICATE CLASSES: Before defining a class, check if it already
  exists in the codebase. If ValidationError is defined in errors.py, do NOT
  redefine it in pipeline.py. Instead import it: from .errors import ValidationError.
- Rule 13 — TEST MOCK STATE: When writing test mocks that raise exceptions, you
  must also set the object's state to match what the real code would set.

{tool_format}

{fewshot_examples}
"""
    return prompt.format(tool_format=tool_format, fewshot_examples=FEWSHOT_EXAMPLES)


SYSTEM_PROMPT = system_prompt()

PLANNING_PROMPT = """Task: {task}

Repository context:
{skeleton}

Write a short, numbered plan (3-6 steps) describing how you will accomplish the task.
Respond with the plan only, no tool calls yet."""

EXECUTION_PRIMER = """Task: {task}

Your plan:
{plan}

Begin executing the plan using the available tools, one tool call per step.
When everything is implemented and verified, call `finish`."""


def planning_messages(task: str, skeleton: str, memory: str = "", customizations: list[str] = None) -> list[dict]:
    """Assemble the planning-phase messages: system prompt, optional memory, and the task + repo skeleton."""
    system_content = SYSTEM_PROMPT
    if customizations:
        system_content += "\n\nAdditional instructions and guidelines for this workspace/task:\n" + "\n\n".join(customizations)
    messages = [{"role": "system", "content": system_content}]
    if memory:
        messages.append({"role": "user", "content": memory})
    messages.append({"role": "user", "content": PLANNING_PROMPT.format(task=task, skeleton=skeleton)})
    return messages


def execution_primer(task: str, plan: str) -> dict:
    """Build the user message that primes the execution phase with the task and plan."""
    return {"role": "user", "content": EXECUTION_PRIMER.format(task=task, plan=plan)}


PLANNER_SYSTEM_PROMPT = """You are a software architect. Your job is to plan codebase changes.
Given a task and the repository layout, identify all the files that need to be created or modified.
Respond ONLY with a JSON array of edit tasks. Each task must have:
- "path": The file path relative to the workspace root.
- "change_description": A detailed description of what needs to be changed in this file.
- "is_new": A boolean indicating if the file needs to be newly created.

Rules:
- For implementing missing functions or fixing logic, the main implementation file (e.g., solution.py, main.py, etc.) MUST be included in the checklist. Do NOT skip the implementation file or target only test files.
- Do NOT edit or modify test files (e.g., test_*.py, *_test.py, *spec*) unless the task specifically instructs you to add, fix, or modify tests. Assume existing tests are correct and should be left unmodified.
- When the change involves optimization or combinatoric logic (subset selection, knapsack, path or matrix search, overlapping subproblems), instruct the editor to use memoization (a cache dict) or dynamic programming rather than naive recursion, so execution stays polynomial and does not time out.

Do NOT include any conversational prose, markdown formatting outside of JSON code block, or raw code implementation. Respond with a valid JSON array only.

Example Output:
[
  {{
    "path": "math_lib.py",
    "change_description": "Fix divide function to return None when divisor is zero.",
    "is_new": false
  }}
]"""

PLANNER_USER_PROMPT = """Task: {task}

Repository context:
{skeleton}

Create the edit checklist JSON array now."""


def planner_messages(task: str, skeleton: str, memory: str = "", customizations: list[str] = None) -> list[dict]:
    """Build the Planner-mode messages that ask the model for a JSON edit-checklist."""
    system_content = PLANNER_SYSTEM_PROMPT
    if customizations:
        system_content += "\n\nAdditional instructions and guidelines for this workspace/task:\n" + "\n\n".join(customizations)
    messages = [{"role": "system", "content": system_content}]
    if memory:
        messages.append({"role": "user", "content": memory})
    messages.append({"role": "user", "content": PLANNER_USER_PROMPT.format(task=task, skeleton=skeleton)})
    return messages


EDITOR_SYSTEM_PROMPT = """You are an expert coder. Your task is to edit a single file in the workspace to satisfy the user's request.
You must output the ENTIRE updated file content, including all unchanged parts, using the `whole` format. 
Do not use placeholders (like '# ... rest of code ...' or '// unchanged code') under any circumstances.
Respond with the entire file content inside a code block of the target language (e.g. ```python). Do not output any conversational prose before or after the code block.

Example Output:
```python
def hello():
    return "world"
```"""

EDITOR_USER_PROMPT = """Original Task: {task}
File Path: {path}
Requested Change: {change_description}

Current File Content:
```
{content}
```

Please output the updated file content in its entirety."""


def editor_messages(
    task: str,
    path: str,
    change_description: str,
    content: str,
    reflexion_lesson: str = "",
    compiler_error: str = ""
) -> list[dict]:
    """Build Editor-mode messages asking the model to rewrite one whole file, with optional failure feedback."""
    messages = [
        {"role": "system", "content": EDITOR_SYSTEM_PROMPT},
        {"role": "user", "content": EDITOR_USER_PROMPT.format(task=task, path=path, change_description=change_description, content=content)}
    ]
    # __init__.py specific guidance
    if path.endswith("__init__.py"):
        messages.append(
            {"role": "user", "content": (
                "IMPORTANT: This is an `__init__.py` file. Its primary job is to "
                "RE-EXPORT public names from submodules, NOT to define classes/functions "
                "directly. Use `from .submodule import ClassName` to re-export. "
                "Do NOT define classes inside `__init__.py`."
            )}
        )
    if reflexion_lesson:
        messages.append(
            {"role": "user", "content": f"A previous attempt failed tests with this feedback: {reflexion_lesson}\nPlease correct your implementation accordingly."}
        )
    if compiler_error:
        messages.append(
            {"role": "user", "content": f"Your previous code output had a compilation/syntax error:\n{compiler_error}\nPlease fix the syntax error and output the entire file content again."}
        )
    return messages


SUBTASK_USER_PROMPT = """Original Task: {task}
File Path: {path}
Requested Subtask Change: {change_description}

Repository Map:
{repo_map}

You have access to the workspace. Use `read_file` to inspect the contents of `{path}`, and then apply focused modifications using `edit_lines` or `search_replace`.
Before calling the `finish` tool, you must verify your changes by running 'python -m pytest -q' via `run_command`.
When verified, call `finish`."""


def subtask_system_prompt(path: str, change_description: str, exclude_names: set[str] | None = None) -> str:
    """Build the system prompt for a tool-driven single-file subtask edit."""
    tool_format = get_tool_format(exclude_names)
    return f"""You are an expert coder. Your task is to edit a single file in the workspace to satisfy the user's request.
Do not make unnecessary changes to other files. Focus only on the target file.

{tool_format}

Prefer `edit_lines` or `search_replace` for edits to existing files and `write_file` for new files. For small changes in large files, always prefer `edit_lines`.
CRITICAL: You must always respond with exactly one tool call in the required JSON format. Do NOT write any conversational prose, explanations, or code blocks in markdown unless they are inside a tool call. If you are correcting a previous failure, output the corrected tool call immediately.
IMPORT PATH RULE: NEVER use the workspace directory name in import paths. The workspace directory is NOT a Python package. Use "from src.xxx import Yyy" — never "from <workspace_dir_name>.xxx import Yyy".

Python correctness rules:
- Rule 9 — ASYNC/AWAIT: When writing async functions (async def), NEVER use time.sleep(). Always use `await asyncio.sleep()`.
- Rule 10 — PYTHON vs JAVASCRIPT: Use True, False, None (capitalized). NOT true, false, null (lowercase).
- Rule 11 — IMPORT BEFORE USE: Before using any class or function, make sure it is imported at the top of the file.
- Rule 12 — NO DUPLICATE CLASSES: Before defining a class, check if it already exists in the codebase. Import it instead.
- Rule 13 — TEST MOCK STATE: When writing test mocks that raise exceptions, also set the object's state to match.
"""


def subtask_user_prompt(
    task: str,
    path: str,
    change_description: str,
    content: str,
    repo_map: str = "",
    reflexion_lesson: str = "",
    test_content: str = "",
    required_exports: list = None,
    references: str = "",
    project_status: str = "",
) -> str:
    """Build the subtask user message with the task, repo map, and any prior-failure lesson."""
    prompt = SUBTASK_USER_PROMPT.format(
        task=task,
        path=path,
        change_description=change_description,
        content=content,
        repo_map=repo_map or "Not available"
    )
    if project_status:
        prompt += f"\n\nPROJECT STATUS:\n{project_status}"
    if required_exports:
        # Scaffolding (#2): the test suite imports these names from this module, so
        # the file MUST define every one of them (a class/function that is missing or
        # misnamed is the single biggest cause of collection/import failures). Making
        # the contract explicit beats hoping the model infers it from the raw tests.
        names = ", ".join(required_exports)
        prompt += (
            f"\n\nREQUIRED INTERFACE — the tests import these names from this module, "
            f"so `{path}` MUST define ALL of them, spelled EXACTLY like this and usable "
            f"the way the tests use them: {names}. Do not rename, omit, or add a "
            f"different spelling."
        )
    if references:
        # Example-RAG (#3): a working reference implementation to mimic. Models copy a
        # nearby correct example far more reliably than they generate boilerplate cold.
        prompt += (
            "\n\nREFERENCE IMPLEMENTATION(S) of the pattern to follow (adapt to THIS "
            "file's names/spec — do not copy verbatim, and do not import from them):\n"
            f"{references}"
        )
    if test_content:
        is_test_file = "test" in Path(path).stem.lower() or "spec" in Path(path).stem.lower()
        if is_test_file:
            # When writing a test file, test_content contains the implementation code
            # so the model can write tests that match the actual API
            prompt += (
                "\n\n=== IMPLEMENTATION CODE your tests must match ===\n"
                "Read the actual method signatures, constructor parameters, and return\n"
                "types below. Your tests MUST call these exact methods with the exact\n"
                "arguments shown. Do NOT guess method names or signatures:\n"
                f"```python\n{test_content}\n```"
            )
        else:
            # The test IS the spec. Without it in context the editor has to guess the
            # exact strings and values the test asserts on (error messages, return
            # shapes) — the dominant remaining failure mode. The model solves these
            # one-shot when the test is in its prompt; give the editor the same.
            prompt += (
                "\n\nThe following test file is the exact specification. Your code must "
                "make it pass UNCHANGED — match its expected messages, return values and "
                "structure exactly (do not modify the test):\n"
                f"```python\n{test_content}\n```"
            )
    # __init__.py specific guidance: these files should re-export, not define
    if path.endswith("__init__.py"):
        prompt += (
            "\n\nIMPORTANT: This is an `__init__.py` file. Its primary job is to "
            "RE-EXPORT public names from submodules, NOT to define classes/functions "
            "directly. Example:\n"
            "```python\n"
            "from .retry import RetryMiddleware\n"
            "from .timeout import TimeoutMiddleware\n"
            "from .logging import LoggingMiddleware\n"
            "```\n"
            "If the module needs its own implementation, put it in a submodule "
            "(e.g., `retry.py`) and import it here. Do NOT define classes inside "
            "`__init__.py`."
        )
    if reflexion_lesson:
        prompt += f"\n\nNote: A previous attempt failed tests with this feedback: {reflexion_lesson}\nPlease correct your implementation accordingly."
    return prompt


PLANNER_REFINER_SYSTEM_PROMPT = """You are a software architect. Your job is to refine an edit checklist after a failed verification attempt.
Given the original task, the current checklist, the test failures, and the root-cause diagnosis, produce an UPDATED JSON array of edit tasks.

Rules:
- Mark tasks that were completed successfully as no longer needed, or omit them, OR modify the checklist to focus ONLY on the remaining failing files/subtasks.
- You can add new tasks (e.g. debugging, correcting specific files).
- Keep the output format exactly as a valid JSON array of edit tasks (path, change_description, is_new).
Do NOT include any conversational prose. Respond with a valid JSON array only."""

PLANNER_REFINER_USER_PROMPT = """Original Task: {task}
Current Checklist:
{checklist}

Impacted/Dependent Test Files (from symbol dependency graph):
{impacted_tests}

Test Failures:
{eval_result}

Root Cause Diagnosis:
{lesson}

Create the refined edit checklist JSON array now."""


def planner_refiner_messages(task: str, checklist: list, eval_result: str, lesson: str, impacted_tests: list[str] = None) -> list[dict]:
    """Build the reflexion messages that ask the planner to refine the checklist after a failed evaluation."""
    import json
    tests_str = ", ".join(impacted_tests) if impacted_tests else "None detected"
    return [
        {"role": "system", "content": PLANNER_REFINER_SYSTEM_PROMPT},
        {"role": "user", "content": PLANNER_REFINER_USER_PROMPT.format(
            task=task,
            checklist=json.dumps(checklist, indent=2),
            impacted_tests=tests_str,
            eval_result=eval_result,
            lesson=lesson
        )}
    ]


MILESTONE_PLANNER_SYSTEM_PROMPT = """You are a software architect planning how a SMALLER model should build a large project INCREMENTALLY, one verifiable layer at a time.

Break the task into a SMALL number of ORDERED milestones — aim for 4 to 7 total, and NEVER more than 8. Each milestone is a whole LAYER (a package or concern), built AND verified before the next. Order strictly by dependency: data models first, then services that use them, then routes/middleware, then app wiring/CLI. Nothing in an earlier milestone may import something defined in a later one.

Respond ONLY with a JSON array of milestones. Each milestone has:
- "name": short label (e.g., "models layer")
- "files": array of {"path", "change_description", "is_new"} — ALL the files that belong to this layer
- "tests": array of test file paths that verify THIS milestone (a subset of the suite); may be empty

Rules — READ CAREFULLY:
- GROUP related files into ONE milestone. One milestone = one whole layer/package (e.g. ALL of `src/models/*` in a single "models" milestone; ALL of `src/routes/*` in a single "routes" milestone).
- Do NOT make a separate milestone per file. A milestone with only one file is almost always wrong unless that file truly is its own layer. Ten files across three layers = THREE milestones, not ten.
- Every implementation file the task requires must appear in exactly one milestone.
- Do NOT create or edit test files unless the task explicitly asks. Assume existing tests are the spec.

Example:
[
  {"name": "models", "files": [{"path": "src/models/user.py", "change_description": "User model", "is_new": true}, {"path": "src/models/product.py", "change_description": "Product model", "is_new": true}, {"path": "src/models/order.py", "change_description": "Order model", "is_new": true}], "tests": ["tests/test_models.py"]},
  {"name": "services", "files": [{"path": "src/services/user_service.py", "change_description": "user CRUD", "is_new": true}, {"path": "src/services/product_service.py", "change_description": "product CRUD", "is_new": true}], "tests": ["tests/test_users.py"]},
  {"name": "routes", "files": [{"path": "src/routes/users.py", "change_description": "user endpoints", "is_new": true}, {"path": "src/routes/products.py", "change_description": "product endpoints", "is_new": true}], "tests": ["tests/test_products.py"]}
]"""

MILESTONE_PLANNER_USER_PROMPT = """Task: {task}

Repository context:
{skeleton}

Break this into ordered, independently-verifiable milestones. Respond with the JSON array now."""


def milestone_planner_messages(task: str, skeleton: str, memory: str = "", customizations: list = None) -> list:
    """Build the messages that ask the architect for an ordered list of verifiable milestones."""
    system_content = MILESTONE_PLANNER_SYSTEM_PROMPT
    if customizations:
        system_content += "\n\nAdditional instructions and guidelines for this workspace/task:\n" + "\n\n".join(customizations)
    messages = [{"role": "system", "content": system_content}]
    if memory:
        messages.append({"role": "user", "content": memory})
    messages.append({"role": "user", "content": MILESTONE_PLANNER_USER_PROMPT.format(task=task, skeleton=skeleton)})
    return messages
