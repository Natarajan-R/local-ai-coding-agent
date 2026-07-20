"""HumanEval task HumanEval_53"""
from pathlib import Path

TASK = """Implement the function 'add' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def add(x: int, y: int):
    \"\"\"Add two numbers x and y
    >>> add(2, 3)
    5
    >>> add(5, 7)
    12
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef add(x: int, y: int):\n    """Add two numbers x and y\n    >>> add(2, 3)\n    5\n    >>> add(5, 7)\n    12\n    """\n',
    "test_solution.py": 'from solution import add\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    import random\n\n    assert candidate(0, 1) == 1\n    assert candidate(1, 0) == 1\n    assert candidate(2, 3) == 5\n    assert candidate(5, 7) == 12\n    assert candidate(7, 5) == 12\n\n    for i in range(100):\n        x, y = random.randint(0, 1000), random.randint(0, 1000)\n        assert candidate(x, y) == x + y\n\n\n\ndef test_candidate():\n    check(add)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import add\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    import random\n\n    assert candidate(0, 1) == 1\n    assert candidate(1, 0) == 1\n    assert candidate(2, 3) == 5\n    assert candidate(5, 7) == 12\n    assert candidate(7, 5) == 12\n\n    for i in range(100):\n        x, y = random.randint(0, 1000), random.randint(0, 1000)\n        assert candidate(x, y) == x + y\n\n\n\ndef test_candidate():\n    check(add)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
