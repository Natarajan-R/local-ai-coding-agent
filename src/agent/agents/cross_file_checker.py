"""Multi-pass cross-file consistency checker.

Runs structural analysis across all workspace .py files after generation:
1. Import consistency  — every ``from X import Y`` has a matching ``def Y`` / ``class Y`` in X
2. Route consistency  — every test route has a matching endpoint in router files (FastAPI)
3. Schema consistency — every field accessed on a model in tests exists in the Pydantic schema
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class CrossFileChecker:
    """Structural consistency checks across generated files."""

    KNOWN_STDLIB = {
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
        "pytest", "numpy", "pandas", "requests", "httpx", "aiohttp",
        "fastapi", "flask", "django", "sqlalchemy", "pydantic", "click",
        "typer", "rich", "yaml", "toml", "redis", "celery",
        "bs4", "lxml", "jinja2", "bcrypt", "jose", "jwt",
    }

    HTTP_VERBS = {"get", "post", "put", "patch", "delete", "options", "head"}

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._file_cache: Dict[Path, Optional[ast.AST]] = {}

    def _parse(self, path: Path) -> Optional[ast.AST]:
        if path not in self._file_cache:
            try:
                self._file_cache[path] = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except (SyntaxError, OSError):
                self._file_cache[path] = None
        return self._file_cache[path]

    def _py_files(self) -> List[Path]:
        return sorted(self.workspace.rglob("*.py"))

    def check_all(self) -> List[str]:
        issues: List[str] = []
        issues.extend(self._check_import_consistency())
        issues.extend(self._check_route_consistency())
        issues.extend(self._check_schema_consistency())
        return issues

    # ----- 1. Import consistency -----

    def _build_export_map(self) -> Dict[str, Set[str]]:
        exports: Dict[str, Set[str]] = {}
        for py_file in self._py_files():
            tree = self._parse(py_file)
            if tree is None:
                continue
            try:
                rel = str(py_file.relative_to(self.workspace).with_suffix(""))
            except ValueError:
                continue
            module = rel.replace("/", ".")
            names: Set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(node.name)
            exports[module] = names
        return exports

    def _check_import_consistency(self) -> List[str]:
        issues: List[str] = []
        exports = self._build_export_map()

        for py_file in self._py_files():
            tree = self._parse(py_file)
            if tree is None:
                continue
            try:
                rel = str(py_file.relative_to(self.workspace))
            except ValueError:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                if isinstance(node, ast.ImportFrom):
                    if node.level and node.level > 0:
                        continue
                    module = node.module
                    if not module:
                        continue
                    top = module.split(".")[0]
                    if top in self.KNOWN_STDLIB:
                        continue
                    for alias in node.names:
                        name = alias.name if alias.asname is None else alias.asname
                        if module in exports and name not in exports[module]:
                            issues.append(
                                f"{rel}:{node.lineno}: '{name}' imported from '{module}' "
                                f"but '{module}' has no definition of '{name}'"
                            )
        return issues

    # ----- 2. Route consistency -----

    def _find_router_routes(self) -> Dict[str, Set[str]]:
        routes: Dict[str, Set[str]] = {}
        for py_file in self._py_files():
            tree = self._parse(py_file)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for deco in node.decorator_list:
                    if not isinstance(deco, ast.Call):
                        continue
                    func = deco.func
                    method = None
                    if isinstance(func, ast.Attribute):
                        method = func.attr
                    elif isinstance(func, ast.Name):
                        method = func.id
                    if method in self.HTTP_VERBS:
                        args = [a for a in deco.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                        if args:
                            try:
                                rel = str(py_file.relative_to(self.workspace))
                            except ValueError:
                                rel = py_file.name
                            routes.setdefault(rel, set()).add(args[0].value)
        return routes

    def _find_test_routes(self) -> List[Tuple[str, str, str]]:
        test_routes: List[Tuple[str, str, str]] = []
        for py_file in self._py_files():
            if "test" not in py_file.stem and "test" not in str(py_file.parent):
                continue
            tree = self._parse(py_file)
            if tree is None:
                continue
            try:
                rel = str(py_file.relative_to(self.workspace))
            except ValueError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr in self.HTTP_VERBS:
                    args = [a for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                    if args:
                        test_routes.append((rel, func.attr.upper(), args[0].value))
        return test_routes

    def _check_route_consistency(self) -> List[str]:
        issues: List[str] = []
        router_routes = self._find_router_routes()
        test_routes = self._find_test_routes()

        if test_routes:
            all_router_paths: Set[str] = set()
            for paths in router_routes.values():
                all_router_paths.update(paths)
            for test_file, verb, path in test_routes:
                if path not in all_router_paths:
                    issues.append(
                        f"{test_file}: route '{verb} {path}' has no matching endpoint in any router"
                    )

        # Check path-param ↔ function-param consistency in router files
        for py_file in self._py_files():
            tree = self._parse(py_file)
            if tree is None:
                continue
            try:
                rel = str(py_file.relative_to(self.workspace))
            except ValueError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for deco in node.decorator_list:
                    if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute):
                        continue
                    if deco.func.attr not in self.HTTP_VERBS:
                        continue
                    # Extract path template from decorator args
                    path_arg = None
                    for arg in deco.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            path_arg = arg.value
                            break
                    if not path_arg:
                        continue
                    # Extract {param} placeholders
                    path_params = set(re.findall(r"\{(\w+)\}", path_arg))
                    if not path_params:
                        continue
                    # Extract function parameter names
                    func_params = {a.arg for a in node.args.args}
                    missing = path_params - func_params
                    if missing:
                        issues.append(
                            f"{rel}: route '{deco.func.attr.upper()} {path_arg}' "
                            f"has path params {', '.join(sorted(missing))} "
                            f"with no matching function parameter in `{node.name}`"
                        )

        return issues

    # ----- 3. Schema consistency -----

    def _find_models(self) -> Dict[str, Set[str]]:
        models: Dict[str, Set[str]] = {}
        for py_file in self._py_files():
            tree = self._parse(py_file)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                # Check if it's a Pydantic model (inherits from BaseModel or similar)
                is_model = False
                for base in node.bases:
                    if isinstance(base, ast.Name) and "Model" in base.id:
                        is_model = True
                        break
                    if isinstance(base, ast.Attribute) and "Model" in base.attr:
                        is_model = True
                        break
                if not is_model:
                    continue
                try:
                    rel = str(py_file.relative_to(self.workspace))
                except ValueError:
                    rel = py_file.name
                fields: Set[str] = set()
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        fields.add(item.target.id)
                models[rel] = fields
        return models

    def _find_test_field_accesses(self) -> List[Tuple[str, str, str]]:
        accesses: List[Tuple[str, str, str]] = []
        for py_file in self._py_files():
            if "test" not in py_file.stem and "test" not in str(py_file.parent):
                continue
            tree = self._parse(py_file)
            if tree is None:
                continue
            try:
                rel = str(py_file.relative_to(self.workspace))
            except ValueError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                if isinstance(node.ctx, ast.Store):
                    continue
                if isinstance(node.value, ast.Name):
                    accesses.append((rel, node.value.id, node.attr))
        return accesses

    def _check_schema_consistency(self) -> List[str]:
        issues: List[str] = []
        models = self._find_models()
        if not models:
            return issues

        test_accesses = self._find_test_field_accesses()
        if not test_accesses:
            return issues

        for test_file, var_name, field in test_accesses:
            for model_file, model_fields in models.items():
                if field not in model_fields:
                    issues.append(
                        f"{test_file}: field '{field}' accessed on '{var_name}' "
                        f"but not found in model '{model_file}' (fields: {sorted(model_fields)})"
                    )

        return issues


def run_cross_file_check(workspace: Path) -> List[str]:
    """Run all consistency checks and return list of issues."""
    checker = CrossFileChecker(workspace)
    return checker.check_all()


def format_issues_as_lesson(issues: List[str]) -> str:
    if not issues:
        return ""
    lines = [
        "POST-GENERATION STRUCTURAL ISSUES (multi-pass + semantic diff):",
        "Fix each issue so the code is structurally correct:",
    ]
    for i, issue in enumerate(issues, 1):
        lines.append(f"  {i}. {issue}")
    lines.append(
        "Run the relevant tests after fixing to verify correctness."
    )
    return "\n".join(lines)
