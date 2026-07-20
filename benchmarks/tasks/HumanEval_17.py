"""HumanEval task HumanEval_17"""
from pathlib import Path

TASK = """Implement the function 'parse_music' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
from typing import List


def parse_music(music_string: str) -> List[int]:
    \"\"\" Input to this function is a string representing musical notes in a special ASCII format.
    Your task is to parse this string and return list of integers corresponding to how many beats does each
    not last.

    Here is a legend:
    'o' - whole note, lasts four beats
    'o|' - half note, lasts two beats
    '.|' - quater note, lasts one beat

    >>> parse_music('o o| .| o| o| .| .| .| .| o o')
    [4, 2, 1, 2, 2, 1, 1, 1, 1, 4, 4]
    \"\"\"

"""

FILES = {
    "solution.py": 'from typing import List\n\n\ndef parse_music(music_string: str) -> List[int]:\n    """ Input to this function is a string representing musical notes in a special ASCII format.\n    Your task is to parse this string and return list of integers corresponding to how many beats does each\n    not last.\n\n    Here is a legend:\n    \'o\' - whole note, lasts four beats\n    \'o|\' - half note, lasts two beats\n    \'.|\' - quater note, lasts one beat\n\n    >>> parse_music(\'o o| .| o| o| .| .| .| .| o o\')\n    [4, 2, 1, 2, 2, 1, 1, 1, 1, 4, 4]\n    """\n',
    "test_solution.py": "from solution import parse_music\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == []\n    assert candidate('o o o o') == [4, 4, 4, 4]\n    assert candidate('.| .| .| .|') == [1, 1, 1, 1]\n    assert candidate('o| o| .| .| o o o o') == [2, 2, 1, 1, 4, 4, 4, 4]\n    assert candidate('o| .| o| .| o o| o o|') == [2, 1, 2, 1, 4, 2, 4, 2]\n\n\ndef test_candidate():\n    check(parse_music)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import parse_music\n\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate('') == []\n    assert candidate('o o o o') == [4, 4, 4, 4]\n    assert candidate('.| .| .| .|') == [1, 1, 1, 1]\n    assert candidate('o| o| .| .| o o o o') == [2, 2, 1, 1, 4, 4, 4, 4]\n    assert candidate('o| .| o| .| o o| o o|') == [2, 1, 2, 1, 4, 2, 4, 2]\n\n\ndef test_candidate():\n    check(parse_music)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
