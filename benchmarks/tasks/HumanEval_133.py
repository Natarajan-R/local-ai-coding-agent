"""HumanEval task HumanEval_133"""
from pathlib import Path

TASK = """Implement the function 'sum_squares' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def sum_squares(lst):
    \"\"\"You are given a list of numbers.
    You need to return the sum of squared numbers in the given list,
    round each element in the list to the upper int(Ceiling) first.
    Examples:
    For lst = [1,2,3] the output should be 14
    For lst = [1,4,9] the output should be 98
    For lst = [1,3,5,7] the output should be 84
    For lst = [1.4,4.2,0] the output should be 29
    For lst = [-2.4,1,1] the output should be 6
    

    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef sum_squares(lst):\n    """You are given a list of numbers.\n    You need to return the sum of squared numbers in the given list,\n    round each element in the list to the upper int(Ceiling) first.\n    Examples:\n    For lst = [1,2,3] the output should be 14\n    For lst = [1,4,9] the output should be 98\n    For lst = [1,3,5,7] the output should be 84\n    For lst = [1.4,4.2,0] the output should be 29\n    For lst = [-2.4,1,1] the output should be 6\n    \n\n    """\n',
    "test_solution.py": 'from solution import sum_squares\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,2,3])==14, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1.0,2,3])==14, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1,3,5,7])==84, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1.4,4.2,0])==29, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([-2.4,1,1])==6, "This prints if this assert fails 1 (good for debugging!)"\n\n    assert candidate([100,1,15,2])==10230, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([10000,10000])==200000000, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([-1.4,4.6,6.3])==75, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([-1.4,17.9,18.9,19.9])==1086, "This prints if this assert fails 1 (good for debugging!)"\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([0])==0, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([-1])==1, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([-1,1,0])==2, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(sum_squares)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import sum_squares\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,2,3])==14, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1.0,2,3])==14, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1,3,5,7])==84, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1.4,4.2,0])==29, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([-2.4,1,1])==6, "This prints if this assert fails 1 (good for debugging!)"\n\n    assert candidate([100,1,15,2])==10230, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([10000,10000])==200000000, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([-1.4,4.6,6.3])==75, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([-1.4,17.9,18.9,19.9])==1086, "This prints if this assert fails 1 (good for debugging!)"\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([0])==0, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([-1])==1, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([-1,1,0])==2, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(sum_squares)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
