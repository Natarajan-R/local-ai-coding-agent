"""Tree-sitter backed skeletons for multiple languages.

Uses the individual ``tree-sitter-<lang>`` grammar wheels (each bundles its
compiled grammar, so this works fully offline -- no runtime download). Grammars
are optional: if ``tree_sitter`` or a specific grammar is not installed, that
language is simply skipped and the caller falls back to a regex profile.
"""
from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .languages import LanguageProfile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LangSpec:
    module: str                     # grammar module name, e.g. "tree_sitter_java"
    extensions: List[str]
    containers: Set[str]            # node types to render as "class { ... }"
    members: Set[str]               # node types to render as signatures
    language_func: str = "language"  # grammar entry point (some wheels differ)


# Grammar wheels each bundle a compiled parser, so this works fully offline.
_SPEC: Dict[str, LangSpec] = {
    "java": LangSpec(
        "tree_sitter_java",
        [".java"],
        {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"},
        {"method_declaration", "constructor_declaration"},
    ),
    "javascript": LangSpec(
        "tree_sitter_javascript",
        [".js", ".mjs", ".cjs", ".jsx"],
        {"class_declaration"},
        {"function_declaration", "generator_function_declaration", "method_definition"},
    ),
    "typescript": LangSpec(
        "tree_sitter_typescript",
        [".ts", ".mts", ".cts"],
        {"class_declaration", "abstract_class_declaration", "interface_declaration", "enum_declaration"},
        {"function_declaration", "method_definition", "type_alias_declaration"},
        language_func="language_typescript",
    ),
    "tsx": LangSpec(
        "tree_sitter_typescript",
        [".tsx"],
        {"class_declaration", "abstract_class_declaration", "interface_declaration", "enum_declaration"},
        {"function_declaration", "method_definition", "type_alias_declaration"},
        language_func="language_tsx",
    ),
    "go": LangSpec(
        "tree_sitter_go",
        [".go"],
        {"type_declaration"},
        {"function_declaration", "method_declaration"},
    ),
    "bash": LangSpec(
        "tree_sitter_bash",
        [".sh", ".bash"],
        set(),
        {"function_definition"},
    ),
    "powershell": LangSpec(
        "tree_sitter_powershell",
        [".ps1", ".psm1", ".psd1"],
        {"class_statement"},
        {"function_statement", "class_method_definition"},
    ),
    "csharp": LangSpec(
        "tree_sitter_c_sharp",
        [".cs"],
        {"namespace_declaration", "class_declaration", "interface_declaration",
         "struct_declaration", "enum_declaration", "record_declaration"},
        {"method_declaration", "constructor_declaration", "property_declaration"},
    ),
    "rust": LangSpec(
        "tree_sitter_rust",
        [".rs"],
        {"struct_item", "enum_item", "trait_item", "impl_item", "mod_item"},
        {"function_item"},
    ),
    "ruby": LangSpec(
        "tree_sitter_ruby",
        [".rb"],
        {"class", "module"},
        {"method", "singleton_method"},
    ),
    "c": LangSpec(
        "tree_sitter_c",
        [".c", ".h"],
        {"struct_specifier", "enum_specifier", "union_specifier"},
        {"function_definition"},
    ),
    "cpp": LangSpec(
        "tree_sitter_cpp",
        [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"],
        {"class_specifier", "struct_specifier", "namespace_definition",
         "enum_specifier", "union_specifier"},
        {"function_definition"},
    ),
}


def _load_parser(spec: LangSpec):
    """Return a configured Parser for a grammar spec, or None if unavailable."""
    try:
        from tree_sitter import Language, Parser

        module = importlib.import_module(spec.module)
        language_fn = getattr(module, spec.language_func)
        return Parser(Language(language_fn()))
    except Exception as exc:  # ImportError, missing entry point, or ABI mismatch
        logger.debug("tree-sitter grammar %s unavailable: %s", spec.module, exc)
        return None


class TreeSitterProfile(LanguageProfile):
    """A language profile that extracts class/function signatures via tree-sitter."""

    def __init__(
        self,
        name: str,
        extensions: List[str],
        parser,
        containers: Set[str],
        members: Set[str],
    ) -> None:
        self._name = name
        self._extensions = extensions
        self._parser = parser
        self._containers = containers
        self._members = members

    @property
    def name(self) -> str:
        return self._name

    @property
    def extensions(self) -> List[str]:
        return self._extensions

    def generate_skeleton(self, content: str) -> str:
        try:
            tree = self._parser.parse(bytes(content, "utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("tree-sitter parse failed for %s: %s", self._name, exc)
            return ""
        lines: List[str] = []
        self._walk(tree.root_node, 0, lines)
        return "\n".join(lines)

    def _walk(self, node, depth: int, lines: List[str]) -> None:
        next_depth = depth
        # Guard on is_named: anonymous keyword tokens can share a node-type name
        # with real nodes (e.g. Ruby's `class`/`module` keyword vs. class node).
        if node.is_named and node.type in self._containers:
            lines.append("    " * depth + self._container_header(node))
            next_depth = depth + 1
        elif node.is_named and node.type in self._members:
            lines.append("    " * depth + self._member_header(node))
        for child in node.children:
            self._walk(child, next_depth, lines)

    @staticmethod
    def _decode(node) -> str:
        return node.text.decode("utf-8", "replace") if node.text else ""

    @staticmethod
    def _segment(text: str) -> str:
        """The signature portion of a declaration: up to the body brace, or the
        first line for brace-less languages (Ruby, etc.)."""
        brace = text.find("{")
        seg = text[:brace] if brace != -1 else text.split("\n", 1)[0]
        return " ".join(seg.split())

    @classmethod
    def _container_header(cls, node) -> str:
        text = cls._decode(node)
        head = cls._segment(text)
        return head + (" { ... }" if "{" in text else "")

    @classmethod
    def _member_header(cls, node) -> str:
        text = cls._decode(node)
        return cls._segment(text).rstrip(";").rstrip()

    # -- structured symbols (for the symbol index) --------------------------
    _PRIMARY_NAME_TYPES = {
        "identifier", "field_identifier", "name", "simple_name",
        "function_name", "word", "constant",
    }
    _SECONDARY_NAME_TYPES = {"type_identifier", "scoped_identifier"}

    @classmethod
    def _node_name(cls, node) -> Optional[str]:
        for child in node.children:
            if child.is_named and child.type in cls._PRIMARY_NAME_TYPES:
                return cls._decode(child)
        for child in node.children:
            if child.is_named and child.type in cls._SECONDARY_NAME_TYPES:
                return cls._decode(child)
        return None

    @staticmethod
    def _kind(node_type: str) -> str:
        kind = node_type
        for suffix in ("_declaration", "_definition", "_specifier", "_statement", "_item", "_spec"):
            kind = kind.replace(suffix, "")
        return kind

    def extract_symbols(self, content: str) -> List[tuple]:
        try:
            tree = self._parser.parse(bytes(content, "utf-8"))
        except Exception:  # pragma: no cover - defensive
            return []
        out: List[tuple] = []

        def walk(node) -> None:
            if node.is_named and (node.type in self._containers or node.type in self._members):
                name = self._node_name(node)
                if name:
                    out.append((name, self._kind(node.type), node.start_point[0] + 1))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return out


def build_profiles(languages: Optional[List[str]] = None) -> List[TreeSitterProfile]:
    """Build TreeSitterProfiles for every grammar that is importable."""
    profiles: List[TreeSitterProfile] = []
    for key, spec in _SPEC.items():
        if languages is not None and key not in languages:
            continue
        parser = _load_parser(spec)
        if parser is None:
            continue
        profiles.append(
            TreeSitterProfile(key, spec.extensions, parser, spec.containers, spec.members)
        )
    return profiles


def treesitter_available() -> bool:
    try:
        import tree_sitter  # noqa: F401
        return True
    except Exception:
        return False
