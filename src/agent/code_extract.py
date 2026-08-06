"""Extract code blocks from model responses."""
from __future__ import annotations

import ast
import re
from typing import List, Optional


class CodeExtractor:
    """Extracts code from model responses."""

    @staticmethod
    def extract_implicit_code(text: str, is_python: bool = False) -> Optional[str]:
        """Extract code blocks from model response."""
        text_stripped = text.strip()
        if not text_stripped:
            return None

        fenced_blocks = CodeExtractor._extract_fenced_blocks(text_stripped)
        if fenced_blocks:
            return "\n\n".join(fenced_blocks)

        if is_python:
            return CodeExtractor._extract_python_code(text_stripped)

        return None

    @staticmethod
    def _extract_fenced_blocks(text: str) -> List[str]:
        """Extract code from fenced markdown blocks."""
        pattern = re.compile(r"```([a-zA-Z0-9+#-]*)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
        blocks = []

        for lang, code in pattern.findall(text):
            lang = (lang or "").strip().lower()
            if lang in ("json", "tool_call", "tool", "tool_name"):
                continue
            if code.strip():
                blocks.append(code.strip())

        return blocks

    @staticmethod
    def _extract_python_code(text: str) -> Optional[str]:
        """Extract Python code using AST validation."""
        try:
            ast.parse(text)
            return text
        except SyntaxError:
            pass

        lines = text.splitlines()
        start_idx = -1

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("def ", "async def ", "class ", "import ", "from ")):
                start_idx = idx
                break

        if start_idx != -1:
            candidate = "\n".join(lines[start_idx:])
            try:
                ast.parse(candidate)
                return candidate
            except SyntaxError:
                cand_lines = candidate.splitlines()
                while len(cand_lines) > 1:
                    cand_lines.pop()
                    try:
                        extracted = "\n".join(cand_lines).strip()
                        ast.parse(extracted)
                        return extracted
                    except SyntaxError:
                        continue
                return candidate.strip()

        return None
