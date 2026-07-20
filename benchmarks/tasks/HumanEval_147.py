"""HumanEval task HumanEval_147"""
from pathlib import Path

TASK = """Implement the function 'get_max_triples' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def get_max_triples(n):
    \"\"\"
    You are given a positive integer n. You have to create an integer array a of length n.
        For each i (1 ≤ i ≤ n), the value of a[i] = i * i - i + 1.
        Return the number of triples (a[i], a[j], a[k]) of a where i < j < k, 
    and a[i] + a[j] + a[k] is a multiple of 3.

    Example :
        Input: n = 5
        Output: 1
        Explanation: 
        a = [1, 3, 7, 13, 21]
        The only valid triple is (1, 7, 13).
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef get_max_triples(n):\n    """\n    You are given a positive integer n. You have to create an integer array a of length n.\n        For each i (1 ≤ i ≤ n), the value of a[i] = i * i - i + 1.\n        Return the number of triples (a[i], a[j], a[k]) of a where i < j < k, \n    and a[i] + a[j] + a[k] is a multiple of 3.\n\n    Example :\n        Input: n = 5\n        Output: 1\n        Explanation: \n        a = [1, 3, 7, 13, 21]\n        The only valid triple is (1, 7, 13).\n    """\n',
    "test_solution.py": 'from solution import get_max_triples\ndef check(candidate):\n\n    assert candidate(5) == 1\n    assert candidate(6) == 4\n    assert candidate(10) == 36\n    assert candidate(100) == 53361\n\n\ndef test_candidate():\n    check(get_max_triples)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import get_max_triples\ndef check(candidate):\n\n    assert candidate(5) == 1\n    assert candidate(6) == 4\n    assert candidate(10) == 36\n    assert candidate(100) == 53361\n\n\ndef test_candidate():\n    check(get_max_triples)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
