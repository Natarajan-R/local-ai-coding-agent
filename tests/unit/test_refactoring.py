import pytest
from agent.tools.registry import ToolRegistry


@pytest.fixture
def registry(local_sandbox, policy, workspace):
    return ToolRegistry(local_sandbox, policy, workspace)


@pytest.mark.asyncio
async def test_add_parameter_basic(registry, workspace):
    # Set up basic test case: a method and a local call site
    code = (
        "class Calculator:\n"
        "    def add(self, a, b):\n"
        "        return a + b\n"
        "\n"
        "def test():\n"
        "    calc = Calculator()\n"
        "    return calc.add(1, 2)\n"
    )
    (workspace / "a.py").write_text(code, encoding="utf-8")

    res = await registry.execute("add_parameter", {
        "path": "a.py",
        "symbol": "Calculator.add",
        "name": "c",
        "default": "0",
        "value": "0",
    })
    assert res.ok, f"Refactoring failed: {res.content}"

    updated = (workspace / "a.py").read_text(encoding="utf-8")
    assert "def add(self, a, b, c=0):" in updated
    assert "calc.add(1, 2, 0)" in updated


@pytest.mark.asyncio
async def test_add_parameter_with_type_annotation(registry, workspace):
    # Set up method signature with type annotations
    code = (
        "class Calculator:\n"
        "    def add(self, a: int, b: int):\n"
        "        return a + b\n"
        "\n"
        "def test():\n"
        "    calc = Calculator()\n"
        "    return calc.add(1, 2)\n"
    )
    (workspace / "a.py").write_text(code, encoding="utf-8")

    res = await registry.execute("add_parameter", {
        "path": "a.py",
        "symbol": "Calculator.add",
        "name": "c: int",
        "default": "0",
        "value": "0",
    })
    assert res.ok, f"Refactoring failed: {res.content}"

    updated = (workspace / "a.py").read_text(encoding="utf-8")
    # Rope strips the existing parameter annotations; the tool restores them (N1).
    # The original `a: int, b: int` must survive, and the new `c: int` be present.
    assert "def add(self, a: int, b: int, c: int=0):" in updated
    assert "calc.add(1, 2, 0)" in updated


@pytest.mark.asyncio
async def test_add_parameter_cross_file(registry, workspace):
    # Set up cross-file refactoring: a definition in one file, calling site in another
    math_code = (
        "def compute(x):\n"
        "    return x * 2\n"
    )
    (workspace / "math_utils.py").write_text(math_code, encoding="utf-8")

    caller_code = (
        "from math_utils import compute\n"
        "\n"
        "def test_caller():\n"
        "    val = compute(10)\n"
        "    return val\n"
    )
    (workspace / "main.py").write_text(caller_code, encoding="utf-8")

    res = await registry.execute("add_parameter", {
        "path": "math_utils.py",
        "symbol": "compute",
        "name": "y",
        "default": "1",
        "value": "5",
    })
    assert res.ok, f"Refactoring failed: {res.content}"

    updated_def = (workspace / "math_utils.py").read_text(encoding="utf-8")
    assert "def compute(x, y=1):" in updated_def

    updated_caller = (workspace / "main.py").read_text(encoding="utf-8")
    assert "compute(10, 5)" in updated_caller


@pytest.mark.asyncio
async def test_add_parameter_preserves_all_annotations(registry, workspace):
    """N1: Rope drops parameter annotations; the tool must restore them.

    Found by verifying the offline rope integration on a typed library: the
    signature kept working (pytest does not type-check) while every annotation
    was silently deleted. On a py.typed project a maintainer rejects that diff.
    """
    (workspace / "m.py").write_text(
        'import typing as t\n\n\n'
        'class Thing:\n'
        '    def __init__(\n'
        '        self,\n'
        '        obj: "Thing",\n'
        '        fn: t.Callable | None,\n'
        '        count: int,\n'
        '    ) -> None:\n'
        '        self.obj = obj\n\n\n'
        'x = Thing(obj=None, fn=None, count=0)\n',
        encoding="utf-8",
    )
    res = await registry.execute("add_parameter", {
        "path": "m.py", "symbol": "Thing.__init__",
        "name": "caller_name: str", "value": "None",
    })
    assert res.ok, res.content
    out = (workspace / "m.py").read_text(encoding="utf-8")

    import ast
    ast.parse(out)  # must still be valid Python
    # every original annotation survived...
    assert "fn: t.Callable | None" in out
    assert "count: int" in out
    assert ("obj: 'Thing'" in out) or ('obj: "Thing"' in out)
    # ...the return annotation survived...
    assert "-> None" in out
    # ...and the new parameter carries its own hint.
    assert "caller_name: str" in out
    # the call site got the new argument
    assert "Thing(None, None, 0, None)" in out


def test_restore_signature_annotations_python_311_compat(monkeypatch):
    from agent.tools.registry import _restore_signature_annotations
    import ast

    source = (
        "@deco1\n"
        "@deco2\n"
        "def foo(a, caller_name) -> None:\n"
        "    pass\n"
    )

    original_parse = ast.parse
    def mock_parse(*args, **kwargs):
        tree = original_parse(*args, **kwargs)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "foo":
                node.lineno = 1
        return tree

    monkeypatch.setattr(ast, "parse", mock_parse)

    rebuilt = _restore_signature_annotations(
        source, "foo", {"a": "int"}, "None"
    )

    assert "@deco1" in rebuilt
    assert "@deco2" in rebuilt
    assert "def foo(a: int, caller_name) -> None:" in rebuilt



@pytest.mark.asyncio
async def test_add_parameter_result_is_complete_and_directive(registry, workspace):
    """The success message must tell the model the refactor is COMPLETE and name
    the files, or it goes hunting for call sites to hand-edit and breaks them.

    Measured failure mode (SR4/VS3): after a correct add_parameter the model
    re-edited the already-updated call sites and corrupted the file — 7/9. Making
    the result specific and directive took it to 10/10. A tool result is evidence;
    make it say what happened and what not to do next.
    """
    (workspace / "a.py").write_text(
        "class C:\n    def __init__(self, x: int):\n        self.x = x\n\ny = C(x=1)\n",
        encoding="utf-8",
    )
    res = await registry.execute("add_parameter", {
        "path": "a.py", "symbol": "C.__init__", "name": "tag: str", "value": "None",
    })
    assert res.ok
    msg = res.content
    assert "COMPLETE" in msg
    assert "Do NOT edit these call sites yourself" in msg
    assert "a.py" in msg          # names the file it touched
    assert "finish" in msg        # tells it the next step


@pytest.mark.asyncio
async def test_add_parameter_is_idempotent(registry, workspace):
    """Calling add_parameter twice must NOT create a duplicate parameter.

    Measured failure (2026-07-16): unsure the first call worked, the model fired
    add_parameter 3x; Rope added `currency` three times -> def __init__(..., currency,
    currency, currency) -> every call site broken. The whole thrash on a small
    project. The second call must be a no-op that says so.
    """
    (workspace / "m.py").write_text(
        "class C:\n    def __init__(self, a, b):\n        self.a = a\n\nx = C(1, 2)\n",
        encoding="utf-8",
    )
    r1 = await registry.execute("add_parameter", {
        "path": "m.py", "symbol": "C.__init__", "name": "cur: str", "value": "'USD'"})
    assert r1.ok
    r2 = await registry.execute("add_parameter", {
        "path": "m.py", "symbol": "C.__init__", "name": "cur: str", "value": "'USD'"})
    assert r2.ok
    assert "ALREADY" in r2.content

    import ast
    src = (workspace / "m.py").read_text()
    ast.parse(src)  # must still be valid
    init = next(n for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    assert [a.arg for a in init.args.args].count("cur") == 1  # exactly once


@pytest.mark.asyncio
async def test_add_parameter_normalizes_bare_literal_value(registry, workspace):
    """Passing a bare unquoted string value/default must automatically wrap it in quotes.
    
    If the value passed is a bare name like 'USD', the tool must quote it as '"USD"'.
    If the default passed is 'None' or 'True', it must remain unquoted.
    """
    (workspace / "m.py").write_text(
        "class C:\n    def __init__(self, a):\n        self.a = a\n\nx = C(1)\n",
        encoding="utf-8",
    )
    r1 = await registry.execute("add_parameter", {
        "path": "m.py", "symbol": "C.__init__", "name": "cur: str", "value": "USD", "default": "USD"
    })
    assert r1.ok
    
    src = (workspace / "m.py").read_text()
    assert '"USD"' in src or "'USD'" in src
    assert 'C(1, "USD")' in src or "C(1, 'USD')" in src

