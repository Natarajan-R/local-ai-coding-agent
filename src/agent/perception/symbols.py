"""Structured symbol graph: a SQLite index of definitions and imports.

Complements textual `search_text` and the (Python-only) LSP with precise,
cross-language "where is X defined" and "who imports Y" queries — the structured-
RAG approach that scales to very large codebases without spending context.

The index is built lazily and held in an in-memory SQLite database, extracted via
the language profiles (Python AST + tree-sitter). Imports are captured for Python.
"""
from __future__ import annotations

import ast
import logging
import sqlite3
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)

MAX_INDEX_FILES = 5000


@dataclass
class SymbolHit:
    name: str
    kind: str
    path: str
    line: int


def python_imports(content: str) -> List[Tuple[str, int]]:
    """Return (dotted_module, line) references for a Python file."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    out: List[Tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                out.append((module, node.lineno))
            for alias in node.names:
                full = f"{module}.{alias.name}" if module else alias.name
                out.append((full, node.lineno))
    return out


class SymbolIndex:
    """Lazily-built SQLite index of symbols and imports for a workspace."""

    def __init__(self, indexer) -> None:
        self.indexer = indexer
        self._conn: sqlite3.Connection | None = None

    # -- build ---------------------------------------------------------------
    def _build(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE symbols (name TEXT, kind TEXT, path TEXT, line INTEGER)")
        conn.execute("CREATE TABLE imports (module TEXT, path TEXT, line INTEGER)")
        conn.execute("CREATE INDEX idx_sym_name ON symbols(name)")
        conn.execute("CREATE INDEX idx_imp_module ON imports(module)")

        router = self.indexer.router
        count = 0
        for f in self.indexer.list_files():
            if count >= MAX_INDEX_FILES:
                break
            profile = router.for_extension(f.suffix.lower())
            if profile is None:
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            count += 1
            rel = str(f.relative_to(self.indexer.workspace))
            for name, kind, line in profile.extract_symbols(content):
                if name:
                    conn.execute(
                        "INSERT INTO symbols VALUES (?, ?, ?, ?)", (name, kind, rel, line)
                    )
            if f.suffix.lower() in (".py", ".pyi"):
                for module, line in python_imports(content):
                    conn.execute("INSERT INTO imports VALUES (?, ?, ?)", (module, rel, line))
        conn.commit()
        logger.info("Symbol index built over %d files", count)
        return conn

    def _ensure(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = self._build()
        return self._conn

    def refresh(self) -> None:
        """Force a rebuild on the next query (call after big edits)."""
        if self._conn is not None:
            self._conn.close()
        self._conn = None

    # -- queries -------------------------------------------------------------
    def find_definition(self, name: str, limit: int = 50) -> List[SymbolHit]:
        conn = self._ensure()
        rows = conn.execute(
            "SELECT name, kind, path, line FROM symbols WHERE name = ? "
            "ORDER BY path, line LIMIT ?",
            (name, limit),
        ).fetchall()
        return [SymbolHit(*r) for r in rows]

    def search(self, pattern: str, limit: int = 50) -> List[SymbolHit]:
        conn = self._ensure()
        rows = conn.execute(
            "SELECT name, kind, path, line FROM symbols WHERE name LIKE ? "
            "ORDER BY name, path LIMIT ?",
            (f"%{pattern}%", limit),
        ).fetchall()
        return [SymbolHit(*r) for r in rows]

    def importers(self, name: str, limit: int = 50) -> List[Tuple[str, int, str]]:
        conn = self._ensure()
        rows = conn.execute(
            "SELECT DISTINCT path, line, module FROM imports "
            "WHERE module = ? OR module LIKE ? OR module LIKE ? "
            "ORDER BY path, line LIMIT ?",
            (name, f"{name}.%", f"%.{name}", limit),
        ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]

    def stats(self) -> dict:
        conn = self._ensure()
        n_sym = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        n_imp = conn.execute("SELECT COUNT(*) FROM imports").fetchone()[0]
        return {"symbols": n_sym, "imports": n_imp}
