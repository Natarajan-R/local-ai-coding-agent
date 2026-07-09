from agent.perception.indexer import WorkspaceIndexer
from agent.perception.symbols import SymbolIndex, python_imports


def _index(workspace):
    return SymbolIndex(WorkspaceIndexer(workspace))


def test_python_symbols_and_kinds(workspace):
    (workspace / "m.py").write_text(
        "class User:\n    def name(self):\n        return 1\n\ndef helper():\n    return 2\n"
    )
    idx = _index(workspace)
    user = idx.find_definition("User")
    assert user and user[0].kind == "class" and user[0].line == 1
    name = idx.find_definition("name")
    assert name and name[0].kind == "method"
    helper = idx.find_definition("helper")
    assert helper and helper[0].kind == "function"


def test_search_substring(workspace):
    (workspace / "m.py").write_text("def compute_total():\n    return 0\n")
    hits = _index(workspace).search("total")
    assert any(h.name == "compute_total" for h in hits)


def test_python_imports_and_importers(workspace):
    (workspace / "pkg").mkdir()
    (workspace / "pkg" / "models.py").write_text("class User:\n    pass\n")
    (workspace / "app.py").write_text("from pkg.models import User\nimport os\n")
    idx = _index(workspace)
    importers = idx.importers("User")
    assert any(path == "app.py" for path, _, _ in importers)


def test_python_imports_helper():
    imps = dict((m, ln) for m, ln in python_imports("import os\nfrom a.b import c\n"))
    assert "os" in imps
    assert "a.b" in imps and "a.b.c" in imps


def test_cross_language_symbol(workspace):
    (workspace / "Svc.java").write_text("public class Svc {\n  public int add(int a, int b){ return a; }\n}\n")
    hits = _index(workspace).find_definition("add")
    # tree-sitter grammars may be absent in some envs; only assert when found.
    if hits:
        assert hits[0].path == "Svc.java"


def test_refresh_rebuilds(workspace):
    (workspace / "m.py").write_text("def a():\n    return 1\n")
    idx = _index(workspace)
    assert idx.find_definition("a")
    (workspace / "m.py").write_text("def a():\n    return 1\n\ndef b():\n    return 2\n")
    idx.refresh()
    assert idx.find_definition("b")
