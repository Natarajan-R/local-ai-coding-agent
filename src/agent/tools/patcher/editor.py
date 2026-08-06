"""High-level editing commands, diffs, and Git checkpointing."""
import logging
import subprocess
from pathlib import Path
from typing import Tuple

from ...errors import AmbiguousMatchError, ToolError
from .core import _clean_str, align_indentation, make_diff, _strip_regex_escapes, _normalize
from .search import _closest_block, _not_found_error, _fuzzy_replace
from .ast_splicer import apply_ast_splice

logger = logging.getLogger(__name__)


def apply_search_replace(content: str, search: str, replace: str, fuzzy: bool = True) -> str:
    """Replace the single occurrence of ``search`` in ``content`` with ``replace``."""
    if search == "":
        raise ToolError("search block must not be empty")

    count = content.count(search)
    if count == 1:
        return content.replace(search, replace, 1)
    if count > 1:
        raise ToolError(
            f"search block is ambiguous (found {count} times). To change every "
            f"occurrence use the `replace_all` tool; to change one, add surrounding "
            f"context to make the search block unique."
        )

    if fuzzy:
        fuzzy_result = _fuzzy_replace(content, search, replace)
        if fuzzy_result is not None:
            return fuzzy_result

    unescaped_search = _strip_regex_escapes(search)
    if unescaped_search != search:
        unescaped_replace = _strip_regex_escapes(replace)
        if content.count(unescaped_search) == 1:
            return content.replace(unescaped_search, unescaped_replace, 1)
        if fuzzy:
            fuzzy_result = _fuzzy_replace(content, unescaped_search, unescaped_replace)
            if fuzzy_result is not None:
                return fuzzy_result

    try:
        ast_result = apply_ast_splice(content, replace)
        if ast_result is not None:
            logger.info("AST semantic splicing fallback succeeded.")
            return ast_result
    except Exception as e:
        logger.debug("AST splicing fallback failed: %s", e)

    raise _not_found_error(content, search)


def apply_line_edit(content: str, start_line: int, end_line: int, search: str, replace: str, window: int = 50) -> str:
    """Replace target lines with `replace` matching `search` with drift-tolerance."""
    if search == "":
        raise ToolError("search block must not be empty")

    file_lines = content.splitlines(keepends=True)
    num_lines = len(file_lines)
    search_lines = search.splitlines()
    n = len(search_lines)
    if n == 0:
        raise ToolError("search block must not be empty")

    norm_search = [_normalize(ln) for ln in search_lines]
    norm_file = [_normalize(ln) for ln in file_lines]

    matches = [
        i for i in range(len(file_lines) - n + 1)
        if norm_file[i:i + n] == norm_search
    ]

    direct_match = False
    if 1 <= start_line <= num_lines and 1 <= end_line <= num_lines and start_line <= end_line:
        direct_slice = file_lines[start_line - 1 : end_line]
        if [_normalize(ln) for ln in direct_slice] == norm_search:
            direct_match = True
            match_idx = start_line - 1
            matched_len = len(direct_slice)

    if not direct_match:
        if len(matches) == 1:
            match_idx = matches[0]
            matched_len = n
        elif len(matches) > 1:
            window_matches = [
                idx for idx in matches
                if abs(idx - (start_line - 1)) <= window
            ]
            if len(window_matches) == 1:
                match_idx = window_matches[0]
                matched_len = n
            elif len(window_matches) == 0:
                raise ToolError(
                    f"expected search block was found at other locations, but not near line {start_line}. "
                    f"To avoid editing the wrong code, please re-read the file or adjust start_line/end_line."
                )
            else:
                raise ToolError(
                    f"expected search block is ambiguous near line {start_line} (found {len(window_matches)} matches in window). "
                    f"Please provide more surrounding context in the search block to make it unique."
                )
        else:
            clean_content, content_map = _clean_str(content)
            clean_search, _ = _clean_str(search)
            if clean_search:
                matches_clean = []
                idx = clean_content.find(clean_search)
                while idx != -1:
                    matches_clean.append(idx)
                    idx = clean_content.find(clean_search, idx + 1)
                
                if len(matches_clean) == 1:
                    start_idx_clean = matches_clean[0]
                    end_idx_clean = start_idx_clean + len(clean_search) - 1
                    start_char_idx = content_map[start_idx_clean]
                    end_char_idx = content_map[end_idx_clean]
                    
                    file_lines_fuzzy = content.splitlines(keepends=True)
                    fuzzy_line_idx = content[:start_char_idx].count('\n')
                    if 0 <= fuzzy_line_idx < len(file_lines_fuzzy):
                        repl = align_indentation(file_lines_fuzzy[fuzzy_line_idx], replace)
                        leading_ws = ""
                        for c in file_lines_fuzzy[fuzzy_line_idx]:
                            if c in (' ', '\t'):
                                leading_ws += c
                            else:
                                break
                        if repl.startswith(leading_ws):
                            repl = repl[len(leading_ws):]
                    else:
                        repl = replace

                    if content[end_char_idx + 1:].startswith("\n") and not repl.endswith("\n"):
                        repl += "\n"

                    line_start = content.rfind("\n", 0, start_char_idx) + 1
                    prefix = content[line_start:start_char_idx]
                    return content[:line_start] + prefix + repl + content[end_char_idx + 1:]
                elif len(matches_clean) > 1:
                    raise AmbiguousMatchError(
                        f"Multiple identical blocks found ({len(matches_clean)} matches) via fuzzy fallback. "
                        "Please provide 3-5 additional lines of surrounding context above and below the target block to disambiguate."
                    )
            
            raise _not_found_error(content, search)

    baseline_line = file_lines[match_idx]
    repl = align_indentation(baseline_line, replace)
    matched_text = "".join(file_lines[match_idx : match_idx + matched_len])
    if matched_text.endswith("\n") and not repl.endswith("\n"):
        repl += "\n"

    new_lines = file_lines[:match_idx] + [repl] + file_lines[match_idx + matched_len:]
    return "".join(new_lines)


def apply_and_diff(content: str, search: str, replace: str, path: str = "file") -> Tuple[str, str]:
    """Apply a search/replace edit and also return the unified diff."""
    updated = apply_search_replace(content, search, replace)
    return updated, make_diff(content, updated, path)


def commit_and_write(workspace: Path, target_path: Path, new_content: str, encoding: str = "utf-8") -> None:
    """Commit the current state of the file to Git (if a repo exists), then write the new content.
    Includes proper subprocess validation and clean-tree handling.
    """
    git_dir = workspace / ".git"
    if git_dir.exists() and target_path.exists():
        try:
            rel_path = target_path.relative_to(workspace)
            
            # Use '--' to prevent filename ambiguity vulnerabilities
            add_res = subprocess.run(
                ["git", "add", "--", str(rel_path)], 
                cwd=str(workspace), 
                capture_output=True, 
                text=True
            )
            if add_res.returncode != 0:
                logger.warning("Git add failed for %s: %s", rel_path, add_res.stderr.strip())
            else:
                # Check if there is actually anything staged to commit
                status_res = subprocess.run(
                    ["git", "diff", "--cached", "--quiet", "--", str(rel_path)],
                    cwd=str(workspace)
                )
                
                # Exit code 1 from diff --quiet means there ARE changes to commit
                if status_res.returncode == 1:
                    commit_res = subprocess.run(
                        ["git", "commit", "--no-verify", "-m", f"Pre-edit checkpoint for {rel_path}", "--", str(rel_path)],
                        cwd=str(workspace),
                        capture_output=True,
                        text=True
                    )
                    if commit_res.returncode == 0:
                        logger.info("Created Git checkpoint for %s before editing.", rel_path)
                    else:
                        logger.warning("Git commit failed for %s: %s", rel_path, commit_res.stderr.strip())
                else:
                    logger.debug("No pre-edit changes detected in %s; skipping checkpoint commit.", rel_path)
                
        except Exception as e:
            logger.warning("Unexpected error during Git checkpointing for %s: %s", target_path, e)
    
    # Finally, write the new content to disk
    target_path.write_text(new_content, encoding=encoding)
