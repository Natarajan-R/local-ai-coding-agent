"""HumanEval task HumanEval_152"""
from pathlib import Path

TASK = """Implement the function 'compare' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def compare(game,guess):
    \"\"\"I think we all remember that feeling when the result of some long-awaited
    event is finally known. The feelings and thoughts you have at that moment are
    definitely worth noting down and comparing.
    Your task is to determine if a person correctly guessed the results of a number of matches.
    You are given two arrays of scores and guesses of equal length, where each index shows a match. 
    Return an array of the same length denoting how far off each guess was. If they have guessed correctly,
    the value is 0, and if not, the value is the absolute difference between the guess and the score.
    
    
    example:

    compare([1,2,3,4,5,1],[1,2,3,4,2,-2]) -> [0,0,0,0,3,3]
    compare([0,5,0,0,0,4],[4,1,1,0,0,-2]) -> [4,4,1,0,0,6]
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef compare(game,guess):\n    """I think we all remember that feeling when the result of some long-awaited\n    event is finally known. The feelings and thoughts you have at that moment are\n    definitely worth noting down and comparing.\n    Your task is to determine if a person correctly guessed the results of a number of matches.\n    You are given two arrays of scores and guesses of equal length, where each index shows a match. \n    Return an array of the same length denoting how far off each guess was. If they have guessed correctly,\n    the value is 0, and if not, the value is the absolute difference between the guess and the score.\n    \n    \n    example:\n\n    compare([1,2,3,4,5,1],[1,2,3,4,2,-2]) -> [0,0,0,0,3,3]\n    compare([0,5,0,0,0,4],[4,1,1,0,0,-2]) -> [4,4,1,0,0,6]\n    """\n',
    "test_solution.py": 'from solution import compare\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,2,3,4,5,1],[1,2,3,4,2,-2])==[0,0,0,0,3,3], "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([0,0,0,0,0,0],[0,0,0,0,0,0])==[0,0,0,0,0,0], "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1,2,3],[-1,-2,-3])==[2,4,6], "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1,2,3,5],[-1,2,3,4])==[2,0,0,1], "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(compare)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import compare\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate([1,2,3,4,5,1],[1,2,3,4,2,-2])==[0,0,0,0,3,3], "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([0,0,0,0,0,0],[0,0,0,0,0,0])==[0,0,0,0,0,0], "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1,2,3],[-1,-2,-3])==[2,4,6], "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate([1,2,3,5],[-1,2,3,4])==[2,0,0,1], "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True, "This prints if this assert fails 2 (also good for debugging!)"\n\n\n\ndef test_candidate():\n    check(compare)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
