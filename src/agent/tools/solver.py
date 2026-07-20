"""Constraint solving, delegated to z3.

Some problems are not a knowledge gap the model can read its way out of --
scheduling, resource allocation, dependency version selection, configuration
validation. A model that cannot do the search will not learn to by being given
more context; it will produce a confident, wrong answer. So the model's job here
is *translation* (describe the problem), and the solving is done by something
that is actually complete.

Constraints arrive as strings. They are NOT eval'd: each is parsed with `ast`
and compiled to z3 through a whitelist of node types, so a constraint can only
ever become a z3 expression -- never a function call, attribute access, import,
or comprehension. Same posture as the AST command guard.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# z3 is optional: the agent must work without it, so import lazily and degrade
# with an actionable message rather than crashing at startup.
try:
    import z3
    Z3_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on install
    z3 = None  # type: ignore
    Z3_AVAILABLE = False


class SolverError(Exception):
    """A constraint could not be understood or the problem was malformed."""


_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}

_CMP_OPS = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}


@dataclass
class Solution:
    status: str                      # "sat" | "unsat" | "unknown"
    assignments: Dict[str, Any]
    message: str = ""


def _declare(variables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build z3 variables from declarations, plus their domain constraints."""
    env: Dict[str, Any] = {}
    domain_constraints = []
    for spec in variables:
        name = spec.get("name")
        if not name or not isinstance(name, str) or not name.isidentifier():
            raise SolverError(f"invalid variable name: {name!r}")
        kind = (spec.get("type") or "int").lower()
        if kind == "int":
            var = z3.Int(name)
        elif kind in ("real", "float"):
            var = z3.Real(name)
        elif kind == "bool":
            var = z3.Bool(name)
        else:
            raise SolverError(f"unknown type {kind!r} for {name!r}; use int, real or bool")
        env[name] = var

        if "domain" in spec and spec["domain"] is not None:
            allowed = spec["domain"]
            if not isinstance(allowed, list) or not allowed:
                raise SolverError(f"domain for {name!r} must be a non-empty list")
            domain_constraints.append(z3.Or([var == v for v in allowed]))
        if spec.get("min") is not None:
            domain_constraints.append(var >= spec["min"])
        if spec.get("max") is not None:
            domain_constraints.append(var <= spec["max"])
    return {"env": env, "domain_constraints": domain_constraints}


def _compile(node: ast.AST, env: Dict[str, Any]) -> Any:
    """Compile a whitelisted AST node to a z3 expression. No eval, ever."""
    if isinstance(node, ast.Expression):
        return _compile(node.body, env)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise SolverError(f"unsupported literal: {node.value!r}")

    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise SolverError(f"undeclared variable {node.id!r} -- declare it in `variables`")

    if isinstance(node, ast.UnaryOp):
        operand = _compile(node.operand, env)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.Not):
            return z3.Not(operand)
        raise SolverError("unsupported unary operator")

    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise SolverError(f"unsupported operator {type(node.op).__name__}")
        return op(_compile(node.left, env), _compile(node.right, env))

    if isinstance(node, ast.Compare):
        # Handles chained comparisons: 1 <= x <= 9 becomes And(1 <= x, x <= 9)
        parts = []
        left = _compile(node.left, env)
        for op_node, comparator in zip(node.ops, node.comparators):
            op = _CMP_OPS.get(type(op_node))
            if op is None:
                raise SolverError(f"unsupported comparison {type(op_node).__name__}")
            right = _compile(comparator, env)
            parts.append(op(left, right))
            left = right
        return parts[0] if len(parts) == 1 else z3.And(*parts)

    if isinstance(node, ast.BoolOp):
        values = [_compile(v, env) for v in node.values]
        if isinstance(node.op, ast.And):
            return z3.And(*values)
        if isinstance(node.op, ast.Or):
            return z3.Or(*values)
        raise SolverError("unsupported boolean operator")

    raise SolverError(
        f"unsupported expression element {type(node).__name__}. "
        "Constraints may only use variables, numbers, + - * / % **, "
        "comparisons, and and/or/not."
    )


def solve(
    variables: List[Dict[str, Any]],
    constraints: List[str],
    all_different: Optional[List[str]] = None,
    minimize: Optional[str] = None,
    maximize: Optional[str] = None,
) -> Solution:
    """Solve a constraint problem and return one satisfying assignment."""
    if not Z3_AVAILABLE:
        raise SolverError(
            "z3 is not installed. Install it with: pip install z3-solver"
        )
    if not variables:
        raise SolverError("no variables declared")

    declared = _declare(variables)
    env = declared["env"]

    compiled = list(declared["domain_constraints"])
    for text in constraints or []:
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            tree = ast.parse(text.strip(), mode="eval")
        except SyntaxError as exc:
            raise SolverError(f"could not parse constraint {text!r}: {exc.msg}") from exc
        compiled.append(_compile(tree, env))

    if all_different:
        missing = [n for n in all_different if n not in env]
        if missing:
            raise SolverError(f"all_different names undeclared variables: {missing}")
        compiled.append(z3.Distinct(*[env[n] for n in all_different]))

    objective = minimize or maximize
    if objective:
        solver = z3.Optimize()
        for c in compiled:
            solver.add(c)
        tree = ast.parse(objective.strip(), mode="eval")
        expr = _compile(tree, env)
        solver.minimize(expr) if minimize else solver.maximize(expr)
    else:
        solver = z3.Solver()
        for c in compiled:
            solver.add(c)

    result = solver.check()
    if result == z3.sat:
        model = solver.model()
        out: Dict[str, Any] = {}
        for name, var in env.items():
            value = model.eval(var, model_completion=True)
            if z3.is_int_value(value):
                out[name] = value.as_long()
            elif z3.is_true(value) or z3.is_false(value):
                out[name] = z3.is_true(value)
            else:
                out[name] = str(value)
        return Solution("sat", out, "found a satisfying assignment")
    if result == z3.unsat:
        # An unsat result is information, not a failure: the constraints
        # genuinely conflict, and saying so beats returning a plausible guess.
        return Solution("unsat", {}, "no assignment satisfies these constraints -- they conflict")
    return Solution("unknown", {}, "the solver could not decide within its limits")
