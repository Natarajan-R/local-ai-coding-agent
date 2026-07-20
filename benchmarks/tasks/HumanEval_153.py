"""HumanEval task HumanEval_153"""
from pathlib import Path

TASK = """Implement the function 'Strongest_Extension' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def Strongest_Extension(class_name, extensions):
    \"\"\"You will be given the name of a class (a string) and a list of extensions.
    The extensions are to be used to load additional classes to the class. The
    strength of the extension is as follows: Let CAP be the number of the uppercase
    letters in the extension's name, and let SM be the number of lowercase letters 
    in the extension's name, the strength is given by the fraction CAP - SM. 
    You should find the strongest extension and return a string in this 
    format: ClassName.StrongestExtensionName.
    If there are two or more extensions with the same strength, you should
    choose the one that comes first in the list.
    For example, if you are given "Slices" as the class and a list of the
    extensions: ['SErviNGSliCes', 'Cheese', 'StuFfed'] then you should
    return 'Slices.SErviNGSliCes' since 'SErviNGSliCes' is the strongest extension 
    (its strength is -1).
    Example:
    for Strongest_Extension('my_class', ['AA', 'Be', 'CC']) == 'my_class.AA'
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef Strongest_Extension(class_name, extensions):\n    """You will be given the name of a class (a string) and a list of extensions.\n    The extensions are to be used to load additional classes to the class. The\n    strength of the extension is as follows: Let CAP be the number of the uppercase\n    letters in the extension\'s name, and let SM be the number of lowercase letters \n    in the extension\'s name, the strength is given by the fraction CAP - SM. \n    You should find the strongest extension and return a string in this \n    format: ClassName.StrongestExtensionName.\n    If there are two or more extensions with the same strength, you should\n    choose the one that comes first in the list.\n    For example, if you are given "Slices" as the class and a list of the\n    extensions: [\'SErviNGSliCes\', \'Cheese\', \'StuFfed\'] then you should\n    return \'Slices.SErviNGSliCes\' since \'SErviNGSliCes\' is the strongest extension \n    (its strength is -1).\n    Example:\n    for Strongest_Extension(\'my_class\', [\'AA\', \'Be\', \'CC\']) == \'my_class.AA\'\n    """\n',
    "test_solution.py": "from solution import Strongest_Extension\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('Watashi', ['tEN', 'niNE', 'eIGHt8OKe']) == 'Watashi.eIGHt8OKe'\n    assert candidate('Boku123', ['nani', 'NazeDa', 'YEs.WeCaNe', '32145tggg']) == 'Boku123.YEs.WeCaNe'\n    assert candidate('__YESIMHERE', ['t', 'eMptY', 'nothing', 'zeR00', 'NuLl__', '123NoooneB321']) == '__YESIMHERE.NuLl__'\n    assert candidate('K', ['Ta', 'TAR', 't234An', 'cosSo']) == 'K.TAR'\n    assert candidate('__HAHA', ['Tab', '123', '781345', '-_-']) == '__HAHA.123'\n    assert candidate('YameRore', ['HhAas', 'okIWILL123', 'WorkOut', 'Fails', '-_-']) == 'YameRore.okIWILL123'\n    assert candidate('finNNalLLly', ['Die', 'NowW', 'Wow', 'WoW']) == 'finNNalLLly.WoW'\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate('_', ['Bb', '91245']) == '_.Bb'\n    assert candidate('Sp', ['671235', 'Bb']) == 'Sp.671235'\n    \n\n\ndef test_candidate():\n    check(Strongest_Extension)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import Strongest_Extension\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('Watashi', ['tEN', 'niNE', 'eIGHt8OKe']) == 'Watashi.eIGHt8OKe'\n    assert candidate('Boku123', ['nani', 'NazeDa', 'YEs.WeCaNe', '32145tggg']) == 'Boku123.YEs.WeCaNe'\n    assert candidate('__YESIMHERE', ['t', 'eMptY', 'nothing', 'zeR00', 'NuLl__', '123NoooneB321']) == '__YESIMHERE.NuLl__'\n    assert candidate('K', ['Ta', 'TAR', 't234An', 'cosSo']) == 'K.TAR'\n    assert candidate('__HAHA', ['Tab', '123', '781345', '-_-']) == '__HAHA.123'\n    assert candidate('YameRore', ['HhAas', 'okIWILL123', 'WorkOut', 'Fails', '-_-']) == 'YameRore.okIWILL123'\n    assert candidate('finNNalLLly', ['Die', 'NowW', 'Wow', 'WoW']) == 'finNNalLLly.WoW'\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate('_', ['Bb', '91245']) == '_.Bb'\n    assert candidate('Sp', ['671235', 'Bb']) == 'Sp.671235'\n    \n\n\ndef test_candidate():\n    check(Strongest_Extension)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
