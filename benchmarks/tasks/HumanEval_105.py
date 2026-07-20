"""HumanEval task HumanEval_105"""
from pathlib import Path

TASK = """Implement the function 'by_length' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def by_length(arr):
    \"\"\"
    Given an array of integers, sort the integers that are between 1 and 9 inclusive,
    reverse the resulting array, and then replace each digit by its corresponding name from
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine".

    For example:
      arr = [2, 1, 1, 4, 5, 8, 2, 3]   
            -> sort arr -> [1, 1, 2, 2, 3, 4, 5, 8] 
            -> reverse arr -> [8, 5, 4, 3, 2, 2, 1, 1]
      return ["Eight", "Five", "Four", "Three", "Two", "Two", "One", "One"]
    
      If the array is empty, return an empty array:
      arr = []
      return []
    
      If the array has any strange number ignore it:
      arr = [1, -1 , 55] 
            -> sort arr -> [-1, 1, 55]
            -> reverse arr -> [55, 1, -1]
      return = ['One']
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef by_length(arr):\n    """\n    Given an array of integers, sort the integers that are between 1 and 9 inclusive,\n    reverse the resulting array, and then replace each digit by its corresponding name from\n    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine".\n\n    For example:\n      arr = [2, 1, 1, 4, 5, 8, 2, 3]   \n            -> sort arr -> [1, 1, 2, 2, 3, 4, 5, 8] \n            -> reverse arr -> [8, 5, 4, 3, 2, 2, 1, 1]\n      return ["Eight", "Five", "Four", "Three", "Two", "Two", "One", "One"]\n    \n      If the array is empty, return an empty array:\n      arr = []\n      return []\n    \n      If the array has any strange number ignore it:\n      arr = [1, -1 , 55] \n            -> sort arr -> [-1, 1, 55]\n            -> reverse arr -> [55, 1, -1]\n      return = [\'One\']\n    """\n',
    "test_solution.py": 'from solution import by_length\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([2, 1, 1, 4, 5, 8, 2, 3]) == ["Eight", "Five", "Four", "Three", "Two", "Two", "One", "One"], "Error"\n    assert candidate([]) == [], "Error"\n    assert candidate([1, -1 , 55]) == [\'One\'], "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([1, -1, 3, 2]) == ["Three", "Two", "One"]\n    assert candidate([9, 4, 8]) == ["Nine", "Eight", "Four"]\n\n\n\ndef test_candidate():\n    check(by_length)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import by_length\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([2, 1, 1, 4, 5, 8, 2, 3]) == ["Eight", "Five", "Four", "Three", "Two", "Two", "One", "One"], "Error"\n    assert candidate([]) == [], "Error"\n    assert candidate([1, -1 , 55]) == [\'One\'], "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([1, -1, 3, 2]) == ["Three", "Two", "One"]\n    assert candidate([9, 4, 8]) == ["Nine", "Eight", "Four"]\n\n\n\ndef test_candidate():\n    check(by_length)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
