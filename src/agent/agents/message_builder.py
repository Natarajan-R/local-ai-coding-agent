"""Prompt construction for subtasks: required-exports scanning, reference-RAG,
and initial message assembly."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from .. import prompts


def compact_subtask_history(messages: List[Dict], ctx: Any) -> List[Dict]:
    """Keep the subtask prompt under the context budget so the turn never trims."""
    budget = max(2000, ctx.budget - 2500)
    if len(messages) <= 4 or ctx.total_tokens(messages) <= budget:
        return messages
    anchors = messages[:2]
    tail = list(messages[2:])
    while len(tail) > 3 and ctx.total_tokens(anchors + tail) > budget:
        tail.pop(0)
    dropped = (len(messages) - 2) - len(tail)
    if dropped <= 0:
        return messages
    marker = {
        "role": "user",
        "content": f"[... {dropped} earlier step(s) condensed to stay within "
                   f"{ctx.max_tokens // 1024}k context ...]",
    }
    return anchors + [marker] + tail


def required_exports(path: str, workspace: Path) -> List[str]:
    """Names the test suite imports from this module — the interface it MUST expose."""
    p = Path(path)
    if p.suffix != ".py":
        return []
    parts = list(p.with_suffix("").parts)
    modforms = {".".join(parts[i:]) for i in range(len(parts))}
    wanted: Set[str] = set()
    for pattern in ("test_*.py", "*_test.py"):
        for tf in workspace.rglob(pattern):
            if "__pycache__" in tf.parts:
                continue
            try:
                tree = ast.parse(tf.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in modforms:
                    wanted.update(a.name for a in node.names if a.name != "*")
    return sorted(wanted)


def relevant_references(
    path: str,
    change_description: str,
    customizations: Any,
    limit: int = 2,
    max_chars: int = 4000,
) -> str:
    """Load user-provided reference implementations relevant to this file."""
    agents_dir = customizations._find_agents_dir()
    refs_dir = (agents_dir / "references") if agents_dir else None
    if not refs_dir or not refs_dir.is_dir():
        return ""
    keywords = {w for w in re.findall(r"[a-z_]{3,}", (path + " " + (change_description or "")).lower())}
    scored: List[Tuple[int, str, str]] = []
    for rf in sorted(refs_dir.rglob("*")):
        if not rf.is_file():
            continue
        try:
            body = rf.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        hay = (rf.name + " " + body[:2000]).lower()
        score = sum(1 for k in keywords if k in hay)
        if score > 0:
            scored.append((score, rf.name, body))
    if not scored:
        return ""
    scored.sort(key=lambda x: -x[0])
    return "\n\n".join(
        f"# --- reference: {name} ---\n```\n{body[:max_chars]}\n```"
        for _, name, body in scored[:limit]
    )


def _workspace_rag_block(path: str, change_description: str, orch: Any) -> str:
    """Workspace-file RAG: retrieve related workspace files for cross-module context."""
    try:
        from .workspace_rag import workspace_relevant_files
        return workspace_relevant_files(
            path, change_description, orch.workspace,
        )
    except Exception:
        return ""


def _project_tree_block(orch: Any) -> str:
    """Build a compact project-status block: file tree + milestone progress."""
    ws = orch.workspace
    lines: List[str] = []

    # File listing
    py_files = sorted(ws.rglob("*.py"))
    py_files = [p for p in py_files if "__pycache__" not in p.parts]
    if py_files:
        lines.append("Workspace files:")
        for pf in py_files:
            try:
                rel = str(pf.relative_to(ws))
                lines.append(f"  {rel}")
            except ValueError:
                continue

    # Milestone progress
    milestones = (orch.frame.metadata or {}).get("milestones", [])
    if milestones:
        total = len(milestones)
        done = sum(
            1 for m in milestones
            if m.get("files") and all(
                (ws / f.get("path", "")).exists()
                for f in m["files"] if f.get("path")
            )
        )
        pct = int(100 * done / total)
        lines.append(f"Progress: {done}/{total} milestones done ({pct}%)")

    return "\n".join(lines)


def build_subtask_messages(
    path: str,
    change_description: str,
    content: str,
    repo_map: str,
    reflexion_lesson: str,
    exclude_names: Set[str],
    orch: Any,
) -> List[Dict]:
    """Build the initial messages for a subtask."""
    refs = relevant_references(path, change_description, orch.customizations)
    ws_rag = _workspace_rag_block(path, change_description, orch)
    combined = refs
    if ws_rag:
        combined = (refs + "\n\n" + ws_rag) if refs else ws_rag
    project_status = _project_tree_block(orch)
    return [
        {
            "role": "system",
            "content": prompts.subtask_system_prompt(
                path, change_description, exclude_names=exclude_names,
            ),
        },
        {
            "role": "user",
            "content": prompts.subtask_user_prompt(
                task=orch.frame.task_description,
                path=path,
                change_description=change_description,
                content=content,
                repo_map=repo_map,
                reflexion_lesson=reflexion_lesson,
                test_content=orch._relevant_test_content(path),
                required_exports=required_exports(path, orch.workspace),
                references=combined,
                project_status=project_status,
            ),
        },
    ]
