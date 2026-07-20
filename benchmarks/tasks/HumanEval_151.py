"""HumanEval task HumanEval_151"""
from pathlib import Path

TASK = """Implement the function 'double_the_difference' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def double_the_difference(lst):
    '''
    Given a list of numbers, return the sum of squares of the numbers
    in the list that are odd. Ignore numbers that are negative or not integers.
    
    double_the_difference([1, 3, 2, 0]) == 1 + 9 + 0 + 0 = 10
    double_the_difference([-1, -2, 0]) == 0
    double_the_difference([9, -2]) == 81
    double_the_difference([0]) == 0  
   
    If the input list is empty, return 0.
    '''

"""

FILES = {
    "solution.py": "\ndef double_the_difference(lst):\n    '''\n    Given a list of numbers, return the sum of squares of the numbers\n    in the list that are odd. Ignore numbers that are negative or not integers.\n    \n    double_the_difference([1, 3, 2, 0]) == 1 + 9 + 0 + 0 = 10\n    double_the_difference([-1, -2, 0]) == 0\n    double_the_difference([9, -2]) == 81\n    double_the_difference([0]) == 0  \n   \n    If the input list is empty, return 0.\n    '''\n",
    "test_solution.py": 'from solution import double_the_difference\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([]) == 0 , "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([5, 4]) == 25 , "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate([0.1, 0.2, 0.3]) == 0 , "This prints if this assert fails 3 (good for debugging!)"\n    assert candidate([-10, -20, -30]) == 0 , "This prints if this assert fails 4 (good for debugging!)"\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([-1, -2, 8]) == 0, "This prints if this assert fails 5 (also good for debugging!)"\n    assert candidate([0.2, 3, 5]) == 34, "This prints if this assert fails 6 (also good for debugging!)"\n    lst = list(range(-99, 100, 2))\n    odd_sum = sum([i**2 for i in lst if i%2!=0 and i > 0])\n    assert candidate(lst) == odd_sum , "This prints if this assert fails 7 (good for debugging!)"\n\n\n\ndef test_candidate():\n    check(double_the_difference)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import double_the_difference\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([]) == 0 , "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([5, 4]) == 25 , "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate([0.1, 0.2, 0.3]) == 0 , "This prints if this assert fails 3 (good for debugging!)"\n    assert candidate([-10, -20, -30]) == 0 , "This prints if this assert fails 4 (good for debugging!)"\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([-1, -2, 8]) == 0, "This prints if this assert fails 5 (also good for debugging!)"\n    assert candidate([0.2, 3, 5]) == 34, "This prints if this assert fails 6 (also good for debugging!)"\n    lst = list(range(-99, 100, 2))\n    odd_sum = sum([i**2 for i in lst if i%2!=0 and i > 0])\n    assert candidate(lst) == odd_sum , "This prints if this assert fails 7 (good for debugging!)"\n\n\n\ndef test_candidate():\n    check(double_the_difference)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
