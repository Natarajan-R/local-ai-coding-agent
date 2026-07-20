"""HumanEval task HumanEval_109"""
from pathlib import Path

TASK = """Implement the function 'move_one_ball' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def move_one_ball(arr):
    \"\"\"We have an array 'arr' of N integers arr[1], arr[2], ..., arr[N].The
    numbers in the array will be randomly ordered. Your task is to determine if
    it is possible to get an array sorted in non-decreasing order by performing 
    the following operation on the given array:
        You are allowed to perform right shift operation any number of times.
    
    One right shift operation means shifting all elements of the array by one
    position in the right direction. The last element of the array will be moved to
    the starting position in the array i.e. 0th index. 

    If it is possible to obtain the sorted array by performing the above operation
    then return True else return False.
    If the given array is empty then return True.

    Note: The given list is guaranteed to have unique elements.

    For Example:
    
    move_one_ball([3, 4, 5, 1, 2])==>True
    Explanation: By performin 2 right shift operations, non-decreasing order can
                 be achieved for the given array.
    move_one_ball([3, 5, 4, 1, 2])==>False
    Explanation:It is not possible to get non-decreasing order for the given
                array by performing any number of right shift operations.
                
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef move_one_ball(arr):\n    """We have an array \'arr\' of N integers arr[1], arr[2], ..., arr[N].The\n    numbers in the array will be randomly ordered. Your task is to determine if\n    it is possible to get an array sorted in non-decreasing order by performing \n    the following operation on the given array:\n        You are allowed to perform right shift operation any number of times.\n    \n    One right shift operation means shifting all elements of the array by one\n    position in the right direction. The last element of the array will be moved to\n    the starting position in the array i.e. 0th index. \n\n    If it is possible to obtain the sorted array by performing the above operation\n    then return True else return False.\n    If the given array is empty then return True.\n\n    Note: The given list is guaranteed to have unique elements.\n\n    For Example:\n    \n    move_one_ball([3, 4, 5, 1, 2])==>True\n    Explanation: By performin 2 right shift operations, non-decreasing order can\n                 be achieved for the given array.\n    move_one_ball([3, 5, 4, 1, 2])==>False\n    Explanation:It is not possible to get non-decreasing order for the given\n                array by performing any number of right shift operations.\n                \n    """\n',
    "test_solution.py": 'from solution import move_one_ball\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([3, 4, 5, 1, 2])==True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([3, 5, 10, 1, 2])==True\n    assert candidate([4, 3, 1, 2])==False\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([3, 5, 4, 1, 2])==False, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([])==True\n\n\ndef test_candidate():\n    check(move_one_ball)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import move_one_ball\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([3, 4, 5, 1, 2])==True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([3, 5, 10, 1, 2])==True\n    assert candidate([4, 3, 1, 2])==False\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate([3, 5, 4, 1, 2])==False, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([])==True\n\n\ndef test_candidate():\n    check(move_one_ball)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
