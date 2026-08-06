"""Deterministic search/replace patching for file edits."""

from .core import _strip_regex_escapes, _normalize, make_diff
from .search import _closest_block, _not_found_error, _fuzzy_replace
from .ast_splicer import apply_ast_splice, collect_definitions
from .editor import apply_search_replace, apply_line_edit, apply_and_diff, commit_and_write

__all__ = [
    "_strip_regex_escapes",
    "_normalize",
    "make_diff",
    "_closest_block",
    "_not_found_error",
    "_fuzzy_replace",
    "apply_ast_splice",
    "collect_definitions",
    "apply_search_replace",
    "apply_line_edit",
    "apply_and_diff",
    "commit_and_write"
]
