"""HumanEval task HumanEval_38"""
from pathlib import Path

TASK = """Implement the function 'decode_cyclic' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:


def encode_cyclic(s: str):
    \"\"\"
    returns encoded string by cycling groups of three characters.
    \"\"\"
    # split string to groups. Each of length 3.
    groups = [s[(3 * i):min((3 * i + 3), len(s))] for i in range((len(s) + 2) // 3)]
    # cycle elements in each group. Unless group has fewer elements than 3.
    groups = [(group[1:] + group[0]) if len(group) == 3 else group for group in groups]
    return "".join(groups)


def decode_cyclic(s: str):
    \"\"\"
    takes as input string encoded with encode_cyclic function. Returns decoded string.
    \"\"\"

"""

FILES = {
    "solution.py": '\n\ndef encode_cyclic(s: str):\n    """\n    returns encoded string by cycling groups of three characters.\n    """\n    # split string to groups. Each of length 3.\n    groups = [s[(3 * i):min((3 * i + 3), len(s))] for i in range((len(s) + 2) // 3)]\n    # cycle elements in each group. Unless group has fewer elements than 3.\n    groups = [(group[1:] + group[0]) if len(group) == 3 else group for group in groups]\n    return "".join(groups)\n\n\ndef decode_cyclic(s: str):\n    """\n    takes as input string encoded with encode_cyclic function. Returns decoded string.\n    """\n',
    "test_solution.py": "from solution import decode_cyclic\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    from random import randint, choice\n    import string\n\n    letters = string.ascii_lowercase\n    for _ in range(100):\n        str = ''.join(choice(letters) for i in range(randint(10, 20)))\n        encoded_str = encode_cyclic(str)\n        assert candidate(encoded_str) == str\n\n\n\ndef test_candidate():\n    check(decode_cyclic)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import decode_cyclic\n\n\nMETADATA = {}\n\n\ndef check(candidate):\n    from random import randint, choice\n    import string\n\n    letters = string.ascii_lowercase\n    for _ in range(100):\n        str = ''.join(choice(letters) for i in range(randint(10, 20)))\n        encoded_str = encode_cyclic(str)\n        assert candidate(encoded_str) == str\n\n\n\ndef test_candidate():\n    check(decode_cyclic)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
