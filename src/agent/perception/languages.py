"""Language profiles that turn source files into compact skeletons.

A skeleton keeps signatures (classes, functions) and drops bodies so the model
can understand a file's shape without spending context on implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class LanguageProfile(ABC):
    @property
    @abstractmethod
    def name(self) -> str:  # pragma: no cover - trivial
        ...

    @property
    @abstractmethod
    def extensions(self) -> List[str]:  # pragma: no cover - trivial
        ...

    @abstractmethod
    def generate_skeleton(self, content: str) -> str:
        ...

    def extract_symbols(self, content: str) -> List[Tuple[str, str, int]]:
        """Return (name, kind, 1-indexed line) for each definition. Optional."""
        return []


class LanguageRouter:
    """Route a file (by extension) to the right :class:`LanguageProfile`.

    Python always uses the stdlib ``ast`` profile (reliable, dependency-free).
    For other languages we prefer tree-sitter when its grammars are installed,
    and fall back to lightweight regex profiles otherwise.
    """

    def __init__(self) -> None:
        self._by_ext: Dict[str, LanguageProfile] = {}
        self.treesitter = False
        self._register_defaults()

    def _register_defaults(self) -> None:
        # Imported here to avoid a circular import at module load time.
        from .java_driver import JavaProfile
        from .python_driver import PythonProfile
        from .shell_driver import ShellProfile

        # Python: stdlib AST, always.
        self.register(PythonProfile())

        # Tree-sitter for richer, multi-language extraction (optional).
        covered: set[str] = set()
        try:
            from .treesitter_driver import build_profiles

            for profile in build_profiles():
                self.register(profile)
                covered.update(e.lower() for e in profile.extensions)
                self.treesitter = True
        except Exception:  # pragma: no cover - defensive: tree-sitter absent
            pass

        # Regex fallbacks only for languages tree-sitter did not cover.
        if ".java" not in covered:
            self.register(JavaProfile())
        if ".sh" not in covered:
            self.register(ShellProfile())

    def register(self, profile: LanguageProfile) -> None:
        for ext in profile.extensions:
            self._by_ext[ext.lower()] = profile

    def for_extension(self, ext: str) -> LanguageProfile | None:
        return self._by_ext.get(ext.lower())

    def supported_extensions(self) -> set[str]:
        return set(self._by_ext.keys())

    def skeleton(self, filename: str, content: str) -> str:
        ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
        profile = self.for_extension(ext)
        if profile is None:
            return content
        return profile.generate_skeleton(content)
