"""Tool execution, parsing, file locking, and filtering."""
from __future__ import annotations

import ast
import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..tools.parser import ToolCall
from ..tools.registry import ToolResult
from .config import AgentConfig

try:
    from ..evaluation.evaluator import _autocorrect_html_tags
except ImportError:
    _autocorrect_html_tags = None

from rich.console import Console
from rich.markup import escape

console = Console()
logger = logging.getLogger(__name__)


# ---- Auto-correction functions for recurring model bugs ----


def _autocorrect_async_sleep(content: str) -> str:
    """AC-01: Replace time.sleep(X) with await asyncio.sleep(X) inside async functions.

    Model frequently uses blocking time.sleep() inside async functions, which
    blocks the event loop and hangs async code.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return content

    lines = content.split('\n')
    modified = False
    has_asyncio_import = any('import asyncio' in line for line in lines)

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for child in ast.walk(node):
                if (isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and isinstance(child.func.value, ast.Name)
                        and child.func.value.id == 'time'
                        and child.func.attr == 'sleep'):
                    line_idx = child.lineno - 1
                    line = lines[line_idx]
                    lines[line_idx] = line.replace('time.sleep', 'await asyncio.sleep', 1)
                    modified = True

    if not modified:
        return content

    result = '\n'.join(lines)

    if not has_asyncio_import:
        last_import = -1
        for i, line in enumerate(lines):
            if re.match(r'^(import |from )', line):
                last_import = i

        lines_list = result.split('\n')
        if last_import >= 0:
            lines_list.insert(last_import + 1, 'import asyncio')
        else:
            lines_list.insert(0, 'import asyncio')
        result = '\n'.join(lines_list)

    return result


def _autocorrect_js_booleans(content: str) -> str:
    """AC-02: Replace JavaScript booleans (true/false/null) with Python equivalents.

    Model trained on mixed JS/Python data frequently writes:
    - ``reverse=true`` instead of ``reverse=True``
    - ``return null`` instead of ``return None``
    - ``if result == false:`` instead of ``if result == False:``
    """
    # Only replace bare identifiers, not inside strings or comments
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Fall back to regex for files with syntax errors
        content = re.sub(r'(?<![\.\w])true(?![\.\w])', 'True', content)
        content = re.sub(r'(?<![\.\w])false(?![\.\w])', 'False', content)
        content = re.sub(r'(?<![\.\w])null(?![\.\w])', 'None', content)
        return content

    lines = content.split('\n')
    modified = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        new_line = re.sub(r'(?<![\.\w])true(?![\.\w])', 'True', line)
        new_line = re.sub(r'(?<![\.\w])false(?![\.\w])', 'False', new_line)
        new_line = re.sub(r'(?<![\.\w])null(?![\.\w])', 'None', new_line)
        if new_line != line:
            lines[i] = new_line
            modified = True

    if modified:
        return '\n'.join(lines)
    return content


def _autocorrect_missing_imports(content: str, file_path: str, workspace: Path) -> str:
    """AC-03: Detect and add missing imports for names used but not imported.

    When the model references a class/function without importing it (e.g.,
    ``raise TransformationError(...)`` without ``from .errors import TransformationError``),
    this function searches the workspace for the definition and adds the import.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return content

    # Collect all names imported/defined in this file
    defined_names: Set[str] = set()
    imported_names: Dict[str, str] = {}  # name -> module

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split('.')[0]
                imported_names[name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names[name] = f"{node.module}.{alias.name}" if node.module else alias.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined_names.add(node.name)

    # Find names that are used but not defined or imported
    used_names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                used_names.add(node.func.id)
        elif isinstance(node, ast.Raise):
            if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                used_names.add(node.exc.func.id)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)

    missing: List[str] = []
    for name in used_names:
        if name not in defined_names and name not in imported_names:
            if name[0].isupper() or name.endswith('Error') or name.endswith('Exception'):
                # Likely a class that needs importing
                missing.append(name)

    if not missing:
        return content

    # Try to find definitions in the workspace
    # Look in the same directory and in src/
    file_dir = (workspace / file_path).parent
    src_dir = workspace / "src"
    search_dirs = [file_dir]
    if src_dir.exists():
        search_dirs.append(src_dir)

    found_imports: Dict[str, str] = {}
    for name in missing:
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for py_file in sorted(search_dir.rglob("*.py")):
                if py_file.name == "__init__.py":
                    continue
                try:
                    py_content = py_file.read_text(encoding="utf-8", errors="replace")
                    py_tree = ast.parse(py_content)
                    for node in ast.iter_child_nodes(py_tree):
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                            if node.name == name:
                                # Found it! Build relative import path
                                rel_path = py_file.relative_to(search_dir.parent if search_dir.parent.name == "src" else search_dir)
                                module_path = str(rel_path.with_suffix('')).replace('/', '.')
                                if search_dir.parent.name == "src":
                                    module_path = f"src.{module_path}"
                                elif search_dir == file_dir:
                                    module_path = f".{module_path}"
                                found_imports[name] = module_path
                                break
                except Exception:
                    continue
            if name in found_imports:
                break

    if not found_imports:
        return content

    # Add missing imports to the file
    lines = content.split('\n')
    insert_pos = 0
    for i, line in enumerate(lines):
        if re.match(r'^(import |from )', line):
            insert_pos = i + 1

    added = []
    for name, module in sorted(found_imports.items()):
        # Check if it's already imported
        already = any(f"import {name}" in line or f"import {name}," in line or f"import {module}" in line for line in lines)
        if not already:
            lines.insert(insert_pos, f"from {module} import {name}")
            insert_pos += 1
            added.append(name)

    if added:
        return '\n'.join(lines)
    return content


def _autocorrect_duplicate_definitions(content: str, file_path: str, workspace: Path) -> str:
    """AC-04: Remove class/function definitions that duplicate existing ones in the package.

    Model frequently re-defines classes already defined in other files
    (e.g., defining ``ValidationError`` in multiple files). This removes
    the duplicate and adds an import from the canonical source instead.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return content

    # Find class/function definitions in THIS file
    local_defs: Dict[str, int] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            local_defs[node.name] = node.lineno

    if not local_defs:
        return content

    # Find definitions in other files in the same package
    file_dir = (workspace / file_path).parent
    same_package = list(file_dir.glob("*.py")) if file_dir.exists() else []
    if not same_package:
        return content

    canonical: Dict[str, Tuple[str, str]] = {}  # name -> (module_path, source_file)

    for py_file in same_package:
        if py_file.name == Path(file_path).name:
            continue  # skip self
        try:
            py_content = py_file.read_text(encoding="utf-8", errors="replace")
            py_tree = ast.parse(py_content)
            for node in ast.iter_child_nodes(py_tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name in local_defs and node.name not in canonical:
                        # This is the canonical source
                        rel = py_file.relative_to(workspace)
                        module_path = str(rel.with_suffix('')).replace('/', '.')
                        canonical[node.name] = (module_path, str(py_file.name))
        except Exception:
            continue

    if not canonical:
        return content

    # Remove duplicate definitions and add imports
    lines = content.split('\n')
    modified = False

    for name, (module_path, source_file) in canonical.items():
        # Find all lines belonging to this definition
        def_start = local_defs[name] - 1  # 0-indexed
        # Find where the definition ends (next top-level def or end)
        def_end = len(lines)
        next_defs = [l for n, l in local_defs.items() if n != name and l > (def_start + 1)]
        if next_defs:
            def_end = min(next_defs) - 1

        # Find indentation of the def/class line
        def_line = lines[def_start]
        indent = len(def_line) - len(def_line.lstrip())

        # Remove the definition lines
        for _ in range(def_start, def_end):
            if def_start < len(lines):
                lines.pop(def_start)

        # Add import at the top
        insert_pos = 0
        for i, line in enumerate(lines):
            if re.match(r'^(import |from )', line):
                insert_pos = i + 1

        import_stmt = f"from {module_path} import {name}"
        if import_stmt not in lines:
            lines.insert(insert_pos, import_stmt)
            modified = True

    if modified:
        return '\n'.join(lines)
    return content


def _autocorrect_import_paths(content: str, file_path: str, workspace: Path) -> str:
    """AC-05: Fix incorrect import paths that reference non-existent modules.

    When the model writes imports like ``from .pipeline_error import ValidationError``
    but the actual module is ``errors.py``, this function searches the workspace
    for the correct module path and fixes the import.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return content

    file_dir = (workspace / file_path).parent
    lines = content.split('\n')
    modified = False

    for i, line in enumerate(lines):
        # Check relative imports: from .X import Y
        match = re.match(r'^from\s+(\.)(\w+)\s+import\s+(.+)$', line)
        if not match:
            # Check also: from src.X import Y (direct, not relative)
            match = re.match(r'^from\s+src\.(\w+)\s+import\s+(.+)$', line)

        if not match:
            continue

        prefix = match.group(1) if match.group(1) == '.' else 'src.'
        module_name = match.group(2) if match.group(1) == '.' else match.group(1)
        imported_names = match.group(len(match.groups()))

        # Check if the module file exists
        module_file = file_dir / f"{module_name}.py"
        module_pkg = file_dir / module_name / "__init__.py"
        if module_file.exists() or module_pkg.exists():
            continue

        # Module doesn't exist — search workspace for files with these names
        for search_dir in [workspace, workspace / "src"]:
            if not search_dir.exists():
                continue
            for py_file in sorted(search_dir.rglob("*.py")):
                if py_file.stem == module_name:
                    rel = py_file.relative_to(search_dir)
                    correct_module = str(rel.with_suffix('')).replace('/', '.')
                    if search_dir.name == "src":
                        correct_module = f"src.{correct_module}"
                    # Fix the import
                    if prefix == '.':
                        lines[i] = f"from .{correct_module} import {imported_names}"
                    else:
                        lines[i] = f"from {correct_module} import {imported_names}"
                    modified = True
                    logger.info(
                        "AC-05: Fixed import '%s' -> '%s' in %s",
                        line.strip(), lines[i].strip(), file_path,
                    )
                    break
            if modified:
                break

    if modified:
        return '\n'.join(lines)
    return content


def _autocorrect_syntax_errors(content: str, file_path: str) -> str:
    """AC-07: Fix Python syntax errors (especially indentation corruption).

    The model frequently corrupts indentation during edit_lines calls,
    producing IndentationError. This function detects such errors and
    attempts to fix them by analysing block structure.
    """
    if not content.strip():
        return content

    for attempt in range(3):
        try:
            compile(content, file_path, 'exec')
            return content
        except (IndentationError, SyntaxError) as e:
            if attempt == 2:
                return content  # give up after 3 tries
            lines = content.split('\n')
            fixed = False

            lineno = getattr(e, 'lineno', None)
            if lineno is None:
                continue

            # Heuristic: find the block structure around the error line
            error_idx = lineno - 1  # 0-indexed
            if error_idx >= len(lines):
                continue

            error_line = lines[error_idx]
            error_indent = len(error_line) - len(error_line.lstrip())

            # Look backwards to find the enclosing block
            block_start = None
            for i in range(error_idx - 1, -1, -1):
                stripped = lines[i].strip()
                if not stripped or stripped.startswith('#'):
                    continue
                line_indent = len(lines[i]) - len(lines[i].lstrip())
                if stripped.endswith(':') and line_indent < error_indent:
                    block_start = i
                    break
                if stripped.startswith(('except', 'elif', 'else:', 'finally')):
                    if line_indent < error_indent:
                        block_start = i
                        break

            if block_start is not None:
                block_indent = len(lines[block_start]) - len(lines[block_start].lstrip())
                expected = block_indent + 4
                if error_indent != expected:
                    lines[error_idx] = ' ' * expected + error_line.lstrip()
                    fixed = True

            # Also check if the error line is an except/elif/else/finally
            # that should match its parent block indent
            stripped = error_line.strip()
            if not fixed and stripped.startswith(('except', 'elif', 'else:', 'finally')):
                for i in range(error_idx - 1, -1, -1):
                    s = lines[i].strip()
                    if not s or s.startswith('#'):
                        continue
                    li = len(lines[i]) - len(lines[i].lstrip())
                    if s.endswith(':') and li < error_indent:
                        # Match the block start indent
                        if error_indent != li:
                            lines[error_idx] = ' ' * li + error_line.lstrip()
                            fixed = True
                        break

            # Broader fix: scan all lines for dangling statements after blocks
            if not fixed:
                stack = []
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if not stripped or stripped.startswith('#'):
                        continue
                    indent = len(line) - len(line.lstrip())

                    # Pop stack for lines at same or lesser indent
                    while stack and indent <= stack[-1]:
                        if indent == stack[-1]:
                            stack.pop()
                            break
                        stack.pop()

                    if stripped.endswith(':'):
                        stack.append(indent)

                    if (stripped.startswith(('except', 'elif', 'else:', 'finally'))
                            and stack):
                        if indent != stack[-1]:
                            lines[i] = ' ' * stack[-1] + stripped
                            fixed = True

            if fixed:
                content = '\n'.join(lines)

    return content


def _autocorrect_async_generator(content: str) -> str:
    """AC-13: Convert ``return <value>`` → ``yield <value>`` in @asynccontextmanager async def.

    Models frequently write ``return db`` inside an ``@asynccontextmanager``
    async generator, but the protocol requires ``yield db``.  This corrector
    detects the pattern and fixes it by rewriting the return statement.
    """
    if "asynccontextmanager" not in content and "contextmanager" not in content:
        return content
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return content

    lines = content.split("\n")
    # Build a mapping from AST line numbers to 0-based line indices
    line_map: dict[int, str] = {}  # lineno → stripped text of the return statement

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Check if decorated with @asynccontextmanager or @contextmanager
        is_cm = False
        for deco in node.decorator_list:
            if isinstance(deco, ast.Name) and deco.id in ("asynccontextmanager", "contextmanager"):
                is_cm = True
                break
            if isinstance(deco, ast.Attribute) and deco.attr in ("asynccontextmanager", "contextmanager"):
                is_cm = True
                break
        if not is_cm:
            continue
        # Collect all returns inside the function (excluding nested defs).
        # Store (lineno_0based, has_value) for each return.
        return_sites: list[tuple[int, bool]] = []
        def _walk_returns(n: ast.AST) -> None:
            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node:
                    continue
                if isinstance(child, ast.Return):
                    return_sites.append((child.lineno - 1, child.value is not None))
                _walk_returns(child)
        _walk_returns(node)
        for idx, has_val in return_sites:
            original_line = lines[idx]
            stripped = original_line.lstrip()
            indent = original_line[:len(original_line) - len(stripped)]
            if not has_val:
                lines[idx] = indent + "yield"
            else:
                expr_text = stripped[len("return"):].strip()
                lines[idx] = indent + "yield " + expr_text

    return "\n".join(lines)


def _autocorrect_file(content: str, file_path: str, workspace: Path) -> str:
    """Apply all auto-correctors to a Python file's content before writing.

    Runs AC-01 through AC-05 in sequence. Each corrector fixes a known
    recurring model bug. Order matters: import fixers should run last
    since they depend on stable content.
    """
    if not content or not file_path.endswith('.py'):
        return content

    original = content

    # AC-07: Fix syntax/indentation errors FIRST (ensures parseable code)
    content = _autocorrect_syntax_errors(content, file_path)

    # AC-02: Fix JavaScript booleans (affects AST parsing)
    content = _autocorrect_js_booleans(content)

    # AC-01: Fix time.sleep in async functions
    content = _autocorrect_async_sleep(content)

    # AC-04: Remove duplicate definitions
    content = _autocorrect_duplicate_definitions(content, file_path, workspace)

    # AC-05: Fix incorrect import paths
    content = _autocorrect_import_paths(content, file_path, workspace)

    # AC-03: Add missing imports LAST (needs stable content)
    content = _autocorrect_missing_imports(content, file_path, workspace)

    # AC-13: Fix `return` vs `yield` in @asynccontextmanager async generators
    content = _autocorrect_async_generator(content)

    if content != original:
        logger.info(
            "Auto-corrected %s (%d chars -> %d chars)",
            file_path, len(original), len(content),
        )

    return content


def _validate_imports(content: str, file_path: str, workspace: Path) -> Optional[str]:
    """Check that local imports in Python code reference existing modules.

    Returns a warning string if broken local imports are detected, or None if OK.
    Skips stdlib and third-party imports (only checks imports that resolve to
    workspace-relative paths). Also warns if imports use the workspace directory
    name instead of the correct module path (e.g. ``from my_ws.core`` instead of
    ``from src.core``).
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    broken = []
    workspace_dir_name = workspace.name  # e.g. "task_queue_ws_08"
    ws_name_imports: List[str] = []
    file_dir = (workspace / file_path).parent

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            continue  # relative imports are fine
        if isinstance(node, ast.ImportFrom) and node.module:
            module = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
        else:
            continue

        if not module:
            continue

        # Only check single-level modules that could be workspace-local
        parts = module.split(".")
        top = parts[0]

        # Detect workspace directory name in import path (e.g. from task_queue_ws_08.core)
        if top == workspace_dir_name:
            ws_name_imports.append(module)
            continue  # already flagged, skip further checks

        # Skip known third-party / stdlib modules
        _KNOWN = {
            "os", "sys", "json", "re", "time", "datetime", "pathlib", "typing",
            "asyncio", "logging", "collections", "functools", "itertools", "io",
            "shlex", "subprocess", "tempfile", "hashlib", "uuid", "abc", "dataclasses",
            "enum", "contextlib", "textwrap", "unittest", "copy", "math", "random",
            "string", "struct", "base64", "urllib", "http", "socket", "threading",
            "multiprocessing", "signal", "errno", "glob", "fnmatch", "csv", "sqlite3",
            "xml", "html", "email", "gzip", "zipfile", "tarfile", "shutil",
            "configparser", "argparse", "getpass", "platform", "traceback",
            "warnings", "weakref", "types", "importlib", "pkgutil", "inspect",
            "ast", "dis", "code", "codeop", "compileall", "py_compile",
            # Common third-party
            "pytest", "numpy", "pandas", "requests", "httpx", "aiohttp",
            "fastapi", "flask", "django", "sqlalchemy", "pydantic", "click",
            "typer", "rich", "yaml", "toml", "redis", "celery", "pytest",
            "bs4", "lxml", "jinja2", "bcrypt", "jose", "jwt",
        }
        if top in _KNOWN or top.startswith("_"):
            continue

        # Check if the module resolves to a workspace file
        module_path = file_dir / top
        candidate_py = module_path.with_suffix(".py")
        candidate_pkg = module_path / "__init__.py"
        if not candidate_py.exists() and not candidate_pkg.exists():
            # Also check from workspace root
            root_module = workspace / top
            root_py = root_module.with_suffix(".py")
            root_pkg = root_module / "__init__.py"
            if not root_py.exists() and not root_pkg.exists():
                # Check src/ layout
                src_module = workspace / "src" / top
                src_py = src_module.with_suffix(".py")
                src_pkg = src_module / "__init__.py"
                if not src_py.exists() and not src_pkg.exists():
                    broken.append(top)

    warnings: List[str] = []
    if ws_name_imports:
        unique_ws = sorted(set(ws_name_imports))
        warnings.append(
            f"WRONG IMPORT PATH: you used the workspace directory name "
            f"({workspace_dir_name}) in imports: {', '.join(unique_ws)}. "
            f"NEVER use the workspace directory name in import paths. "
            f"Use 'from src.xxx' instead of 'from {workspace_dir_name}.xxx'. "
            f"The workspace directory name is NOT a Python package."
        )
    if broken:
        unique = sorted(set(broken))
        warnings.append(
            f"these local imports may fail (module not found in workspace): "
            f"{', '.join(unique)}. Make sure __init__.py files exist and the modules are created."
        )

    if warnings:
        return "\n\nWarning: " + "; ".join(warnings)
    return None


def _check_dependency_graph(file_path: str, content: str, workspace: Path) -> Optional[str]:
    """Scan workspace for reverse imports and circular dependencies after a write.

    Returns a warning string if other files import from the written module,
    or if a circular dependency is detected, or None if OK.
    """
    rel = Path(file_path)
    if rel.suffix != ".py":
        return None

    stem_parts = list(rel.with_suffix("").parts)
    module_name = ".".join(stem_parts)

    ws_files = list(workspace.rglob("*.py"))
    reverse_deps: List[str] = []
    circular_deps: List[str] = []

    src_relative = workspace / file_path
    for ws_file in ws_files:
        if ws_file.resolve() == src_relative.resolve():
            continue
        try:
            ws_content = ws_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(ws_content)
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
            else:
                continue
            if mod == module_name or mod.startswith(module_name + "."):
                try:
                    reverse_deps.append(str(ws_file.relative_to(workspace)))
                except ValueError:
                    reverse_deps.append(ws_file.name)
                break

    # Check circular dependency: does the written file import any file
    # that in turn imports this file?
    if content:
        try:
            this_tree = ast.parse(content)
        except SyntaxError:
            this_tree = None
        if this_tree:
            imported_mods = set()
            for node in ast.walk(this_tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported_mods.add(node.module.split(".")[0])
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_mods.add(alias.name.split(".")[0])
            for ws_file in ws_files:
                if ws_file.resolve() == src_relative.resolve():
                    continue
                try:
                    ws_content = ws_file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                # Check if THIS file imports from ws_file's module
                ws_rel = ws_file.relative_to(workspace)
                ws_parts = list(ws_rel.with_suffix("").parts)
                ws_module = ".".join(ws_parts)
                ws_top = ws_parts[0] if ws_parts else ""
                if ws_top in imported_mods or ws_module in imported_mods:
                    # ws_file imports from us AND we import from ws_file = circular
                    try:
                        ws_tree = ast.parse(ws_content)
                    except SyntaxError:
                        continue
                    for node in ast.walk(ws_tree):
                        if not isinstance(node, (ast.Import, ast.ImportFrom)):
                            continue
                        mod = None
                        if isinstance(node, ast.ImportFrom) and node.module:
                            mod = node.module
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name == module_name or alias.name.startswith(module_name + "."):
                                    mod = alias.name
                                    break
                        if mod and (mod == module_name or mod.startswith(module_name + ".")):
                            circular_deps.append(str(ws_rel))
                            break

    warnings: List[str] = []
    if reverse_deps:
        warnings.append(
            f"these files import from '{module_name}': "
            f"{', '.join(sorted(set(reverse_deps)))}. "
            f"Ensure your write doesn't break them."
        )
    if circular_deps:
        warnings.append(
            f"circular dependency detected between '{file_path}' and: "
            f"{', '.join(sorted(set(circular_deps)))}"
        )

    if warnings:
        return "\n[DEPENDENCY GRAPH] " + " | ".join(warnings)
    return None


def _ensure_parent_init_files(file_path: str, workspace: Path) -> None:
    """Create __init__.py in every ancestor directory up to workspace root.

    This prevents 'No module named X' errors when the model writes files
    into a new package directory but forgets __init__.py.
    """
    target = workspace / file_path
    if not target.suffix == ".py":
        return
    for parent in reversed(target.relative_to(workspace).parents):
        if parent == Path("."):
            break
        init = workspace / parent / "__init__.py"
        if not init.exists():
            init.parent.mkdir(parents=True, exist_ok=True)
            init.touch()


async def execute_tool_safely(
    call: ToolCall,
    path: str,
    orch: Any,
    security: Any,
    execution_context: Any,
    file_locks: Dict[Path, asyncio.Lock],
) -> ToolResult:
    """Execute a tool with safety checks and mutation tracking."""
    if call.name in ["write_file", "search_replace"]:
        tool_path = call.arguments.get("path", path)
        if not security.validate_path(tool_path):
            return ToolResult(False, f"Security error: Path '{tool_path}' is not allowed")

    if call.name in AgentConfig.MUTATING_TOOLS:
        if execution_context.mutation_steps >= AgentConfig.MAX_MUTATIONS_PER_SUBTASK:
            return ToolResult(
                False,
                f"Modification budget exhausted. You have already made "
                f"{AgentConfig.MAX_MUTATIONS_PER_SUBTASK} edits. "
                "Use `run_command` with heredocs to create remaining files "
                "(e.g. `cat > path/to/file.py << 'PYEOF'\\ncode\\nPYEOF`). "
                "`run_command` does NOT count against this budget. "
                "Then run verification tests and call finish.",
            )
        async with _lock_file(path, orch.workspace, file_locks):
            # Apply auto-correctors BEFORE writing the file (disabled via SKIP_AUTOCORRECT=1 for A/B comparison)
            if call.name == "write_file" and path.endswith(".py") and not os.environ.get("SKIP_AUTOCORRECT"):
                content = call.arguments.get("content", "")
                corrected = _autocorrect_file(content, path, orch.workspace)
                if corrected != content:
                    call.arguments["content"] = corrected
                    orch.log.info("Applied auto-correctors to %s", path)
            result = await orch.tools.execute(call.name, call.arguments)
            if result.ok:
                execution_context.mutations += 1
                execution_context.mutation_steps += 1
                # Post-write syntax fix for both write_file and search_replace on .py files
                if call.name in ("write_file", "search_replace") and path.endswith(".py"):
                    file_path = orch.workspace / path
                    if file_path.exists():
                        try:
                            current = file_path.read_text(encoding="utf-8", errors="replace")
                            fixed = _autocorrect_syntax_errors(current, path)
                            if fixed != current:
                                file_path.write_text(fixed, encoding="utf-8")
                                orch.log.info("AC-07: Fixed syntax errors in %s", path)
                        except Exception:
                            pass
                    # AC-08: Align HTML tags in parser files after any edit
                    if _autocorrect_html_tags is not None:
                        try:
                            n = _autocorrect_html_tags(orch.workspace)
                            if n:
                                orch.log.info("AC-08: Aligned %d HTML tag(s) in %s", n, path)
                        except Exception:
                            pass
                # Validate imports for write_file on Python files
                if call.name == "write_file" and path.endswith(".py"):
                    content = call.arguments.get("content", "")
                    warning = _validate_imports(content, path, orch.workspace)
                    if warning:
                        result.content += warning
                    # AC-12: Dependency graph check — reverse deps + circular
                    dep_warning = _check_dependency_graph(path, content, orch.workspace)
                    if dep_warning:
                        result.content += dep_warning
                    _ensure_parent_init_files(path, orch.workspace)
                if execution_context.mutation_steps >= AgentConfig.MAX_MUTATIONS_PER_SUBTASK:
                    result.content += "\n\nWarning: You have exhausted your file modification budget. "
                    result.content += "Use `run_command` with heredocs to create any remaining files "
                    result.content += "(e.g. `cat > file.py << 'PYEOF'`), then verify and call finish."
    else:
        result = await orch.tools.execute(call.name, call.arguments)

    result.content = security.scrub_output(result.content)
    return result


@asynccontextmanager
async def _lock_file(path: str, workspace: Path, file_locks: Dict[Path, asyncio.Lock]):
    path_obj = workspace / path
    if path_obj not in file_locks:
        file_locks[path_obj] = asyncio.Lock()
    async with file_locks[path_obj]:
        yield


async def read_file_safe(path: str, is_new: bool, workspace: Path) -> str:
    target_path = workspace / path
    if is_new or not target_path.exists():
        return ""
    try:
        return await asyncio.to_thread(
            lambda: target_path.read_text(encoding="utf-8", errors="replace")
        )
    except Exception:
        return ""


async def parse_tool_calls(
    orch: Any,
    response: Any,
    path: str,
) -> Optional[List[ToolCall]]:
    """Parse tool calls from model response with fallback for code blocks."""
    native = orch.parser.parse_native(response.tool_calls)
    calls = native or orch.parser.parse(response.content)

    if not calls:
        is_py = path.endswith(".py")
        implicit_code = orch._extract_implicit_code(response.content or "", is_py)
        if implicit_code:
            orch.log.info("Converted implicit code block to write_file for %s", path)
            calls = [ToolCall(name="write_file", arguments={"path": path, "content": implicit_code})]
            return calls

    return calls


async def handle_no_tool_call(messages: List[Dict], content: str, orch: Any):
    """Handle case where model produced no valid tool call."""
    if orch.parser.saw_truncated_call(content):
        messages.append({
            "role": "user",
            "content": (
                "Your previous tool call was cut off before it finished "
                "(incomplete JSON), so it was NOT applied. It was too long. "
                "Send a SMALLER edit: change fewer lines at once, or use "
                "search_replace on a short, unique snippet instead of "
                "rewriting a large block in one call."
            ),
        })
    else:
        messages.append({
            "role": "user",
            "content": "Respond with exactly one tool call in the required JSON format.",
        })


async def parse_legacy_tool_calls(
    orch: Any,
    response: Any,
    execution_context: Any,
) -> Optional[List[ToolCall]]:
    """Parse tool calls for legacy mode."""
    native = orch.parser.parse_native(response.tool_calls)
    calls = native or orch.parser.parse(response.content)

    if not calls:
        target_file = orch._find_target_file()
        if target_file:
            is_py = target_file.endswith(".py")
            implicit_code = orch._extract_implicit_code(response.content or "", is_py)
            if implicit_code:
                orch.log.info("Converted implicit code block to write_file tool call for %s", target_file)
                calls = [ToolCall(name="write_file", arguments={"path": target_file, "content": implicit_code})]

    if not calls:
        console.print(f"[dim]step {execution_context.step}: model produced no tool call[/dim]")
        orch.frame.messages.append({"role": "assistant", "content": response.content})
        if orch.parser.saw_truncated_call(response.content or ""):
            orch.frame.messages.append({
                "role": "user",
                "content": (
                    "Your previous tool call was cut off before it finished "
                    "(incomplete JSON), so it was NOT applied. It was too long. "
                    "Send a SMALLER edit: change fewer lines at once, or use "
                    "search_replace on a short, unique snippet instead of "
                    "rewriting a large block."
                ),
            })
        else:
            orch.frame.messages.append({
                "role": "user",
                "content": "Respond with exactly one tool call in the required JSON format.",
            })

    return calls


def get_filtered_tools(orch: Any, exclude_names: Optional[Set[str]] = None) -> List[Dict]:
    """Get filtered tool descriptions."""
    tools = orch.tools.get_descriptions()
    exclude = exclude_names or set()

    if orch._is_single_file_workspace():
        exclude.update({"rename_symbol", "add_parameter", "add_docstring"})

    if exclude:
        return [t for t in tools if t.get("function", {}).get("name") not in exclude]

    return tools


def get_excluded_tools(orch: Any, is_new: bool) -> Set[str]:
    """Get tools that should be excluded for the current context."""
    exclude = set()
    if is_new:
        exclude.update({"search_replace", "replace_all"})
    if orch._is_single_file_workspace():
        exclude.update({"rename_symbol", "add_parameter", "add_docstring"})
    return exclude


async def get_repo_map(orch: Any) -> str:
    """Get repository skeleton with error handling."""
    try:
        return orch.indexer.get_repo_skeleton()
    except Exception as e:
        orch.log.warning("Failed to get repo skeleton: %s", e)
        return ""
