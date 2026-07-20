"""HumanEval task HumanEval_124"""
from pathlib import Path

TASK = """Implement the function 'valid_date' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:

def valid_date(date):
    \"\"\"You have to write a function which validates a given date string and
    returns True if the date is valid otherwise False.
    The date is valid if all of the following rules are satisfied:
    1. The date string is not empty.
    2. The number of days is not less than 1 or higher than 31 days for months 1,3,5,7,8,10,12. And the number of days is not less than 1 or higher than 30 days for months 4,6,9,11. And, the number of days is not less than 1 or higher than 29 for the month 2.
    3. The months should not be less than 1 or higher than 12.
    4. The date should be in the format: mm-dd-yyyy

    for example: 
    valid_date('03-11-2000') => True

    valid_date('15-01-2012') => False

    valid_date('04-0-2040') => False

    valid_date('06-04-2020') => True

    valid_date('06/04/2020') => False
    \"\"\"

"""

FILES = {
    "solution.py": '\ndef valid_date(date):\n    """You have to write a function which validates a given date string and\n    returns True if the date is valid otherwise False.\n    The date is valid if all of the following rules are satisfied:\n    1. The date string is not empty.\n    2. The number of days is not less than 1 or higher than 31 days for months 1,3,5,7,8,10,12. And the number of days is not less than 1 or higher than 30 days for months 4,6,9,11. And, the number of days is not less than 1 or higher than 29 for the month 2.\n    3. The months should not be less than 1 or higher than 12.\n    4. The date should be in the format: mm-dd-yyyy\n\n    for example: \n    valid_date(\'03-11-2000\') => True\n\n    valid_date(\'15-01-2012\') => False\n\n    valid_date(\'04-0-2040\') => False\n\n    valid_date(\'06-04-2020\') => True\n\n    valid_date(\'06/04/2020\') => False\n    """\n',
    "test_solution.py": "from solution import valid_date\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('03-11-2000') == True\n\n    assert candidate('15-01-2012') == False\n\n    assert candidate('04-0-2040') == False\n\n    assert candidate('06-04-2020') == True\n\n    assert candidate('01-01-2007') == True\n\n    assert candidate('03-32-2011') == False\n\n    assert candidate('') == False\n\n    assert candidate('04-31-3000') == False\n\n    assert candidate('06-06-2005') == True\n\n    assert candidate('21-31-2000') == False\n\n    assert candidate('04-12-2003') == True\n\n    assert candidate('04122003') == False\n\n    assert candidate('20030412') == False\n\n    assert candidate('2003-04') == False\n\n    assert candidate('2003-04-12') == False\n\n    assert candidate('04-2003') == False\n\n\ndef test_candidate():\n    check(valid_date)\n"
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = "from solution import valid_date\ndef check(candidate):\n\n    # Check some simple cases\n    assert candidate('03-11-2000') == True\n\n    assert candidate('15-01-2012') == False\n\n    assert candidate('04-0-2040') == False\n\n    assert candidate('06-04-2020') == True\n\n    assert candidate('01-01-2007') == True\n\n    assert candidate('03-32-2011') == False\n\n    assert candidate('') == False\n\n    assert candidate('04-31-3000') == False\n\n    assert candidate('06-06-2005') == True\n\n    assert candidate('21-31-2000') == False\n\n    assert candidate('04-12-2003') == True\n\n    assert candidate('04122003') == False\n\n    assert candidate('20030412') == False\n\n    assert candidate('2003-04') == False\n\n    assert candidate('2003-04-12') == False\n\n    assert candidate('04-2003') == False\n\n\ndef test_candidate():\n    check(valid_date)\n"
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
