"""HumanEval task HumanEval_162"""
from pathlib import Path

TASK = """Implement the function 'string_to_md5' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def string_to_md5(text):
    \"\"\"
    Given a string 'text', return its md5 hash equivalent string.
    If 'text' is an empty string, return None.

    >>> string_to_md5('Hello world') == '3e25960a79dbc69b674cd4ec67a72c62'
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef string_to_md5(text):\n    """\n    Given a string \'text\', return its md5 hash equivalent string.\n    If \'text\' is an empty string, return None.\n\n    >>> string_to_md5(\'Hello world\') == \'3e25960a79dbc69b674cd4ec67a72c62\'\n    """\n',
    "test_solution.py": "from solution import string_to_md5\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('Hello world') == '3e25960a79dbc69b674cd4ec67a72c62'\n    assert candidate('') == None\n    assert candidate('A B C') == '0ef78513b0cb8cef12743f5aeb35f888'\n    assert candidate('password') == '5f4dcc3b5aa765d61d8327deb882cf99'\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(string_to_md5)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import string_to_md5\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('Hello world') == '3e25960a79dbc69b674cd4ec67a72c62'\n    assert candidate('') == None\n    assert candidate('A B C') == '0ef78513b0cb8cef12743f5aeb35f888'\n    assert candidate('password') == '5f4dcc3b5aa765d61d8327deb882cf99'\n\n    # Check some edge cases that are easy to work out by hand.\n    assert True\n\n\n\ndef test_candidate():\n    check(string_to_md5)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
