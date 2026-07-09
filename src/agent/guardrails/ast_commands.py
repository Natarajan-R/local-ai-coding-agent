"""AST-based command analysis using bashlex.

Regex deny-lists are trivially bypassed (``s"u"do``, ``$(...)`` substitution,
base64-pipe). Parsing the command into a shell AST lets us inspect the *actual*
executable of every command — including inside pipelines, subshells, and command
substitutions — and normalizes quoting (bashlex resolves ``s"u"do`` to ``sudo``).

bashlex is optional: :func:`ast_check` returns None when it isn't installed or
the command can't be parsed, and the caller falls back to the regex guard.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

DENY_EXECUTABLES = {
    "sudo", "su", "doas", "shutdown", "reboot", "halt", "poweroff", "init",
    "mkfs", "shred", "wipe", "chpasswd", "passwd", "visudo", "userdel", "useradd",
    "dd",
}
FETCH_EXECUTABLES = {"curl", "wget", "nc", "ncat"}
DECODE_EXECUTABLES = {"base64", "xxd", "uudecode", "openssl"}
SHELL_EXECUTABLES = {"sh", "bash", "zsh", "dash", "ksh", "fish"}

_RM_RECURSIVE = {"-r", "-R", "--recursive"}
_RM_FORCE = {"-f", "--force"}
_DANGEROUS_TARGETS = {"/", "~", "*", "/*", ".", "./", "./*", "~/*"}
# Commands where an unresolved variable argument is too risky to auto-run.
DESTRUCTIVE_EXECUTABLES = {"rm", "chmod", "dd", "shred", "wipe", "chown"}
_VAR_ONLY = re.compile(r"^\$\{?(\w+)\}?$")


def _available() -> bool:
    try:
        import bashlex  # noqa: F401
        return True
    except Exception:
        return False


def _walk(node):
    """Yield every node in a bashlex AST."""
    yield node
    for attr in ("parts", "list", "command", "output"):
        val = getattr(node, attr, None)
        if isinstance(val, list):
            for child in val:
                if hasattr(child, "kind"):
                    yield from _walk(child)
        elif val is not None and hasattr(val, "kind"):
            yield from _walk(val)


def _command_words(command_node) -> List[str]:
    return [p.word for p in getattr(command_node, "parts", []) if getattr(p, "kind", None) == "word"]


def _basename(word: str) -> str:
    return os.path.basename(word)


def _collect_assignments(trees) -> Dict[str, str]:
    """Map simple `VAR=value` assignments so `$VAR` can be resolved."""
    var_map: Dict[str, str] = {}
    for tree in trees:
        for node in _walk(tree):
            if getattr(node, "kind", None) == "assignment":
                word = getattr(node, "word", "")
                if "=" in word:
                    key, value = word.split("=", 1)
                    var_map[key] = value
    return var_map


def _resolve_words(command_node, var_map: Dict[str, str]) -> Tuple[List[str], List[bool]]:
    """Return (resolved words, per-word "has unresolved variable expansion")."""
    words: List[str] = []
    unresolved: List[bool] = []
    for part in getattr(command_node, "parts", []):
        if getattr(part, "kind", None) != "word":
            continue
        raw = getattr(part, "word", "")
        has_param = any(getattr(p, "kind", None) == "parameter"
                        for p in getattr(part, "parts", []))
        if not has_param:
            words.append(raw)
            unresolved.append(False)
            continue
        m = _VAR_ONLY.match(raw)
        if m and m.group(1) in var_map:
            words.append(var_map[m.group(1)])
            unresolved.append(False)
        else:
            words.append(raw)          # keep literal ($VAR) for display
            unresolved.append(True)    # but flag it as unresolved
    return words, unresolved


def _check_words(words: List[str], unresolved: Optional[List[bool]] = None) -> Optional[str]:
    if not words:
        return None
    unresolved = unresolved or [False] * len(words)
    exe = _basename(words[0])
    args = words[1:]
    args_unresolved = unresolved[1:]

    if exe in DENY_EXECUTABLES or exe.startswith("mkfs"):
        return f"blocked executable: {exe}"

    # An unresolved variable in a destructive command could expand to anything
    # (e.g. `rm -rf $ROOT` where ROOT=/). Refuse to auto-run it.
    if exe in DESTRUCTIVE_EXECUTABLES and any(args_unresolved):
        return f"blocked: unresolved variable expansion in a destructive `{exe}` command"

    if exe == "git" and "push" in args:
        if any(a in ("--force", "-f") for a in args) or any(args_unresolved):
            return "blocked: git push --force (or unresolved variable) rewrites history"

    if exe == "rm":
        flags = {a for a in args if a.startswith("-")}
        recursive = bool(flags & _RM_RECURSIVE) or any(
            "r" in f.lstrip("-") for f in flags if not f.startswith("--")
        )
        force = bool(flags & _RM_FORCE) or any(
            "f" in f.lstrip("-") for f in flags if not f.startswith("--")
        )
        targets = [a for a in args if not a.startswith("-")]
        if recursive and force and any(t in _DANGEROUS_TARGETS or t == "/" for t in targets):
            return "blocked: recursive force-remove of a dangerous path"

    if exe == "chmod":
        if "777" in args and any(t.startswith("/") for t in args):
            return "blocked: chmod 777 on an absolute path"

    return None


def _pipeline_exes(pipeline_node) -> List[str]:
    exes: List[str] = []
    for part in getattr(pipeline_node, "parts", []):
        if getattr(part, "kind", None) == "command":
            words = _command_words(part)
            if words:
                exes.append(_basename(words[0]))
    return exes


def ast_check(command: str) -> Optional[Tuple[bool, str]]:
    """Analyze ``command`` via bashlex.

    Returns ``(allowed, reason)`` — ``(False, reason)`` when something dangerous is
    found, ``(True, "ok")`` when the AST looks safe. Returns ``None`` when bashlex
    is unavailable or the command cannot be parsed (caller should fall back).
    """
    try:
        import bashlex
    except Exception:
        return None
    try:
        trees = bashlex.parse(command)
    except Exception:
        return None

    var_map = _collect_assignments(trees)
    for tree in trees:
        for node in _walk(tree):
            kind = getattr(node, "kind", None)
            if kind == "command":
                words, unresolved = _resolve_words(node, var_map)
                reason = _check_words(words, unresolved)
                if reason:
                    return (False, reason)
            elif kind == "pipeline":
                exes = set(_pipeline_exes(node))
                if exes & SHELL_EXECUTABLES and exes & (FETCH_EXECUTABLES | DECODE_EXECUTABLES):
                    return (False, "blocked: piping fetched/decoded data into a shell")
    return (True, "ok")
