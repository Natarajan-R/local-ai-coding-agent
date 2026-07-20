"""HumanEval task HumanEval_140"""
from pathlib import Path

TASK = """Implement the function 'fix_spaces' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def fix_spaces(text):
    \"\"\"
    Given a string text, replace all spaces in it with underscores, 
    and if a string has more than 2 consecutive spaces, 
    then replace all consecutive spaces with - 
    
    fix_spaces("Example") == "Example"
    fix_spaces("Example 1") == "Example_1"
    fix_spaces(" Example 2") == "_Example_2"
    fix_spaces(" Example   3") == "_Example-3"
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef fix_spaces(text):\n    """\n    Given a string text, replace all spaces in it with underscores, \n    and if a string has more than 2 consecutive spaces, \n    then replace all consecutive spaces with - \n    \n    fix_spaces("Example") == "Example"\n    fix_spaces("Example 1") == "Example_1"\n    fix_spaces(" Example 2") == "_Example_2"\n    fix_spaces(" Example   3") == "_Example-3"\n    """\n',
    "test_solution.py": 'from solution import fix_spaces\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("Example") == "Example", "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate("Mudasir Hanif ") == "Mudasir_Hanif_", "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate("Yellow Yellow  Dirty  Fellow") == "Yellow_Yellow__Dirty__Fellow", "This prints if this assert fails 3 (good for debugging!)"\n    \n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("Exa   mple") == "Exa-mple", "This prints if this assert fails 4 (good for debugging!)"\n    assert candidate("   Exa 1 2 2 mple") == "-Exa_1_2_2_mple", "This prints if this assert fails 4 (good for debugging!)"\n\n\n\ndef test_candidate():\n    check(fix_spaces)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import fix_spaces\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("Example") == "Example", "This prints if this assert fails 1 (good for debugging!)"\n    assert candidate("Mudasir Hanif ") == "Mudasir_Hanif_", "This prints if this assert fails 2 (good for debugging!)"\n    assert candidate("Yellow Yellow  Dirty  Fellow") == "Yellow_Yellow__Dirty__Fellow", "This prints if this assert fails 3 (good for debugging!)"\n    \n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("Exa   mple") == "Exa-mple", "This prints if this assert fails 4 (good for debugging!)"\n    assert candidate("   Exa 1 2 2 mple") == "-Exa_1_2_2_mple", "This prints if this assert fails 4 (good for debugging!)"\n\n\n\ndef test_candidate():\n    check(fix_spaces)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
