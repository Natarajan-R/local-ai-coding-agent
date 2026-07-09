"""Path guardrails: keep all file access confined to the workspace."""
from __future__ import annotations

from pathlib import Path


def _resolve(workspace: Path, target: str) -> Path:
    """Resolve ``target`` against ``workspace`` without following it outside."""
    ws = Path(workspace).resolve()
    candidate = Path(target)
    if not candidate.is_absolute():
        candidate = ws / candidate
    return candidate.resolve()


def is_safe_path(workspace: Path, target: str) -> bool:
    """Return True if ``target`` resolves to a location inside ``workspace``.

    Rejects path traversal (``..``), absolute escapes and symlinks that would
    lead outside the sandbox workspace.
    """
    try:
        ws = Path(workspace).resolve()
        candidate = _resolve(ws, target)
    except (OSError, ValueError, RuntimeError):
        return False
    return candidate == ws or ws in candidate.parents


def safe_join(workspace: Path, target: str) -> Path:
    """Resolve ``target`` inside ``workspace`` or raise ``ValueError``."""
    if not is_safe_path(workspace, target):
        raise ValueError(f"Path '{target}' escapes the workspace boundary")
    return _resolve(Path(workspace).resolve(), target)
