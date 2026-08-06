"""Test-impact analysis: find tests transitively importing modified modules."""
from __future__ import annotations

from pathlib import Path
from typing import List


def find_impacted_tests(
    modified_paths: List[str],
    symbol_index: Any,
) -> List[str]:
    """Return sorted list of test files transitively importing *modified_paths*.

    Uses the symbol-index ``importers()`` API to walk the import graph from each
    modified Python module outward, collecting any file whose basename looks like
    a test along the way.
    """
    impacted_tests: set[str] = set()
    visited_modules: set[str] = set()

    queue: list[str] = []
    for p in modified_paths:
        path_obj = Path(p)
        if path_obj.suffix.lower() == ".py":
            mod_parts = list(path_obj.with_suffix("").parts)
            mod_name = ".".join(mod_parts)
            queue.append(mod_name)
            visited_modules.add(mod_name)

    while queue:
        curr_mod = queue.pop(0)
        imports = symbol_index.importers(curr_mod)
        for imp_path, _line, _module in imports:
            if any(pat in Path(imp_path).name.lower() for pat in ("test_", "_test")):
                impacted_tests.add(imp_path)

            imp_path_obj = Path(imp_path)
            if imp_path_obj.suffix.lower() == ".py":
                imp_mod = ".".join(imp_path_obj.with_suffix("").parts)
                if imp_mod not in visited_modules:
                    visited_modules.add(imp_mod)
                    queue.append(imp_mod)

    return sorted(impacted_tests)
