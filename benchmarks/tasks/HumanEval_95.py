"""HumanEval task HumanEval_95"""
from pathlib import Path

TASK = """Implement the function 'check_dict_case' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def check_dict_case(dict):
    \"\"\"
    Given a dictionary, return True if all keys are strings in lower 
    case or all keys are strings in upper case, else return False.
    The function should return False is the given dictionary is empty.
    Examples:
    check_dict_case({"a":"apple", "b":"banana"}) should return True.
    check_dict_case({"a":"apple", "A":"banana", "B":"banana"}) should return False.
    check_dict_case({"a":"apple", 8:"banana", "a":"apple"}) should return False.
    check_dict_case({"Name":"John", "Age":"36", "City":"Houston"}) should return False.
    check_dict_case({"STATE":"NC", "ZIP":"12345" }) should return True.
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef check_dict_case(dict):\n    """\n    Given a dictionary, return True if all keys are strings in lower \n    case or all keys are strings in upper case, else return False.\n    The function should return False is the given dictionary is empty.\n    Examples:\n    check_dict_case({"a":"apple", "b":"banana"}) should return True.\n    check_dict_case({"a":"apple", "A":"banana", "B":"banana"}) should return False.\n    check_dict_case({"a":"apple", 8:"banana", "a":"apple"}) should return False.\n    check_dict_case({"Name":"John", "Age":"36", "City":"Houston"}) should return False.\n    check_dict_case({"STATE":"NC", "ZIP":"12345" }) should return True.\n    """\n',
    "test_solution.py": 'from solution import check_dict_case\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate({"p":"pineapple", "b":"banana"}) == True, "First test error: " + str(candidate({"p":"pineapple", "b":"banana"}))\n    assert candidate({"p":"pineapple", "A":"banana", "B":"banana"}) == False, "Second test error: " + str(candidate({"p":"pineapple", "A":"banana", "B":"banana"}))\n    assert candidate({"p":"pineapple", 5:"banana", "a":"apple"}) == False, "Third test error: " + str(candidate({"p":"pineapple", 5:"banana", "a":"apple"}))\n    assert candidate({"Name":"John", "Age":"36", "City":"Houston"}) == False, "Fourth test error: " + str(candidate({"Name":"John", "Age":"36", "City":"Houston"}))\n    assert candidate({"STATE":"NC", "ZIP":"12345" }) == True, "Fifth test error: " + str(candidate({"STATE":"NC", "ZIP":"12345" }))      \n    assert candidate({"fruit":"Orange", "taste":"Sweet" }) == True, "Fourth test error: " + str(candidate({"fruit":"Orange", "taste":"Sweet" }))      \n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate({}) == False, "1st edge test error: " + str(candidate({}))\n\n\n\ndef test_candidate():\n    check(check_dict_case)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = 'from solution import check_dict_case\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate({"p":"pineapple", "b":"banana"}) == True, "First test error: " + str(candidate({"p":"pineapple", "b":"banana"}))\n    assert candidate({"p":"pineapple", "A":"banana", "B":"banana"}) == False, "Second test error: " + str(candidate({"p":"pineapple", "A":"banana", "B":"banana"}))\n    assert candidate({"p":"pineapple", 5:"banana", "a":"apple"}) == False, "Third test error: " + str(candidate({"p":"pineapple", 5:"banana", "a":"apple"}))\n    assert candidate({"Name":"John", "Age":"36", "City":"Houston"}) == False, "Fourth test error: " + str(candidate({"Name":"John", "Age":"36", "City":"Houston"}))\n    assert candidate({"STATE":"NC", "ZIP":"12345" }) == True, "Fifth test error: " + str(candidate({"STATE":"NC", "ZIP":"12345" }))      \n    assert candidate({"fruit":"Orange", "taste":"Sweet" }) == True, "Fourth test error: " + str(candidate({"fruit":"Orange", "taste":"Sweet" }))      \n\n\n    # Check some edge cases that are easy to work out by hand.\n    assert candidate({}) == False, "1st edge test error: " + str(candidate({}))\n\n\n\ndef test_candidate():\n    check(check_dict_case)\n'
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
