"""HumanEval task HumanEval_62"""
from pathlib import Path

TASK = """Implement the function 'derivative' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def derivative(xs: list):
    \"\"\" xs represent coefficients of a polynomial.
    xs[0] + xs[1] * x + xs[2] * x^2 + ....
     Return derivative of this polynomial in the same form.
    >>> derivative([3, 1, 2, 4, 5])
    [1, 4, 12, 20]
    >>> derivative([1, 2, 3])
    [2, 6]
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef derivative(xs: list):\n    """ xs represent coefficients of a polynomial.\n    xs[0] + xs[1] * x + xs[2] * x^2 + ....\n     Return derivative of this polynomial in the same form.\n    >>> derivative([3, 1, 2, 4, 5])\n    [1, 4, 12, 20]\n    >>> derivative([1, 2, 3])\n    [2, 6]\n    """\n',
    "test_solution.py": 'from solution import derivative\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([3, 1, 2, 4, 5]) == [1, 4, 12, 20]\n    assert candidate([1, 2, 3]) == [2, 6]\n    assert candidate([3, 2, 1]) == [2, 2]\n    assert candidate([3, 2, 1, 0, 4]) == [2, 2, 0, 16]\n    assert candidate([1]) == []\n\n\n\ndef test_candidate():\n    check(derivative)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import derivative\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate([3, 1, 2, 4, 5]) == [1, 4, 12, 20]\n    assert candidate([1, 2, 3]) == [2, 6]\n    assert candidate([3, 2, 1]) == [2, 2]\n    assert candidate([3, 2, 1, 0, 4]) == [2, 2, 0, 16]\n    assert candidate([1]) == []\n\n\n\ndef test_candidate():\n    check(derivative)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
