"""HumanEval task HumanEval_41"""
from pathlib import Path

TASK = """Implement the function 'car_race_collision' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def car_race_collision(n: int):
    \"\"\"
    Imagine a road that's a perfectly straight infinitely long line.
    n cars are driving left to right;  simultaneously, a different set of n cars
    are driving right to left.   The two sets of cars start out being very far from
    each other.  All cars move in the same speed.  Two cars are said to collide
    when a car that's moving left to right hits a car that's moving right to left.
    However, the cars are infinitely sturdy and strong; as a result, they continue moving
    in their trajectory as if they did not collide.

    This function outputs the number of such collisions.
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef car_race_collision(n: int):\n    """\n    Imagine a road that\'s a perfectly straight infinitely long line.\n    n cars are driving left to right;  simultaneously, a different set of n cars\n    are driving right to left.   The two sets of cars start out being very far from\n    each other.  All cars move in the same speed.  Two cars are said to collide\n    when a car that\'s moving left to right hits a car that\'s moving right to left.\n    However, the cars are infinitely sturdy and strong; as a result, they continue moving\n    in their trajectory as if they did not collide.\n\n    This function outputs the number of such collisions.\n    """\n',
    "test_solution.py": 'from solution import car_race_collision\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(2) == 4\n    assert candidate(3) == 9\n    assert candidate(4) == 16\n    assert candidate(8) == 64\n    assert candidate(10) == 100\n\n\n\ndef test_candidate():\n    check(car_race_collision)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import car_race_collision\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate(2) == 4\n    assert candidate(3) == 9\n    assert candidate(4) == 16\n    assert candidate(8) == 64\n    assert candidate(10) == 100\n\n\n\ndef test_candidate():\n    check(car_race_collision)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
