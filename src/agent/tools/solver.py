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
from contextlib import contextmanager
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
    """Exception raised for errors in the Z3 solver tool."""
    pass

def _reject_floordiv(a, b):
    raise SolverError("Unsupported operator // (FloorDiv) because Z3 division handles types differently. Please rewrite without //.")


@dataclass
class Solution:
    """The result of a constraint solve: satisfiability plus any assignments."""

    status: str                      # "sat" | "unsat" | "unknown"
    assignments: Dict[str, Any]
    message: str = ""


@contextmanager
def _catch_z3_errors(context_msg: str):
    """Catch Z3 sort mismatches and Python type errors, re-raising as clean SolverErrors.
    
    Dynamically resolves Z3Exception to prevent crashes if z3 failed to import.
    """
    z3_exceptions = (z3.Z3Exception,) if Z3_AVAILABLE and z3 is not None else ()
    
    try:
        yield
    except SolverError:
        raise
    except z3_exceptions as exc:
        err_msg = str(exc).strip()
        raise SolverError(
            f"Z3 sort mismatch in {context_msg}: {err_msg}. "
            "Ensure variables and literals have compatible types (e.g., do not mix Int/Real with Bool)."
        ) from exc
    except (TypeError, ValueError) as exc:
        err_msg = str(exc).strip()
        raise SolverError(
            f"Incompatible types or values in {context_msg}: {err_msg}. "
            "Check operator syntax and variable declarations."
        ) from exc


_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: _reject_floordiv,
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


def _compile_call(node: ast.Call, env: Dict[str, Any]) -> Any:
    """Safely compile a strict whitelist of mathematical function calls."""
    if not isinstance(node.func, ast.Name):
        raise SolverError("Only direct function calls (e.g., min, max, abs) are supported.")
    
    func_name = node.func.id
    args = [_compile(arg, env) for arg in node.args]
    
    if func_name == "abs":
        if len(args) != 1:
            raise SolverError("abs() requires exactly 1 argument")
        val = args[0]
        return z3.If(val >= 0, val, -val)
        
    elif func_name in ("min", "max"):
        if len(args) < 2:
            raise SolverError(f"{func_name}() requires at least 2 arguments")
        
        result = args[0]
        is_min = (func_name == "min")
        for next_arg in args[1:]:
            cond = (result <= next_arg) if is_min else (result >= next_arg)
            result = z3.If(cond, result, next_arg)
        return result
        
    raise SolverError(f"Unsupported function call: {func_name!r}. Allowed: abs, min, max.")


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

        with _catch_z3_errors(f"domain declaration for variable {name!r}"):
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

    # Support sequence literals for membership testing (e.g., [1, 2, 3])
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_compile(item, env) for item in node.elts]

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
        left = _compile(node.left, env)
        right = _compile(node.right, env)
        with _catch_z3_errors(f"binary operation '{type(node.op).__name__}'"):
            return op(left, right)

    # Support ternary conditional expressions (a if cond else b)
    if isinstance(node, ast.IfExp):
        test = _compile(node.test, env)
        body = _compile(node.body, env)
        orelse = _compile(node.orelse, env)
        with _catch_z3_errors("conditional expression (if/else)"):
            return z3.If(test, body, orelse)

    # Support whitelisted math functions (abs, min, max)
    if isinstance(node, ast.Call):
        return _compile_call(node, env)

    if isinstance(node, ast.Compare):
        parts = []
        left = _compile(node.left, env)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = _compile(comparator, env)
            with _catch_z3_errors(f"comparison '{type(op_node).__name__}'"):
                if isinstance(op_node, ast.In):
                    if not isinstance(right, list):
                        raise SolverError("Right-hand side of 'in' must be a list, tuple, or set literal.")
                    parts.append(z3.Or([left == item for item in right]) if right else z3.BoolVal(False))
                elif isinstance(op_node, ast.NotIn):
                    if not isinstance(right, list):
                        raise SolverError("Right-hand side of 'not in' must be a list, tuple, or set literal.")
                    parts.append(z3.And([left != item for item in right]) if right else z3.BoolVal(True))
                else:
                    op = _CMP_OPS.get(type(op_node))
                    if op is None:
                        raise SolverError(f"unsupported comparison {type(op_node).__name__}")
                    parts.append(op(left, right))
            left = right
        with _catch_z3_errors("chained comparison conjunction"):
            return parts[0] if len(parts) == 1 else z3.And(*parts)

    if isinstance(node, ast.BoolOp):
        values = [_compile(v, env) for v in node.values]
        with _catch_z3_errors(f"boolean operation '{type(node.op).__name__}'"):
            if isinstance(node.op, ast.And):
                return z3.And(*values)
            if isinstance(node.op, ast.Or):
                return z3.Or(*values)
        raise SolverError("unsupported boolean operator")

    raise SolverError(
        f"unsupported expression element {type(node).__name__}. "
        "Constraints may use variables, numbers, sequence literals, math operators, "
        "comparisons, membership (in/not in), conditionals (if/else), and abs/min/max."
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
        
        with _catch_z3_errors(f"constraint {text!r}"):
            compiled.append(_compile(tree, env))

    if all_different:
        missing = [n for n in all_different if n not in env]
        if missing:
            raise SolverError(f"all_different names undeclared variables: {missing}")
        with _catch_z3_errors("all_different constraint"):
            compiled.append(z3.Distinct(*[env[n] for n in all_different]))

    objective = minimize or maximize
    if objective:
        solver = z3.Optimize()
        for c in compiled:
            solver.add(c)
        try:
            tree = ast.parse(objective.strip(), mode="eval")
        except SyntaxError as exc:
            raise SolverError(f"could not parse objective {objective!r}: {exc.msg}") from exc
            
        with _catch_z3_errors(f"objective {objective!r}"):
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
        return Solution("unsat", {}, "no assignment satisfies these constraints -- they conflict")
    return Solution("unknown", {}, "the solver could not decide within its limits")
