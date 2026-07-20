"""HumanEval task HumanEval_88"""
from pathlib import Path

TASK = """Implement the function 'sort_array' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def sort_array(array):
    \"\"\"
    Given an array of non-negative integers, return a copy of the given array after sorting,
    you will sort the given array in ascending order if the sum( first index value, last index value) is odd,
    or sort it in descending order if the sum( first index value, last index value) is even.

    Note:
    * don't change the given array.

    Examples:
    * sort_array([]) => []
    * sort_array([5]) => [5]
    * sort_array([2, 4, 3, 0, 1, 5]) => [0, 1, 2, 3, 4, 5]
    * sort_array([2, 4, 3, 0, 1, 5, 6]) => [6, 5, 4, 3, 2, 1, 0]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef sort_array(array):\n    """\n    Given an array of non-negative integers, return a copy of the given array after sorting,\n    you will sort the given array in ascending order if the sum( first index value, last index value) is odd,\n    or sort it in descending order if the sum( first index value, last index value) is even.\n\n    Note:\n    * don\'t change the given array.\n\n    Examples:\n    * sort_array([]) => []\n    * sort_array([5]) => [5]\n    * sort_array([2, 4, 3, 0, 1, 5]) => [0, 1, 2, 3, 4, 5]\n    * sort_array([2, 4, 3, 0, 1, 5, 6]) => [6, 5, 4, 3, 2, 1, 0]\n    """\n',
    "test_solution.py": 'from solution import sort_array\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([]) == [], "Error"\n    assert candidate([5]) == [5], "Error"\n    assert candidate([2, 4, 3, 0, 1, 5]) == [0, 1, 2, 3, 4, 5], "Error"\n    assert candidate([2, 4, 3, 0, 1, 5, 6]) == [6, 5, 4, 3, 2, 1, 0], "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([2, 1]) == [1, 2], "Error"\n    assert candidate([15, 42, 87, 32 ,11, 0]) == [0, 11, 15, 32, 42, 87], "Error"\n    assert candidate([21, 14, 23, 11]) == [23, 21, 14, 11], "Error"\n\n\n\ndef test_candidate():\n    check(sort_array)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import sort_array\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([]) == [], "Error"\n    assert candidate([5]) == [5], "Error"\n    assert candidate([2, 4, 3, 0, 1, 5]) == [0, 1, 2, 3, 4, 5], "Error"\n    assert candidate([2, 4, 3, 0, 1, 5, 6]) == [6, 5, 4, 3, 2, 1, 0], "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([2, 1]) == [1, 2], "Error"\n    assert candidate([15, 42, 87, 32 ,11, 0]) == [0, 11, 15, 32, 42, 87], "Error"\n    assert candidate([21, 14, 23, 11]) == [23, 21, 14, 11], "Error"\n\n\n\ndef test_candidate():\n    check(sort_array)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
