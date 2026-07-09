"""Python language profile: skeleton via the AST when possible."""
from __future__ import annotations

import ast
from typing import List, Tuple

from .languages import LanguageProfile


class PythonProfile(LanguageProfile):
    @property
    def name(self) -> str:
        return "python"

    @property
    def extensions(self) -> List[str]:
        return [".py", ".pyi"]

    def extract_symbols(self, content: str) -> List[Tuple[str, str, int]]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        out: List[Tuple[str, str, int]] = []

        def visit(node, in_class: bool) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append((child.name, "method" if in_class else "function", child.lineno))
                    visit(child, False)
                elif isinstance(child, ast.ClassDef):
                    out.append((child.name, "class", child.lineno))
                    visit(child, True)
                else:
                    visit(child, in_class)

        visit(tree, False)
        return out

    def generate_skeleton(self, content: str) -> str:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._fallback(content)

        lines: List[str] = []

        def render(node: ast.AST, indent: int = 0) -> None:
            pad = "    " * indent
            for child in getattr(node, "body", []):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async def" if isinstance(child, ast.AsyncFunctionDef) else "def"
                    args = ast.unparse(child.args) if hasattr(ast, "unparse") else ""
                    lines.append(f"{pad}{prefix} {child.name}({args}): ...")
                elif isinstance(child, ast.ClassDef):
                    bases = ", ".join(ast.unparse(b) for b in child.bases) if hasattr(ast, "unparse") else ""
                    header = f"{pad}class {child.name}" + (f"({bases})" if bases else "") + ":"
                    lines.append(header)
                    render(child, indent + 1)

        render(tree)
        return "\n".join(lines) if lines else self._fallback(content)

    @staticmethod
    def _fallback(content: str) -> str:
        keep = [
            ln.rstrip()
            for ln in content.splitlines()
            if ln.lstrip().startswith(("def ", "class ", "async def "))
        ]
        return "\n".join(keep)
