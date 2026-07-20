"""HumanEval task HumanEval_159"""
from pathlib import Path

TASK = """Implement the function 'eat' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def eat(number, need, remaining):
    \"\"\"
    You're a hungry rabbit, and you already have eaten a certain number of carrots,
    but now you need to eat more carrots to complete the day's meals.
    you should return an array of [ total number of eaten carrots after your meals,
                                    the number of carrots left after your meals ]
    if there are not enough remaining carrots, you will eat all remaining carrots, but will still be hungry.
    
    Example:
    * eat(5, 6, 10) -> [11, 4]
    * eat(4, 8, 9) -> [12, 1]
    * eat(1, 10, 10) -> [11, 0]
    * eat(2, 11, 5) -> [7, 0]
    
    Variables:
    @number : integer
        the number of carrots that you have eaten.
    @need : integer
        the number of carrots that you need to eat.
    @remaining : integer
        the number of remaining carrots thet exist in stock
    
    Constrain:
    * 0 <= number <= 1000
    * 0 <= need <= 1000
    * 0 <= remaining <= 1000

    Have fun :)
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef eat(number, need, remaining):\n    """\n    You\'re a hungry rabbit, and you already have eaten a certain number of carrots,\n    but now you need to eat more carrots to complete the day\'s meals.\n    you should return an array of [ total number of eaten carrots after your meals,\n                                    the number of carrots left after your meals ]\n    if there are not enough remaining carrots, you will eat all remaining carrots, but will still be hungry.\n    \n    Example:\n    * eat(5, 6, 10) -> [11, 4]\n    * eat(4, 8, 9) -> [12, 1]\n    * eat(1, 10, 10) -> [11, 0]\n    * eat(2, 11, 5) -> [7, 0]\n    \n    Variables:\n    @number : integer\n        the number of carrots that you have eaten.\n    @need : integer\n        the number of carrots that you need to eat.\n    @remaining : integer\n        the number of remaining carrots thet exist in stock\n    \n    Constrain:\n    * 0 <= number <= 1000\n    * 0 <= need <= 1000\n    * 0 <= remaining <= 1000\n\n    Have fun :)\n    """\n',
    "test_solution.py": 'from solution import eat\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(5, 6, 10) == [11, 4], "Error"\n    assert candidate(4, 8, 9) == [12, 1], "Error"\n    assert candidate(1, 10, 10) == [11, 0], "Error"\n    assert candidate(2, 11, 5) == [7, 0], "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(4, 5, 7) == [9, 2], "Error"\n    assert candidate(4, 5, 1) == [5, 0], "Error"\n\n\n\ndef test_candidate():\n    check(eat)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import eat\ndef check(candidate):\n\n    # Check some simple cases\n    assert True, "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate(5, 6, 10) == [11, 4], "Error"\n    assert candidate(4, 8, 9) == [12, 1], "Error"\n    assert candidate(1, 10, 10) == [11, 0], "Error"\n    assert candidate(2, 11, 5) == [7, 0], "Error"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert candidate(4, 5, 7) == [9, 2], "Error"\n    assert candidate(4, 5, 1) == [5, 0], "Error"\n\n\n\ndef test_candidate():\n    check(eat)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
