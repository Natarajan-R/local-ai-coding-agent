"""HumanEval task HumanEval_32"""
from pathlib import Path

TASK = """Implement the function 'find_zero' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
import math


def poly(xs: list, x: float):
    \"\"\"
    Evaluates polynomial with coefficients xs at point x.
    return xs[0] + xs[1] * x + xs[1] * x^2 + .... xs[n] * x^n
    \"\"\"
    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])


def find_zero(xs: list):
    \"\"\" xs are coefficients of a polynomial.
    find_zero find x such that poly(x) = 0.
    find_zero returns only only zero point, even if there are many.
    Moreover, find_zero only takes list xs having even number of coefficients
    and largest non zero coefficient as it guarantees
    a solution.
    >>> round(find_zero([1, 2]), 2) # f(x) = 1 + 2x
    -0.5
    >>> round(find_zero([-6, 11, -6, 1]), 2) # (x - 1) * (x - 2) * (x - 3) = -6 + 11x - 6x^2 + x^3
    1.0
    \"\"\"

"""

FILES = {
    "solution.py": 'import math\n\n\ndef poly(xs: list, x: float):\n    """\n    Evaluates polynomial with coefficients xs at point x.\n    return xs[0] + xs[1] * x + xs[1] * x^2 + .... xs[n] * x^n\n    """\n    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])\n\n\ndef find_zero(xs: list):\n    """ xs are coefficients of a polynomial.\n    find_zero find x such that poly(x) = 0.\n    find_zero returns only only zero point, even if there are many.\n    Moreover, find_zero only takes list xs having even number of coefficients\n    and largest non zero coefficient as it guarantees\n    a solution.\n    >>> round(find_zero([1, 2]), 2) # f(x) = 1 + 2x\n    -0.5\n    >>> round(find_zero([-6, 11, -6, 1]), 2) # (x - 1) * (x - 2) * (x - 3) = -6 + 11x - 6x^2 + x^3\n    1.0\n    """\n',
    "test_solution.py": 'from solution import find_zero\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    import math\n    import random\n    rng = random.Random(42)\n    import copy\n    for _ in range(100):\n        ncoeff = 2 * rng.randint(1, 4)\n        coeffs = []\n        for _ in range(ncoeff):\n            coeff = rng.randint(-10, 10)\n            if coeff == 0:\n                coeff = 1\n            coeffs.append(coeff)\n        solution = candidate(copy.deepcopy(coeffs))\n        assert math.fabs(poly(coeffs, solution)) < 1e-4\n\n\n\ndef test_candidate():\n    check(find_zero)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import find_zero\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    import math\n    import random\n    rng = random.Random(42)\n    import copy\n    for _ in range(100):\n        ncoeff = 2 * rng.randint(1, 4)\n        coeffs = []\n        for _ in range(ncoeff):\n            coeff = rng.randint(-10, 10)\n            if coeff == 0:\n                coeff = 1\n            coeffs.append(coeff)\n        solution = candidate(copy.deepcopy(coeffs))\n        assert math.fabs(poly(coeffs, solution)) < 1e-4\n\n\n\ndef test_candidate():\n    check(find_zero)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
