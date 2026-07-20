"""HumanEval task HumanEval_127"""
from pathlib import Path

TASK = """Implement the function 'intersection' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def intersection(interval1, interval2):
    \"\"\"You are given two intervals,
    where each interval is a pair of integers. For example, interval = (start, end) = (1, 2).
    The given intervals are closed which means that the interval (start, end)
    includes both start and end.
    For each given interval, it is assumed that its start is less or equal its end.
    Your task is to determine whether the length of intersection of these two 
    intervals is a prime number.
    Example, the intersection of the intervals (1, 3), (2, 4) is (2, 3)
    which its length is 1, which not a prime number.
    If the length of the intersection is a prime number, return "YES",
    otherwise, return "NO".
    If the two intervals don't intersect, return "NO".


    [input/output] samples:
    intersection((1, 2), (2, 3)) ==> "NO"
    intersection((-1, 1), (0, 4)) ==> "NO"
    intersection((-3, -1), (-5, 5)) ==> "YES"
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef intersection(interval1, interval2):\n    """You are given two intervals,\n    where each interval is a pair of integers. For example, interval = (start, end) = (1, 2).\n    The given intervals are closed which means that the interval (start, end)\n    includes both start and end.\n    For each given interval, it is assumed that its start is less or equal its end.\n    Your task is to determine whether the length of intersection of these two \n    intervals is a prime number.\n    Example, the intersection of the intervals (1, 3), (2, 4) is (2, 3)\n    which its length is 1, which not a prime number.\n    If the length of the intersection is a prime number, return "YES",\n    otherwise, return "NO".\n    If the two intervals don\'t intersect, return "NO".\n\n\n    [input/output] samples:\n    intersection((1, 2), (2, 3)) ==> "NO"\n    intersection((-1, 1), (0, 4)) ==> "NO"\n    intersection((-3, -1), (-5, 5)) ==> "YES"\n    """\n',
    "test_solution.py": 'from solution import intersection\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate((1, 2), (2, 3)) == "NO"\n    assert candidate((-1, 1), (0, 4)) == "NO"\n    assert candidate((-3, -1), (-5, 5)) == "YES"\n    assert candidate((-2, 2), (-4, 0)) == "YES"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate((-11, 2), (-1, -1)) == "NO"\n    assert candidate((1, 2), (3, 5)) == "NO"\n    assert candidate((1, 2), (1, 2)) == "NO"\n    assert candidate((-2, -2), (-3, -2)) == "NO"\n\n\n\ndef test_candidate():\n    check(intersection)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import intersection\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate((1, 2), (2, 3)) == "NO"\n    assert candidate((-1, 1), (0, 4)) == "NO"\n    assert candidate((-3, -1), (-5, 5)) == "YES"\n    assert candidate((-2, 2), (-4, 0)) == "YES"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate((-11, 2), (-1, -1)) == "NO"\n    assert candidate((1, 2), (3, 5)) == "NO"\n    assert candidate((1, 2), (1, 2)) == "NO"\n    assert candidate((-2, -2), (-3, -2)) == "NO"\n\n\n\ndef test_candidate():\n    check(intersection)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
