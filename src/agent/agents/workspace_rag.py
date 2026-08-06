"""Workspace-file RAG: dynamically retrieve related workspace files for context.

When writing file X, this module finds the most relevant other workspace files
by analysing import relationships, name similarity, and test–source pairing.
The top matches are injected into the subtask prompt so the model sees the
actual interfaces it must conform to — not just static reference examples.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def workspace_relevant_files(
    target_path: str,
    change_description: str,
    workspace: Path,
    limit: int = 3,
    max_total_chars: int = 6000,
) -> str:
    """Retrieve workspace files related to *target_path*.

    Scoring (each file can score 0–6):
      +3  Import relationship — target imports from this file, OR this file
          imports from target's module.
      +2  Test–source pairing — one is ``test_<other>`` or ``<other>_test``.
      +1  Same directory — files in the same directory as the target.

    Returns a formatted block suitable for prompt injection, or an empty string.
    """
    target = Path(target_path)
    if target.suffix != ".py":
        return ""

    target_stem = target.stem  # e.g. "exporter"
    target_module = ".".join(target.with_suffix("").parts)  # e.g. "src.exporter"

    # Collect candidate workspace .py files (exclude target, __pycache__)
    candidates: List[Path] = []
    for py in workspace.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        if py.resolve() == (workspace / target_path).resolve():
            continue
        candidates.append(py)

    if not candidates:
        return ""

    # Pre-parse: build import-from map for all candidates AND target
    import_map: Dict[Path, Set[str]] = {}
    target_abs = (workspace / target_path).resolve()
    all_files = candidates + ([target_abs] if target_abs.exists() else [])
    for f in all_files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        imported: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and not node.level:
                    imported.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
        import_map[f] = imported

    # Score candidates
    scored: List[Tuple[int, Path]] = []
    for c in candidates:
        score = 0
        c_stem = c.stem

        # --- Import relationship (+3) ---
        c_module = ".".join(c.relative_to(workspace).with_suffix("").parts)
        c_imports = import_map.get(c, set())

        # Does target import from this candidate?
        target_imports = import_map.get(workspace / target_path, set())
        if c_module in target_imports or any(
            i.startswith(c_module + ".") for i in target_imports
        ):
            score += 3

        # Does this candidate import from target?
        target_mod = target_module
        if target_mod in c_imports or any(
            i.startswith(target_mod + ".") for i in c_imports
        ):
            score += 3

        # --- Test–source pairing (+2) ---
        target_no_test = re.sub(r"^test_|_test$", "", target_stem)
        c_no_test = re.sub(r"^test_|_test$", "", c_stem)
        if target_no_test != target_stem or c_no_test != c_stem:
            if target_no_test == c_no_test:
                score += 2

        # --- Same directory (+1) ---
        if c.parent.resolve() == target.parent.resolve():
            score += 1

        if score > 0:
            scored.append((score, c))

    if not scored:
        return ""

    scored.sort(key=lambda x: -x[0])

    # Build output, capped at max_total_chars
    chunks: List[str] = []
    total = 0
    for score, cf in scored[:limit]:
        try:
            body = cf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(cf.relative_to(workspace))
        # Include filename and first max_total_chars/limit chars per file
        chunk = f"# --- related: {rel} ---\n```python\n{body[:max_total_chars // limit]}\n```"
        if total + len(chunk) > max_total_chars:
            remaining = max_total_chars - total
            if remaining > 200:
                chunk = chunk[:remaining] + "\n```"
            else:
                break
        chunks.append(chunk)
        total += len(chunk)

    if not chunks:
        return ""

    return "\n\n".join(chunks)
