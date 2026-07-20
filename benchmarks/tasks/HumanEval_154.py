"""HumanEval task HumanEval_154"""
from pathlib import Path

TASK = """Implement the function 'cycpattern_check' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def cycpattern_check(a , b):
    \"\"\"You are given 2 words. You need to return True if the second word or any of its rotations is a substring in the first word
    cycpattern_check("abcd","abd") => False
    cycpattern_check("hello","ell") => True
    cycpattern_check("whassup","psus") => False
    cycpattern_check("abab","baa") => True
    cycpattern_check("efef","eeff") => False
    cycpattern_check("himenss","simen") => True

    \"\"\"

"""

FILES = {
    "solution.py": '\ndef cycpattern_check(a , b):\n    """You are given 2 words. You need to return True if the second word or any of its rotations is a substring in the first word\n    cycpattern_check("abcd","abd") => False\n    cycpattern_check("hello","ell") => True\n    cycpattern_check("whassup","psus") => False\n    cycpattern_check("abab","baa") => True\n    cycpattern_check("efef","eeff") => False\n    cycpattern_check("himenss","simen") => True\n\n    """\n',
    "test_solution.py": 'from solution import cycpattern_check\ndef check(candidate):\n\n    # Check some simple cases\n    #assert True, "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    #assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert  candidate("xyzw","xyw") == False , "test #0"\n    assert  candidate("yello","ell") == True , "test #1"\n    assert  candidate("whattup","ptut") == False , "test #2"\n    assert  candidate("efef","fee") == True , "test #3"\n    assert  candidate("abab","aabb") == False , "test #4"\n    assert  candidate("winemtt","tinem") == True , "test #5"\n\n\n\ndef test_candidate():\n    check(cycpattern_check)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import cycpattern_check\ndef check(candidate):\n\n    # Check some simple cases\n    #assert True, "This prints if this assert fails 1 (good for debugging!)"\n\n    # Check some edge cases that are easy to work out by hand.\n    #assert True, "This prints if this assert fails 2 (also good for debugging!)"\n    assert  candidate("xyzw","xyw") == False , "test #0"\n    assert  candidate("yello","ell") == True , "test #1"\n    assert  candidate("whattup","ptut") == False , "test #2"\n    assert  candidate("efef","fee") == True , "test #3"\n    assert  candidate("abab","aabb") == False , "test #4"\n    assert  candidate("winemtt","tinem") == True , "test #5"\n\n\n\ndef test_candidate():\n    check(cycpattern_check)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
