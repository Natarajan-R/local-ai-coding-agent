"""HumanEval task HumanEval_115"""
from pathlib import Path

TASK = """Implement the function 'max_fill' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def max_fill(grid, capacity):
    import math
    \"\"\"
    You are given a rectangular grid of wells. Each row represents a single well,
    and each 1 in a row represents a single unit of water.
    Each well has a corresponding bucket that can be used to extract water from it, 
    and all buckets have the same capacity.
    Your task is to use the buckets to empty the wells.
    Output the number of times you need to lower the buckets.

    Example 1:
        Input: 
            grid : [[0,0,1,0], [0,1,0,0], [1,1,1,1]]
            bucket_capacity : 1
        Output: 6

    Example 2:
        Input: 
            grid : [[0,0,1,1], [0,0,0,0], [1,1,1,1], [0,1,1,1]]
            bucket_capacity : 2
        Output: 5
    
    Example 3:
        Input: 
            grid : [[0,0,0], [0,0,0]]
            bucket_capacity : 5
        Output: 0

    Constraints:
        * all wells have the same length
        * 1 <= grid.length <= 10^2
        * 1 <= grid[:,1].length <= 10^2
        * grid[i][j] -> 0 | 1
        * 1 <= capacity <= 10
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef max_fill(grid, capacity):\n    import math\n    """\n    You are given a rectangular grid of wells. Each row represents a single well,\n    and each 1 in a row represents a single unit of water.\n    Each well has a corresponding bucket that can be used to extract water from it, \n    and all buckets have the same capacity.\n    Your task is to use the buckets to empty the wells.\n    Output the number of times you need to lower the buckets.\n\n    Example 1:\n        Input: \n            grid : [[0,0,1,0], [0,1,0,0], [1,1,1,1]]\n            bucket_capacity : 1\n        Output: 6\n\n    Example 2:\n        Input: \n            grid : [[0,0,1,1], [0,0,0,0], [1,1,1,1], [0,1,1,1]]\n            bucket_capacity : 2\n        Output: 5\n    \n    Example 3:\n        Input: \n            grid : [[0,0,0], [0,0,0]]\n            bucket_capacity : 5\n        Output: 0\n\n    Constraints:\n        * all wells have the same length\n        * 1 <= grid.length <= 10^2\n        * 1 <= grid[:,1].length <= 10^2\n        * grid[i][j] -> 0 | 1\n        * 1 <= capacity <= 10\n    """\n',
    "test_solution.py": 'from solution import max_fill\ndef check(candidate):\n\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([[0,0,1,0], [0,1,0,0], [1,1,1,1]], 1) == 6, "Error"\n    assert candidate([[0,0,1,1], [0,0,0,0], [1,1,1,1], [0,1,1,1]], 2) == 5, "Error"\n    assert candidate([[0,0,0], [0,0,0]], 5) == 0, "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([[1,1,1,1], [1,1,1,1]], 2) == 4, "Error"\n    assert candidate([[1,1,1,1], [1,1,1,1]], 9) == 2, "Error"\n\n\n\ndef test_candidate():\n    check(max_fill)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import max_fill\ndef check(candidate):\n\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([[0,0,1,0], [0,1,0,0], [1,1,1,1]], 1) == 6, "Error"\n    assert candidate([[0,0,1,1], [0,0,0,0], [1,1,1,1], [0,1,1,1]], 2) == 5, "Error"\n    assert candidate([[0,0,0], [0,0,0]], 5) == 0, "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate([[1,1,1,1], [1,1,1,1]], 2) == 4, "Error"\n    assert candidate([[1,1,1,1], [1,1,1,1]], 9) == 2, "Error"\n\n\n\ndef test_candidate():\n    check(max_fill)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
