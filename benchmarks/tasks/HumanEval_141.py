"""HumanEval task HumanEval_141"""
from pathlib import Path

TASK = """Implement the function 'file_name_check' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def file_name_check(file_name):
    \"\"\"Create a function which takes a string representing a file's name, and returns
    'Yes' if the the file's name is valid, and returns 'No' otherwise.
    A file's name is considered to be valid if and only if all the following conditions 
    are met:
    - There should not be more than three digits ('0'-'9') in the file's name.
    - The file's name contains exactly one dot '.'
    - The substring before the dot should not be empty, and it starts with a letter from 
    the latin alphapet ('a'-'z' and 'A'-'Z').
    - The substring after the dot should be one of these: ['txt', 'exe', 'dll']
    Examples:
    file_name_check("example.txt") # => 'Yes'
    file_name_check("1example.dll") # => 'No' (the name should start with a latin alphapet letter)
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef file_name_check(file_name):\n    """Create a function which takes a string representing a file\'s name, and returns\n    \'Yes\' if the the file\'s name is valid, and returns \'No\' otherwise.\n    A file\'s name is considered to be valid if and only if all the following conditions \n    are met:\n    - There should not be more than three digits (\'0\'-\'9\') in the file\'s name.\n    - The file\'s name contains exactly one dot \'.\'\n    - The substring before the dot should not be empty, and it starts with a letter from \n    the latin alphapet (\'a\'-\'z\' and \'A\'-\'Z\').\n    - The substring after the dot should be one of these: [\'txt\', \'exe\', \'dll\']\n    Examples:\n    file_name_check("example.txt") # => \'Yes\'\n    file_name_check("1example.dll") # => \'No\' (the name should start with a latin alphapet letter)\n    """\n',
    "test_solution.py": 'from solution import file_name_check\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("example.txt") == \'Yes\'\n    assert candidate("1example.dll") == \'No\'\n    assert candidate(\'s1sdf3.asd\') == \'No\'\n    assert candidate(\'K.dll\') == \'Yes\'\n    assert candidate(\'MY16FILE3.exe\') == \'Yes\'\n    assert candidate(\'His12FILE94.exe\') == \'No\'\n    assert candidate(\'_Y.txt\') == \'No\'\n    assert candidate(\'?aREYA.exe\') == \'No\'\n    assert candidate(\'/this_is_valid.dll\') == \'No\'\n    assert candidate(\'this_is_valid.wow\') == \'No\'\n    assert candidate(\'this_is_valid.txt\') == \'Yes\'\n    assert candidate(\'this_is_valid.txtexe\') == \'No\'\n    assert candidate(\'#this2_i4s_5valid.ten\') == \'No\'\n    assert candidate(\'@this1_is6_valid.exe\') == \'No\'\n    assert candidate(\'this_is_12valid.6exe4.txt\') == \'No\'\n    assert candidate(\'all.exe.txt\') == \'No\'\n    assert candidate(\'I563_No.exe\') == \'Yes\'\n    assert candidate(\'Is3youfault.txt\') == \'Yes\'\n    assert candidate(\'no_one#knows.dll\') == \'Yes\'\n    assert candidate(\'1I563_Yes3.exe\') == \'No\'\n    assert candidate(\'I563_Yes3.txtt\') == \'No\'\n    assert candidate(\'final..txt\') == \'No\'\n    assert candidate(\'final132\') == \'No\'\n    assert candidate(\'_f4indsartal132.\') == \'No\'\n    \n        \n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'.txt\') == \'No\'\n    assert candidate(\'s.\') == \'No\'\n\n\n\ndef test_candidate():\n    check(file_name_check)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import file_name_check\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("example.txt") == \'Yes\'\n    assert candidate("1example.dll") == \'No\'\n    assert candidate(\'s1sdf3.asd\') == \'No\'\n    assert candidate(\'K.dll\') == \'Yes\'\n    assert candidate(\'MY16FILE3.exe\') == \'Yes\'\n    assert candidate(\'His12FILE94.exe\') == \'No\'\n    assert candidate(\'_Y.txt\') == \'No\'\n    assert candidate(\'?aREYA.exe\') == \'No\'\n    assert candidate(\'/this_is_valid.dll\') == \'No\'\n    assert candidate(\'this_is_valid.wow\') == \'No\'\n    assert candidate(\'this_is_valid.txt\') == \'Yes\'\n    assert candidate(\'this_is_valid.txtexe\') == \'No\'\n    assert candidate(\'#this2_i4s_5valid.ten\') == \'No\'\n    assert candidate(\'@this1_is6_valid.exe\') == \'No\'\n    assert candidate(\'this_is_12valid.6exe4.txt\') == \'No\'\n    assert candidate(\'all.exe.txt\') == \'No\'\n    assert candidate(\'I563_No.exe\') == \'Yes\'\n    assert candidate(\'Is3youfault.txt\') == \'Yes\'\n    assert candidate(\'no_one#knows.dll\') == \'Yes\'\n    assert candidate(\'1I563_Yes3.exe\') == \'No\'\n    assert candidate(\'I563_Yes3.txtt\') == \'No\'\n    assert candidate(\'final..txt\') == \'No\'\n    assert candidate(\'final132\') == \'No\'\n    assert candidate(\'_f4indsartal132.\') == \'No\'\n    \n        \n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate(\'.txt\') == \'No\'\n    assert candidate(\'s.\') == \'No\'\n\n\n\ndef test_candidate():\n    check(file_name_check)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
