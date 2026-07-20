"""HumanEval task HumanEval_50"""
from pathlib import Path

TASK = """Implement the function 'decode_shift' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def encode_shift(s: str):
    \"\"\"
    returns encoded string by shifting every character by 5 in the alphabet.
    \"\"\"
    return "".join([chr(((ord(ch) + 5 - ord("a")) % 26) + ord("a")) for ch in s])


def decode_shift(s: str):
    \"\"\"
    takes as input string encoded with encode_shift function. Returns decoded string.
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef encode_shift(s: str):\n    """\n    returns encoded string by shifting every character by 5 in the alphabet.\n    """\n    return "".join([chr(((ord(ch) + 5 - ord("a")) % 26) + ord("a")) for ch in s])\n\n\ndef decode_shift(s: str):\n    """\n    takes as input string encoded with encode_shift function. Returns decoded string.\n    """\n',
    "test_solution.py": "from solution import decode_shift\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    from random import randint, choice\n    import copy\n    import string\n\n    letters = string.ascii_lowercase\n    for _ in range(100):\n        str = ''.join(choice(letters) for i in range(randint(10, 20)))\n        encoded_str = encode_shift(str)\n        assert candidate(copy.deepcopy(encoded_str)) == str\n\n\n\ndef test_candidate():\n    check(decode_shift)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import decode_shift\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    from random import randint, choice\n    import copy\n    import string\n\n    letters = string.ascii_lowercase\n    for _ in range(100):\n        str = ''.join(choice(letters) for i in range(randint(10, 20)))\n        encoded_str = encode_shift(str)\n        assert candidate(copy.deepcopy(encoded_str)) == str\n\n\n\ndef test_candidate():\n    check(decode_shift)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
