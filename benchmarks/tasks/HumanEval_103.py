"""HumanEval task HumanEval_103"""
from pathlib import Path

TASK = """Implement the function 'rounded_avg' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def rounded_avg(n, m):
    \"\"\"You are given two positive integers n and m, and your task is to compute the
    average of the integers from n through m (including n and m). 
    Round the answer to the nearest integer and convert that to binary.
    If n is greater than m, return -1.
    Example:
    rounded_avg(1, 5) => "0b11"
    rounded_avg(7, 5) => -1
    rounded_avg(10, 20) => "0b1111"
    rounded_avg(20, 33) => "0b11010"
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef rounded_avg(n, m):\n    """You are given two positive integers n and m, and your task is to compute the\n    average of the integers from n through m (including n and m). \n    Round the answer to the nearest integer and convert that to binary.\n    If n is greater than m, return -1.\n    Example:\n    rounded_avg(1, 5) => "0b11"\n    rounded_avg(7, 5) => -1\n    rounded_avg(10, 20) => "0b1111"\n    rounded_avg(20, 33) => "0b11010"\n    """\n',
    "test_solution.py": 'from solution import rounded_avg\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(1, 5) == "0b11"\n    assert candidate(7, 13) == "0b1010"\n    assert candidate(964,977) == "0b1111001010"\n    assert candidate(996,997) == "0b1111100100"\n    assert candidate(560,851) == "0b1011000010"\n    assert candidate(185,546) == "0b101101110"\n    assert candidate(362,496) == "0b110101101"\n    assert candidate(350,902) == "0b1001110010"\n    assert candidate(197,233) == "0b11010111"\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(7, 5) == -1\n    assert candidate(5, 1) == -1\n    assert candidate(5, 5) == "0b101"\n\n\n\ndef test_candidate():\n    check(rounded_avg)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import rounded_avg\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate(1, 5) == "0b11"\n    assert candidate(7, 13) == "0b1010"\n    assert candidate(964,977) == "0b1111001010"\n    assert candidate(996,997) == "0b1111100100"\n    assert candidate(560,851) == "0b1011000010"\n    assert candidate(185,546) == "0b101101110"\n    assert candidate(362,496) == "0b110101101"\n    assert candidate(350,902) == "0b1001110010"\n    assert candidate(197,233) == "0b11010111"\n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(7, 5) == -1\n    assert candidate(5, 1) == -1\n    assert candidate(5, 5) == "0b101"\n\n\n\ndef test_candidate():\n    check(rounded_avg)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
