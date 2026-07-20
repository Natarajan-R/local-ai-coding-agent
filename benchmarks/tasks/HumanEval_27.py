"""HumanEval task HumanEval_27"""
from pathlib import Path

TASK = """Implement the function 'flip_case' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def flip_case(string: str) -> str:
    \"\"\" For a given string, flip lowercase characters to uppercase and uppercase to lowercase.
    >>> flip_case('Hello')
    'hELLO'
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef flip_case(string: str) -> str:\n    """ For a given string, flip lowercase characters to uppercase and uppercase to lowercase.\n    >>> flip_case(\'Hello\')\n    \'hELLO\'\n    """\n',
    "test_solution.py": "from solution import flip_case\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == ''\n    assert candidate('Hello!') == 'hELLO!'\n    assert candidate('These violent delights have violent ends') == 'tHESE VIOLENT DELIGHTS HAVE VIOLENT ENDS'\n\n\ndef test_candidate():\n    check(flip_case)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import flip_case\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == ''\n    assert candidate('Hello!') == 'hELLO!'\n    assert candidate('These violent delights have violent ends') == 'tHESE VIOLENT DELIGHTS HAVE VIOLENT ENDS'\n\n\ndef test_candidate():\n    check(flip_case)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
