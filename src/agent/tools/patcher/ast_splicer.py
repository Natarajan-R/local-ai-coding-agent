"""AST-aware semantic splicing for Python files."""
import ast
import re
from typing import List, NamedTuple, Optional, Tuple

from .core import clean_indentation, align_indentation


class DefNode(NamedTuple):
    """A def/class in the AST: its dotted name path and start/end line numbers."""

    name_path: Tuple[str, ...]
    lineno: int
    end_lineno: int


def collect_definitions(node: ast.AST, current_path: Tuple[str, ...] = ()) -> List[DefNode]:
    """Recursively collect every function/class definition with its qualified name and span."""
    defs = []
    
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        current_path = current_path + (node.name,)
        defs.append(DefNode(current_path, node.lineno, node.end_lineno))
        
    for child in ast.iter_child_nodes(node):
        defs.extend(collect_definitions(child, current_path))
        
    return defs


def apply_ast_splice(content: str, replace: str) -> Optional[str]:
    """Replace a whole def/class in ``content`` by matching the definition in ``replace`` via the AST."""
    clean_repl = clean_indentation(replace)
    try:
        repl_tree = ast.parse(clean_repl)
        repl_defs = collect_definitions(repl_tree)
    except Exception:
        return None

    if not repl_defs:
        return None

    try:
        orig_tree = ast.parse(content)
        orig_defs = collect_definitions(orig_tree)
    except Exception:
        return None

    matches = []
    for r_def in repl_defs:
        exact_matches = [o for o in orig_defs if o.name_path == r_def.name_path]
        if len(exact_matches) == 1:
            matches.append((exact_matches[0], r_def))
            continue
        elif len(exact_matches) > 1:
            return None

        suffix_matches = [
            o_def for o_def in orig_defs
            if len(o_def.name_path) >= len(r_def.name_path) and
               o_def.name_path[-len(r_def.name_path):] == r_def.name_path
        ]
        if len(suffix_matches) != 1:
            return None
        matches.append((suffix_matches[0], r_def))

    matches.sort(key=lambda m: m[0].lineno, reverse=True)

    clean_repl_lines = clean_repl.splitlines(keepends=True)
    orig_lines = content.splitlines(keepends=True)

    for orig_def, r_def in matches:
        r_lines = clean_repl_lines[r_def.lineno - 1 : r_def.end_lineno]
        r_str = "".join(r_lines)

        if orig_def.lineno - 1 < len(orig_lines):
            start_line = orig_lines[orig_def.lineno - 1]
            match = re.match(r'^([ \t]*)', start_line)
            indent = match.group(1) if match else ""
        else:
            indent = ""

        repl_lines = []
        is_tab = '\t' in indent
        for line in r_lines:
            if not line.strip():
                repl_lines.append(line)
                continue
            
            match = re.match(r'^([ \t]*)', line)
            line_ws = match.group(1) if match else ""
            line_content = line[len(line_ws):]
            
            if is_tab:
                num_tabs = len(line_ws.replace('\t', '    ')) // 4
                new_ws = '\t' * num_tabs
            else:
                num_spaces = len(line_ws.replace('\t', '    '))
                new_ws = ' ' * num_spaces
                
            repl_lines.append(indent + new_ws + line_content)

        repl_str = "".join(repl_lines)
        if not repl_str.endswith("\n"):
            repl_str += "\n"

        orig_lines = orig_lines[:orig_def.lineno - 1] + [repl_str] + orig_lines[orig_def.end_lineno:]

    return "".join(orig_lines)
