"""Evaluate the workspace by running its tests, detecting the project type.

Detection order (first match wins):
  1. An explicit ``test_command`` (from ``--test-command``).
  2. A recognized project marker file (package.json, go.mod, Cargo.toml, ...).
  3. Python test files (``test_*.py`` / ``*_test.py``) -> pytest.
  4. Otherwise a best-effort Python compile check.
"""
from __future__ import annotations

import ast
import hashlib
import logging
import os
import re
import shlex
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Set, Dict
import re

logger = logging.getLogger(__name__)

# Constants
PYTEST_NO_TESTS = 5
FAILURE_DETAIL_LIMIT = 3000
MAX_TEST_FILES_TO_SCAN = 1000
TEST_EXECUTION_TIMEOUT = 300  # 5 minutes default timeout

# Excluded directories for test file scanning
EXCLUDED_DIRS = {".venv", "venv", "__pycache__", "node_modules", ".git", "dist", "build", ".pytest_cache"}

# Collection error markers for pytest
_COLLECTION_ERROR_MARKERS = (
    "error collecting",
    "errors during collection",
    "error during collection",
    "importerror while importing test module",
    "interrupted: ",
)

# Skip reasons that mean "required work was deferred", not "legitimately not applicable
# here" (platform/optional-dep). A green run that only got green by skipping tests for
# these reasons is a skip-to-green — unverified required functionality, not a real pass.
_UNIMPLEMENTED_SKIP_MARKERS = (
    "not implemented", "notimplemented", "unimplemented", "not yet",
    "todo", "to do", "stub", "placeholder", "coming soon",
    "work in progress", "wip",
)


def _unimplemented_skips(output: str) -> List[str]:
    """Return pytest ``SKIPPED`` lines whose reason signals deferred required work.

    Relies on ``-rs`` being in the pytest command so skip reasons are printed. A skip
    for an unimplemented feature is the classic way a weak model reaches a false green
    (`@pytest.mark.skip("Extension system not yet implemented")`); surface those so the
    caller can refuse to call the run DONE. Platform/optional-dep skips are ignored.
    """
    hits: List[str] = []
    for line in (output or "").splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("SKIPPED"):
            continue
        low = stripped.lower()
        if any(marker in low for marker in _UNIMPLEMENTED_SKIP_MARKERS):
            hits.append(stripped)
    return hits

# Project markers with their test commands
PROJECT_MARKERS: List[Tuple[str, str]] = [
    ("package.json", "npm test --silent"),
    ("go.mod", "go test ./..."),
    ("Cargo.toml", "cargo test"),
    ("pom.xml", "mvn -q test"),
    ("build.gradle", "gradle test"),
    ("build.gradle.kts", "gradle test"),
]

# Dangerous patterns for command injection
_DANGEROUS_PATTERNS = [';', '&&', '||', '|', '`', '$(', '$(']


def _is_collection_error(output: str) -> bool:
    """True if pytest's output shows collection *failed* rather than found nothing."""
    if not output:
        return False
    low = output.lower()
    return any(marker in low for marker in _COLLECTION_ERROR_MARKERS)


def _is_safe_command(command: str) -> bool:
    """Validate that a command doesn't contain dangerous shell metacharacters."""
    if not command:
        return False
    # Allow basic commands with arguments and flags
    if any(pattern in command for pattern in _DANGEROUS_PATTERNS):
        logger.warning(f"Unsafe command rejected: {command}")
        return False
    return True


def _extract_failures(output: str) -> str:
    """Pull the failing-test names and their error/traceback lines out of raw test output."""
    if not output:
        return ""
    lines = output.splitlines()
    failures = []
    
    current_test = None
    current_error: List[str] = []
    current_file_line = None
    
    in_failures = False
    
    for line in lines:
        # ERRORS as well as FAILURES: a module that will not import is reported
        # under an ERRORS banner
        if line.startswith("=") and ("FAILURES" in line or "ERRORS" in line):
            in_failures = True
            continue
        if in_failures and line.startswith("="):
            if any(word in line for word in ["FAILURES", "ERRORS"]):
                continue
            else:
                in_failures = False
                
        if in_failures:
            stripped = line.strip()
            is_separator = (
                len(stripped) > 4
                and stripped.startswith("_")
                and stripped.endswith("_")
                and stripped.strip("_ ") != ""
            )
            if is_separator:
                if current_test:
                    failures.append((current_test, "\n".join(current_error), current_file_line))
                current_test = line.strip("_ ")
                current_error = []
                current_file_line = None
                continue
                
            if current_test:
                if line.startswith("E   "):
                    current_error.append(line)
                elif (line.strip() and ":" in line and not line.startswith(" ") 
                      and not line.startswith("E") and not line.startswith(">")):
                    parts = line.strip().split(":")
                    if len(parts) >= 2 and parts[-2].strip().isdigit():
                        current_file_line = line.strip()
                        
    if current_test:
        failures.append((current_test, "\n".join(current_error), current_file_line))
        
    if not failures:
        return ""
        
    summary_lines = ["\n=== FAILURES SUMMARY ==="]
    for test, err, file_line in failures:
        summary_lines.append(f"FAILED TEST: {test}")
        if file_line:
            summary_lines.append(f"LOCATION: {file_line}")
        if err:
            summary_lines.append(f"ERROR DETAILS:\n{err}")
        summary_lines.append("")
    summary_lines.append("========================\n")
    return "\n".join(summary_lines)


def _condense_test_output(output: str, limit: int = FAILURE_DETAIL_LIMIT) -> str:
    """Keep the *diagnostic* part of a failed test run, drop the passing noise."""
    if not output:
        return "Test failed with no output."
    
    # Try to extract failure summary first
    summary = _extract_failures(output)
    
    lines = output.splitlines()
    
    # Find the failures/errors section
    start = next(
        (i for i, ln in enumerate(lines)
         if ln.startswith("=") and ("FAILURES" in ln or "ERRORS" in ln)),
        None,
    )
    
    if start is not None:
        condensed = "\n".join(lines[start:])
    else:
        # Keep error-related lines
        keep = [
            ln for ln in lines
            if (ln[:1] in ("E", ">") or
                ln.startswith(("FAILED", "ERROR", "Traceback")) or
                "Error" in ln or "assert" in ln)
        ]
        condensed = "\n".join(keep) if keep else output
        
        # If output is still huge, take last 100 lines
        if len(condensed) > limit:
            condensed = "\n".join(lines[-100:])
    
    # Trim to limit
    if len(condensed) > limit:
        condensed = "...[earlier test output truncated]...\n" + condensed[-limit:]
        
    # Prefer summary if available
    if summary:
        return summary + "\n" + condensed
    return condensed


def _extract_implementation_signatures(workspace: Path, failing_tests: List[str],
                                       test_output: str) -> str:
    """Extract class/function signatures from implementation files referenced by failing tests.

    When tests fail due to wrong method signatures, this gives the model the actual
    API it wrote so it can align its tests. Returns a formatted string, or empty
    if nothing useful was found.
    """
    try:
        # Collect candidate source files from:
        # 1. Import paths mentioned in the test output (ImportError lines)
        # 2. The test files themselves (to find what they import)
        source_files: set[Path] = set()

        # Parse ImportError / ModuleNotFoundError lines
        import_errors = re.findall(
            r"(?:cannot import name|No module named) ['\"](\S+?)['\"]",
            test_output,
        )
        for mod_path in import_errors:
            parts = mod_path.replace(".", "/")
            # Try as a .py file and as a package
            for ext in ("", ".py"):
                candidate = workspace / (parts + ext)
                if candidate.exists():
                    source_files.add(candidate)
            init = workspace / parts / "__init__.py"
            if init.exists():
                source_files.add(init)

        # Also scan test files for import statements
        for test_name in failing_tests:
            # test_name like "tests/test_foo.py::TestClass::test_method"
            test_path = workspace / test_name.split("::")[0]
            if test_path.exists():
                try:
                    tree = ast.parse(test_path.read_text(encoding="utf-8", errors="replace"))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom) and node.module:
                            mod = node.module
                            # Only look at local imports (not stdlib/third-party)
                            parts = mod.split(".")
                            for depth in range(len(parts), 0, -1):
                                sub = "/".join(parts[:depth])
                                for ext in ("", ".py"):
                                    candidate = workspace / (sub + ext)
                                    if candidate.exists():
                                        source_files.add(candidate)
                                init = workspace / sub / "__init__.py"
                                if init.exists():
                                    source_files.add(init)
                except Exception:
                    pass

        # Also scan all src/ files for .py files that might be implementation
        src_dir = workspace / "src"
        if src_dir.exists():
            for py_file in src_dir.rglob("*.py"):
                if py_file.name != "__init__.py" and py_file.is_file():
                    source_files.add(py_file)

        # Extract signatures from collected files
        sigs: List[str] = []
        for src in sorted(source_files)[:10]:  # cap at 10 files
            try:
                content = src.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content)
                rel = src.relative_to(workspace)
                file_sigs = [f"--- {rel} ---"]
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = []
                        for item in ast.iter_child_nodes(node):
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                args = ast.unparse(item.args)
                                ret = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                                prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                                methods.append(f"    {prefix}def {item.name}({args}){ret}")
                        file_sigs.append(f"class {node.name}:")
                        file_sigs.extend(methods if methods else ["    (no methods)"])
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = ast.unparse(node.args)
                        ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                        file_sigs.append(f"{prefix}def {node.name}({args}){ret}")
                if len(file_sigs) > 1:
                    sigs.append("\n".join(file_sigs))
            except Exception:
                pass

        if sigs:
            header = (
                "\n\n=== ACTUAL IMPLEMENTATION SIGNATURES ===\n"
                "The tests above reference these files. Here are the REAL method\n"
                "signatures your tests must match exactly:\n\n"
                "If your tests call methods with wrong names, wrong arguments, or\n"
                "expect wrong return types, FIX THE TESTS to match these signatures.\n\n"
            )
            return header + "\n\n".join(sigs)
        return ""
    except Exception:
        return ""


def _ensure_workspace_structure(workspace: Path) -> int:
    """AC-06: Fix structural issues in the workspace before test evaluation.

    1. Detect root-level ``test_*.py`` / ``*_test.py`` files
    2. Create ``tests/`` directory if root test files exist
    3. Move root test files into ``tests/``
    4. Create ``tests/__init__.py`` if ``tests/`` contains test files
    5. Ensure package ``__init__.py`` has re-exports if it was left empty
    6. Fix test methods that are at module level instead of inside a TestCase class

    Returns the number of files modified.
    """
    corrected = 0

    tests_dir = workspace / "tests"

    # --- Step 1: Find root-level test files ---
    root_test_files: List[Path] = []
    for pat in ("test_*.py", "*_test.py"):
        for tf in workspace.glob(pat):
            if tf.parent == workspace:
                root_test_files.append(tf)

    # --- Step 2: Create tests/ dir if root test files exist ---
    if root_test_files and not tests_dir.is_dir():
        try:
            tests_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Created tests/ directory for %d root test file(s)", len(root_test_files))
            corrected += 1
        except Exception as exc:
            logger.warning("Failed to create tests/ directory: %s", exc)

    # --- Step 3: Move root test files into tests/ ---
    if tests_dir.is_dir():
        for tf in root_test_files:
            try:
                dest = tests_dir / tf.name
                if not dest.exists():
                    shutil.move(str(tf), str(dest))
                    logger.info("Moved %s -> %s", tf.name, dest.relative_to(workspace))
                    corrected += 1
            except Exception as exc:
                logger.warning("Failed to move %s: %s", tf.name, exc)

    # --- Step 4: Create tests/__init__.py if missing ---
    if tests_dir.is_dir() and not (tests_dir / "__init__.py").exists():
        test_files = list(tests_dir.glob("*.py"))
        if test_files:
            try:
                (tests_dir / "__init__.py").write_text("# tests\n", encoding="utf-8")
                logger.info("Created tests/__init__.py (%d test files)", len(test_files))
                corrected += 1
            except Exception as exc:
                logger.warning("Failed to create tests/__init__.py: %s", exc)

    # --- Step 5: Ensure package __init__.py has re-exports ---
    src_dir = workspace / "src"
    if src_dir.is_dir():
        init_py = src_dir / "__init__.py"
        if init_py.exists():
            content = init_py.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                # Find submodules and add re-exports
                submodules = sorted(
                    f.stem for f in src_dir.glob("*.py")
                    if f.name != "__init__.py" and not f.name.startswith("_")
                )
                if submodules:
                    lines = []
                    for mod in submodules:
                        lines.append(f"from .{mod} import *")
                    init_py.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    logger.info("Populated empty src/__init__.py with re-exports from %s", submodules)
                    corrected += 1

    # --- Step 6: Fix test method indentation ---
    test_files = []
    if tests_dir.is_dir():
        for pat in ("test_*.py", "*_test.py"):
            test_files.extend(tests_dir.glob(pat))
    for pat in ("test_*.py", "*_test.py"):
        test_files.extend(workspace.glob(pat))

    for tf in test_files:
        corrected += _fix_test_indentation(tf)

    # --- Step 7: Align parser HTML tag selectors with test fixtures ---
    corrected += _autocorrect_html_tags(workspace)

    return corrected


def _autocorrect_html_tags(workspace: Path) -> int:
    """AC-08: Align parser BeautifulSoup tag selectors with test HTML fixtures.

    The model frequently guesses wrong HTML tags/classes for BeautifulSoup
    selectors (e.g. uses <h2> when the test fixture uses <h1>, or <span> when
    the test uses <p>). This function extracts tag+class patterns from test
    file HTML literals and fixes the parser to match.
    """
    import json

    corrected = 0

    # Collect tag->class mappings from test HTML fixtures
    html_tag_map: Dict[str, str] = {}  # field_class_str -> ("tag", "class" or None)
    tag_re = re.compile(r'''<(\w+)(?:\s+class=['"]([^'"]*)['"])?''')

    test_dirs = [workspace / "tests"] if (workspace / "tests").is_dir() else []
    for td in test_dirs:
        for pat in ("test_*.py", "*_test.py"):
            for tf in td.glob(pat):
                try:
                    c = tf.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for tag_match in tag_re.finditer(c):
                    tag = tag_match.group(1).lower()
                    cls = tag_match.group(2)
                    # Only map tags that look like HTML content (not setup code)
                    if tag in ('div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                               'a', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th',
                               'section', 'article', 'header', 'footer', 'main',
                               'form', 'input', 'button', 'label', 'select',
                               'img', 'video', 'audio', 'figure', 'figcaption'):
                        key = f"{tag}.{cls}" if cls else tag
                        if key not in html_tag_map:
                            html_tag_map[key] = (tag, cls)

    if not html_tag_map:
        return 0

    # Find parser files and fix BeautifulSoup calls
    parser_files = list(workspace.glob("src/*.py")) + list(workspace.glob("*.py"))
    for pf in parser_files:
        if pf.name.startswith("test_") or pf.name == "__init__.py":
            continue
        try:
            content = pf.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        original = content

        # Find BeautifulSoup .find() / .find_all() calls
        # Pattern: .find('tag', class_='class') or .find_all('tag', class_='class')
        bs_call_re = re.compile(r'''
            \.\s*find(?:_all)?\s*\(
            \s*['"](\w+)['"]       # tag name argument
            (?:\s*,\s*class_\s*=\s*['"](\w+)['"])?  # optional class_ argument
            \s*\)
        ''', re.VERBOSE)

        for m in bs_call_re.finditer(content):
            found_tag = m.group(1).lower()
            found_class = m.group(2)  # None if no class
            found_key = f"{found_tag}.{found_class}" if found_class else found_tag

            if found_key in html_tag_map:
                continue  # Already matches

            # Try to find a match in the test fixtures
            # Priority: exact class match -> heading tag match -> any tag match
            best_match = None
            for test_key, (test_tag, test_class) in html_tag_map.items():
                if found_class and test_class == found_class:
                    best_match = (test_tag, test_class)
                    break
                # If no class in parser, match by tag if same
                elif not found_class and found_tag == test_tag:
                    best_match = (test_tag, test_class)
                    break
                # Heading tag match (h1-h6): if parser uses h2 and test has h1
                elif not found_class and not test_class:
                    if (found_tag.startswith('h') and len(found_tag) == 2
                            and test_tag.startswith('h') and len(test_tag) == 2):
                        best_match = (test_tag, test_class)
                        break

            if best_match and best_match[0] != found_tag:
                # Fix the tag
                old = m.group(0)
                if found_class:
                    new = old.replace(f"'{found_tag}'", f"'{best_match[0]}'", 1)
                else:
                    new = old.replace(f"'{found_tag}'", f"'{best_match[0]}'", 1)
                content = content.replace(old, new)
                corrected += 1
                logger.info(
                    "AC-08: Fixed HTML tag '%s' -> '%s' in %s",
                    found_tag, best_match[0], pf.name,
                )
            elif best_match and best_match[1] and found_class != best_match[1]:
                # Fix the class
                old = m.group(0)
                new = old.replace(f"class_='{found_class}'", f"class_='{best_match[1]}'")
                content = content.replace(old, new)
                corrected += 1
                logger.info(
                    "AC-08: Fixed HTML class '%s' -> '%s' in %s",
                    found_class, best_match[1], pf.name,
                )

        if content != original:
            pf.write_text(content, encoding="utf-8")

    return corrected


def _fix_test_indentation(filepath: Path) -> int:
    """Fix test methods that are accidentally at module level instead of inside a TestCase class.

    The 32b model frequently writes test functions that should be class methods
    but leaves them at module indentation. This detects them, finds the nearest
    ``unittest.TestCase`` class, and re-indents the methods inside it.
    """
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content)
    except SyntaxError:
        # Can't parse — try a simpler regex-based fix
        return _fix_test_indentation_regex(filepath, content)

    lines = content.split("\n")
    modified = False

    # Find TestCase classes and their line ranges
    class_defs: List[Tuple[str, int, int]] = []  # (name, start_line, end_line)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it inherits from TestCase
            is_testcase = any(
                isinstance(base, ast.Attribute) and base.attr == "TestCase"
                or isinstance(base, ast.Name) and base.id == "TestCase"
                for base in node.bases
            )
            if is_testcase:
                end = len(lines)
                # Find end of class by looking at next top-level node
                for sibling in ast.iter_child_nodes(tree):
                    if isinstance(sibling, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        if sibling.lineno > node.lineno:
                            end = sibling.lineno - 2  # -2 for blank line
                            break
                class_defs.append((node.name, node.lineno, end))

    if not class_defs:
        return 0

    # Find module-level functions that look like test methods
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            func_line = node.lineno - 1  # 0-indexed
            func_end = _find_func_end(node, len(lines))

            # Check if this function is at module level (not inside a class)
            inside_class = any(start <= func_line < end for _, start, end in class_defs)
            if inside_class:
                continue

            # Found a module-level test function — move it inside the first TestCase class
            if class_defs:
                class_name, class_start, class_end = class_defs[0]
                # Get the function lines
                func_lines = lines[func_line:func_end]

                # Calculate indentation (class body indentation + 4)
                class_indent = len(lines[class_start - 1]) - len(lines[class_start - 1].lstrip())
                body_indent = " " * (class_indent + 4)

                # Re-indent the function body
                reindented = []
                for fl in func_lines:
                    stripped = fl.lstrip()
                    if stripped:
                        reindented.append(body_indent + stripped)
                    else:
                        reindented.append("")

                # Remove the old function lines
                del lines[func_line:func_end]

                # Insert the re-indented function before the class's last line
                # Find the last line of the class
                for cls in class_defs:
                    if cls[0] == class_name:
                        _, _, cls_end_line = cls
                        # Insert before the last line of the class
                        # Adjust func_end if it was before the insertion point
                        insert_at = cls_end_line - 1  # before closing blank line
                        for _ in range(func_end - func_line):
                            reindented.insert(0, "")
                        for line in reindented:
                            lines.insert(insert_at, line)
                        modified = True
                        break

    if modified:
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Fixed test indentation in %s", filepath.relative_to(filepath.parent.parent))
        return 1
    return 0


def _find_func_end(node: ast.FunctionDef, total_lines: int) -> int:
    """Find the last line of a function definition (approximate)."""
    # Walk the AST to find the deepest line number in this function
    max_line = node.lineno
    for child in ast.walk(node):
        if hasattr(child, "lineno") and child.lineno:
            max_line = max(max_line, child.lineno)
    # Add a bit for trailing blank lines
    return min(max_line + 2, total_lines)


def _fix_test_indentation_regex(filepath: Path, content) -> int:
    """Fallback regex-based indentation fix when AST parsing fails."""
    lines = content.split("\n")
    modified = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Match: def test_X(self): at column 0 (module level)
        match = re.match(r"^def test_\w+\(self\):", stripped)
        if match and not line.startswith(" ") and not line.startswith("\t"):
            # This is a module-level test function — find its body
            func_start = i
            body_found = False
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or (lines[j].startswith(" ") or lines[j].startswith("\t"))):
                if lines[j].strip() and (lines[j].startswith(" ") or lines[j].startswith("\t")):
                    body_found = True
                j += 1
            # Indent the entire function by 4 spaces
            for k in range(func_start, j):
                if lines[k].strip():
                    lines[k] = "    " + lines[k]
            modified = True
            i = j
        else:
            i += 1

    if modified:
        filepath.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Regex indentation fix in %s", filepath.relative_to(filepath.parent))
        return 1
    return 0


def _autocorrect_test_mismatches(workspace: Path) -> int:
    """Auto-correct method name mismatches in test files by comparing against implementation AST.

    When the model writes tests calling methods that don't exist on the implementation
    classes (e.g., ``parser.parse()`` when the real method is ``parser.extract_product_data()``),
    this function detects the mismatch and rewrites the test file with the correct method name.

    Returns the number of test files corrected (0 if nothing changed).
    """
    corrected_count = 0

    # Step 1: Build a mapping of class_name -> {method_name -> source_file}
    # from all Python files in src/ and top-level .py files
    class_methods: Dict[str, Dict[str, str]] = {}  # class_name -> {method_name -> source_file}
    impl_files = list(workspace.rglob("src/**/*.py")) + list(workspace.glob("*.py"))
    for py_file in impl_files:
        if py_file.name == "__init__.py" or not py_file.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in py_file.parts):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    methods = {}
                    for item in ast.iter_child_nodes(node):
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methods[item.name] = str(py_file.relative_to(workspace))
                    if methods:
                        class_methods[node.name] = methods
        except Exception:
            continue

    if not class_methods:
        return 0

    # Step 2: Find all test files
    test_files = []
    for pat in ("tests/test_*.py", "test_*.py", "tests/*_test.py", "*_test.py"):
        test_files.extend(workspace.glob(pat))
    # Also check in subdirectories
    for py_file in workspace.rglob("test_*.py"):
        if py_file not in test_files and not any(part in EXCLUDED_DIRS for part in py_file.parts):
            test_files.append(py_file)
    for py_file in workspace.rglob("*_test.py"):
        if py_file not in test_files and not any(part in EXCLUDED_DIRS for part in py_file.parts):
            test_files.append(py_file)

    # Step 3: For each test file, find mismatches and correct them
    for test_file in test_files:
        try:
            content = test_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except Exception:
            continue

        # Build a mapping: variable_name -> class_name (from imports and assignments)
        var_to_class: Dict[str, str] = {}
        for node in ast.walk(tree):
            # from src.parser import ProductParser
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    imported_name = alias.asname or alias.name
                    if alias.name in class_methods:
                        var_to_class[imported_name] = alias.name
            # parser = ProductParser()
            if isinstance(node, ast.Assign):
                if (isinstance(node.value, ast.Call) and
                    isinstance(node.value.func, ast.Name) and
                    node.value.func.id in class_methods):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_to_class[target.id] = node.value.func.id

        if not var_to_class:
            continue

        # Find all method calls and check for mismatches
        changes: List[Tuple[str, str, str, str]] = []  # (var_name, wrong_method, correct_method, class_name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    var_name = node.func.value.id
                    method_name = node.func.attr
                    if var_name in var_to_class:
                        class_name = var_to_class[var_name]
                        if class_name in class_methods:
                            actual_methods = class_methods[class_name]
                            if method_name not in actual_methods and actual_methods:
                                # Find the closest matching method (simple heuristic: same prefix or common substring)
                                correct = _find_closest_method(method_name, actual_methods.keys())
                                if correct:
                                    changes.append((var_name, method_name, correct, class_name))

        if changes:
            # Apply changes to the source code
            new_content = content
            for var_name, wrong_method, correct_method, class_name in changes:
                # Replace var_name.wrong_method( with var_name.correct_method(
                # Use word boundaries to avoid partial matches
                pattern = re.compile(
                    r'\b' + re.escape(var_name) + r'\.' + re.escape(wrong_method) + r'\b'
                )
                new_content = pattern.sub(f'{var_name}.{correct_method}', new_content)
                logger.info(
                    "Auto-corrected %s.%s() -> %s.%s() in %s (class %s)",
                    var_name, wrong_method, var_name, correct_method,
                    test_file.relative_to(workspace), class_name,
                )

            if new_content != content:
                test_file.write_text(new_content, encoding="utf-8")
                corrected_count += 1

    return corrected_count


def _find_closest_method(wrong_name: str, actual_methods) -> Optional[str]:
    """Find the closest matching method name from actual_methods using simple heuristics."""
    actual_list = list(actual_methods)
    if not actual_list:
        return None

    # Exact prefix match (e.g., "parse" matches "parse_data")
    prefix_matches = [m for m in actual_list if m.startswith(wrong_name)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    # Suffix match (e.g., "get_data" matches "extract_data")
    suffix_matches = [m for m in actual_list if m.endswith(wrong_name.split("_")[-1])]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    # Common substring (longest common substring > 3 chars)
    best = None
    best_len = 0
    for m in actual_list:
        # Find longest common substring
        for i in range(len(wrong_name)):
            for j in range(i + 3, len(wrong_name) + 1):
                substr = wrong_name[i:j]
                if substr in m and len(substr) > best_len:
                    best_len = len(substr)
                    best = m
    if best and best_len >= 3:
        return best

    # If only one method exists on the class, use it
    if len(actual_list) == 1:
        return actual_list[0]

    return None


@dataclass
class EvalResult:
    """The outcome of an evaluation: pass/fail, a summary, detail, and whether tests actually ran."""
    passed: bool
    summary: str
    details: str = ""
    ran_tests: bool = False
    test_files_written_during_run: bool = False
    # Structured tally, so a reader (and the audit log) can see convergence across
    # retries — "6 failing -> 4 -> 0" -- rather than just repeated "passed=False".
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    failing_tests: List[str] = field(default_factory=list)


def _parse_pytest_tally(output: str) -> Tuple[int, int, int, List[str]]:
    """Return (passed, failed, skipped, failing_test_ids) parsed from pytest output.

    Best-effort and runner-specific to pytest; on any non-pytest or unparseable
    output the counts come back zero and the caller simply logs no tally.

    Counts are read ONLY from pytest's final summary line (the one ending in
    ``... in <n>s``), never with a bare ``re.search(r"\\d+ failed")`` over the whole
    output — a failing run with 20 tracebacks can contain the substring "0 failed"
    inside an assertion/diff, and matching that first gave a count of 0 while 20
    tests were actually failing. That contradiction then blinded the no-progress
    stop. The count is finally reconciled with the FAILED ids so it can never be
    lower than the number of failures we can actually name.
    """
    if not output:
        return 0, 0, 0, []
    failing = re.findall(r"^FAILED (\S+)", output, re.MULTILINE)

    # In -q mode pytest omits the "FAILED ..." summary lines; fall back to the
    # underscore-delimited section headers in the FAILURES block.
    if not failing:
        failing = re.findall(
            r"^_{3,}\s+(\S+?)\s+_{3,}$", output, re.MULTILINE
        )

    # pytest's tally lives on the last line that ends in a duration ("... in 0.5s").
    summary = ""
    for line in reversed(output.splitlines()):
        if re.search(r"\bin \d+(?:\.\d+)?s\b", line) and re.search(
            r"\b(passed|failed|error|errors|skipped)\b", line
        ):
            summary = line
            break

    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", summary)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", summary)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", summary)) else 0
    skipped = int(m.group(1)) if (m := re.search(r"(\d+) skipped", summary)) else 0
    failed += errors
    # Never report fewer failures than we can name (handles a truncated summary).
    failed = max(failed, len(failing))
    return passed, failed, skipped, failing


class Evaluator:
    """Run tests inside the sandbox and interpret the outcome."""

    def __init__(
        self, 
        sandbox, 
        policy,
        test_command: Optional[str] = None,
        initial_test_files: Optional[List[str]] = None,
        timeout: int = TEST_EXECUTION_TIMEOUT
    ) -> None:
        """Bind the sandbox and policy, plus an optional forced test command and initial test-file set."""
        self.sandbox = sandbox
        self.policy = policy
        self.timeout = timeout
        
        # Validate and store test command
        if test_command and not _is_safe_command(test_command):
            logger.error(f"Unsafe test command provided: {test_command}")
            self.test_command = None
        else:
            self.test_command = test_command
            
        self.initial_test_files = initial_test_files
        self._initial_test_hashes: Set[str] = set()
        self._workspace_checksum: Optional[str] = None

    # -- detection -----------------------------------------------------------
    def _find_test_files(self, workspace: Path) -> List[str]:
        """Return workspace-relative paths of every pytest-style test file present now."""
        found: List[str] = []
        count = 0
        
        for pattern in ("test_*.py", "*_test.py"):
            try:
                for p in workspace.rglob(pattern):
                    # Skip excluded directories
                    if EXCLUDED_DIRS & set(p.parts):
                        continue
                    
                    # Skip if not a file
                    if not p.is_file():
                        continue
                        
                    # Limit scanning
                    count += 1
                    if count > MAX_TEST_FILES_TO_SCAN:
                        logger.warning(f"Test file scan limit reached ({MAX_TEST_FILES_TO_SCAN})")
                        break
                        
                    found.append(p.relative_to(workspace).as_posix())
            except Exception as e:
                logger.warning(f"Error scanning for pattern {pattern}: {e}")
                continue
                
        return sorted(set(found))

    def _has_python_tests(self, workspace: Path) -> bool:
        """Return True if the workspace contains pytest-style test files *right now*."""
        return bool(self._find_test_files(workspace))

    def _self_authored_only(self, workspace: Path) -> bool:
        """True if every test file present was written during this run."""
        if self.initial_test_files is None:
            return False

        current = self._find_test_files(workspace)
        if not current:
            return False

        # Compute content hashes for initial test files (may have been moved by AC-06a)
        if not self._initial_test_hashes:
            for f in self.initial_test_files:
                p = workspace / f
                if p.is_file():
                    try:
                        h = hashlib.sha256(p.read_bytes()).hexdigest()
                        self._initial_test_hashes.add(h)
                    except Exception:
                        pass

        # Compute content hashes for current test files
        current_hashes: Set[str] = set()
        for f in current:
            p = workspace / f
            if p.is_file():
                try:
                    current_hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
                except Exception:
                    pass

        # If any current test file's content matches a pre-existing file, not self-authored
        return not bool(current_hashes & self._initial_test_hashes)

    def _detect_command(self, workspace: Path) -> Optional[str]:
        """Pick the test command: the override, then project markers, then pytest, else None."""
        if self.test_command:
            return self.test_command
            
        for marker, command in PROJECT_MARKERS:
            if (workspace / marker).exists():
                return command
                
        if self._has_python_tests(workspace):
            # -rs surfaces skip REASONS so a skip-to-green ("not implemented") is visible.
            return "PYTHONPATH=. python -m pytest -q -rs"

        return None

    def _revert_test_files(self, workspace: Path) -> None:
        """Revert modifications to initial test files."""
        if self.initial_test_files is None:
            return
            
        for test_file in self.initial_test_files:
            try:
                # Check if file exists and is tracked
                test_path = workspace / test_file
                if not test_path.exists():
                    continue
                    
                # Check git tracking
                check_cmd = f"test -f {test_file} && git ls-files --error-unmatch {test_file} 2>/dev/null"
                check_result = self.sandbox.exec(check_cmd)
                
                if check_result.exit_code == 0:
                    # File is tracked, revert it
                    revert_cmd = f"git checkout -- {shlex.quote(test_file)}"
                    self.sandbox.exec(revert_cmd)
                    logger.debug(f"Reverted test file: {test_file}")
                else:
                    logger.debug(f"Test file not tracked or missing: {test_file}")
            except Exception as e:
                logger.warning(f"Failed to revert test file {test_file}: {e}")

    # -- dependency installation -----------------------------------------------
    def _install_dependencies(self, workspace: Path) -> None:
        """Detect and install project dependencies before running tests.

        Checks for requirements.txt, setup.py, or pyproject.toml and runs the
        appropriate pip install command. Failures are logged but do not abort
        the evaluation — the tests may still pass without the packages.
        """
        req = workspace / "requirements.txt"
        setup_py = workspace / "setup.py"
        pyproject = workspace / "pyproject.toml"
        setup_cfg = workspace / "setup.cfg"

        if req.exists():
            cmd = f"pip install -r {shlex.quote(str(req))} -q"
            logger.info("Installing dependencies from requirements.txt")
            try:
                self.sandbox.exec(cmd, timeout=120)
            except Exception as exc:
                logger.warning("pip install -r requirements.txt failed: %s", exc)
        elif setup_py.exists() or (pyproject.exists() and not setup_cfg.exists()):
            cmd = "pip install -e . -q"
            logger.info("Installing project in editable mode")
            try:
                self.sandbox.exec(cmd, timeout=120)
            except Exception as exc:
                logger.warning("pip install -e . failed: %s", exc)

    # -- evaluation ----------------------------------------------------------
    def evaluate(self, workspace: Path) -> EvalResult:
        """Run the detected test command in the sandbox and interpret pass/fail/timeout/no-tests."""
        workspace = Path(workspace)

        # Install dependencies if a requirements file or setup.py exists
        self._install_dependencies(workspace)

        # Revert any modifications to initial test files
        self._revert_test_files(workspace)

        # Snapshot content hashes of initial test files before any structural changes
        if self.initial_test_files and not self._initial_test_hashes:
            for f in self.initial_test_files:
                p = workspace / f
                if p.is_file():
                    try:
                        h = hashlib.sha256(p.read_bytes()).hexdigest()
                        self._initial_test_hashes.add(h)
                    except Exception:
                        pass

        # Fix workspace structure issues before running tests (disabled via SKIP_AUTOCORRECT=1)
        if not os.environ.get("SKIP_AUTOCORRECT"):
            _ensure_workspace_structure(workspace)

        # Auto-correct test/implementation mismatches before running tests (disabled via SKIP_AUTOCORRECT=1)
        if not os.environ.get("SKIP_AUTOCORRECT"):
            _autocorrect_test_mismatches(workspace)

        command = self._detect_command(workspace)
        if command is None:
            return self._syntax_check(workspace)

        # Run the test command with timeout
        try:
            result = self.sandbox.exec(command, timeout=self.timeout)
        except TimeoutError:
            return EvalResult(
                False,
                f"Tests timed out ({command})",
                "Test execution exceeded time limit. Check for infinite loops or slow tests.",
                ran_tests=True
            )
        
        output = self.policy.scrub(result.output)

        # Handle pytest no-tests case
        if (command.startswith("PYTHONPATH=. python -m pytest") and 
            result.exit_code == PYTEST_NO_TESTS):
            if _is_collection_error(output):
                return EvalResult(
                    False,
                    f"Tests were found but none could be collected ({command}). This is "
                    f"usually an import error, a missing plugin, or a broken conftest -- "
                    f"fix it so the tests can run; the code is NOT verified.",
                    _condense_test_output(output),
                    ran_tests=False,
                )
            return self._syntax_check(workspace)

        passed_n, failed_n, skipped_n, failing = _parse_pytest_tally(output)

        # Handle successful test run
        if result.ok:
            # A green reached only by SKIPPING required work ("not implemented") is a
            # false green — unverified functionality, not a pass. Refuse to call it done.
            unimplemented = _unimplemented_skips(output)
            if unimplemented:
                shown = "\n".join(unimplemented[:10])
                return EvalResult(
                    False,
                    f"Tests are green ONLY because {len(unimplemented)} test(s) were "
                    f"skipped as unimplemented/TODO — that is not a pass, the required "
                    f"functionality is unverified. Implement them so they run:\n{shown}",
                    _condense_test_output(output),
                    ran_tests=True,
                    tests_passed=passed_n,
                    tests_failed=failed_n,
                    tests_skipped=skipped_n,
                    failing_tests=failing,
                )
            authored_note = self._self_authored_only(workspace)
            note = " — note: all tests were written during this run" if authored_note else ""
            # Surface skipped tests. A green run that reaches "done" by SKIPPING
            # required tests (e.g. @pytest.mark.skip("not implemented")) is not a
            # clean pass — the skipped work is unverified. Make it visible in the
            # summary so a skip-to-green never looks identical to a genuine green.
            skip_note = (
                f" — WARNING: {skipped_n} test(s) SKIPPED and NOT verified "
                f"({passed_n} passed of {passed_n + skipped_n})"
                if skipped_n else ""
            )
            return EvalResult(
                True,
                f"Tests passed ({command}){note}{skip_note}",
                output,
                ran_tests=True,
                test_files_written_during_run=authored_note,
                tests_passed=passed_n,
                tests_failed=failed_n,
                tests_skipped=skipped_n,
                failing_tests=failing,
            )

        # Handle test failure
        details = _condense_test_output(output)
        # Surface actual implementation signatures so the model can align tests
        sigs = _extract_implementation_signatures(workspace, failing, output)
        if sigs:
            details += sigs
        return EvalResult(
            False,
            f"Tests failed ({command})",
            details,
            ran_tests=True,
            tests_passed=passed_n,
            tests_failed=failed_n,
            tests_skipped=skipped_n,
            failing_tests=failing,
        )

    def _syntax_check(self, workspace: Path) -> EvalResult:
        """Fallback when no tests exist: compile all sources and confirm edits were made."""
        try:
            result = self.sandbox.exec("python -m compileall -q .", timeout=60)
        except TimeoutError:
            return EvalResult(
                False,
                "Syntax check timed out",
                "The codebase is too large to compile in reasonable time.",
                ran_tests=False
            )
            
        output = self.policy.scrub(result.output)
        
        if result.ok:
            # Verify edits were actually made using git status
            try:
                git_check = self.sandbox.exec("git status --porcelain", timeout=30)
            except TimeoutError:
                return EvalResult(
                    True, 
                    "No tests found; sources compile cleanly (git status timed out)",
                    output,
                    ran_tests=False
                )
                
            if git_check.exit_code == 0:
                git_lines = [
                    line for line in git_check.output.splitlines()
                    if "__pycache__" not in line and not line.strip().endswith(".pyc")
                ]
                if not git_lines:
                    return EvalResult(
                        False,
                        "No tests found, and no edits/mutations made to the workspace.",
                        "The original codebase compiles cleanly, but no modifications were detected. "
                        "An edit task requires modifying the codebase.",
                        ran_tests=False
                    )
                    
            return EvalResult(
                True, 
                "No tests found; sources compile cleanly", 
                output,
                ran_tests=False
            )
            
        return EvalResult(
            False, 
            "Syntax errors detected", 
            output,
            ran_tests=False
        )

    def cleanup(self) -> None:
        """Clean up any resources used by the evaluator."""
        # Nothing to clean up currently, but method exists for future extensibility
        pass
