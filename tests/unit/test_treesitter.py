import pytest

# Skip the whole module if the tree-sitter grammars aren't installed.
pytest.importorskip("tree_sitter")
pytest.importorskip("tree_sitter_java")

from agent.perception.indexer import WorkspaceIndexer
from agent.perception.languages import LanguageRouter
from agent.perception.treesitter_driver import build_profiles, treesitter_available


def test_treesitter_available_and_router_enabled():
    assert treesitter_available()
    router = LanguageRouter()
    assert router.treesitter is True
    exts = router.supported_extensions()
    assert {".java", ".go", ".js", ".sh"} <= exts


def test_java_skeleton_extracts_types_and_members():
    router = LanguageRouter()
    code = (
        "public class Foo extends Bar {\n"
        "  private int x;\n"
        "  public int add(int a, int b) { return a + b; }\n"
        "  Foo() {}\n"
        "}\n"
        "interface Greeter { String hi(); }\n"
    )
    sk = router.skeleton("Foo.java", code)
    assert "class Foo" in sk
    assert "add(int a, int b)" in sk
    assert "Foo()" in sk           # constructor
    assert "interface Greeter" in sk
    assert "return a + b" not in sk  # bodies dropped


def test_go_skeleton():
    router = LanguageRouter()
    code = "package main\ntype Point struct {\n  X int\n}\nfunc (p Point) Dist() int { return p.X }\nfunc main() {}\n"
    sk = router.skeleton("m.go", code)
    assert "type Point struct" in sk
    assert "func (p Point) Dist() int" in sk
    assert "func main()" in sk


def test_javascript_skeleton():
    router = LanguageRouter()
    code = "class Animal {\n  speak() { return 'x'; }\n}\nfunction greet(name) { return name; }\n"
    sk = router.skeleton("a.js", code)
    assert "class Animal" in sk
    assert "speak()" in sk
    assert "function greet(name)" in sk


def test_treesitter_is_error_tolerant():
    router = LanguageRouter()
    # Missing closing brace -- tree-sitter still recovers partial structure.
    code = "public class Broken {\n  public void go() {\n"
    sk = router.skeleton("Broken.java", code)
    assert "class Broken" in sk


def test_indexer_includes_go_file_skeleton(workspace):
    (workspace / "main.go").write_text("package main\nfunc main() {}\n")
    indexer = WorkspaceIndexer(workspace)
    skeleton = indexer.get_repo_skeleton()
    assert "main.go" in skeleton
    assert "func main()" in skeleton


def test_typescript_skeleton():
    pytest.importorskip("tree_sitter_typescript")
    router = LanguageRouter()
    assert {".ts", ".tsx"} <= router.supported_extensions()
    code = (
        "interface Shape { area(): number; }\n"
        "type ID = string | number;\n"
        "enum Color { Red, Green }\n"
        "abstract class Base { abstract run(): void; }\n"
        "export class Circle extends Base implements Shape {\n"
        "  constructor(private r: number) { super(); }\n"
        "  area(): number { return 3.14 * this.r * this.r; }\n"
        "}\n"
        "function greet(name: string): string { return name; }\n"
    )
    sk = router.skeleton("m.ts", code)
    assert "interface Shape" in sk
    assert "type ID = string | number" in sk
    assert "enum Color" in sk
    assert "abstract class Base" in sk
    assert "class Circle extends Base implements Shape" in sk
    assert "constructor(private r: number)" in sk
    assert "area(): number" in sk
    assert "function greet(name: string): string" in sk
    assert "3.14" not in sk  # bodies dropped


def test_tsx_skeleton():
    pytest.importorskip("tree_sitter_typescript")
    router = LanguageRouter()
    sk = router.skeleton("c.tsx", "export function App() { return <div/>; }\nclass W { render() { return null; } }")
    assert "function App()" in sk
    assert "class W" in sk
    assert "render()" in sk


def test_powershell_skeleton():
    pytest.importorskip("tree_sitter_powershell")
    router = LanguageRouter()
    assert ".ps1" in router.supported_extensions()
    code = (
        "function Get-Greeting {\n"
        "    param([string]$Name)\n"
        "    return \"Hi $Name\"\n"
        "}\n"
        "class Animal {\n"
        "    [string]$Name\n"
        "    Animal([string]$n) { $this.Name = $n }\n"
        "    [string] Speak() { return \"...\" }\n"
        "}\n"
    )
    sk = router.skeleton("demo.ps1", code)
    assert "function Get-Greeting" in sk
    assert "class Animal" in sk
    assert "Animal([string]$n)" in sk   # constructor
    assert "Speak()" in sk
    assert "return" not in sk           # bodies dropped


def test_csharp_skeleton():
    pytest.importorskip("tree_sitter_c_sharp")
    router = LanguageRouter()
    code = (
        "namespace N {\n"
        "  public class Foo : Bar {\n"
        "    public int Add(int a, int b) { return a + b; }\n"
        "    public Foo() {}\n"
        "  }\n"
        "  interface I { void M(); }\n"
        "}\n"
    )
    sk = router.skeleton("a.cs", code)
    assert "namespace N" in sk
    assert "class Foo : Bar" in sk
    assert "int Add(int a, int b)" in sk
    assert "interface I" in sk


def test_rust_skeleton():
    pytest.importorskip("tree_sitter_rust")
    router = LanguageRouter()
    code = "trait T { fn m(&self); }\nimpl Point {\n  fn dist(&self) -> i32 { self.x }\n}\nfn main() {}\n"
    sk = router.skeleton("a.rs", code)
    assert "trait T" in sk
    assert "impl Point" in sk
    assert "fn dist(&self) -> i32" in sk
    assert "fn main()" in sk


def test_ruby_skeleton_has_no_spurious_keyword_lines():
    pytest.importorskip("tree_sitter_ruby")
    router = LanguageRouter()
    sk = router.skeleton("a.rb", "class Animal\n  def speak\n    'x'\n  end\nend\n")
    lines = [ln.strip() for ln in sk.splitlines()]
    assert "class Animal" in sk
    assert "def speak" in sk
    assert "class" not in lines  # anonymous keyword token must not leak in


def test_c_and_cpp_skeleton():
    pytest.importorskip("tree_sitter_c")
    pytest.importorskip("tree_sitter_cpp")
    router = LanguageRouter()
    c_sk = router.skeleton("a.c", "struct Point { int x; };\nint add(int a, int b) {\n  return a + b;\n}\n")
    assert "struct Point" in c_sk
    assert "int add(int a, int b)" in c_sk

    cpp_sk = router.skeleton("a.cpp", "namespace ns {\nclass Foo : public Bar {\npublic:\n  int add(int a, int b) { return a+b; }\n};\n}\n")
    assert "namespace ns" in cpp_sk
    assert "class Foo : public Bar" in cpp_sk
    assert "int add(int a, int b)" in cpp_sk


def test_build_profiles_skips_unknown_language():
    assert build_profiles(languages=["nonexistent-lang"]) == []
