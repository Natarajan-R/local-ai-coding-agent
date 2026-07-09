from agent.evaluation.evaluator import Evaluator


def test_detects_project_type_from_markers(local_sandbox, policy, workspace):
    ev = Evaluator(local_sandbox, policy)
    (workspace / "go.mod").write_text("module x\n")
    assert ev._detect_command(workspace) == "go test ./..."
    (workspace / "package.json").write_text("{}")
    # package.json is checked before go.mod
    assert ev._detect_command(workspace) == "npm test --silent"


def test_explicit_test_command_overrides_detection(local_sandbox, policy, workspace):
    (workspace / "go.mod").write_text("module x\n")
    ev = Evaluator(local_sandbox, policy, test_command="make check")
    assert ev._detect_command(workspace) == "make check"


def test_test_command_is_run(local_sandbox, policy, workspace):
    # A trivially-passing custom command should make evaluation pass.
    ev = Evaluator(local_sandbox, policy, test_command="true")
    result = ev.evaluate(workspace)
    assert result.passed and result.ran_tests


def test_evaluator_passes_when_tests_pass(local_sandbox, policy, workspace):
    (workspace / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (workspace / "test_calc.py").write_text(
        "from calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
    )
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert result.passed
    assert result.ran_tests


def test_evaluator_fails_when_tests_fail(local_sandbox, policy, workspace):
    (workspace / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n")
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert not result.passed
    assert result.ran_tests


def test_evaluator_syntax_check_without_tests(local_sandbox, policy, workspace):
    (workspace / "ok.py").write_text("x = 1\n")
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert result.passed
    assert not result.ran_tests


def test_evaluator_handles_test_file_with_no_tests(local_sandbox, policy, workspace):
    # A test file that only has module-level asserts collects zero tests
    # (pytest exit code 5); this must not be reported as a failure.
    (workspace / "mod.py").write_text("def f():\n    return 1\n")
    (workspace / "test_mod.py").write_text("import mod\n\nassert mod.f() == 1\n")
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert result.passed
