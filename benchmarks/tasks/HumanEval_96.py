"""HumanEval task HumanEval_96"""
from pathlib import Path

TASK = """Implement the function 'count_up_to' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def count_up_to(n):
    \"\"\"Implement a function that takes an non-negative integer and returns an array of the first n
    integers that are prime numbers and less than n.
    for example:
    count_up_to(5) => [2,3]
    count_up_to(11) => [2,3,5,7]
    count_up_to(0) => []
    count_up_to(20) => [2,3,5,7,11,13,17,19]
    count_up_to(1) => []
    count_up_to(18) => [2,3,5,7,11,13,17]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef count_up_to(n):\n    """Implement a function that takes an non-negative integer and returns an array of the first n\n    integers that are prime numbers and less than n.\n    for example:\n    count_up_to(5) => [2,3]\n    count_up_to(11) => [2,3,5,7]\n    count_up_to(0) => []\n    count_up_to(20) => [2,3,5,7,11,13,17,19]\n    count_up_to(1) => []\n    count_up_to(18) => [2,3,5,7,11,13,17]\n    """\n',
    "test_solution.py": 'from solution import count_up_to\ndef check(candidate):\n\n    assert candidate(5) == [2,3]\n    assert candidate(6) == [2,3,5]\n    assert candidate(7) == [2,3,5]\n    assert candidate(10) == [2,3,5,7]\n    assert candidate(0) == []\n    assert candidate(22) == [2,3,5,7,11,13,17,19]\n    assert candidate(1) == []\n    assert candidate(18) == [2,3,5,7,11,13,17]\n    assert candidate(47) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43]\n    assert candidate(101) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]\n\n\n\ndef test_candidate():\n    check(count_up_to)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import count_up_to\ndef check(candidate):\n\n    assert candidate(5) == [2,3]\n    assert candidate(6) == [2,3,5]\n    assert candidate(7) == [2,3,5]\n    assert candidate(10) == [2,3,5,7]\n    assert candidate(0) == []\n    assert candidate(22) == [2,3,5,7,11,13,17,19]\n    assert candidate(1) == []\n    assert candidate(18) == [2,3,5,7,11,13,17]\n    assert candidate(47) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43]\n    assert candidate(101) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]\n\n\n\ndef test_candidate():\n    check(count_up_to)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
