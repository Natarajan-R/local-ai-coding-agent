"""Workspace perception: build a map of the repository for the model.

Small repos get a full skeleton (file tree + code signatures) up front. Large
repos get a compact directory overview instead, and the agent explores on demand
with the ``list_files`` / ``search_text`` / ``outline`` / ``read_file`` tools —
this keeps the planning prompt within the context window regardless of repo size.
"""
from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import List, Tuple

from .languages import LanguageRouter

logger = logging.getLogger(__name__)

IGNORE_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", "dist", "build", ".idea",
    ".ai-agent",
}
TEXT_EXTS = {
    ".py", ".pyi", ".java", ".sh", ".bash", ".txt", ".md", ".toml",
    ".cfg", ".ini", ".json", ".yaml", ".yml",
}

# Above this many files, switch from a full skeleton to a compact overview.
FULL_SKELETON_MAX_FILES = 40
# Guards for content search on large repos.
SEARCH_MAX_FILE_BYTES = 1_000_000
SEARCH_MAX_FILES_SCANNED = 5000


class WorkspaceIndexer:
    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.router = LanguageRouter()

    def list_files(self, directory: str | None = None) -> List[Path]:
        root = self.workspace
        if directory:
            root = (self.workspace / directory).resolve()
        files: List[Path] = []
        if not root.exists():
            return files
        for p in sorted(root.rglob("*")):
            if any(part in IGNORE_DIRS for part in p.parts):
                continue
            if p.is_file():
                files.append(p)
        return files

    # -- repo map ------------------------------------------------------------
    def get_repo_skeleton(self, max_skeleton_files: int = 15) -> str:
        """Full skeleton for small repos; a compact overview for large ones."""
        files = self.list_files()
        if not files:
            return "(empty workspace)"
        if len(files) <= FULL_SKELETON_MAX_FILES:
            return self._full_skeleton(files, max_skeleton_files)
        return self._overview(files)

    def _full_skeleton(self, files: List[Path], max_skeleton_files: int) -> str:
        lines: List[str] = ["# Repository structure"]
        for f in files:
            rel = f.relative_to(self.workspace)
            try:
                size = f.stat().st_size
            except OSError:
                size = 0
            lines.append(f"- {rel} ({size} bytes)")

        supported = self.router.supported_extensions()
        code_files = [f for f in files if f.suffix.lower() in supported]
        shown = 0
        for f in code_files:
            if shown >= max_skeleton_files:
                break
            rel = f.relative_to(self.workspace)
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            skeleton = self.router.skeleton(f.name, content).strip()
            if skeleton:
                lines.append(f"\n## {rel}\n{skeleton}")
                shown += 1
        return "\n".join(lines)

    def _overview(self, files: List[Path]) -> str:
        rel_paths = [f.relative_to(self.workspace) for f in files]
        top_dir_counts: Counter = Counter()
        root_files: List[str] = []
        for r in rel_paths:
            if len(r.parts) == 1:
                root_files.append(str(r))
            else:
                top_dir_counts[r.parts[0]] += 1

        lines = [
            f"# Repository overview — {len(files)} files "
            f"({len(top_dir_counts)} top-level directories).",
            "# Large repo: the full skeleton is omitted. Explore with tools:",
            "#   list_files(directory) · search_text(query) · outline(path) · "
            "read_file(path, start_line, end_line)",
            "",
        ]
        for d, count in sorted(top_dir_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"{d}/  ({count} files)")
            sub_counts: Counter = Counter()
            for r in rel_paths:
                if r.parts[0] == d and len(r.parts) > 2:
                    sub_counts[r.parts[1]] += 1
            for sd, sc in sorted(sub_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]:
                lines.append(f"  {d}/{sd}/  ({sc} files)")
        if root_files:
            lines.append("")
            lines.append("root files: " + ", ".join(sorted(root_files)[:40]))
        return "\n".join(lines)

    # -- on-demand exploration ----------------------------------------------
    def outline(self, path: Path, content: str | None = None) -> str:
        """Language-aware signature skeleton of a single file."""
        target = Path(path)
        if content is None:
            try:
                content = target.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return f"(could not read file: {exc})"
        return self.router.skeleton(target.name, content).strip()

    def search_text(
        self, query: str, max_results: int = 50, ignore_case: bool = True
    ) -> List[Tuple[Path, int, str]]:
        """Grep-like content search. Returns (relative_path, line_no, line)."""
        if not query:
            return []
        needle = query.lower() if ignore_case else query
        results: List[Tuple[Path, int, str]] = []
        scanned = 0
        for f in self.list_files():
            if scanned >= SEARCH_MAX_FILES_SCANNED:
                break
            try:
                if f.stat().st_size > SEARCH_MAX_FILE_BYTES:
                    continue
                text = f.read_text(encoding="utf-8")  # strict: skip binaries
            except (OSError, UnicodeDecodeError):
                continue
            scanned += 1
            rel = f.relative_to(self.workspace)
            for i, line in enumerate(text.splitlines(), 1):
                hay = line.lower() if ignore_case else line
                if needle in hay:
                    results.append((rel, i, line.strip()[:200]))
                    if len(results) >= max_results:
                        return results
        return results
