"""HumanEval task HumanEval_56"""
from pathlib import Path

TASK = """Implement the function 'correct_bracketing' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def correct_bracketing(brackets: str):
    \"\"\" brackets is a string of "<" and ">".
    return True if every opening bracket has a corresponding closing bracket.

    >>> correct_bracketing("<")
    False
    >>> correct_bracketing("<>")
    True
    >>> correct_bracketing("<<><>>")
    True
    >>> correct_bracketing("><<>")
    False
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef correct_bracketing(brackets: str):\n    """ brackets is a string of "<" and ">".\n    return True if every opening bracket has a corresponding closing bracket.\n\n    >>> correct_bracketing("<")\n    False\n    >>> correct_bracketing("<>")\n    True\n    >>> correct_bracketing("<<><>>")\n    True\n    >>> correct_bracketing("><<>")\n    False\n    """\n',
    "test_solution.py": 'from solution import correct_bracketing\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate("<>")\n    assert candidate("<<><>>")\n    assert candidate("<><><<><>><>")\n    assert candidate("<><><<<><><>><>><<><><<>>>")\n    assert not candidate("<<<><>>>>")\n    assert not candidate("><<>")\n    assert not candidate("<")\n    assert not candidate("<<<<")\n    assert not candidate(">")\n    assert not candidate("<<>")\n    assert not candidate("<><><<><>><>><<>")\n    assert not candidate("<><><<><>><>>><>")\n\n\n\ndef test_candidate():\n    check(correct_bracketing)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import correct_bracketing\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    assert candidate("<>")\n    assert candidate("<<><>>")\n    assert candidate("<><><<><>><>")\n    assert candidate("<><><<<><><>><>><<><><<>>>")\n    assert not candidate("<<<><>>>>")\n    assert not candidate("><<>")\n    assert not candidate("<")\n    assert not candidate("<<<<")\n    assert not candidate(">")\n    assert not candidate("<<>")\n    assert not candidate("<><><<><>><>><<>")\n    assert not candidate("<><><<><>><>>><>")\n\n\n\ndef test_candidate():\n    check(correct_bracketing)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
