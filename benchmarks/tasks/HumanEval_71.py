"""HumanEval task HumanEval_71"""
from pathlib import Path

TASK = """Implement the function 'triangle_area' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def triangle_area(a, b, c):
    '''
    Given the lengths of the three sides of a triangle. Return the area of
    the triangle rounded to 2 decimal points if the three sides form a valid triangle. 
    Otherwise return -1
    Three sides make a valid triangle when the sum of any two sides is greater 
    than the third side.
    Example:
    triangle_area(3, 4, 5) == 6.00
    triangle_area(1, 2, 10) == -1
    '''

"""

FILES = {
    "solution.py": "\ndef triangle_area(a, b, c):\n    '''\n    Given the lengths of the three sides of a triangle. Return the area of\n    the triangle rounded to 2 decimal points if the three sides form a valid triangle. \n    Otherwise return -1\n    Three sides make a valid triangle when the sum of any two sides is greater \n    than the third side.\n    Example:\n    triangle_area(3, 4, 5) == 6.00\n    triangle_area(1, 2, 10) == -1\n    '''\n",
    "test_solution.py": 'from solution import triangle_area\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(3, 4, 5) == 6.00, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(1, 2, 10) == -1\n    assert candidate(4, 8, 5) == 8.18\n    assert candidate(2, 2, 2) == 1.73\n    assert candidate(1, 2, 3) == -1\n    assert candidate(10, 5, 7) == 16.25\n    assert candidate(2, 6, 3) == -1\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1, 1, 1) == 0.43, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(2, 2, 10) == -1\n\n\n\ndef test_candidate():\n    check(triangle_area)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import triangle_area\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(3, 4, 5) == 6.00, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(1, 2, 10) == -1\n    assert candidate(4, 8, 5) == 8.18\n    assert candidate(2, 2, 2) == 1.73\n    assert candidate(1, 2, 3) == -1\n    assert candidate(10, 5, 7) == 16.25\n    assert candidate(2, 6, 3) == -1\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(1, 1, 1) == 0.43, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(2, 2, 10) == -1\n\n\n\ndef test_candidate():\n    check(triangle_area)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
