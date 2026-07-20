"""HumanEval task HumanEval_148"""
from pathlib import Path

TASK = """Implement the function 'bf' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def bf(planet1, planet2):
    '''
    There are eight planets in our solar system: the closerst to the Sun 
    is Mercury, the next one is Venus, then Earth, Mars, Jupiter, Saturn, 
    Uranus, Neptune.
    Write a function that takes two planet names as strings planet1 and planet2. 
    The function should return a tuple containing all planets whose orbits are 
    located between the orbit of planet1 and the orbit of planet2, sorted by 
    the proximity to the sun. 
    The function should return an empty tuple if planet1 or planet2
    are not correct planet names. 
    Examples
    bf("Jupiter", "Neptune") ==> ("Saturn", "Uranus")
    bf("Earth", "Mercury") ==> ("Venus")
    bf("Mercury", "Uranus") ==> ("Venus", "Earth", "Mars", "Jupiter", "Saturn")
    '''

"""

FILES = {
    "solution.py": '\ndef bf(planet1, planet2):\n    \'\'\'\n    There are eight planets in our solar system: the closerst to the Sun \n    is Mercury, the next one is Venus, then Earth, Mars, Jupiter, Saturn, \n    Uranus, Neptune.\n    Write a function that takes two planet names as strings planet1 and planet2. \n    The function should return a tuple containing all planets whose orbits are \n    located between the orbit of planet1 and the orbit of planet2, sorted by \n    the proximity to the sun. \n    The function should return an empty tuple if planet1 or planet2\n    are not correct planet names. \n    Examples\n    bf("Jupiter", "Neptune") ==> ("Saturn", "Uranus")\n    bf("Earth", "Mercury") ==> ("Venus")\n    bf("Mercury", "Uranus") ==> ("Venus", "Earth", "Mars", "Jupiter", "Saturn")\n    \'\'\'\n',
    "test_solution.py": 'from solution import bf\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("Jupiter", "Neptune") == ("Saturn", "Uranus"), "First test error: " + str(len(candidate("Jupiter", "Neptune")))      \n    assert candidate("Earth", "Mercury") == ("Venus",), "Second test error: " + str(candidate("Earth", "Mercury"))  \n    assert candidate("Mercury", "Uranus") == ("Venus", "Earth", "Mars", "Jupiter", "Saturn"), "Third test error: " + str(candidate("Mercury", "Uranus"))      \n    assert candidate("Neptune", "Venus") == ("Earth", "Mars", "Jupiter", "Saturn", "Uranus"), "Fourth test error: " + str(candidate("Neptune", "Venus"))  \n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("Earth", "Earth") == ()\n    assert candidate("Mars", "Earth") == ()\n    assert candidate("Jupiter", "Makemake") == ()\n\n\n\ndef test_candidate():\n    check(bf)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import bf\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate("Jupiter", "Neptune") == ("Saturn", "Uranus"), "First test error: " + str(len(candidate("Jupiter", "Neptune")))      \n    assert candidate("Earth", "Mercury") == ("Venus",), "Second test error: " + str(candidate("Earth", "Mercury"))  \n    assert candidate("Mercury", "Uranus") == ("Venus", "Earth", "Mars", "Jupiter", "Saturn"), "Third test error: " + str(candidate("Mercury", "Uranus"))      \n    assert candidate("Neptune", "Venus") == ("Earth", "Mars", "Jupiter", "Saturn", "Uranus"), "Fourth test error: " + str(candidate("Neptune", "Venus"))  \n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate("Earth", "Earth") == ()\n    assert candidate("Mars", "Earth") == ()\n    assert candidate("Jupiter", "Makemake") == ()\n\n\n\ndef test_candidate():\n    check(bf)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
