"""HumanEval task HumanEval_90"""
from pathlib import Path

TASK = """Implement the function 'next_smallest' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def next_smallest(lst):
    \"\"\"
    You are given a list of integers.
    Write a function next_smallest() that returns the 2nd smallest element of the list.
    Return None if there is no such element.
    
    next_smallest([1, 2, 3, 4, 5]) == 2
    next_smallest([5, 1, 4, 3, 2]) == 2
    next_smallest([]) == None
    next_smallest([1, 1]) == None
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef next_smallest(lst):\n    """\n    You are given a list of integers.\n    Write a function next_smallest() that returns the 2nd smallest element of the list.\n    Return None if there is no such element.\n    \n    next_smallest([1, 2, 3, 4, 5]) == 2\n    next_smallest([5, 1, 4, 3, 2]) == 2\n    next_smallest([]) == None\n    next_smallest([1, 1]) == None\n    """\n',
    "test_solution.py": 'from solution import next_smallest\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1, 2, 3, 4, 5]) == 2\n    assert candidate([5, 1, 4, 3, 2]) == 2\n    assert candidate([]) == None\n    assert candidate([1, 1]) == None\n    assert candidate([1,1,1,1,0]) == 1\n    assert candidate([1, 0**0]) == None\n    assert candidate([-35, 34, 12, -45]) == -35\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(next_smallest)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import next_smallest\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1, 2, 3, 4, 5]) == 2\n    assert candidate([5, 1, 4, 3, 2]) == 2\n    assert candidate([]) == None\n    assert candidate([1, 1]) == None\n    assert candidate([1,1,1,1,0]) == 1\n    assert candidate([1, 0**0]) == None\n    assert candidate([-35, 34, 12, -45]) == -35\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(next_smallest)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
