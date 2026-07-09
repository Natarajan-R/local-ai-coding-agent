from agent.perception.indexer import WorkspaceIndexer
from agent.perception.languages import LanguageRouter


def test_python_skeleton_extracts_signatures():
    router = LanguageRouter()
    code = "import os\n\n\nclass Foo:\n    def bar(self, x):\n        return x + 1\n\n\ndef top():\n    return 2\n"
    skeleton = router.skeleton("m.py", code)
    assert "class Foo" in skeleton
    assert "def bar" in skeleton
    assert "def top" in skeleton
    assert "return x + 1" not in skeleton  # bodies are dropped


def test_shell_skeleton():
    router = LanguageRouter()
    code = "greet() {\n  echo hi\n}\n"
    skeleton = router.skeleton("s.sh", code)
    assert "greet()" in skeleton


def test_indexer_lists_files_and_skeleton(workspace):
    (workspace / "a.py").write_text("def hello():\n    return 1\n")
    (workspace / "notes.md").write_text("# hi")
    sub = workspace / "pkg"
    sub.mkdir()
    (sub / "b.py").write_text("class B:\n    pass\n")

    indexer = WorkspaceIndexer(workspace)
    files = indexer.list_files()
    names = {f.name for f in files}
    assert {"a.py", "notes.md", "b.py"} <= names

    skeleton = indexer.get_repo_skeleton()
    assert "a.py" in skeleton
    assert "def hello" in skeleton


def test_indexer_empty_workspace(workspace):
    indexer = WorkspaceIndexer(workspace)
    assert "empty" in indexer.get_repo_skeleton().lower()


def test_small_repo_gets_full_skeleton(workspace):
    (workspace / "a.py").write_text("def foo():\n    return 1\n")
    skeleton = WorkspaceIndexer(workspace).get_repo_skeleton()
    assert "# Repository structure" in skeleton
    assert "def foo" in skeleton


def test_large_repo_gets_compact_overview(workspace):
    for d in ("src/pkg", "src/util", "tests"):
        (workspace / d).mkdir(parents=True)
        for i in range(20):
            (workspace / d / f"m{i}.py").write_text(f"def f_{i}(x):\n    return x\n")
    (workspace / "README.md").write_text("hi")
    skeleton = WorkspaceIndexer(workspace).get_repo_skeleton()
    assert "Repository overview" in skeleton
    assert "src/  (40 files)" in skeleton
    assert "list_files" in skeleton and "search_text" in skeleton
    assert "README.md" in skeleton
    # No full per-file skeletons in overview mode.
    assert "## src/pkg/m0.py" not in skeleton


def test_search_text_finds_matches(workspace):
    (workspace / "one.py").write_text("alpha = 1\nbeta = 2\n")
    (workspace / "two.py").write_text("gamma = 3\nalpha_again = 4\n")
    matches = WorkspaceIndexer(workspace).search_text("alpha")
    found = {str(rel) for rel, _, _ in matches}
    assert "one.py" in found and "two.py" in found


def test_search_text_skips_binary_and_empty_query(workspace):
    (workspace / "data.bin").write_bytes(b"\x00\x01\x02alpha\xff")
    idx = WorkspaceIndexer(workspace)
    assert idx.search_text("") == []
    # Binary file must not crash the search (decode error -> skipped).
    assert idx.search_text("alpha") == []


def test_outline_of_file(workspace):
    (workspace / "m.py").write_text("class A:\n    def go(self):\n        return 1\n")
    out = WorkspaceIndexer(workspace).outline(workspace / "m.py")
    assert "class A" in out and "def go" in out


def test_list_files_scoped_to_directory(workspace):
    (workspace / "src").mkdir()
    (workspace / "src" / "x.py").write_text("x = 1")
    (workspace / "top.py").write_text("y = 2")
    idx = WorkspaceIndexer(workspace)
    scoped = {str(f.relative_to(workspace)) for f in idx.list_files("src")}
    assert scoped == {"src/x.py"}


def test_router_falls_back_to_regex_without_treesitter(monkeypatch):
    # Simulate tree-sitter being unavailable and confirm the router still
    # routes Java/Shell via the regex profiles instead of crashing.
    import agent.perception.treesitter_driver as ts

    def _boom(*args, **kwargs):
        raise ImportError("tree-sitter not installed")

    monkeypatch.setattr(ts, "build_profiles", _boom)

    router = LanguageRouter()
    assert router.treesitter is False
    sk = router.skeleton("Foo.java", "class Foo { void go() {} }")
    assert "Foo" in sk
    # Python still works (stdlib AST, independent of tree-sitter).
    assert "def m" in router.skeleton("p.py", "class A:\n    def m(self):\n        return 1\n")
