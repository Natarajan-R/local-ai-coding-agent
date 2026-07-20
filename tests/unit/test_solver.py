import pytest

from agent.tools.solver import solve, SolverError, Z3_AVAILABLE

pytestmark = pytest.mark.skipif(not Z3_AVAILABLE, reason="z3 not installed")


def test_scheduling_respects_ordering_and_deadline():
    r = solve(
        variables=[{"name": "a", "type": "int", "min": 0, "max": 10},
                   {"name": "b", "type": "int", "min": 0, "max": 10}],
        constraints=["a + 3 <= b", "b + 2 <= 10"],
    )
    assert r.status == "sat"
    assert r.assignments["a"] + 3 <= r.assignments["b"]
    assert r.assignments["b"] + 2 <= 10


def test_domain_restricts_to_allowed_values():
    r = solve(
        variables=[{"name": "version", "type": "int", "domain": [1, 3, 7]}],
        constraints=["version > 2"],
    )
    assert r.status == "sat"
    assert r.assignments["version"] in (3, 7)


def test_all_different():
    r = solve(
        variables=[{"name": f"p{i}", "type": "int", "min": 1, "max": 3} for i in range(3)],
        constraints=[],
        all_different=["p0", "p1", "p2"],
    )
    assert r.status == "sat"
    assert sorted(r.assignments.values()) == [1, 2, 3]


def test_maximize_finds_the_optimum():
    r = solve(
        variables=[{"name": "x", "type": "int", "min": 0, "max": 5},
                   {"name": "y", "type": "int", "min": 0, "max": 5}],
        constraints=["2*x + 3*y <= 12"],
        maximize="5*x + 4*y",
    )
    assert r.status == "sat"
    assert 5 * r.assignments["x"] + 4 * r.assignments["y"] == 25


def test_contradiction_reports_unsat_rather_than_guessing():
    """unsat is information. Returning a plausible number here would be a lie."""
    r = solve(variables=[{"name": "n", "type": "int"}], constraints=["n > 5", "n < 3"])
    assert r.status == "unsat"
    assert r.assignments == {}


def test_chained_comparison():
    r = solve(variables=[{"name": "x", "type": "int"}], constraints=["1 <= x", "x <= 1"])
    assert r.status == "sat" and r.assignments["x"] == 1


def test_boolean_variables():
    r = solve(
        variables=[{"name": "p", "type": "bool"}, {"name": "q", "type": "bool"}],
        constraints=["p or q", "not p"],
    )
    assert r.status == "sat"
    assert r.assignments["p"] is False and r.assignments["q"] is True


@pytest.mark.parametrize("hostile", [
    '__import__("os").system("echo pwned")',
    'open("/etc/passwd").read()',
    "[i for i in range(9)]",
    "x.__class__.__bases__",
    "(lambda: 1)()",
    "globals()",
])
def test_constraints_are_never_executed_as_code(hostile):
    """Constraints are parsed and compiled, never eval'd.

    The model supplies these strings, so a Call or Attribute node reaching an
    interpreter would be arbitrary code execution inside the agent process.
    """
    with pytest.raises(SolverError):
        solve(variables=[{"name": "x", "type": "int"}], constraints=[hostile])


def test_undeclared_variable_is_rejected_with_a_fix():
    with pytest.raises(SolverError) as exc:
        solve(variables=[{"name": "x", "type": "int"}], constraints=["x + y == 3"])
    assert "y" in str(exc.value) and "declare" in str(exc.value)


def test_malformed_constraint_names_the_offender():
    with pytest.raises(SolverError) as exc:
        solve(variables=[{"name": "x", "type": "int"}], constraints=["x +"])
    assert "x +" in str(exc.value)
